#!/usr/bin/env python3
"""
edit - Smart file editor launcher

Invokes the appropriate editor based on MIME type (auto-detected or
explicitly specified) or file extension. The MIME type takes precedence
over the extension when both would match unless overridden by config.

Configuration is loaded from (in order, later entries override earlier):
  1. Built-in defaults
  2. /etc/zedit/config.toml        (system-wide config, path via $ZEDIT_SYSCONFDIR)
  3. ~/.config/zedit/config.toml   (user global config)
  4. ./.zedit.toml                 (project-local config, overrides global)
  5. --config FILE                (ad-hoc override on the command line)

Use --install-alias to create an 'ed' shortcut in a non-conflicting location.
Use --map FILE to interactively update the MIME/extension → editor mapping.
"""

from __future__ import annotations

import argparse
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

APP_NAME = "zedit"

# Candidate directories for the 'ed' symlink alias, tried in order.
# These are all user-accessible or local-admin locations that do not
# overlap with distro-managed paths such as /usr/bin.
_ALIAS_NAME = "ze"
_ALIAS_CANDIDATES: list[Path] = [
    Path.home() / ".local" / "bin",  # XDG user bin (pip --user default)
    Path("/opt/bin"),                  # site-local optional programs
    Path("/usr/local/bin"),            # locally-administered programs
]

# Bundled defaults — used when no config file exists.
# Values are intentionally minimal so that $VISUAL / $EDITOR take over when
# no explicit mapping has been configured.
_DEFAULT_CONFIG_TOML = """\
[defaults]
# Final-fallback editor when nothing else matches.
# The special value "$EDITOR" instructs the app to consult the environment
# variables $VISUAL and $EDITOR (in that order) before giving up.
editor = "$EDITOR"

# When a file's MIME type AND its extension both have a mapping, prefer the
# MIME-type mapping.  Set to false to prefer the extension mapping.
prefer_mime = true

[mime_types]
"text/plain"            = "$EDITOR"
"text/x-python"         = "$EDITOR"
"text/x-script.python"  = "$EDITOR"
"text/html"             = "$EDITOR"
"text/css"              = "$EDITOR"
"text/javascript"       = "$EDITOR"
"text/x-shellscript"    = "$EDITOR"
"text/x-sh"             = "$EDITOR"
"application/json"      = "$EDITOR"
"application/xml"       = "$EDITOR"
"application/toml"      = "$EDITOR"

[extensions]
".py"   = "$EDITOR"
".pyi"  = "$EDITOR"
".js"   = "$EDITOR"
".ts"   = "$EDITOR"
".jsx"  = "$EDITOR"
".tsx"  = "$EDITOR"
".html" = "$EDITOR"
".htm"  = "$EDITOR"
".css"  = "$EDITOR"
".scss" = "$EDITOR"
".json" = "$EDITOR"
".xml"  = "$EDITOR"
".yaml" = "$EDITOR"
".yml"  = "$EDITOR"
".toml" = "$EDITOR"
".txt"  = "$EDITOR"
".md"   = "$EDITOR"
".rst"  = "$EDITOR"
".sh"   = "$EDITOR"
".bash" = "$EDITOR"
".zsh"  = "$EDITOR"
".fish" = "$EDITOR"
".c"    = "$EDITOR"
".h"    = "$EDITOR"
".cpp"  = "$EDITOR"
".hpp"  = "$EDITOR"
".rs"   = "$EDITOR"
".go"   = "$EDITOR"
".java" = "$EDITOR"
".rb"   = "$EDITOR"
".php"  = "$EDITOR"
".sql"  = "$EDITOR"
"""

# ---------------------------------------------------------------------------
# TOML write helpers
# ---------------------------------------------------------------------------
# tomllib is read-only by design; these helpers serialise our limited config
# schema (one level of nested string/bool tables) back to disk.

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(k: str) -> str:
    """Return *k* formatted as a TOML key, quoting when necessary."""
    if _BARE_KEY_RE.match(k):
        return k
    escaped = k.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_scalar(v: Any) -> str:
    """Render a scalar Python value as a TOML value literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, (int, float)):
        return str(v)
    raise TypeError(f"Cannot serialise {type(v).__name__!r} as TOML scalar")


def _dict_to_toml(data: dict[str, Any], *, header: str = "") -> str:
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
            lines.append(f"{_toml_key(key)} = {_toml_scalar(val)}")

    # Then table sections
    for key, val in data.items():
        if isinstance(val, dict):
            lines.append(f"\n[{key}]")
            for k, v in val.items():
                lines.append(f"{_toml_key(k)} = {_toml_scalar(v)}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _parse_toml_str(source: str) -> dict[str, Any]:
    return tomllib.loads(source)


def _parse_toml_file(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into a copy of *base*.

    Nested dicts are merged; all other values are replaced.
    """
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _system_config_path() -> Path:
    """Return the system-wide config path.

    The directory can be overridden at install time via the ``ZEDIT_SYSCONFDIR``
    environment variable (used by staged/packaged installs to point at the
    correct prefix before the final install step completes).
    """
    sysconfdir = os.environ.get("ZEDIT_SYSCONFDIR", "/etc")
    return Path(sysconfdir) / APP_NAME / "config.toml"


def _user_config_path() -> Path:
    """Return the canonical path for the user-global config file."""
    return Path.home() / ".config" / APP_NAME / "config.toml"


def load_config_layers(extra_config: Path | None = None) -> list[ConfigLayer]:
    """Return each config layer as (data, label), **lowest** priority first.

    Layers (each overrides the previous):
      1. Built-in defaults
      2. System-wide config  ($ZEDIT_SYSCONFDIR/zedit/config.toml)
      3. User-global config  (~/.config/zedit/config.toml)
      4. Project-local       (./.zedit.toml in CWD)
      5. --config FILE       (ad-hoc override)
    """
    layers: list[ConfigLayer] = [
        (_parse_toml_str(_DEFAULT_CONFIG_TOML), "built-in defaults"),
    ]
    sys_path = _system_config_path()
    if sys_path.exists():
        layers.append((_parse_toml_file(sys_path), f"system  ({sys_path})"))
    user_path = _user_config_path()
    if user_path.exists():
        layers.append((_parse_toml_file(user_path), f"user    ({user_path})"))
    local_path = Path.cwd() / f".{APP_NAME}.toml"
    if local_path.exists():
        layers.append((_parse_toml_file(local_path), f"project ({local_path})"))
    if extra_config is not None:
        layers.append((_parse_toml_file(extra_config), f"--config ({extra_config})"))
    return layers


def load_config(extra_config: Path | None = None) -> dict[str, Any]:
    """Load and deep-merge config from all layers (highest priority wins)."""
    result: dict[str, Any] = {}
    for data, _ in load_config_layers(extra_config):
        result = _deep_merge(result, data)
    return result


def collect_editor_candidates(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
) -> list[tuple[str, str]]:
    """Build a priority-ordered list of ``(resolved_editor, source_label)`` for *file_path*.

    Priority rules (highest first):

    * Higher config layer beats lower (project > user > system > built-in defaults).
    * Within a layer, a **later**-defined mapping key beats an earlier one (last wins).
    * Within a layer, when both a MIME and an extension entry match, their relative
      order is controlled by the effective ``prefer_mime`` setting.

    Editors are deduplicated — the first occurrence (highest priority) is kept.
    If no mapping matches at all, the effective ``defaults.editor`` is returned as a
    single-element list so the caller always has something to work with.
    """
    # ── Detect MIME and extension ──────────────────────────────────────────────
    detected_mime: str | None = mime_override or (
        detect_mime(file_path) if file_path.exists() else None
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
        resolved = _resolve_sentinel(raw)
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
        ext_hit  = _find_ext(data.get("extensions", {}))

        # Interleave mime / extension results in prefer_mime order
        hits: list[tuple[tuple[str, str], str] | None] = (
            [
                ((mime_hit[0], mime_hit[1]), "mime_types") if mime_hit else None,
                ((ext_hit[0],  ext_hit[1]),  "extensions") if ext_hit  else None,
            ]
            if prefer_mime else
            [
                ((ext_hit[0],  ext_hit[1]),  "extensions") if ext_hit  else None,
                ((mime_hit[0], mime_hit[1]), "mime_types") if mime_hit else None,
            ]
        )
        for item in hits:
            if item is not None:
                (raw_val, key), section = item
                _add(raw_val, f"{source_label}  [{section}][{key!r}]")

    # ── Fallback to defaults.editor when nothing matched ──────────────────────
    if not candidates:
        for data, source_label in reversed(layers):
            fb = data.get("defaults", {}).get("editor")
            if fb is not None:
                _add(fb, f"{source_label}  [defaults][editor]")
                break
        if not candidates:
            _add(_SENTINEL, "built-in fallback")

    return candidates


def resolve_editor(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
    verbose: bool = False,
) -> str:
    """Return the highest-priority editor for *file_path*.

    Delegates to :func:`collect_editor_candidates` and returns the first entry's
    command string.  Use *verbose* to print resolution details to stderr.
    """
    candidates = collect_editor_candidates(file_path, layers, mime_override=mime_override)
    editor, source = candidates[0]
    if verbose:
        mime = mime_override or (detect_mime(file_path) if file_path.exists() else None)
        suffix = file_path.suffix.lower() or None
        print(
            f"  mime: {mime or '(unknown)'}  ext: {suffix or '(none)'}",
            file=sys.stderr,
        )
        print(f"  → {editor!r}  (from {source})", file=sys.stderr)
        if len(candidates) > 1:
            print(
                f"  ({len(candidates) - 1} lower-priority alternative(s) available;"
                " use -c to choose interactively)",
                file=sys.stderr,
            )
    return editor
    """Read *only* the user-global config file (not the merged stack).

    Returns an empty dict when the file does not exist yet.
    """
    p = _user_config_path()
    return _parse_toml_file(p) if p.exists() else {}


def save_user_config(data: dict[str, Any]) -> None:
    """Write *data* to the user config file, creating directories as needed.

    Any existing comments are replaced; the file is fully rewritten.
    """
    p = _user_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# edit user configuration\n"
        "# Written by 'edit --map'.  Manual edits are welcome.\n"
        f"# See 'edit --list' for the full resolved mapping.\n"
    )
    p.write_text(_dict_to_toml(data, header=header))


# ---------------------------------------------------------------------------
# MIME-type detection
# ---------------------------------------------------------------------------

def detect_mime(path: Path) -> str | None:
    """Return the MIME type of *path*, or *None* if it cannot be determined."""
    if _HAVE_LIBMAGIC:
        try:
            mime = _libmagic.from_file(str(path), mime=True)
            if mime:
                return mime
        except Exception:
            pass  # fall through to mimetypes stdlib

    mime, _ = mimetypes.guess_type(str(path))
    return mime


# ---------------------------------------------------------------------------
# Editor resolution
# ---------------------------------------------------------------------------

_SENTINEL = "$EDITOR"


def _resolve_sentinel(value: str) -> str:
    """Replace the ``$EDITOR`` sentinel with the environment-supplied editor."""
    if value != _SENTINEL:
        return value
    return (
        os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or "vi"  # POSIX-guaranteed last resort
    )


# ---------------------------------------------------------------------------
# Config scaffold helper
# ---------------------------------------------------------------------------

def write_default_config(path: Path) -> None:
    """Write a well-commented starter config to *path*."""
    header = """\
# edit configuration file
#
# Locations searched (later files override earlier ones):
#   ~/.config/zedit/config.toml   — user-global config  (this file)
#   ./.zedit.toml                 — project-local override
#
# Editor values may be:
#   - A plain command name:       "vim", "nano", "code --wait"
#   - The special token $EDITOR:  resolved via $VISUAL / $EDITOR env vars
#
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + _DEFAULT_CONFIG_TOML)
    print(f"Config written to {path}")


# ---------------------------------------------------------------------------
# Listing helper
# ---------------------------------------------------------------------------

def print_mappings(cfg: dict[str, Any]) -> None:
    """Pretty-print the resolved editor mappings."""
    def _res(v: str) -> str:
        r = _resolve_sentinel(v)
        return r if v != _SENTINEL else f"{r}  ($EDITOR sentinel)"

    print("=== MIME-type mappings ===")
    for k, v in sorted(cfg.get("mime_types", {}).items()):
        print(f"  {k:<40} → {_res(v)}")

    print("\n=== Extension mappings ===")
    for k, v in sorted(cfg.get("extensions", {}).items()):
        print(f"  {k:<15} → {_res(v)}")

    fallback = cfg.get("defaults", {}).get("editor", _SENTINEL)
    print(f"\n=== Fallback editor ===\n  {_res(fallback)}")

    prefer = cfg.get("defaults", {}).get("prefer_mime", True)
    print(f"\n=== prefer_mime ===\n  {prefer}")


# ---------------------------------------------------------------------------
# -d / --dump: priority-ordered editor list for a file
# ---------------------------------------------------------------------------

def cmd_dump_editors(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
) -> int:
    """Print the priority-ordered editor candidate list for *file_path* and exit.

    Highest-priority editor is listed first and marked as the one that would be
    used on a normal (non-interactive) invocation.
    """
    detected_mime = mime_override or (detect_mime(file_path) if file_path.exists() else None)
    suffix = file_path.suffix.lower() or None
    candidates = collect_editor_candidates(file_path, layers, mime_override=mime_override)

    print(f"File : {file_path}")
    print(f"MIME : {detected_mime or '(unknown)'}")
    print(f"Ext  : {suffix or '(none)'}")
    print(f"\nEditors (decreasing priority):")
    for i, (editor, source) in enumerate(candidates, 1):
        marker = "  ← would be used" if i == 1 else ""
        print(f"  {i}. {editor:<28}  {source}{marker}")
    return 0


# ---------------------------------------------------------------------------
# -c / --choose: interactive editor selection
# ---------------------------------------------------------------------------

def cmd_choose_editor(
    file_path: Path,
    layers: list[ConfigLayer],
    *,
    mime_override: str | None = None,
    dry_run: bool = False,
) -> int:
    """Present a numbered menu of editors and open *file_path* with the chosen one.

    Candidates are listed in priority order (highest first).  Pressing Enter
    without a choice selects the default (top) entry.
    """
    if not file_path.exists():
        print(
            f"Note: '{file_path}' does not exist; MIME detection skipped.",
            file=sys.stderr,
        )
    detected_mime = mime_override or (detect_mime(file_path) if file_path.exists() else None)
    suffix = file_path.suffix.lower() or None
    candidates = collect_editor_candidates(file_path, layers, mime_override=mime_override)

    print(f"\nFile : {file_path}")
    print(f"MIME : {detected_mime or '(unknown)'}")
    print(f"Ext  : {suffix or '(none)'}")
    print(f"\nAvailable editors (highest priority first):")
    width = max(len(ed) for ed, _ in candidates)
    for i, (editor, source) in enumerate(candidates, 1):
        tag = "  [default]" if i == 1 else ""
        print(f"  [{i}] {editor:<{width}}  from {source}{tag}")
    print("  [q] Cancel")

    while True:
        try:
            raw = input("\nChoice [1]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0
        if raw in ("", "1"):
            chosen_editor, chosen_source = candidates[0]
            break
        if raw == "q":
            print("Cancelled.")
            return 0
        if raw.isdigit() and 1 <= int(raw) <= len(candidates):
            chosen_editor, chosen_source = candidates[int(raw) - 1]
            break
        print(f"  Please enter a number 1–{len(candidates)} or 'q' to cancel.")

    cmd = chosen_editor.split() + [str(file_path)]
    if dry_run:
        print(f"would run: {' '.join(cmd)}")
        return 0

    print(f"Opening with: {chosen_editor}  (from {chosen_source})")
    result = subprocess.run(cmd)
    return result.returncode


# ---------------------------------------------------------------------------
# 'ed' alias installation
# ---------------------------------------------------------------------------

def _find_self() -> Path | None:
    """Locate the installed 'zedit' executable."""
    found = shutil.which(APP_NAME)
    if found:
        return Path(found)
    # Invoked directly as a script (python edit.py)
    script = Path(sys.argv[0]).resolve()
    if script.stem == APP_NAME:
        return script
    return None


def install_ed_alias(
    candidates: list[Path] | None = None,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Install an ``ed`` symlink in the first suitable candidate directory.

    Candidate directories (default: ``~/.local/bin``, ``/opt/bin``,
    ``/usr/local/bin``) are tried in order.  For each directory the function:

    * Skips if the directory does not exist.
    * Warns and skips if an ``ed`` entry already exists that does not point
      to this program.
    * Warns if the chosen directory appears *after* a directory that already
      contains a system ``ed`` in PATH (the alias would be shadowed).
    * Creates the symlink and stops at the first success.

    Returns 0 on success, 1 if no symlink could be created.
    """
    if candidates is None:
        candidates = list(_ALIAS_CANDIDATES)

    edit_exe = _find_self()
    if edit_exe is None:
        print(f"error: cannot locate '{APP_NAME}' executable in PATH", file=sys.stderr)
        return 1

    # Build an ordered list of PATH dirs for shadowing analysis.
    path_dirs = [
        Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p
    ]

    any_created = False
    for target_dir in candidates:
        link_path = target_dir / _ALIAS_NAME

        if not target_dir.exists():
            if verbose:
                print(f"  skip {target_dir}: directory does not exist")
            continue

        # --- Conflict check: 'ed' already present in this directory ---
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_symlink():
                dest = link_path.resolve()
                if dest == edit_exe.resolve():
                    print(f"✓ {link_path} already points to '{APP_NAME}' — nothing to do")
                    any_created = True
                    break
                else:
                    print(
                        f"⚠  {link_path} exists and points to {dest} "
                        f"(not '{APP_NAME}') — skipping this location"
                    )
            else:
                print(f"⚠  {link_path} exists as a real file/directory — skipping")
            continue

        # --- Shadowing check: is there a higher-priority 'ed' in PATH? ---
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


# ---------------------------------------------------------------------------
# --map: interactive MIME / extension → editor mapping
# ---------------------------------------------------------------------------

def cmd_map_editor(
    file_path: Path,
    cfg: dict[str, Any],
    *,
    mime_override: str | None = None,
    verbose: bool = False,
) -> int:
    """Interactively update the MIME-type / extension → editor mapping.

    Detects the MIME type and extension of *file_path*, shows the current
    effective mapping (from the merged config stack), then prompts the user
    for a new editor value.  The result is written to the user config file
    (``~/.config/zedit/config.toml``) only — lower-priority layers are not
    touched.
    """
    # --- Detect ---
    if file_path.exists():
        if mime_override:
            detected_mime: str | None = mime_override
            mime_src = "--mime override"
        else:
            detected_mime = detect_mime(file_path)
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
    fallback = cfg.get("defaults", {}).get("editor", _SENTINEL)

    def _eff(raw: str | None) -> str:
        if raw is None:
            return f"{_resolve_sentinel(fallback)}  (fallback)"
        resolved = _resolve_sentinel(raw)
        return f"{resolved}  ($EDITOR)" if raw == _SENTINEL else resolved

    cur_mime_editor: str | None = None
    if detected_mime:
        cur_mime_editor = mime_map.get(detected_mime)
        if cur_mime_editor is None:
            cur_mime_editor = mime_map.get(detected_mime.split("/")[0])

    cur_ext_editor: str | None = ext_map.get(suffix) if suffix else None

    print("\nCurrent mappings (effective, from merged config):")
    if detected_mime:
        print(f"  MIME  {detected_mime!r:<42}  →  {_eff(cur_mime_editor)}")
    if suffix:
        print(f"  Ext   {suffix!r:<42}  →  {_eff(cur_ext_editor)}")

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

    # --- Prompt for new editor value(s) ---
    def _prompt(current_raw: str | None, kind: str, key: str) -> str | None:
        current_disp = (
            current_raw if current_raw is not None
            else f"{_resolve_sentinel(fallback)} (fallback)"
        )
        try:
            val = input(
                f"\nNew editor for {kind} {key!r}\n"
                f"  current : {current_disp}\n"
                f"  (Enter to keep current, '$EDITOR' to follow env var): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return val if val else None

    # Read only the user config layer — we update that file alone.
    user_cfg = read_user_config()
    changed = False

    if chosen_mime is not None:
        new_val = _prompt(cur_mime_editor, "MIME type", chosen_mime)
        if new_val is not None:
            user_cfg.setdefault("mime_types", {})[chosen_mime] = new_val
            print(f"  mime_types[{chosen_mime!r}] = {new_val!r}")
            changed = True

    if chosen_ext is not None:
        new_val = _prompt(cur_ext_editor, "extension", chosen_ext)
        if new_val is not None:
            user_cfg.setdefault("extensions", {})[chosen_ext] = new_val
            print(f"  extensions[{chosen_ext!r}] = {new_val!r}")
            changed = True

    if changed:
        save_user_config(user_cfg)
        print(f"\n✓ Saved to {_user_config_path()}")
    else:
        print("\nNo changes made.")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Open file(s) in the appropriate editor determined by MIME type "
            "or file extension according to a configurable TOML mapping."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
Config file locations (applied in order, later overrides earlier):
  /etc/{APP_NAME}/config.toml        system-wide  (set $ZEDIT_SYSCONFDIR to override /etc)
  ~/.config/{APP_NAME}/config.toml   user-global
  ./.{APP_NAME}.toml                 project-local (CWD)
  FILE given to --config             ad-hoc override

Use `{APP_NAME} --init-config` to write a starter config to the global location.
""",
    )

    p.add_argument("files", nargs="*", metavar="FILE", help="File(s) to open.")
    p.add_argument(
        "-m", "--mime",
        metavar="TYPE",
        help="Override MIME-type detection (e.g. text/x-python).",
    )
    p.add_argument(
        "-e", "--editor",
        metavar="CMD",
        help="Use this editor directly, bypassing all config lookups.",
    )
    p.add_argument(
        "-C", "--config",
        metavar="FILE",
        type=Path,
        help="Additional config file to merge on top of the standard stack.",
    )
    p.add_argument(
        "-c", "--choose",
        action="store_true",
        help=(
            "Present a numbered menu of editors (highest priority first) for each "
            "FILE and let you pick one interactively.  Default choice (Enter) uses "
            "the highest-priority editor."
        ),
    )
    p.add_argument(
        "-d", "--dump",
        action="store_true",
        help=(
            "Dump the priority-ordered list of editors for each FILE and exit.  "
            "The first entry is the one that would be used on a normal invocation."
        ),
    )
    p.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Print the editor command that would be run, but don't launch it.",
    )
    p.add_argument(
        "-l", "--list",
        action="store_true",
        help="Print all configured editor mappings and exit.",
    )
    p.add_argument(
        "--init-config",
        action="store_true",
        help=f"Write a starter config to ~/.config/{APP_NAME}/config.toml and exit.",
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
            "Interactively update the MIME-type / extension → editor mapping "
            "for FILE.  Detects the MIME type and extension, shows the current "
            "mapping, and prompts for a new editor.  Saves to "
            f"~/.config/{APP_NAME}/config.toml."
        ),
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show resolution details on stderr.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --- --init-config ---
    if args.init_config:
        write_default_config(_user_config_path())
        return 0

    # --- --install-alias ---
    if args.install_alias:
        return install_ed_alias(dry_run=args.dry_run, verbose=args.verbose)

    layers = load_config_layers(args.config)

    # --- --map FILE ---
    if args.map is not None:
        cfg = load_config(args.config)
        return cmd_map_editor(
            args.map, cfg, mime_override=args.mime, verbose=args.verbose
        )

    # --- --list ---
    if args.list:
        print_mappings(load_config(args.config))
        return 0

    if not args.files:
        parser.print_help()
        return 1

    exit_code = 0

    for file_arg in args.files:
        file_path = Path(file_arg)

        # --- -d / --dump: print priority list and move on to next file ---
        if args.dump:
            rc = cmd_dump_editors(file_path, layers, mime_override=args.mime)
            if rc != 0:
                exit_code = rc
            continue

        # --- -c / --choose: interactive editor selection ---
        if args.choose:
            rc = cmd_choose_editor(
                file_path, layers, mime_override=args.mime, dry_run=args.dry_run
            )
            if rc != 0:
                exit_code = rc
            continue

        # --- Normal / --editor: resolve and open ---
        if args.editor:
            editor_cmd = args.editor
        else:
            if not file_path.exists() and args.verbose:
                print(
                    f"  {file_arg}: file does not exist; skipping MIME detection",
                    file=sys.stderr,
                )
            editor_cmd = resolve_editor(
                file_path, layers, mime_override=args.mime, verbose=args.verbose
            )

        # Group consecutive files sharing the same editor into one invocation
        pass  # grouping handled below

        cmd = editor_cmd.split() + [str(file_path)]
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
