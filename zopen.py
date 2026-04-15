#!/usr/bin/env python3
"""
zopen - Smart file opener

Opens files using the appropriate application based on MIME type (auto-detected or
explicitly specified) or file extension. The MIME type takes precedence over the
extension when both would match, unless overridden by config.

Configuration is loaded from (in order, later entries override earlier):
  1. Built-in defaults
  2. /opt/etc/zopen/config.toml   (system-wide config, path via $ZOPEN_SYSCONFDIR)
  3. ~/.config/zopen/config.toml   (user global config)
  4. ./.zopen.toml                 (project-local config, overrides global)
  5. --config FILE                (ad-hoc override on the command line)

Falls back to xdg-open when no explicit mapping matches.
Use --install-alias to create a 'zo' shortcut in a non-conflicting location.
Use --map FILE to interactively update the MIME/extension → application mapping.
"""

from __future__ import annotations

import argparse
import datetime
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# A single config layer: (parsed data dict, human-readable source label)
ConfigLayer = tuple[dict[str, Any], str]

try:
    import tomllib
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        sys.exit("tomllib not available; upgrade to Python 3.11+ or: pip install tomli")

try:
    import magic as _libmagic  # python-magic (wraps libmagic)

    _HAVE_LIBMAGIC = True
except ImportError:
    _HAVE_LIBMAGIC = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_NAME = "zopen"
APP_VERSION = "0.6.4"

# Candidate directories for the 'ed' symlink alias, tried in order.
# These are all user-accessible or local-admin locations that do not
# overlap with distro-managed paths such as /usr/bin.
_ALIAS_NAME = "zo"
_ALIAS_CANDIDATES: list[Path] = [
    Path.home() / ".local" / "bin",  # XDG user bin (pip --user default)
    Path("/opt/bin"),  # site-local optional programs
    Path("/usr/local/bin"),  # locally-administered programs
]

# Bundled defaults — used when no config file exists.
# Values are intentionally minimal so that $VISUAL / $EDITOR take over when
# no explicit mapping has been configured.
# Built-in defaults used when no config file is found at all.
# Minimal: just set the fallback to xdg-open so any file type is handled by
# the platform's own association database.  Rich per-type overrides live in
# _SYSTEM_CONFIG_TOML (installed to /opt/etc/zopen/config.toml).
_DEFAULT_CONFIG_TOML = """\
[defaults]
app = "xdg-open"
prefer_mime = true
"""

# System-level config installed to /opt/etc/zopen/config.toml.
# Maps common file types to the standard Ubuntu 24.04 LTS desktop applications.
# Users override individual entries in ~/.config/zopen/config.toml.
_SYSTEM_CONFIG_TOML = """\
# zopen — system-wide configuration
# Installed to /opt/etc/zopen/config.toml
#
# Generated for Ubuntu 24.04 LTS (Noble Numbat).
# Default applications follow the Ubuntu 24.04 default desktop suite.
#
# Override any entry per-user in:  ~/.config/zopen/config.toml
# Override per-project in:         ./.zopen.toml
#
# App values:
#   Plain command:  "evince", "libreoffice --writer", "code"
#   Sentinel:       "$EDITOR"   →  resolved via $VISUAL → $EDITOR → vi
#   Fallback:       "xdg-open"  →  delegate to the platform association database

[defaults]
app         = "xdg-open"
prefer_mime = true

# ── Text & source code ───────────────────────────────────────────────────────
# Text and code files are opened in the user's preferred terminal editor.
# Remove or override these entries to use a GUI editor instead.
[mime_types]
"text/plain"                    = "$EDITOR"
"text/x-python"                 = "$EDITOR"
"text/x-script.python"          = "$EDITOR"
"text/html"                     = "$EDITOR"
"text/css"                      = "$EDITOR"
"text/javascript"               = "$EDITOR"
"text/x-shellscript"            = "$EDITOR"
"text/x-sh"                     = "$EDITOR"
"text/x-csrc"                   = "$EDITOR"
"text/x-c++src"                 = "$EDITOR"
"text/x-java"                   = "$EDITOR"
"text/x-ruby"                   = "$EDITOR"
"text/x-go"                     = "$EDITOR"
"text/x-rust"                   = "$EDITOR"
"text/x-markdown"               = "$EDITOR"
"text/x-rst"                    = "$EDITOR"
"text/csv"                      = "libreoffice --calc"
"text/tab-separated-values"     = "libreoffice --calc"

# ── Structured data / config ─────────────────────────────────────────────────
"application/json"              = "$EDITOR"
"application/xml"               = "$EDITOR"
"application/toml"              = "$EDITOR"
"application/x-yaml"            = "$EDITOR"

# ── PDF & PostScript ─────────────────────────────────────────────────────────
# evince: GNOME document viewer, Ubuntu default PDF/PS viewer
"application/pdf"               = "evince"
"application/postscript"        = "evince"
"image/x-eps"                   = "evince"

# ── Office documents (LibreOffice — Ubuntu 24.04 default office suite) ───────
"application/msword"                                                        = "libreoffice --writer"
"application/vnd.openxmlformats-officedocument.wordprocessingml.document"  = "libreoffice --writer"
"application/vnd.oasis.opendocument.text"                                  = "libreoffice --writer"
"application/rtf"                                                           = "libreoffice --writer"

"application/vnd.ms-excel"                                                  = "libreoffice --calc"
"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"         = "libreoffice --calc"
"application/vnd.oasis.opendocument.spreadsheet"                            = "libreoffice --calc"

"application/vnd.ms-powerpoint"                                             = "libreoffice --impress"
"application/vnd.openxmlformats-officedocument.presentationml.presentation" = "libreoffice --impress"
"application/vnd.oasis.opendocument.presentation"                           = "libreoffice --impress"

# ── Images ───────────────────────────────────────────────────────────────────
# eog: Eye of GNOME — Ubuntu 24.04 default image viewer
"image/png"                     = "eog"
"image/jpeg"                    = "eog"
"image/gif"                     = "eog"
"image/webp"                    = "eog"
"image/bmp"                     = "eog"
"image/tiff"                    = "eog"
"image/x-icon"                  = "eog"
"image/heic"                    = "eog"
"image/heif"                    = "eog"
# inkscape: vector graphics editor (install: sudo apt install inkscape)
"image/svg+xml"                 = "inkscape"
# GIMP for raw/high-bit-depth editing (install: sudo apt install gimp)
# "image/x-xcf"                 = "gimp"

# ── Audio ────────────────────────────────────────────────────────────────────
# rhythmbox: Ubuntu 24.04 default music player
"audio/mpeg"                    = "rhythmbox"
"audio/ogg"                     = "rhythmbox"
"audio/flac"                    = "rhythmbox"
"audio/x-flac"                  = "rhythmbox"
"audio/wav"                     = "rhythmbox"
"audio/x-wav"                   = "rhythmbox"
"audio/mp4"                     = "rhythmbox"
"audio/aac"                     = "rhythmbox"
"audio/x-ms-wma"                = "rhythmbox"
"audio/opus"                    = "rhythmbox"

# ── Video ────────────────────────────────────────────────────────────────────
# totem: GNOME Videos — Ubuntu 24.04 default video player
"video/mp4"                     = "totem"
"video/x-matroska"              = "totem"
"video/x-msvideo"               = "totem"
"video/quicktime"               = "totem"
"video/webm"                    = "totem"
"video/x-ms-wmv"                = "totem"
"video/mpeg"                    = "totem"
"video/ogg"                     = "totem"
"video/3gpp"                    = "totem"

# ── Archives ─────────────────────────────────────────────────────────────────
# file-roller: GNOME Archive Manager — Ubuntu 24.04 default
"application/zip"               = "file-roller"
"application/x-tar"             = "file-roller"
"application/gzip"              = "file-roller"
"application/x-bzip2"           = "file-roller"
"application/x-xz"              = "file-roller"
"application/x-7z-compressed"   = "file-roller"
"application/x-rar-compressed"  = "file-roller"
"application/x-rar"             = "file-roller"
"application/x-compressed-tar"  = "file-roller"
"application/x-zstd-compressed-tar" = "file-roller"

# ── E-books ──────────────────────────────────────────────────────────────────
# foliate: modern e-book reader (install: sudo apt install foliate)
"application/epub+zip"          = "foliate"
"application/x-mobipocket-ebook" = "foliate"

# ── Extension mappings ───────────────────────────────────────────────────────
# These supplement MIME detection for files whose type is hard to detect.
[extensions]
# Text / source code
".txt"   = "$EDITOR"
".md"    = "$EDITOR"
".rst"   = "$EDITOR"
".py"    = "$EDITOR"
".pyi"   = "$EDITOR"
".js"    = "$EDITOR"
".mjs"   = "$EDITOR"
".cjs"   = "$EDITOR"
".ts"    = "$EDITOR"
".tsx"   = "$EDITOR"
".jsx"   = "$EDITOR"
".html"  = "$EDITOR"
".htm"   = "$EDITOR"
".css"   = "$EDITOR"
".scss"  = "$EDITOR"
".sass"  = "$EDITOR"
".less"  = "$EDITOR"
".json"  = "$EDITOR"
".jsonc" = "$EDITOR"
".xml"   = "$EDITOR"
".yaml"  = "$EDITOR"
".yml"   = "$EDITOR"
".toml"  = "$EDITOR"
".ini"   = "$EDITOR"
".cfg"   = "$EDITOR"
".conf"  = "$EDITOR"
".sh"    = "$EDITOR"
".bash"  = "$EDITOR"
".zsh"   = "$EDITOR"
".fish"  = "$EDITOR"
".c"     = "$EDITOR"
".h"     = "$EDITOR"
".cpp"   = "$EDITOR"
".cc"    = "$EDITOR"
".cxx"   = "$EDITOR"
".hpp"   = "$EDITOR"
".hxx"   = "$EDITOR"
".rs"    = "$EDITOR"
".go"    = "$EDITOR"
".java"  = "$EDITOR"
".kt"    = "$EDITOR"
".rb"    = "$EDITOR"
".php"   = "$EDITOR"
".sql"   = "$EDITOR"
".tf"    = "$EDITOR"
".lua"   = "$EDITOR"
".r"     = "$EDITOR"
".R"     = "$EDITOR"
".swift" = "$EDITOR"
".dart"  = "$EDITOR"

# Documents
".pdf"   = "evince"
".ps"    = "evince"
".eps"   = "evince"
".doc"   = "libreoffice --writer"
".docx"  = "libreoffice --writer"
".odt"   = "libreoffice --writer"
".rtf"   = "libreoffice --writer"
".xls"   = "libreoffice --calc"
".xlsx"  = "libreoffice --calc"
".ods"   = "libreoffice --calc"
".csv"   = "libreoffice --calc"
".ppt"   = "libreoffice --impress"
".pptx"  = "libreoffice --impress"
".odp"   = "libreoffice --impress"

# Images
".png"   = "eog"
".jpg"   = "eog"
".jpeg"  = "eog"
".gif"   = "eog"
".webp"  = "eog"
".bmp"   = "eog"
".tiff"  = "eog"
".tif"   = "eog"
".ico"   = "eog"
".heic"  = "eog"
".heif"  = "eog"
".svg"   = "inkscape"

# Audio
".mp3"   = "rhythmbox"
".ogg"   = "rhythmbox"
".flac"  = "rhythmbox"
".wav"   = "rhythmbox"
".m4a"   = "rhythmbox"
".aac"   = "rhythmbox"
".wma"   = "rhythmbox"
".opus"  = "rhythmbox"

# Video
".mp4"   = "totem"
".mkv"   = "totem"
".avi"   = "totem"
".mov"   = "totem"
".webm"  = "totem"
".wmv"   = "totem"
".mpg"   = "totem"
".mpeg"  = "totem"
".3gp"   = "totem"
".flv"   = "totem"

# Archives
".zip"   = "file-roller"
".tar"   = "file-roller"
".gz"    = "file-roller"
".bz2"   = "file-roller"
".xz"    = "file-roller"
".7z"    = "file-roller"
".rar"   = "file-roller"
".zst"   = "file-roller"

# E-books
".epub"  = "foliate"
".mobi"  = "foliate"
"""

# ---------------------------------------------------------------------------
# Dynamic user-config generation via XDG MIME defaults
# ---------------------------------------------------------------------------

# MIME types to probe for OS-installed default handlers, mapped to:
#   (fallback_cmd, [extensions_that_use_this_mime])
# Text/code types are intentionally absent — they always stay as $EDITOR.
_XDG_PROBE_MIMES: list[tuple[str, str, list[str]]] = [
    # Documents
    ("application/pdf", "evince", [".pdf"]),
    ("application/postscript", "evince", [".ps", ".eps"]),
    ("application/msword", "libreoffice --writer", [".doc"]),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "libreoffice --writer",
        [".docx"],
    ),
    ("application/vnd.oasis.opendocument.text", "libreoffice --writer", [".odt"]),
    ("application/rtf", "libreoffice --writer", [".rtf"]),
    ("application/vnd.ms-excel", "libreoffice --calc", [".xls"]),
    (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "libreoffice --calc",
        [".xlsx"],
    ),
    ("application/vnd.oasis.opendocument.spreadsheet", "libreoffice --calc", [".ods"]),
    ("text/csv", "libreoffice --calc", [".csv"]),
    ("application/vnd.ms-powerpoint", "libreoffice --impress", [".ppt"]),
    (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "libreoffice --impress",
        [".pptx"],
    ),
    (
        "application/vnd.oasis.opendocument.presentation",
        "libreoffice --impress",
        [".odp"],
    ),
    # Images
    ("image/png", "eog", [".png"]),
    ("image/jpeg", "eog", [".jpg", ".jpeg"]),
    ("image/gif", "eog", [".gif"]),
    ("image/webp", "eog", [".webp"]),
    ("image/bmp", "eog", [".bmp"]),
    ("image/tiff", "eog", [".tiff", ".tif"]),
    ("image/x-icon", "eog", [".ico"]),
    ("image/heic", "eog", [".heic", ".heif"]),
    ("image/svg+xml", "inkscape", [".svg"]),
    # Audio
    ("audio/mpeg", "rhythmbox", [".mp3"]),
    ("audio/ogg", "rhythmbox", [".ogg"]),
    ("audio/flac", "rhythmbox", [".flac"]),
    ("audio/x-flac", "rhythmbox", []),
    ("audio/wav", "rhythmbox", [".wav"]),
    ("audio/mp4", "rhythmbox", [".m4a"]),
    ("audio/aac", "rhythmbox", [".aac"]),
    ("audio/opus", "rhythmbox", [".opus"]),
    ("audio/x-ms-wma", "rhythmbox", [".wma"]),
    # Video
    ("video/mp4", "totem", [".mp4"]),
    ("video/x-matroska", "totem", [".mkv"]),
    ("video/x-msvideo", "totem", [".avi"]),
    ("video/quicktime", "totem", [".mov"]),
    ("video/webm", "totem", [".webm"]),
    ("video/x-ms-wmv", "totem", [".wmv"]),
    ("video/mpeg", "totem", [".mpg", ".mpeg"]),
    ("video/ogg", "totem", [".ogv"]),
    ("video/3gpp", "totem", [".3gp"]),
    # Archives
    ("application/zip", "file-roller", [".zip"]),
    ("application/x-tar", "file-roller", [".tar"]),
    ("application/gzip", "file-roller", [".gz"]),
    ("application/x-bzip2", "file-roller", [".bz2"]),
    ("application/x-xz", "file-roller", [".xz"]),
    ("application/x-7z-compressed", "file-roller", [".7z"]),
    ("application/x-rar", "file-roller", [".rar"]),
    ("application/x-rar-compressed", "file-roller", []),
    ("application/x-zstd-compressed-tar", "file-roller", [".zst"]),
    # E-books
    ("application/epub+zip", "foliate", [".epub"]),
    ("application/x-mobipocket-ebook", "foliate", [".mobi"]),
]

# TOML serialization regex
_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SENTINEL = "$EDITOR"


# ---------------------------------------------------------------------------
# Configuration Schema and Validation
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when configuration is invalid or malformed."""

    pass


class ConfigSchema:
    """Defines and validates the zopen configuration schema.

    The config schema consists of:
    - [defaults] section: global defaults (app, prefer_mime)
    - [mime_types] section: MIME type → app mappings
    - [extensions] section: file extension → app mappings
    """

    # Valid keys in [defaults] section with their types
    DEFAULTS_SCHEMA = {
        "app": str,
        "editor": str,  # Deprecated, maps to 'app'
        "prefer_mime": bool,
    }

    @staticmethod
    def validate_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize [defaults] section.

        Returns normalized defaults dict with type checking.
        Raises ConfigError on invalid values.
        """
        if not isinstance(defaults, dict):
            raise ConfigError(
                f"[defaults] must be a dict, got {type(defaults).__name__}"
            )

        normalized: dict[str, Any] = {}

        for key, value in defaults.items():
            expected_type = ConfigSchema.DEFAULTS_SCHEMA.get(key)
            if expected_type is None:
                # Unknown key - warn but allow (forward compatibility)
                continue

            if not isinstance(value, expected_type):
                raise ConfigError(
                    f"[defaults][{key!r}] must be {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

            # Map deprecated 'editor' to 'app'
            if key == "editor":
                if "app" not in normalized:
                    normalized["app"] = value
            else:
                normalized[key] = value

        return normalized

    @staticmethod
    def validate_mapping(section_name: str, mapping: dict[str, Any]) -> dict[str, str]:
        """Validate [mime_types] or [extensions] mapping section.

        Returns normalized mapping dict with type checking.
        Raises ConfigError on invalid values.
        """
        if not isinstance(mapping, dict):
            raise ConfigError(
                f"[{section_name}] must be a dict, got {type(mapping).__name__}"
            )

        normalized: dict[str, str] = {}

        for key, value in mapping.items():
            if not isinstance(key, str):
                raise ConfigError(
                    f"[{section_name}] key must be str, got {type(key).__name__}: {key!r}"
                )

            if not isinstance(value, str):
                raise ConfigError(
                    f"[{section_name}][{key!r}] value must be str, "
                    f"got {type(value).__name__}: {value!r}"
                )

            normalized[key] = value

        return normalized

    @staticmethod
    def validate_config(config: dict[str, Any]) -> dict[str, Any]:
        """Validate complete configuration.

        Returns normalized config with all sections validated.
        Raises ConfigError on invalid structure.
        """
        if not isinstance(config, dict):
            raise ConfigError(f"Config must be a dict, got {type(config).__name__}")

        validated: dict[str, Any] = {}

        # Validate [defaults] section
        if "defaults" in config:
            validated["defaults"] = ConfigSchema.validate_defaults(config["defaults"])
        else:
            validated["defaults"] = {}

        # Validate [mime_types] section
        if "mime_types" in config:
            validated["mime_types"] = ConfigSchema.validate_mapping(
                "mime_types", config["mime_types"]
            )
        else:
            validated["mime_types"] = {}

        # Validate [extensions] section
        if "extensions" in config:
            validated["extensions"] = ConfigSchema.validate_mapping(
                "extensions", config["extensions"]
            )
        else:
            validated["extensions"] = {}

        return validated


class ConfigDefaults:
    """Manages configuration default values and fallback chains."""

    # Built-in defaults that are always present
    BUILTIN_DEFAULTS = {
        "app": "xdg-open",
        "prefer_mime": True,
    }

    @staticmethod
    def get_default(key: str, fallback: Any = None) -> Any:
        """Get a built-in default value.

        Args:
            key: The default key to retrieve
            fallback: Value to return if key not found

        Returns:
            The default value, or fallback if not found
        """
        return ConfigDefaults.BUILTIN_DEFAULTS.get(key, fallback)

    @staticmethod
    def merge_with_defaults(config: dict[str, Any]) -> dict[str, Any]:
        """Merge config with built-in defaults, preferring config values.

        Ensures all required defaults are present even if not in config.
        """
        result = dict(ConfigDefaults.BUILTIN_DEFAULTS)
        if "defaults" in config:
            result.update(config["defaults"])
        return result

    @staticmethod
    def get_app_command(config: dict[str, Any]) -> str:
        """Get the fallback app command from config defaults.

        Returns config's app/editor setting, or xdg-open as last resort.
        """
        defaults = config.get("defaults", {})
        return defaults.get("app") or defaults.get("editor") or "xdg-open"

    @staticmethod
    def get_prefer_mime(config: dict[str, Any]) -> bool:
        """Get the prefer_mime setting from config defaults."""
        defaults = config.get("defaults", {})
        return defaults.get("prefer_mime", True)


class ConfigCache:
    """Simple in-memory cache for loaded configurations.

    Caches config files to avoid repeated I/O and parsing.
    """

    def __init__(self):
        self._cache: dict[Path | str, tuple[dict[str, Any], float]] = {}

    def get(self, key: Path | str) -> dict[str, Any] | None:
        """Get cached config, or None if not cached or expired.

        Currently never expires (could be enhanced with TTL).
        """
        if key in self._cache:
            config, _ = self._cache[key]
            return config
        return None

    def put(self, key: Path | str, config: dict[str, Any]) -> None:
        """Cache a configuration."""
        import time

        self._cache[key] = (config, time.time())

    def clear(self) -> None:
        """Clear all cached configurations."""
        self._cache.clear()

    def size(self) -> int:
        """Return number of cached items."""
        return len(self._cache)


class ConfigProvider:
    """High-level configuration provider with validation, defaults, and caching.

    Provides a unified interface for loading, validating, and caching configurations.
    """

    def __init__(self, use_cache: bool = True):
        """Initialize ConfigProvider.

        Args:
            use_cache: Whether to cache loaded configs (default: True)
        """
        self.use_cache = use_cache
        self.cache = ConfigCache() if use_cache else None

    def load_and_validate(self, config: dict[str, Any]) -> dict[str, Any]:
        """Load and validate a configuration.

        Args:
            config: Raw configuration dict (typically from TOML)

        Returns:
            Validated and normalized configuration

        Raises:
            ConfigError: If config is invalid
        """
        try:
            return ConfigSchema.validate_config(config)
        except ConfigError as e:
            raise ConfigError(f"Configuration validation failed: {e}")

    def merge_layers(self, layers: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple config layers (later layers override earlier).

        Args:
            layers: List of config dicts to merge

        Returns:
            Merged configuration
        """
        result: dict[str, Any] = {
            "defaults": dict(ConfigDefaults.BUILTIN_DEFAULTS),
            "mime_types": {},
            "extensions": {},
        }

        for config in layers:
            validated = self.load_and_validate(config)
            result["defaults"].update(validated.get("defaults", {}))
            result["mime_types"].update(validated.get("mime_types", {}))
            result["extensions"].update(validated.get("extensions", {}))

        return result

    def get_effective_value(
        self, config: dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """Get an effective config value from the merged config.

        Handles nested lookups like 'defaults.app' → config['defaults']['app'].
        """
        if "." in key:
            section, subkey = key.split(".", 1)
            return config.get(section, {}).get(subkey, default)
        return config.get(key, default)


# ---------------------------------------------------------------------------
# XDG Integration Module
# ---------------------------------------------------------------------------


class XdgIntegration:
    """Encapsulates all XDG Desktop Entry integration operations."""

    @staticmethod
    def parse_desktop_exec(desktop_path: Path) -> str | None:
        """Extract and clean the Exec command from a .desktop file."""
        try:
            for line in desktop_path.read_text(errors="replace").splitlines():
                if line.startswith("Exec="):
                    cmd = line[5:].strip()
                    # Remove field-code placeholders: %f %F %u %U %i %c %k …
                    cmd = re.sub(r"\s*%[a-zA-Z]", "", cmd).strip()
                    return cmd if cmd else None
        except OSError:
            pass
        return None

    @staticmethod
    def desktop_to_cmd(desktop_file: str) -> str | None:
        """Resolve a .desktop filename to its Exec command."""
        search_dirs = [
            Path.home() / ".local/share/applications",
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
        ]
        for d in search_dirs:
            p = d / desktop_file
            if p.exists():
                return XdgIntegration.parse_desktop_exec(p)
        return None

    @staticmethod
    def query_xdg_default(mime_type: str) -> str | None:
        """Return the resolved Exec command for *mime_type* via xdg-mime, or None."""
        try:
            result = subprocess.run(
                ["xdg-mime", "query", "default", mime_type],
                capture_output=True,
                text=True,
                timeout=3,
            )
            desktop_file = result.stdout.strip()
            if not desktop_file:
                return None
            return XdgIntegration.desktop_to_cmd(desktop_file)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    @staticmethod
    def query_all_xdg_apps(mime_type: str) -> tuple[str | None, list[str]]:
        """Return *(default_cmd, all_cmds)* for *mime_type* via ``gio mime``.

        *all_cmds* is ordered: the platform default application first, then every
        other registered application in the order ``gio`` reports them.  Entries
        that resolve to the same command string are deduplicated.

        Returns *(None, [])* when ``gio`` is unavailable or finds nothing.
        """
        try:
            result = subprocess.run(
                ["gio", "mime", mime_type],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None, []

        if result.returncode != 0:
            return None, []

        default_desktop: str | None = None
        all_desktops: list[str] = []
        in_list = False

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            m = re.match(r"Default application for .+:\s+(\S+\.desktop)", stripped)
            if m:
                default_desktop = m.group(1)
                continue
            if re.match(r"(Registered|Recommended) applications:", stripped):
                in_list = True
                continue
            if in_list and stripped.endswith(".desktop"):
                all_desktops.append(stripped)

        default_cmd = (
            XdgIntegration.desktop_to_cmd(default_desktop) if default_desktop else None
        )

        seen: set[str] = set()
        all_cmds: list[str] = []

        if default_cmd:
            all_cmds.append(default_cmd)
            seen.add(default_cmd)

        for desktop in all_desktops:
            if desktop == default_desktop:
                continue
            cmd = XdgIntegration.desktop_to_cmd(desktop)
            if cmd and cmd not in seen:
                all_cmds.append(cmd)
                seen.add(cmd)

        return default_cmd, all_cmds


# ---------------------------------------------------------------------------
# MIME Type Detection - Enhanced System
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod


class MimeDetectionResult:
    """Result of a MIME type detection attempt.

    Tracks detection result and metadata about the detection process.
    """

    def __init__(
        self,
        mime_type: str | None,
        source: str,
        confidence: float = 1.0,
        fallback: bool = False,
    ):
        """Initialize detection result.

        Args:
            mime_type: Detected MIME type, or None
            source: Name of detector that produced this result
            confidence: Confidence level (0.0 to 1.0)
            fallback: Whether this is from a fallback detector
        """
        self.mime_type = mime_type
        self.source = source
        self.confidence = max(0.0, min(1.0, confidence))
        self.fallback = fallback

    def is_valid(self) -> bool:
        """Return True if detection succeeded."""
        return self.mime_type is not None

    def __repr__(self) -> str:
        return (
            f"MimeDetectionResult(mime_type={self.mime_type!r}, "
            f"source={self.source!r}, confidence={self.confidence:.1f})"
        )


class MimeDetectionStrategy(ABC):
    """Abstract base for MIME detection strategies.

    Each strategy implements a specific MIME detection method
    (libmagic, file extensions, content sniffing, etc).
    """

    @abstractmethod
    def detect(self, path: Path) -> MimeDetectionResult | None:
        """Detect MIME type using this strategy.

        Returns MimeDetectionResult if detection succeeded, None if this
        strategy cannot determine the MIME type.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this detector strategy."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority order (higher number = higher priority, checked first)."""
        pass


class LibmagicDetectionStrategy(MimeDetectionStrategy):
    """MIME detection using libmagic (python-magic).

    Most accurate detection based on file magic numbers.
    Requires python-magic package.
    """

    @property
    def name(self) -> str:
        return "libmagic"

    @property
    def priority(self) -> int:
        return 100  # Highest priority - most reliable

    def detect(self, path: Path) -> MimeDetectionResult | None:
        """Detect using libmagic if available."""
        if not _HAVE_LIBMAGIC:
            return None

        try:
            mime = _libmagic.from_file(str(path), mime=True)
            if mime:
                return MimeDetectionResult(
                    mime, source=self.name, confidence=0.95, fallback=False
                )
        except Exception:
            pass

        return None


class ExtensionDetectionStrategy(MimeDetectionStrategy):
    """MIME detection based on file extension.

    Uses Python's mimetypes module for standard extensions.
    Fast but less accurate than content-based detection.
    """

    @property
    def name(self) -> str:
        return "extension"

    @property
    def priority(self) -> int:
        return 50  # Lower priority - less reliable

    def detect(self, path: Path) -> MimeDetectionResult | None:
        """Detect using file extension."""
        mime, _ = mimetypes.guess_type(str(path))
        if mime:
            return MimeDetectionResult(
                mime, source=self.name, confidence=0.70, fallback=False
            )
        return None


class CustomMappingDetectionStrategy(MimeDetectionStrategy):
    """MIME detection using custom extension mappings.

    Allows registering custom MIME type mappings for non-standard extensions.
    """

    def __init__(self, mappings: dict[str, str] | None = None):
        """Initialize with optional custom mappings.

        Args:
            mappings: Dict of {extension: mime_type}
        """
        self._mappings = mappings or {}

    @property
    def name(self) -> str:
        return "custom_mapping"

    @property
    def priority(self) -> int:
        return 75  # Between extension and libmagic

    def add_mapping(self, extension: str, mime_type: str) -> None:
        """Add or update a custom mapping."""
        if not extension.startswith("."):
            extension = "." + extension
        self._mappings[extension.lower()] = mime_type

    def detect(self, path: Path) -> MimeDetectionResult | None:
        """Detect using custom mappings."""
        suffix = path.suffix.lower()
        if suffix in self._mappings:
            return MimeDetectionResult(
                self._mappings[suffix],
                source=self.name,
                confidence=0.80,
                fallback=False,
            )
        return None


class MimeDetectionStatistics:
    """Tracks MIME detection statistics."""

    def __init__(self):
        self.total_detections = 0
        self.successful_detections = 0
        self.failed_detections = 0
        self.detections_by_strategy: dict[str, int] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def record_detection(
        self, result: MimeDetectionResult | None, strategy: str
    ) -> None:
        """Record a detection attempt."""
        self.total_detections += 1
        if result and result.is_valid():
            self.successful_detections += 1
        else:
            self.failed_detections += 1
        self.detections_by_strategy[strategy] = (
            self.detections_by_strategy.get(strategy, 0) + 1
        )

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1

    def get_success_rate(self) -> float:
        """Get detection success rate (0.0 to 1.0)."""
        if self.total_detections == 0:
            return 0.0
        return self.successful_detections / self.total_detections

    def __repr__(self) -> str:
        return (
            f"MimeDetectionStatistics("
            f"total={self.total_detections}, "
            f"successful={self.successful_detections}, "
            f"success_rate={self.get_success_rate():.1%}, "
            f"cache_hits={self.cache_hits}, "
            f"cache_misses={self.cache_misses}"
            f")"
        )


class MimeDetectionCache:
    """Simple cache for MIME detection results."""

    def __init__(self, max_size: int = 1000):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached results
        """
        self.max_size = max_size
        self._cache: dict[Path, str] = {}

    def get(self, path: Path) -> str | None:
        """Get cached MIME type for path."""
        # Normalize path for consistent caching
        normalized = path.resolve()
        return self._cache.get(normalized)

    def put(self, path: Path, mime_type: str) -> None:
        """Cache a MIME type result."""
        normalized = path.resolve()
        if len(self._cache) >= self.max_size:
            # Simple eviction: remove first item (FIFO)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[normalized] = mime_type

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)


class EnhancedMimeDetector:
    """Enhanced MIME type detector with strategy pattern and caching.

    Supports multiple detection strategies with priority ordering,
    caching, and statistics tracking.
    """

    def __init__(self, use_cache: bool = True, enable_stats: bool = False):
        """Initialize detector.

        Args:
            use_cache: Whether to cache detection results
            enable_stats: Whether to track detection statistics
        """
        self.use_cache = use_cache
        self.enable_stats = enable_stats
        self.cache = MimeDetectionCache() if use_cache else None
        self.stats = MimeDetectionStatistics() if enable_stats else None
        self._strategies: list[MimeDetectionStrategy] = []
        self._setup_default_strategies()

    def _setup_default_strategies(self) -> None:
        """Set up default detection strategies."""
        self.add_strategy(LibmagicDetectionStrategy())
        self.add_strategy(ExtensionDetectionStrategy())

    def add_strategy(self, strategy: MimeDetectionStrategy) -> None:
        """Add a detection strategy.

        Strategies are sorted by priority (higher priority checked first).
        """
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority, reverse=True)

    def remove_strategy(self, name: str) -> bool:
        """Remove a strategy by name. Returns True if found and removed."""
        original_len = len(self._strategies)
        self._strategies = [s for s in self._strategies if s.name != name]
        return len(self._strategies) < original_len

    def detect(self, path: Path) -> str | None:
        """Detect MIME type using all strategies in priority order.

        Returns the first successful MIME type detected, or None if all
        strategies fail.
        """
        if not path.exists():
            return None

        # Check cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(path)
            if cached:
                if self.enable_stats and self.stats:
                    self.stats.record_cache_hit()
                return cached

        if self.enable_stats and self.stats:
            self.stats.record_cache_miss()

        # Try each strategy in priority order
        for strategy in self._strategies:
            result = strategy.detect(path)
            if self.enable_stats and self.stats:
                self.stats.record_detection(result, strategy.name)
            if result and result.is_valid():
                # Cache successful result
                if self.use_cache and self.cache:
                    self.cache.put(path, result.mime_type)
                return result.mime_type

        return None

    def detect_with_details(self, path: Path) -> MimeDetectionResult | None:
        """Detect MIME type and return detailed result.

        Returns MimeDetectionResult with source, confidence, and other metadata.
        """
        if not path.exists():
            return None

        # Try each strategy in priority order
        for strategy in self._strategies:
            result = strategy.detect(path)
            if self.enable_stats and self.stats:
                self.stats.record_detection(result, strategy.name)
            if result and result.is_valid():
                return result

        return None

    def get_statistics(self) -> MimeDetectionStatistics | None:
        """Get detection statistics if enabled."""
        return self.stats

    def clear_cache(self) -> None:
        """Clear detection cache."""
        if self.cache:
            self.cache.clear()

    def get_strategy_info(self) -> list[dict[str, Any]]:
        """Get information about registered strategies."""
        return [
            {
                "name": s.name,
                "priority": s.priority,
                "available": isinstance(s, LibmagicDetectionStrategy)
                and _HAVE_LIBMAGIC
                or True,
            }
            for s in self._strategies
        ]


# Global instance of enhanced detector
_enhanced_detector = EnhancedMimeDetector(use_cache=True, enable_stats=False)


class MimeDetector:
    """Encapsulates MIME type detection logic with enhanced strategy support.

    Uses EnhancedMimeDetector internally while maintaining full backward compatibility.
    Provides both simple detection and advanced features like caching and statistics.
    """

    # Global enhanced detector instance (created lazily)
    _enhanced_detector: EnhancedMimeDetector | None = None
    _simple_detector: EnhancedMimeDetector | None = None

    @classmethod
    def _get_enhanced_detector(
        cls, use_cache: bool = True, enable_stats: bool = False
    ) -> EnhancedMimeDetector:
        """Get or create enhanced detector instance.

        For performance, we cache the default configuration detector.
        """
        if use_cache and not enable_stats:
            # Default case: with caching, no stats
            if cls._simple_detector is None:
                cls._simple_detector = EnhancedMimeDetector(
                    use_cache=True, enable_stats=False
                )
            return cls._simple_detector
        else:
            # Non-default case: create new instance
            return EnhancedMimeDetector(use_cache=use_cache, enable_stats=enable_stats)

    @staticmethod
    def detect(path: Path) -> str | None:
        """Return the MIME type of *path*, or *None* if it cannot be determined.

        Uses libmagic if available, falls back to mimetypes stdlib.
        Results are cached for performance.
        """
        detector = MimeDetector._get_enhanced_detector(
            use_cache=True, enable_stats=False
        )
        return detector.detect(path)

    @classmethod
    def detect_with_details(
        cls, path: Path, use_cache: bool = True
    ) -> MimeDetectionResult | None:
        """Detect MIME type and return detailed result.

        Returns a MimeDetectionResult object with detection metadata,
        or None if detection failed.
        """
        detector = cls._get_enhanced_detector(use_cache=use_cache, enable_stats=False)
        return detector.detect_with_details(path)

    @classmethod
    def detect_with_strategy(
        cls, path: Path, strategy_name: str, use_cache: bool = False
    ) -> str | None:
        """Detect using a specific strategy.

        Useful for testing or forcing a particular detection method.
        """
        detector = cls._get_enhanced_detector(use_cache=use_cache, enable_stats=False)
        for strategy in detector._strategies:
            if strategy.name == strategy_name:
                result = strategy.detect(path)
                return result.mime_type if result else None
        return None

    @classmethod
    def add_custom_strategy(cls, strategy: MimeDetectionStrategy) -> None:
        """Add a custom detection strategy.

        Custom strategies are added to all detector instances.
        """
        detector = cls._get_enhanced_detector(use_cache=True, enable_stats=False)
        detector.add_strategy(strategy)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear detection cache."""
        if cls._simple_detector and cls._simple_detector.cache:
            cls._simple_detector.cache.clear()

    @classmethod
    def get_cache_stats(cls) -> dict | None:
        """Get cache statistics if available."""
        if cls._simple_detector and cls._simple_detector.cache:
            return {
                "size": cls._simple_detector.cache.size(),
                "max_size": cls._simple_detector.cache.max_size,
            }
        return None


# ---------------------------------------------------------------------------
# TOML Serialization Module
# ---------------------------------------------------------------------------


class TomlSerializer:
    """Encapsulates TOML serialization helpers."""

    @staticmethod
    def toml_key(k: str) -> str:
        """Return *k* formatted as a TOML key, quoting when necessary."""
        if _BARE_KEY_RE.match(k):
            return k
        escaped = k.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    @staticmethod
    def toml_scalar(v: Any) -> str:
        """Render a scalar Python value as a TOML value literal."""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        if isinstance(v, (int, float)):
            return str(v)
        raise TypeError(f"Cannot serialise {type(v).__name__!r} as TOML scalar")

    @staticmethod
    def dict_to_toml(data: dict[str, Any], *, header: str = "") -> str:
        """Serialise *data* to a TOML string.

        Only handles one level of nested tables — sufficient for the edit config
        schema ([defaults], [mime_types], [extensions]).
        """
        lines: list[str] = []
        if header:
            lines.append(header.rstrip())
            lines.append("")

        # Top-level scalars first
        for key, val in data.items():
            if not isinstance(val, dict):
                lines.append(
                    f"{TomlSerializer.toml_key(key)} = {TomlSerializer.toml_scalar(val)}"
                )

        # Then table sections
        for key, val in data.items():
            if isinstance(val, dict):
                lines.append(f"\n[{key}]")
                for k, v in val.items():
                    lines.append(
                        f"{TomlSerializer.toml_key(k)} = {TomlSerializer.toml_scalar(v)}"
                    )

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Configuration File I/O Module
# ---------------------------------------------------------------------------


class ConfigIO:
    """Encapsulates configuration file reading and writing."""

    @staticmethod
    def parse_toml_str(source: str) -> dict[str, Any]:
        """Parse TOML from a string."""
        return tomllib.loads(source)

    @staticmethod
    def parse_toml_file(path: Path) -> dict[str, Any]:
        """Parse TOML from a file."""
        with path.open("rb") as fh:
            return tomllib.load(fh)

    @staticmethod
    def read_user_config() -> dict[str, Any]:
        """Read *only* the user-global config file (not the merged stack).

        Returns an empty dict when the file does not exist yet.
        """
        p = ConfigManager.user_config_path()
        return ConfigIO.parse_toml_file(p) if p.exists() else {}

    @staticmethod
    def save_user_config(data: dict[str, Any]) -> None:
        """Write *data* to the user config file, creating directories as needed.

        Any existing comments are replaced; the file is fully rewritten.
        """
        p = ConfigManager.user_config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "# zopen user configuration\n"
            "# Written by 'zopen --map'.  Manual edits are welcome.\n"
            f"# See 'zopen --list' for the full resolved mapping.\n"
        )
        p.write_text(TomlSerializer.dict_to_toml(data, header=header))


# ---------------------------------------------------------------------------
# Configuration Management Module
# ---------------------------------------------------------------------------


class ConfigManager:
    """Encapsulates configuration loading, merging, and validation.

    Uses ConfigProvider for validation and ConfigCache for performance.
    """

    # Shared provider instance for all config operations
    _provider: ConfigProvider | None = None

    @classmethod
    def _get_provider(cls) -> ConfigProvider:
        """Get or create the shared ConfigProvider instance."""
        if cls._provider is None:
            cls._provider = ConfigProvider(use_cache=True)
        return cls._provider

    @staticmethod
    def system_config_path() -> Path:
        """Return the system-wide config path.

        The directory can be overridden at install time via the ``ZOPEN_SYSCONFDIR``
        environment variable (used by staged/packaged installs to point at the
        correct prefix before the final install step completes).
        """
        sysconfdir = os.environ.get("ZOPEN_SYSCONFDIR", "/opt/etc")
        return Path(sysconfdir) / APP_NAME / "config.toml"

    @staticmethod
    def user_config_path() -> Path:
        """Return the canonical path for the user-global config file."""
        return Path.home() / ".config" / APP_NAME / "config.toml"

    @staticmethod
    def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge *override* into a copy of *base*.

        Nested dicts are merged; all other values are replaced.
        """
        result = dict(base)
        for key, val in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(val, dict)
            ):
                result[key] = ConfigManager.deep_merge(result[key], val)
            else:
                result[key] = val
        return result

    @staticmethod
    def load_layers(extra_config: Path | None = None) -> list[ConfigLayer]:
        """Return each config layer as (data, label), **lowest** priority first.

        Layers (each overrides the previous):
          1. Built-in defaults
          2. System-wide config  ($ZOPEN_SYSCONFDIR/zopen/config.toml)
          3. User-global config  (~/.config/zopen/config.toml)
          4. Project-local       (./.zopen.toml in CWD)
          5. --config FILE       (ad-hoc override)
        """
        layers: list[ConfigLayer] = [
            (ConfigIO.parse_toml_str(_DEFAULT_CONFIG_TOML), "built-in defaults"),
            (ConfigIO.parse_toml_str(_SYSTEM_CONFIG_TOML), "built-in system"),
        ]
        sys_path = ConfigManager.system_config_path()
        if sys_path.exists():
            layers.append((ConfigIO.parse_toml_file(sys_path), f"system  ({sys_path})"))
        user_path = ConfigManager.user_config_path()
        if user_path.exists():
            layers.append(
                (ConfigIO.parse_toml_file(user_path), f"user    ({user_path})")
            )
        local_path = Path.cwd() / f".{APP_NAME}.toml"
        if local_path.exists():
            layers.append(
                (ConfigIO.parse_toml_file(local_path), f"project ({local_path})")
            )
        if extra_config is not None:
            layers.append(
                (ConfigIO.parse_toml_file(extra_config), f"--config ({extra_config})")
            )
        return layers

    @staticmethod
    def load(extra_config: Path | None = None) -> dict[str, Any]:
        """Load and deep-merge config from all layers (highest priority wins).

        Validates and normalizes the merged configuration using ConfigProvider.
        """
        provider = ConfigManager._get_provider()
        result: dict[str, Any] = {}
        for data, _ in ConfigManager.load_layers(extra_config):
            result = ConfigManager.deep_merge(result, data)
        # Validate the merged result
        return provider.load_and_validate(result)

    @staticmethod
    def get_provider() -> ConfigProvider:
        """Get the ConfigProvider instance used by ConfigManager.

        Useful for advanced use cases or testing.
        """
        return ConfigManager._get_provider()

    @staticmethod
    def get_defaults(config: dict[str, Any]) -> dict[str, Any]:
        """Get the effective defaults from config.

        Combines built-in defaults with config defaults.
        """
        return ConfigDefaults.merge_with_defaults(config)

    @staticmethod
    def get_app_command(config: dict[str, Any]) -> str:
        """Get the fallback app command from config.

        Returns the configured app/editor or 'xdg-open' as last resort.
        """
        return ConfigDefaults.get_app_command(config)

    @staticmethod
    def get_prefer_mime(config: dict[str, Any]) -> bool:
        """Get the prefer_mime setting from config.

        Returns True if MIME types should be preferred over extensions.
        """
        return ConfigDefaults.get_prefer_mime(config)

    @staticmethod
    def clear_cache() -> None:
        """Clear the configuration cache.

        Useful for testing or after manual config changes.
        """
        provider = ConfigManager._get_provider()
        if provider.cache:
            provider.cache.clear()


# ---------------------------------------------------------------------------
# Application Resolution Module
# ---------------------------------------------------------------------------


class SentinelResolver:
    """Encapsulates sentinel value resolution logic."""

    @staticmethod
    def resolve(value: str) -> str:
        """Replace the ``$EDITOR`` sentinel with the environment-supplied editor command."""
        if value != _SENTINEL:
            return value
        return (
            os.environ.get("VISUAL")
            or os.environ.get("EDITOR")
            or "vi"  # POSIX-guaranteed last resort
        )


class AppResolver:
    """Encapsulates application resolution logic."""

    @staticmethod
    def collect_candidates(
        file_path: Path,
        layers: list[ConfigLayer],
        *,
        mime_override: str | None = None,
    ) -> list[tuple[str, str]]:
        """Build a priority-ordered list of ``(resolved_command, source_label)`` for *file_path*.

        Priority rules (highest first):

        * Higher config layer beats lower (project > user > system > built-in defaults).
        * Within a layer, a **later**-defined mapping key beats an earlier one (last wins).
        * Within a layer, when both a MIME and an extension entry match, their relative
          order is controlled by the effective ``prefer_mime`` setting.

        When no config entry matches:
        1. The platform's ``xdg-mime query default`` result is tried (desktop association).
        2. ``xdg-open`` is used as the universal catch-all fallback.

        Commands are deduplicated — the first occurrence (highest priority) is kept.
        """
        # ── Detect MIME and extension ──────────────────────────────────────────────
        detected_mime: str | None = mime_override or (
            MimeDetector.detect(file_path) if file_path.exists() else None
        )
        suffix = file_path.suffix.lower() or None

        # ── Effective prefer_mime: use the highest-priority layer that defines it ──
        prefer_mime = True
        for data, _ in reversed(layers):
            pm = data.get("defaults", {}).get("prefer_mime")
            if pm is not None:
                prefer_mime = bool(pm)
                break

        candidates: list[tuple[str, str]] = []
        seen: set[str] = set()

        def _add(raw: str, label: str) -> None:
            resolved = SentinelResolver.resolve(raw)
            if resolved not in seen:
                seen.add(resolved)
                candidates.append((resolved, label))

        def _find_mime(mime_map: dict[str, str]) -> tuple[str, str] | None:
            """Scan *mime_map* in reverse (last-defined first) for detected_mime."""
            if not detected_mime:
                return None
            items = list(mime_map.items())[::-1]
            for key, val in items:
                if key == detected_mime:
                    return (val, key)
            base = detected_mime.split("/")[0]
            for key, val in items:
                if key == base:
                    return (val, key)
            return None

        def _find_ext(ext_map: dict[str, str]) -> tuple[str, str] | None:
            """Scan *ext_map* in reverse (last-defined first) for suffix."""
            if not suffix:
                return None
            items = list(ext_map.items())[::-1]
            for key, val in items:
                if key == suffix:
                    return (val, key)
            return None

        # ── Process layers from HIGHEST to LOWEST priority ─────────────────────────
        for data, source_label in reversed(layers):
            mime_hit = _find_mime(data.get("mime_types", {}))
            ext_hit = _find_ext(data.get("extensions", {}))

            # Interleave mime / extension results in prefer_mime order
            hits: list[tuple[tuple[str, str], str] | None] = (
                [
                    ((mime_hit[0], mime_hit[1]), "mime_types") if mime_hit else None,
                    ((ext_hit[0], ext_hit[1]), "extensions") if ext_hit else None,
                ]
                if prefer_mime
                else [
                    ((ext_hit[0], ext_hit[1]), "extensions") if ext_hit else None,
                    ((mime_hit[0], mime_hit[1]), "mime_types") if mime_hit else None,
                ]
            )
            for item in hits:
                if item is not None:
                    (raw_val, key), section = item
                    _add(raw_val, f"{source_label}  [{section}][{key!r}]")

        # ── When config has no match, add platform defaults ────────────────────────
        if not candidates:
            # 1. defaults.app / defaults.editor from the highest layer that has one
            for data, source_label in reversed(layers):
                fb = data.get("defaults", {}).get("app") or data.get(
                    "defaults", {}
                ).get("editor")
                if fb is not None and fb not in ("xdg-open",):
                    _add(fb, f"{source_label}  [defaults][app]")
                    break

            # 2. Platform association via xdg-mime (reflects the desktop's own default)
            if detected_mime:
                xdg_cmd = XdgIntegration.query_xdg_default(detected_mime)
                if xdg_cmd:
                    _add(xdg_cmd, f"xdg-mime default  ({detected_mime})")

            # 3. xdg-open — universal catch-all: delegates to the OS at runtime
            _add("xdg-open", "xdg-open (platform fallback)")

        return candidates

    @staticmethod
    def resolve(
        file_path: Path,
        layers: list[ConfigLayer],
        *,
        mime_override: str | None = None,
        verbose: bool = False,
    ) -> str:
        """Return the highest-priority application command for *file_path*.

        Delegates to :func:`collect_candidates` and returns the first entry's
        command string.  Use *verbose* to print resolution details to stderr.
        """
        candidates = AppResolver.collect_candidates(
            file_path, layers, mime_override=mime_override
        )
        app_cmd, source = candidates[0]
        if verbose:
            mime = mime_override or (
                MimeDetector.detect(file_path) if file_path.exists() else None
            )
            suffix = file_path.suffix.lower() or None
            print(
                f"  mime: {mime or '(unknown)'}  ext: {suffix or '(none)'}",
                file=sys.stderr,
            )
            print(f"  → {app_cmd!r}  (from {source})", file=sys.stderr)
            if len(candidates) > 1:
                print(
                    f"  ({len(candidates) - 1} lower-priority alternative(s) available;"
                    " use -c to choose interactively)",
                    file=sys.stderr,
                )
        return app_cmd


# Backward-compatible module-level aliases
def detect_mime(path: Path) -> str | None:
    return MimeDetector.detect(path)


def _resolve_sentinel(value: str) -> str:
    return SentinelResolver.resolve(value)


# Exports for new configuration system classes
def get_config_provider() -> ConfigProvider:
    """Get the shared ConfigProvider instance."""
    return ConfigManager.get_provider()


def clear_config_cache() -> None:
    """Clear the configuration cache."""
    ConfigManager.clear_cache()


def load_config_layers(extra_config: Path | None = None) -> list[ConfigLayer]:
    return ConfigManager.load_layers(extra_config)


def load_config(extra_config: Path | None = None) -> dict[str, Any]:
    return ConfigManager.load(extra_config)


def collect_app_candidates(
    file_path: Path, layers: list[ConfigLayer], *, mime_override: str | None = None
) -> list[tuple[str, str]]:
    return AppResolver.collect_candidates(
        file_path, layers, mime_override=mime_override
    )


collect_editor_candidates = collect_app_candidates


def resolve_app(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
    verbose: bool = False,
) -> str:
    return AppResolver.resolve(
        file_path, layers, mime_override=mime_override, verbose=verbose
    )


resolve_editor = resolve_app


def read_user_config() -> dict[str, Any]:
    return ConfigIO.read_user_config()


def save_user_config(data: dict[str, Any]) -> None:
    ConfigIO.save_user_config(data)


def _system_config_path() -> Path:
    return ConfigManager.system_config_path()


def _user_config_path() -> Path:
    return ConfigManager.user_config_path()


def _parse_toml_file(path: Path) -> dict[str, Any]:
    return ConfigIO.parse_toml_file(path)


def _parse_toml_str(source: str) -> dict[str, Any]:
    return ConfigIO.parse_toml_str(source)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    return ConfigManager.deep_merge(base, override)


def _toml_key(k: str) -> str:
    return TomlSerializer.toml_key(k)


def _toml_scalar(v: Any) -> str:
    return TomlSerializer.toml_scalar(v)


def _dict_to_toml(data: dict[str, Any], *, header: str = "") -> str:
    return TomlSerializer.dict_to_toml(data, header=header)


# ---------------------------------------------------------------------------
# User Config Generation Module
# ---------------------------------------------------------------------------


class ConfigGenerator:
    """Encapsulates user configuration generation."""

    @staticmethod
    def generate_user_config_content() -> str:
        """Build a user config TOML by querying the OS for its default handlers.

        For each MIME type in *_XDG_PROBE_MIMES* the function calls ``gio mime``
        (falling back to ``xdg-mime``) to discover the installed default
        application *and* every other registered application.  The platform
        default is written as the active mapping; all alternatives are written
        as commented-out lines immediately below, so the user can switch by
        uncommenting a single line.

        Text and source-code types stay as ``$EDITOR`` so the user's terminal
        editor preference is preserved.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # mime → (default_cmd, [all_cmds ordered: default first, then alternatives])
        resolved_mimes: dict[str, tuple[str, list[str]]] = {}
        # ext  → same tuple (inherited from primary MIME, first probe wins)
        resolved_exts: dict[str, tuple[str, list[str]]] = {}

        for mime, fallback, exts in _XDG_PROBE_MIMES:
            default_cmd, all_cmds = XdgIntegration.query_all_xdg_apps(mime)
            if not default_cmd:
                # Fall back to xdg-mime or static default
                default_cmd = XdgIntegration.query_xdg_default(mime) or fallback
                all_cmds = [default_cmd]
            resolved_mimes[mime] = (default_cmd, all_cmds)
            for ext in exts:
                if ext not in resolved_exts:
                    resolved_exts[ext] = (default_cmd, all_cmds)

        def _fmt_mime(k: str) -> str:
            escaped = k.replace('"', '\\"')
            return f'"{escaped}"'

        def _esc(cmd: str) -> str:
            return cmd.replace("\\", "\\\\").replace('"', '\\"')

        def _mime_lines(
            key: str, default_cmd: str, all_cmds: list[str], width: int = 60
        ) -> list[str]:
            """Emit one active line + commented alternatives for a MIME/ext key."""
            out = [f'{_fmt_mime(key):<{width}} = "{_esc(default_cmd)}"']
            for alt in all_cmds[1:]:
                out.append(
                    f'# {_fmt_mime(key):<{width - 2}} = "{_esc(alt)}"  # alternative'
                )
            return out

        # Build TOML manually so we can add per-section comments
        lines: list[str] = [
            "# zopen — user configuration",
            f"# Auto-generated on {now} from OS MIME defaults (gio/xdg-mime).",
            "#",
            '# Text/code files are intentionally left as "$EDITOR" so your',
            "# preferred terminal editor ($VISUAL / $EDITOR env vars) is used.",
            "#",
            "# When the platform has multiple registered apps for a type, the",
            "# platform default is active; alternatives appear as commented lines.",
            "# Uncomment an alternative (and comment out the active line) to switch.",
            "#",
            "# Override any entry or add new ones below.  Changes are never",
            "# overwritten automatically (use --init-config --force to regenerate).",
            "",
            "[defaults]",
            'app         = "xdg-open"',
            "prefer_mime = true",
            "",
            "# ── Text & source code (" + '"$EDITOR" = defer to $VISUAL/$EDITOR/vi) ─',
            "[mime_types]",
            '"text/plain"                    = "$EDITOR"',
            '"text/x-python"                 = "$EDITOR"',
            '"text/x-script.python"          = "$EDITOR"',
            '"text/html"                     = "$EDITOR"',
            '"text/css"                      = "$EDITOR"',
            '"text/javascript"               = "$EDITOR"',
            '"text/x-shellscript"            = "$EDITOR"',
            '"text/x-sh"                     = "$EDITOR"',
            '"text/x-csrc"                   = "$EDITOR"',
            '"text/x-c++src"                 = "$EDITOR"',
            '"text/x-java"                   = "$EDITOR"',
            '"text/x-ruby"                   = "$EDITOR"',
            '"text/x-go"                     = "$EDITOR"',
            '"text/x-rust"                   = "$EDITOR"',
            '"text/x-markdown"               = "$EDITOR"',
            '"application/json"              = "$EDITOR"',
            '"application/xml"               = "$EDITOR"',
            '"application/toml"              = "$EDITOR"',
            '"application/x-yaml"            = "$EDITOR"',
            "",
            "# ── OS-detected defaults (alternatives shown as comments) ───────────",
        ]

        # Group probed MIME entries by category (comment headers)
        categories = [
            (
                "Documents",
                [
                    "application/pdf",
                    "application/postscript",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.oasis.opendocument.text",
                    "application/rtf",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.oasis.opendocument.spreadsheet",
                    "text/csv",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "application/vnd.oasis.opendocument.presentation",
                ],
            ),
            (
                "Images",
                [
                    "image/png",
                    "image/jpeg",
                    "image/gif",
                    "image/webp",
                    "image/bmp",
                    "image/tiff",
                    "image/x-icon",
                    "image/heic",
                    "image/heif",
                    "image/svg+xml",
                ],
            ),
            (
                "Audio",
                [
                    "audio/mpeg",
                    "audio/ogg",
                    "audio/flac",
                    "audio/x-flac",
                    "audio/wav",
                    "audio/mp4",
                    "audio/aac",
                    "audio/opus",
                    "audio/x-ms-wma",
                ],
            ),
            (
                "Video",
                [
                    "video/mp4",
                    "video/x-matroska",
                    "video/x-msvideo",
                    "video/quicktime",
                    "video/webm",
                    "video/x-ms-wmv",
                    "video/mpeg",
                    "video/ogg",
                    "video/3gpp",
                ],
            ),
            (
                "Archives",
                [
                    "application/zip",
                    "application/x-tar",
                    "application/gzip",
                    "application/x-bzip2",
                    "application/x-xz",
                    "application/x-7z-compressed",
                    "application/x-rar",
                    "application/x-rar-compressed",
                    "application/x-zstd-compressed-tar",
                ],
            ),
            ("E-books", ["application/epub+zip", "application/x-mobipocket-ebook"]),
        ]

        for cat_name, mimes in categories:
            lines.append(f"# {cat_name}")
            for m in mimes:
                if m in resolved_mimes:
                    default_cmd, all_cmds = resolved_mimes[m]
                    lines.extend(_mime_lines(m, default_cmd, all_cmds, width=60))
            lines.append("")

        # Extension mappings
        ext_categories = [
            (
                "Text / source code",
                [
                    ".txt",
                    ".md",
                    ".rst",
                    ".py",
                    ".pyi",
                    ".js",
                    ".mjs",
                    ".cjs",
                    ".ts",
                    ".tsx",
                    ".jsx",
                    ".html",
                    ".htm",
                    ".css",
                    ".scss",
                    ".sass",
                    ".less",
                    ".json",
                    ".jsonc",
                    ".xml",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".ini",
                    ".cfg",
                    ".conf",
                    ".sh",
                    ".bash",
                    ".zsh",
                    ".fish",
                    ".c",
                    ".h",
                    ".cpp",
                    ".cc",
                    ".cxx",
                    ".hpp",
                    ".hxx",
                    ".rs",
                    ".go",
                    ".java",
                    ".kt",
                    ".rb",
                    ".php",
                    ".sql",
                    ".tf",
                    ".lua",
                    ".r",
                    ".R",
                    ".swift",
                    ".dart",
                ],
            ),
            (
                "Documents",
                [
                    ".pdf",
                    ".ps",
                    ".eps",
                    ".doc",
                    ".docx",
                    ".odt",
                    ".rtf",
                    ".xls",
                    ".xlsx",
                    ".ods",
                    ".csv",
                    ".ppt",
                    ".pptx",
                    ".odp",
                ],
            ),
            (
                "Images",
                [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".webp",
                    ".bmp",
                    ".tiff",
                    ".tif",
                    ".ico",
                    ".heic",
                    ".heif",
                    ".svg",
                ],
            ),
            (
                "Audio",
                [".mp3", ".ogg", ".flac", ".wav", ".m4a", ".aac", ".wma", ".opus"],
            ),
            (
                "Video",
                [
                    ".mp4",
                    ".mkv",
                    ".avi",
                    ".mov",
                    ".webm",
                    ".wmv",
                    ".mpg",
                    ".mpeg",
                    ".ogv",
                    ".3gp",
                ],
            ),
            ("Archives", [".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst"]),
            ("E-books", [".epub", ".mobi"]),
        ]

        lines.append("[extensions]")
        for cat_name, exts in ext_categories:
            lines.append(f"# {cat_name}")
            for ext in exts:
                if ext in resolved_exts:
                    default_cmd, all_cmds = resolved_exts[ext]
                    lines.extend(_mime_lines(ext, default_cmd, all_cmds, width=10))
                else:
                    lines.append(f'{_fmt_mime(ext):<10} = "$EDITOR"')
            lines.append("")

        return "\n".join(lines) + "\n"


def generate_user_config_content() -> str:
    return ConfigGenerator.generate_user_config_content()


# ---------------------------------------------------------------------------
# Config Initialization Module
# ---------------------------------------------------------------------------


class ConfigInit:
    """Encapsulates config file initialization."""

    @staticmethod
    def write_default_config(path: Path, *, force: bool = False) -> int:
        """Write a dynamically-generated user config to *path*.

        Queries the OS via xdg-mime to discover the currently installed default
        application for each common file type, then writes a TOML config reflecting
        those choices.  Text and source-code types always stay as ``$EDITOR``.

        Does NOT overwrite an existing file unless *force* is True.
        Returns 0 on success, non-zero on error.
        """
        if path.exists() and not force:
            print(
                f"User config already exists: {path}\n"
                f"Use --force (-f) to overwrite it.",
                file=sys.stderr,
            )
            return 1

        print("Querying OS for installed application defaults…", file=sys.stderr)
        content = ConfigGenerator.generate_user_config_content()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"✓ User config written to {path}")
        return 0

    @staticmethod
    def write_system_config(path: Path, *, force: bool = False) -> int:
        """Write the system-wide config with Ubuntu 24.04 LTS default apps.

        Checks write permission on the target directory and advises the user to
        re-run with sudo if needed.  Returns 0 on success, non-zero on error.
        """
        if path.exists() and not force:
            print(
                f"System config already exists: {path}\n"
                f"Use --force (-f) to overwrite it.",
                file=sys.stderr,
            )
            return 1

        # Check write permission
        target_dir = path.parent
        can_write = os.access(target_dir, os.W_OK) if target_dir.exists() else False
        if not can_write:
            # Try parent directories up to root to find writable ancestor
            ancestor = target_dir
            while not ancestor.exists() and ancestor != ancestor.parent:
                ancestor = ancestor.parent
            can_write = os.access(ancestor, os.W_OK) if ancestor.exists() else False

        if not can_write:
            print(
                f"✗ Cannot write to {target_dir} — permission denied.\n"
                f"  Re-run with sudo:\n"
                f"    sudo zopen --init-config --force",
                file=sys.stderr,
            )
            return 2

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(_SYSTEM_CONFIG_TOML)
            print(f"✓ System config written to {path}")
            return 0
        except PermissionError:
            print(
                f"✗ Permission denied writing to {path}.\n"
                f"  Re-run with sudo:\n"
                f"    sudo zopen --init-config --force",
                file=sys.stderr,
            )
            return 2


def write_default_config(path: Path, *, force: bool = False) -> int:
    return ConfigInit.write_default_config(path, force=force)


def write_system_config(path: Path, *, force: bool = False) -> int:
    return ConfigInit.write_system_config(path, force=force)


# ---------------------------------------------------------------------------
# Display Module
# ---------------------------------------------------------------------------


class DisplayFormatter:
    """Encapsulates display and formatting logic."""

    @staticmethod
    def print_mappings(cfg: dict[str, Any]) -> None:
        """Pretty-print the resolved application mappings."""

        def _res(v: str) -> str:
            r = SentinelResolver.resolve(v)
            return r if v != _SENTINEL else f"{r}  (via $EDITOR env var)"

        print("=== MIME-type mappings ===")
        for k, v in sorted(cfg.get("mime_types", {}).items()):
            print(f"  {k:<40} → {_res(v)}")

        print("\n=== Extension mappings ===")
        for k, v in sorted(cfg.get("extensions", {}).items()):
            print(f"  {k:<15} → {_res(v)}")

        fallback = (
            cfg.get("defaults", {}).get("app")
            or cfg.get("defaults", {}).get("editor")
            or "xdg-open"
        )
        print(f"\n=== Default application ===\n  {_res(fallback)}")

        prefer = cfg.get("defaults", {}).get("prefer_mime", True)
        print(f"\n=== prefer_mime ===\n  {prefer}")


def print_mappings(cfg: dict[str, Any]) -> None:
    DisplayFormatter.print_mappings(cfg)


# ---------------------------------------------------------------------------
# CLI Command Handlers Module
# ---------------------------------------------------------------------------


class CliHandlers:
    """Encapsulates CLI command handlers."""

    @staticmethod
    def cmd_dump_apps(
        file_path: Path,
        layers: list[ConfigLayer],
        *,
        mime_override: str | None = None,
    ) -> int:
        """Print the priority-ordered application candidate list for *file_path* and exit.

        Highest-priority application is listed first and marked as the one that would be
        used on a normal (non-interactive) invocation.
        """
        detected_mime = mime_override or (
            MimeDetector.detect(file_path) if file_path.exists() else None
        )
        suffix = file_path.suffix.lower() or None
        candidates = AppResolver.collect_candidates(
            file_path, layers, mime_override=mime_override
        )

        print(f"File : {file_path}")
        print(f"MIME : {detected_mime or '(unknown)'}")
        print(f"Ext  : {suffix or '(none)'}")
        print(f"\nApplications (decreasing priority):")
        for i, (app_cmd, source) in enumerate(candidates, 1):
            marker = "  ← would be used" if i == 1 else ""
            print(f"  {i}. {app_cmd:<28}  {source}{marker}")
        return 0

    @staticmethod
    def cmd_choose_app(
        file_path: Path,
        layers: list[ConfigLayer],
        *,
        mime_override: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Present a numbered menu of applications and open *file_path* with the chosen one.

        Candidates are listed in priority order (highest first).  Pressing Enter
        without a choice selects the default (top) entry.
        """
        if not file_path.exists():
            print(
                f"Note: '{file_path}' does not exist; MIME detection skipped.",
                file=sys.stderr,
            )
        detected_mime = mime_override or (
            MimeDetector.detect(file_path) if file_path.exists() else None
        )
        suffix = file_path.suffix.lower() or None
        candidates = AppResolver.collect_candidates(
            file_path, layers, mime_override=mime_override
        )

        print(f"\nFile : {file_path}")
        print(f"MIME : {detected_mime or '(unknown)'}")
        print(f"Ext  : {suffix or '(none)'}")
        print(f"\nAvailable applications (highest priority first):")
        width = max(len(app_cmd) for app_cmd, _ in candidates)
        for i, (app_cmd, source) in enumerate(candidates, 1):
            tag = "  [default]" if i == 1 else ""
            print(f"  [{i}] {app_cmd:<{width}}  from {source}{tag}")
        print("  [q] Cancel")

        while True:
            try:
                raw = input("\nChoice [1]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return 0
            if raw in ("", "1"):
                chosen_app, chosen_source = candidates[0]
                break
            if raw == "q":
                print("Cancelled.")
                return 0
            if raw.isdigit() and 1 <= int(raw) <= len(candidates):
                chosen_app, chosen_source = candidates[int(raw) - 1]
                break
            print(f"  Please enter a number 1–{len(candidates)} or 'q' to cancel.")

        cmd = chosen_app.split() + [str(file_path)]
        if dry_run:
            print(f"would run: {' '.join(cmd)}")
            return 0

        print(f"Opening with: {chosen_app}  (from {chosen_source})")
        result = subprocess.run(cmd)
        return result.returncode

    @staticmethod
    def cmd_map_app(
        file_path: Path,
        cfg: dict[str, Any],
        *,
        mime_override: str | None = None,
        verbose: bool = False,
    ) -> int:
        """Interactively update the MIME-type / extension → application mapping.

        Detects the MIME type and extension of *file_path*, shows the current
        effective mapping (from the merged config stack), then prompts the user
        for a new application value.  The result is written to the user config file
        (``~/.config/zopen/config.toml``) only — lower-priority layers are not
        touched.
        """
        # --- Detect ---
        if file_path.exists():
            if mime_override:
                detected_mime: str | None = mime_override
                mime_src = "--mime override"
            else:
                detected_mime = MimeDetector.detect(file_path)
                mime_src = "libmagic" if _HAVE_LIBMAGIC else "mimetypes"
        else:
            detected_mime = mime_override  # may be None
            mime_src = "--mime override" if mime_override else "file not found"

        suffix = file_path.suffix.lower() or None

        # --- Display file info ---
        print(f"\nFile : {file_path}")
        if detected_mime:
            print(f"MIME : {detected_mime}  (via {mime_src})")
        else:
            print(f"MIME : (unknown — {mime_src})")
        if suffix:
            print(f"Ext  : {suffix}")
        else:
            print("Ext  : (none)")

        # --- Look up current effective mappings ---
        mime_map: dict[str, str] = cfg.get("mime_types", {})
        ext_map: dict[str, str] = cfg.get("extensions", {})
        fallback = (
            cfg.get("defaults", {}).get("app")
            or cfg.get("defaults", {}).get("editor")
            or "xdg-open"
        )

        def _eff(raw: str | None) -> str:
            if raw is None:
                return f"{SentinelResolver.resolve(fallback)}  (fallback)"
            resolved = SentinelResolver.resolve(raw)
            return f"{resolved}  ($EDITOR)" if raw == _SENTINEL else resolved

        cur_mime_app: str | None = None
        if detected_mime:
            cur_mime_app = mime_map.get(detected_mime)
            if cur_mime_app is None:
                cur_mime_app = mime_map.get(detected_mime.split("/")[0])

        cur_ext_app: str | None = ext_map.get(suffix) if suffix else None

        print("\nCurrent mappings (effective, from merged config):")
        if detected_mime:
            print(f"  MIME  {detected_mime!r:<42}  →  {_eff(cur_mime_app)}")
        if suffix:
            print(f"  Ext   {suffix!r:<42}  →  {_eff(cur_ext_app)}")

        # --- Build interactive menu ---
        options: list[tuple[str, str | None, str | None]] = []
        if detected_mime:
            options.append((f"MIME type  ({detected_mime})", detected_mime, None))
        if suffix:
            options.append((f"Extension  ({suffix})", None, suffix))
        if detected_mime and suffix:
            options.append(("Both", detected_mime, suffix))

        if not options:
            print(
                "\nNothing to map: no MIME type detected and the file has no extension.",
                file=sys.stderr,
            )
            return 1

        print("\nWhat would you like to update?")
        for i, (label, _, _) in enumerate(options, 1):
            print(f"  [{i}] {label}")
        print("  [q] Cancel")

        while True:
            try:
                raw = input("\nChoice: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return 0
            if raw == "q":
                print("Cancelled.")
                return 0
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                chosen_label, chosen_mime, chosen_ext = options[int(raw) - 1]
                break
            print(f"  Please enter a number 1–{len(options)} or 'q' to cancel.")

        # --- Prompt for new application value(s) ---
        def _prompt(current_raw: str | None, kind: str, key: str) -> str | None:
            current_disp = (
                current_raw
                if current_raw is not None
                else f"{SentinelResolver.resolve(fallback)} (fallback)"
            )
            try:
                val = input(
                    f"\nNew application for {kind} {key!r}\n"
                    f"  current : {current_disp}\n"
                    f"  (Enter to keep current, '$EDITOR' to follow $EDITOR env var): "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                return None
            return val if val else None

        # Read only the user config layer — we update that file alone.
        user_cfg = ConfigIO.read_user_config()
        changed = False

        if chosen_mime is not None:
            new_val = _prompt(cur_mime_app, "MIME type", chosen_mime)
            if new_val is not None:
                user_cfg.setdefault("mime_types", {})[chosen_mime] = new_val
                print(f"  mime_types[{chosen_mime!r}] = {new_val!r}")
                changed = True

        if chosen_ext is not None:
            new_val = _prompt(cur_ext_app, "extension", chosen_ext)
            if new_val is not None:
                user_cfg.setdefault("extensions", {})[chosen_ext] = new_val
                print(f"  extensions[{chosen_ext!r}] = {new_val!r}")
                changed = True

        if changed:
            ConfigIO.save_user_config(user_cfg)
            print(f"\n✓ Saved to {ConfigManager.user_config_path()}")
        else:
            print("\nNo changes made.")

        return 0

    @staticmethod
    def install_ed_alias(
        candidates: list[Path] | None = None,
        *,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> int:
        """Install a ``zo`` symlink in the first suitable candidate directory.

        Candidate directories (default: ``~/.local/bin``, ``/opt/bin``,
        ``/usr/local/bin``) are tried in order.  For each directory the function:

        * Skips if the directory does not exist.
        * **Always overwrites** any existing entry in ``~/.local/bin`` (user-level).
        * Warns and skips if an entry already exists in a system directory that does
          not point to this program.
        * Warns if the chosen directory appears *after* a directory that already
          contains the alias in PATH (the alias would be shadowed).
        * Creates the symlink and stops at the first success.

        Returns 0 on success, 1 if no symlink could be created.
        """
        if candidates is None:
            candidates = list(_ALIAS_CANDIDATES)

        user_bin = Path.home() / ".local" / "bin"

        def _find_self() -> Path | None:
            """Locate the installed 'zopen' executable."""
            found = shutil.which(APP_NAME)
            if found:
                return Path(found)
            # Invoked directly as a script (python zopen.py)
            script = Path(sys.argv[0]).resolve()
            if script.stem == APP_NAME:
                return script
            return None

        edit_exe = _find_self()
        if edit_exe is None:
            print(
                f"error: cannot locate '{APP_NAME}' executable in PATH", file=sys.stderr
            )
            return 1

        # Build an ordered list of PATH dirs for shadowing analysis.
        path_dirs = [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p]

        any_created = False
        for target_dir in candidates:
            link_path = target_dir / _ALIAS_NAME
            is_user_bin = target_dir.resolve() == user_bin.resolve()

            if not target_dir.exists():
                if verbose:
                    print(f"  skip {target_dir}: directory does not exist")
                continue

            # --- Conflict check ---
            if link_path.exists() or link_path.is_symlink():
                if is_user_bin:
                    # User-level location: always overwrite (symlink, broken, or file)
                    if verbose:
                        print(f"  {link_path}: overwriting existing entry (user-level)")
                    if not dry_run:
                        link_path.unlink(missing_ok=True)
                    # Fall through to create fresh symlink
                elif link_path.is_symlink():
                    try:
                        dest = link_path.resolve(strict=True)
                    except (OSError, RuntimeError):
                        # Broken or looping symlink — safe to replace
                        print(
                            f"⚠  {link_path} is a broken/looping symlink — removing it"
                        )
                        if not dry_run:
                            link_path.unlink()
                        # Fall through to create a fresh symlink
                    else:
                        if dest == edit_exe.resolve():
                            print(
                                f"✓ {link_path} already points to '{APP_NAME}' — nothing to do"
                            )
                            any_created = True
                            break
                        else:
                            print(
                                f"⚠  {link_path} exists and points to {dest} "
                                f"(not '{APP_NAME}') — skipping this location"
                            )
                            continue
                else:
                    print(f"⚠  {link_path} exists as a real file/directory — skipping")
                    continue

            # --- Shadowing check: is there a higher-priority alias in PATH? ---
            system_ed = shutil.which(_ALIAS_NAME)
            if system_ed and Path(system_ed).resolve() != edit_exe.resolve():
                sys_ed_dir = Path(system_ed).parent
                try:
                    sys_idx = path_dirs.index(sys_ed_dir)
                except ValueError:
                    sys_idx = len(path_dirs)
                try:
                    tgt_idx = path_dirs.index(target_dir)
                except ValueError:
                    tgt_idx = len(path_dirs)
                if sys_idx < tgt_idx:
                    print(
                        f"⚠  Warning: '{_ALIAS_NAME}' already exists at {system_ed}, "
                        f"which appears earlier in PATH than {target_dir}.\n"
                        f"   The alias will be shadowed.  "
                        f"Move {target_dir} earlier in PATH or remove the other '{_ALIAS_NAME}'."
                    )

            # --- Create symlink ---
            if dry_run:
                print(f"  would create: {link_path} → {edit_exe}")
                any_created = True
                break

            try:
                link_path.symlink_to(edit_exe)
                print(f"✓ Created: {link_path} → {edit_exe}")
                any_created = True
                break
            except PermissionError:
                print(f"  {target_dir}: permission denied — trying next location…")

        if not any_created:
            print(
                f"Could not install '{_ALIAS_NAME}' alias in any of:\n"
                + "".join(f"  {d}\n" for d in candidates)
                + f"Create it manually:  ln -s $(which {APP_NAME}) ~/.local/bin/{_ALIAS_NAME}",
                file=sys.stderr,
            )
            return 1

        return 0


def cmd_dump_apps(
    file_path: Path, layers: list[ConfigLayer], *, mime_override: str | None = None
) -> int:
    return CliHandlers.cmd_dump_apps(file_path, layers, mime_override=mime_override)


cmd_dump_editors = cmd_dump_apps


def cmd_choose_app(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
    dry_run: bool = False,
) -> int:
    return CliHandlers.cmd_choose_app(
        file_path, layers, mime_override=mime_override, dry_run=dry_run
    )


cmd_choose_editor = cmd_choose_app


def cmd_map_app(
    file_path: Path,
    cfg: dict[str, Any],
    *,
    mime_override: str | None = None,
    verbose: bool = False,
) -> int:
    return CliHandlers.cmd_map_app(
        file_path, cfg, mime_override=mime_override, verbose=verbose
    )


cmd_map_editor = cmd_map_app


def install_ed_alias(
    candidates: list[Path] | None = None,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    return CliHandlers.install_ed_alias(candidates, dry_run=dry_run, verbose=verbose)


# ---------------------------------------------------------------------------
# CLI Architecture - Command Builder and Handler
# ---------------------------------------------------------------------------


class CliBuilder:
    """Builds hierarchical CLI argument parser with subcommands.

    Supports both modern subcommand structure (zopen config list) and
    legacy flat structure (zopen --list) for backward compatibility.
    """

    @staticmethod
    def build_parser_modern() -> argparse.ArgumentParser:
        """Build modern parser with subcommand structure.

        Provides hierarchical commands:
        - zopen open [FILES]          - Open files (default)
        - zopen config list           - List config mappings
        - zopen config init           - Initialize config
        - zopen config map FILE       - Map MIME type for file
        - zopen mime detect [FILES]   - Detect MIME types
        - zopen mime strategies       - List detection strategies
        - zopen app info [FILES]      - Show app resolution info
        """
        p = argparse.ArgumentParser(
            prog=APP_NAME,
            description=(
                "Open file(s) using the appropriate application determined by MIME type "
                "or file extension according to a configurable TOML mapping.  "
                "Falls back to the platform's xdg-open when no explicit mapping is found."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""\
Config file locations (applied in order, later overrides earlier):
  /opt/etc/{APP_NAME}/config.toml   system-wide  (set $ZOPEN_SYSCONFDIR to override /opt/etc)
  ~/.config/{APP_NAME}/config.toml   user-global
  ./.{APP_NAME}.toml                 project-local (CWD)
  FILE given via --config flag       ad-hoc override

Use `{APP_NAME} config init` to write a starter config to the global location.
Use `{APP_NAME} --help` for legacy flat interface.
""",
        )

        # Global options (apply to all subcommands)
        global_group = p.add_argument_group("Global Options")
        global_group.add_argument(
            "-C",
            "--config",
            metavar="FILE",
            type=Path,
            help="Additional config file to merge on top of the standard stack.",
        )
        global_group.add_argument(
            "--verbose",
            action="store_true",
            help="Show resolution details on stderr.",
        )
        global_group.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"%(prog)s {APP_VERSION}",
        )

        # Create subparsers for commands
        subparsers = p.add_subparsers(
            dest="command", help="Available commands", metavar="COMMAND"
        )

        # --- OPEN command (default, can be omitted) ---
        open_parser = subparsers.add_parser(
            "open",
            help="Open file(s) with appropriate application",
            aliases=["o"],
        )
        open_parser.add_argument(
            "files",
            nargs="*",
            metavar="FILE",
            help="File(s) to open.",
        )
        open_parser.add_argument(
            "-m",
            "--mime",
            metavar="TYPE",
            help="Override MIME-type detection (e.g. text/x-python).",
        )
        open_parser.add_argument(
            "-a",
            "--app",
            metavar="CMD",
            help="Use this application directly, bypassing all config lookups.",
        )
        open_parser.add_argument(
            "-c",
            "--choose",
            action="store_true",
            help="Present a numbered menu of applications and let you pick one interactively.",
        )
        open_parser.add_argument(
            "-d",
            "--dump",
            action="store_true",
            help="Dump the priority-ordered list of applications and exit.",
        )
        open_parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="Print the application command that would be run, but don't launch it.",
        )

        # --- CONFIG subcommand ---
        config_parser = subparsers.add_parser(
            "config",
            help="Manage configuration",
            aliases=["cfg"],
        )
        config_subs = config_parser.add_subparsers(
            dest="config_cmd", help="Config operations", metavar="OPERATION"
        )

        # config list
        config_list = config_subs.add_parser(
            "list",
            help="List all configured application mappings",
            aliases=["ls"],
        )

        # config init
        config_init = config_subs.add_parser(
            "init",
            help="Initialize default configuration files",
        )
        config_init.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Also write system-wide config at /opt/etc/zopen/config.toml (requires permissions)",
        )

        # config map
        config_map = config_subs.add_parser(
            "map",
            help="Interactively map MIME type / extension for a file",
        )
        config_map.add_argument(
            "file",
            type=Path,
            help="File to configure mapping for",
        )
        config_map.add_argument(
            "-m",
            "--mime",
            metavar="TYPE",
            help="Override MIME-type detection for this file",
        )

        # --- MIME subcommand ---
        mime_parser = subparsers.add_parser(
            "mime",
            help="MIME type detection utilities",
        )
        mime_subs = mime_parser.add_subparsers(
            dest="mime_cmd", help="MIME operations", metavar="OPERATION"
        )

        # mime detect
        mime_detect = mime_subs.add_parser(
            "detect",
            help="Detect MIME types for files",
            aliases=["d"],
        )
        mime_detect.add_argument(
            "files",
            nargs="+",
            metavar="FILE",
            help="File(s) to detect MIME type for",
        )
        mime_detect.add_argument(
            "--strategy",
            choices=["libmagic", "extension"],
            help="Force specific detection strategy",
        )
        mime_detect.add_argument(
            "--detailed",
            action="store_true",
            help="Show detection details (confidence, source, etc)",
        )

        # mime strategies
        mime_strategies = mime_subs.add_parser(
            "strategies",
            help="List available MIME detection strategies",
            aliases=["strat"],
        )

        # --- APP subcommand ---
        app_parser = subparsers.add_parser(
            "app",
            help="Application resolution utilities",
        )
        app_subs = app_parser.add_subparsers(
            dest="app_cmd", help="Application operations", metavar="OPERATION"
        )

        # app info
        app_info = app_subs.add_parser(
            "info",
            help="Show application resolution information for files",
            aliases=["i"],
        )
        app_info.add_argument(
            "files",
            nargs="+",
            metavar="FILE",
            help="File(s) to show info for",
        )
        app_info.add_argument(
            "-m",
            "--mime",
            metavar="TYPE",
            help="Override MIME-type detection",
        )

        # --- UTIL subcommand ---
        util_parser = subparsers.add_parser(
            "util",
            help="Utility operations",
        )
        util_subs = util_parser.add_subparsers(
            dest="util_cmd", help="Utility operations", metavar="OPERATION"
        )

        # util alias
        util_alias = util_subs.add_parser(
            "alias",
            help=f"Install '{_ALIAS_NAME}' symlink for quick access",
        )

        return p

    @staticmethod
    def build_parser_legacy() -> argparse.ArgumentParser:
        """Build legacy flat parser (original structure).

        Maintained for backward compatibility. All old options still work.
        """
        p = argparse.ArgumentParser(
            prog=APP_NAME,
            description=(
                "Open file(s) using the appropriate application determined by MIME type "
                "or file extension according to a configurable TOML mapping.  "
                "Falls back to the platform's xdg-open when no explicit mapping is found."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""\
Config file locations (applied in order, later overrides earlier):
  /opt/etc/{APP_NAME}/config.toml   system-wide  (set $ZOPEN_SYSCONFDIR to override /opt/etc)
  ~/.config/{APP_NAME}/config.toml   user-global
  ./.{APP_NAME}.toml                 project-local (CWD)
  FILE given to --config             ad-hoc override

Use `{APP_NAME} --init-config` to write a starter config to the global location.
Use `{APP_NAME} config --help` for modern subcommand interface.
""",
        )

        p.add_argument("files", nargs="*", metavar="FILE", help="File(s) to open.")
        p.add_argument(
            "-m",
            "--mime",
            metavar="TYPE",
            help="Override MIME-type detection (e.g. text/x-python).",
        )
        p.add_argument(
            "-a",
            "--app",
            metavar="CMD",
            help="Use this application directly, bypassing all config lookups.",
        )
        p.add_argument(
            "-C",
            "--config",
            metavar="FILE",
            type=Path,
            help="Additional config file to merge on top of the standard stack.",
        )
        p.add_argument(
            "-c",
            "--choose",
            action="store_true",
            help=(
                "Present a numbered menu of applications (highest priority first) for each "
                "FILE and let you pick one interactively.  Default choice (Enter) uses "
                "the highest-priority application."
            ),
        )
        p.add_argument(
            "-d",
            "--dump",
            action="store_true",
            help=(
                "Dump the priority-ordered list of applications for each FILE and exit.  "
                "The first entry is the one that would be used on a normal invocation."
            ),
        )
        p.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="Print the application command that would be run, but don't launch it.",
        )
        p.add_argument(
            "-l",
            "--list",
            action="store_true",
            help="Print all configured application mappings and exit.",
        )
        p.add_argument(
            "--init-config",
            action="store_true",
            help=(
                f"Write a starter user config to ~/.config/{APP_NAME}/config.toml and exit.  "
                f"Does NOT touch the system config.  "
                f"Add --force / -f to also (re)write the system config at "
                f"/opt/etc/{APP_NAME}/config.toml (requires write permission; use sudo if needed)."
            ),
        )
        p.add_argument(
            "-f",
            "--force",
            action="store_true",
            help=(
                "When used with --init-config: write (or overwrite) the system-wide "
                f"config at /opt/etc/{APP_NAME}/config.toml with Ubuntu 24.04 LTS defaults.  "
                "Requires write permission on /opt/etc; run with sudo if needed."
            ),
        )
        p.add_argument(
            "--install-alias",
            action="store_true",
            help=(
                f"Install an '{_ALIAS_NAME}' symlink in the first writable location from: "
                + ", ".join(str(d) for d in _ALIAS_CANDIDATES)
                + ".  Warns if an existing program would shadow the alias."
            ),
        )
        p.add_argument(
            "--map",
            metavar="FILE",
            type=Path,
            help=(
                "Interactively update the MIME-type / extension → application mapping "
                "for FILE.  Detects the MIME type and extension, shows the current "
                "mapping, and prompts for a new application command.  Saves to "
                f"~/.config/{APP_NAME}/config.toml."
            ),
        )
        p.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"%(prog)s {APP_VERSION}",
        )
        p.add_argument(
            "--verbose",
            action="store_true",
            help="Show resolution details on stderr.",
        )
        return p


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser.

    Returns the legacy (flat) parser for backward compatibility.
    Use CliBuilder.build_parser_modern() for new subcommand interface.
    """
    return CliBuilder.build_parser_legacy()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --- --init-config ---
    if args.init_config:
        # Write user config (dynamically generated from OS MIME defaults)
        rc = ConfigInit.write_default_config(
            ConfigManager.user_config_path(), force=args.force
        )
        if rc != 0:
            return rc
        # With -f/--force also write system config
        if args.force:
            rc = ConfigInit.write_system_config(
                ConfigManager.system_config_path(), force=True
            )
            if rc != 0:
                return rc
        return 0

    # --- --install-alias ---
    if args.install_alias:
        return CliHandlers.install_ed_alias(dry_run=args.dry_run, verbose=args.verbose)

    layers = ConfigManager.load_layers(args.config)

    # --- --map FILE ---
    if args.map is not None:
        cfg = ConfigManager.load(args.config)
        return CliHandlers.cmd_map_app(
            args.map, cfg, mime_override=args.mime, verbose=args.verbose
        )

    # --- --list ---
    if args.list:
        DisplayFormatter.print_mappings(ConfigManager.load(args.config))
        return 0

    if not args.files:
        parser.print_help()
        return 1

    exit_code = 0

    for file_arg in args.files:
        file_path = Path(file_arg)

        # --- -d / --dump: print priority list and move on to next file ---
        if args.dump:
            rc = CliHandlers.cmd_dump_apps(file_path, layers, mime_override=args.mime)
            if rc != 0:
                exit_code = rc
            continue

        # --- -c / --choose: interactive application selection ---
        if args.choose:
            rc = CliHandlers.cmd_choose_app(
                file_path, layers, mime_override=args.mime, dry_run=args.dry_run
            )
            if rc != 0:
                exit_code = rc
            continue

        # --- Normal / --app: resolve and open ---
        if args.app:
            app_cmd = args.app
        else:
            if not file_path.exists() and args.verbose:
                print(
                    f"  {file_arg}: file does not exist; skipping MIME detection",
                    file=sys.stderr,
                )
            app_cmd = AppResolver.resolve(
                file_path, layers, mime_override=args.mime, verbose=args.verbose
            )

        cmd = app_cmd.split() + [str(file_path)]
        if args.dry_run or args.verbose:
            label = "would run" if args.dry_run else "running"
            dest = sys.stdout if args.dry_run else sys.stderr
            print(f"{label}: {' '.join(cmd)}", file=dest)
        if not args.dry_run:
            result = subprocess.run(cmd)
            if result.returncode != 0:
                exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
