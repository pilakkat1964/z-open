---
layout: default
title: Z-Open User Guide
---

# zopen — User Guide

`zopen` is a smart file-editor launcher. Instead of typing the editor name
yourself, you run `zopen <file>` and the right editor opens automatically,
chosen by MIME type (content-based) or file extension, according to a
layered TOML configuration you control at the system, user, and project level.

---

## Table of contents

1. [Installation](#1-installation)
   - 1.1 [From a Debian / Ubuntu package](#11-from-a-debian--ubuntu-package)
   - 1.2 [From a Python wheel (pip)](#12-from-a-python-wheel-pip)
   - 1.3 [From the tarball (cmake --install)](#13-from-the-tarball-cmake---install)
   - 1.4 [Developer / editable install](#14-developer--editable-install)
2. [Quick start](#2-quick-start)
3. [CLI reference](#3-cli-reference)
4. [Configuration](#4-configuration)
   - 4.1 [Config file locations and precedence](#41-config-file-locations-and-precedence)
   - 4.2 [Config file format](#42-config-file-format)
   - 4.3 [The `$EDITOR` sentinel](#43-the-editor-sentinel)
   - 4.4 [Editor values with flags](#44-editor-values-with-flags)
   - 4.5 [Deep-merge semantics](#45-deep-merge-semantics)
   - 4.6 [MIME base-type wildcard](#46-mime-base-type-wildcard)
   - 4.7 [Scaffolding a starter config](#47-scaffolding-a-starter-config)
5. [MIME-type detection](#5-mime-type-detection)
6. [Editor resolution logic](#6-editor-resolution-logic)
7. [Common workflows](#7-common-workflows)
8. [Environment variables](#8-environment-variables)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Installation

### 1.1 From a Debian / Ubuntu package

The preferred method for system-wide installation on Debian-based systems.
The package places the `zopen` binary in `/usr/bin` and installs the
system-wide config to `/opt/etc/zopen/config.toml` as a managed **conffile**
(preserved across upgrades unless you choose to overwrite it).

```bash
# If you have the .deb file:
sudo dpkg -i edit_0.1.0-1_all.deb

# Install any missing dependencies afterwards:
sudo apt-get install -f

# Or, if a repository is configured:
sudo apt-get install zopen
```

To also get accurate content-based MIME detection (highly recommended):

```bash
sudo apt-get install python3-magic
```

To remove the package while preserving `/opt/etc/zopen/config.toml`:

```bash
sudo apt-get remove zopen
```

To remove the package **and** purge the config:

```bash
sudo apt-get purge zopen
```

---

### 1.2 From a Python wheel (pip)

Suitable for user-level installs without root privileges, virtual environments,
or any platform with Python ≥ 3.11.

```bash
# Install for the current user only (no root needed)
pip install --user zopen-0.5.0-py3-none-any.whl

# Or install into the active virtual environment
pip install zopen-0.5.0-py3-none-any.whl

# With libmagic support (recommended)
pip install "zopen-0.5.0-py3-none-any.whl[magic]"

# Or directly from source
pip install .
pip install ".[magic]"
```

> **Note:** A pip install does **not** create `/opt/etc/zopen/config.toml`.
> The system-wide config layer is simply skipped when that file does not exist.
> Use `zopen --init-config` to create a personal config instead.

---

### 1.3 From the tarball (cmake --install)

The CPack-generated tarball (`zopen-0.5.0-Linux.tar.gz`) is a pre-staged tree
that can be unpacked into any prefix.

```bash
tar -xzf zopen-0.5.0-Linux.tar.gz -C /usr/local --strip-components=1
```

Or use CMake's install step directly from a build tree (see
[docs/build.md](build) for the full CMake workflow):

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build build
sudo cmake --install build
```

---

### 1.4 Developer / editable install

```bash
git clone https://github.com/proteus-cpi/zopen
cd zopen

# Editable install — changes to zopen.py take effect immediately
pip install -e .

# Run without installing
python zopen.py --help
python -m zopen --help   # if __main__.py is present
```

---

## 2. Quick start

```bash
# Open a file — editor is chosen automatically
zopen README.md
zopen src/main.py
zopen config.json

# Open multiple files at once
zopen *.py

# Preview what would happen without launching anything
zopen --dry-run report.pdf image.png

# See the full mapping table currently in effect
zopen --list

# Create a personal config to start customising
zopen --init-config
```

---

## 3. CLI reference

```
zopen [OPTIONS] [FILE ...]
```

| Option | Short | Description |
|---|---|---|
| `--mime TYPE` | `-m` | Override MIME-type detection. `TYPE` must be a valid MIME type string, e.g. `text/x-python`. |
| `--editor CMD` | `-e` | Use this editor unconditionally, bypassing all config lookups. `CMD` may include flags: `"code --wait"`. |
| `--config FILE` | `-c` | Load an additional TOML file on top of the standard config stack. Merged last (highest priority). |
| `--dry-run` | `-n` | Print the editor command(s) that would be executed to **stdout**, then exit without launching. |
| `--list` | `-l` | Print all MIME-type mappings, extension mappings, fallback editor, and `prefer_mime` setting, then exit. |
| `--init-config` | | Write a commented starter config to `~/.config/zopen/config.toml` and exit. Safe to run on a fresh install; will **overwrite** any existing file. |
| `--verbose` | `-v` | Print resolution details (detected MIME type, which mapping matched, which strategy won) to **stderr**. |
| `--help` | `-h` | Show help and exit. |

### Positional arguments

`FILE ...` — One or more file paths to open. Files may or may not exist; if
a file does not exist, MIME detection is skipped and only the extension is
used. Multiple files that resolve to the **same editor** are passed to that
editor in a single invocation. If they resolve to different editors they are
launched in separate sequential invocations.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | All editors exited successfully, or `--list` / `--dry-run` / `--init-config` completed. |
| `1` | No FILE arguments supplied (help was printed). |
| other | The exit code of the last editor invocation that failed. |

---

## 4. Configuration

### 4.1 Config file locations and precedence

Configuration is loaded from up to five sources and **deep-merged** in this
order. A later source overrides a earlier one for any key that appears in both;
keys present only in an earlier source are kept unchanged.

| Priority | Path | When used |
|---|---|---|
| 1 (lowest) | Built-in defaults | Always; hardcoded inside `zopen.py`. |
| 2 | `/opt/etc/zopen/config.toml` | When the file exists. Installed by OS packages. Override path via `$ZOPEN_SYSCONFDIR`. |
| 3 | `~/.config/zopen/config.toml` | When the file exists. Personal preferences. |
| 4 | `./.zopen.toml` in CWD | When the file exists. Project-level overrides. |
| 5 (highest) | File given to `--config` | When `--config FILE` is passed. Ad-hoc overrides. |

The `--editor CMD` flag bypasses the entire config lookup.

---

### 4.2 Config file format

Config files are [TOML](https://toml.io) and contain three sections:

```toml
# ── Behaviour settings ────────────────────────────────────────────────────────
[defaults]
editor     = "$EDITOR"   # fallback when no mapping matches
prefer_mime = true        # true = MIME wins over extension when both match

# ── Content-based editor mapping ──────────────────────────────────────────────
[mime_types]
"text/x-python"   = "vim"
"text/html"       = "vim"
"application/pdf" = "evince"
"image/png"       = "gimp"
"image/jpeg"      = "gimp"
"audio/mpeg"      = "audacity"
"video/mp4"       = "vlc"

# ── Extension-based editor mapping ────────────────────────────────────────────
[extensions]
".py"  = "vim"
".md"  = "typora"
".jpg" = "gimp"
".mp4" = "vlc"
".pdf" = "evince"
```

All three sections are optional. Any section omitted in a user or project
config inherits the values from lower-priority configs.

---

### 4.3 The `$EDITOR` sentinel

The special string `"$EDITOR"` in any editor value is **not** a shell variable
— it is a sentinel recognised by `zopen` itself. At runtime it is resolved
through the following chain, stopping at the first non-empty value:

```
$VISUAL  →  $EDITOR  →  vi   (POSIX-guaranteed fallback)
```

The bundled built-in defaults use `"$EDITOR"` for every mapping, so `zopen`
behaves like a smart wrapper around your preferred editor out of the box.

To hard-code a specific editor for a mapping, just use its name:

```toml
[extensions]
".py" = "vim"    # always vim, regardless of $VISUAL / $EDITOR
```

---

### 4.4 Editor values with flags

Editor values may include command-line flags. The string is split on
whitespace before being passed to the OS:

```toml
[mime_types]
"text/x-python"  = "vim -p"           # open each file in a new tab
"application/pdf" = "evince --fullscreen"

[extensions]
".ts"  = "code --wait"                # VS Code, waiting for close
".md"  = "ghostwriter"
```

> **Caution:** Only simple whitespace splitting is performed. Shell quoting,
> globbing, and variable expansion are **not** supported in editor values.

---

### 4.5 Deep-merge semantics

When two config files both define `[mime_types]`, the tables are merged
key-by-key, not replaced wholesale:

**System config** (`/opt/etc/zopen/config.toml`):
```toml
[mime_types]
"text/x-python" = "vim"
"text/html"     = "vim"
```

**User config** (`~/.config/zopen/config.toml`):
```toml
[mime_types]
"text/html" = "firefox"    # overrides the system default for HTML
```

**Effective result:**
```toml
[mime_types]
"text/x-python" = "vim"     # kept from system config
"text/html"     = "firefox" # overridden by user config
```

To **delete** a system mapping at the user level, set its value to
`"$EDITOR"` (which then falls through to your preferred editor):

```toml
[mime_types]
"image/png" = "$EDITOR"   # disable the system-set gimp mapping
```

---

### 4.6 MIME base-type wildcard

If the full MIME type (e.g. `image/jpeg`) is not found in `[mime_types]`,
`zopen` retries with just the base type (e.g. `image`). This lets you write
a single catch-all rule:

```toml
[mime_types]
"image" = "gimp"    # matches image/png, image/jpeg, image/webp, …
"video" = "vlc"     # matches video/mp4, video/mkv, …
```

Exact entries always take priority over base-type entries.

---

### 4.7 Scaffolding a starter config

```bash
zopen --init-config
```

This writes a fully-commented copy of the built-in defaults to
`~/.config/zopen/config.toml`, creating the directory if needed.
Edit the file to add your own mappings.

---

## 5. MIME-type detection

`zopen` uses two detection methods, tried in order:

### 1. libmagic (preferred)

When the `python-magic` package is installed, `zopen` uses the C library
`libmagic` to inspect the **content** of the file, not its name. This
correctly identifies:

- Python scripts without a `.py` extension (e.g. executable scripts in `bin/`)
- Renamed files (e.g. a `.txt` file that is actually a JSON document)
- Files with no extension at all

```bash
# Install
sudo apt-get install python3-magic    # Debian/Ubuntu
pip install python-magic              # PyPI
```

### 2. Python `mimetypes` stdlib (fallback)

When `python-magic` is not available, `zopen` falls back to Python's built-in
`mimetypes` module, which guesses the MIME type solely from the file extension
and a platform-specific MIME database. This is fast and has no external
dependencies, but cannot detect content mismatches.

### Forcing a MIME type

Use `--mime` to skip detection entirely and assert a MIME type manually:

```bash
zopen --mime application/json mydata   # treat 'mydata' as JSON
zopen --mime text/x-python script      # treat 'script' as Python
```

---

## 6. Editor resolution logic

For each file, `zopen` follows this decision tree:

```
┌─────────────────────────────────────────────────────┐
│  --editor CMD given?                                │
│  Yes → use CMD for every file, skip all below       │
└───────────────────────┬─────────────────────────────┘
                        │ No
                        ▼
┌─────────────────────────────────────────────────────┐
│  Determine MIME type                                │
│  --mime TYPE given?  → use TYPE                     │
│  else file exists?   → detect via libmagic /        │
│                          mimetypes stdlib           │
│  else (new file)     → MIME = None                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  MIME lookup in [mime_types]                        │
│    1. Exact key  "text/x-python"                    │
│    2. Base type  "text"                             │
│  → mime_editor (may be None)                        │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Extension lookup in [extensions]                   │
│    Lowercase suffix of filename, e.g. ".py"         │
│  → ext_editor (may be None)                         │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Both mime_editor AND ext_editor found?             │
│    prefer_mime = true  → use mime_editor            │
│    prefer_mime = false → use ext_editor             │
│  Only one found        → use that one               │
│  Neither found         → use defaults.editor        │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Resolve "$EDITOR" sentinel if present              │
│    $VISUAL → $EDITOR → "vi"                         │
└─────────────────────────────────────────────────────┘
```

Use `--verbose` to see each step printed to stderr in real time.

---

## 7. Common workflows

### Use a specific editor for all web files

```toml
# ~/.config/zopen/config.toml
[mime_types]
"text/html"       = "code --wait"
"text/css"        = "code --wait"
"text/javascript" = "code --wait"

[extensions]
".html" = "code --wait"
".css"  = "code --wait"
".js"   = "code --wait"
".ts"   = "code --wait"
```

### Open images and PDFs in GUI viewers

```toml
[mime_types]
"image"           = "eog"       # GNOME image viewer (base-type wildcard)
"application/pdf" = "evince"

[extensions]
".pdf" = "evince"
".svg" = "inkscape"
```

### Per-project config (no root needed)

Drop a `.zopen.toml` in your project root to override any mapping locally:

```toml
# .zopen.toml — checked in with the project
[defaults]
prefer_mime = false    # extension wins in this project

[extensions]
".py"   = "emacs"
".md"   = "ghostwriter"
```

### Inspect what would open before committing

```bash
# See the editor for each file without opening anything
zopen --dry-run --verbose $(git diff --name-only)
```

### Override from a script

```bash
#!/bin/bash
# Always use vim in this script, regardless of user config
zopen --editor vim "$@"
```

---

## 8. Environment variables

| Variable | Effect |
|---|---|
| `VISUAL` | Preferred editor. Resolved when an editor value is the `$EDITOR` sentinel, checked before `EDITOR`. |
| `EDITOR` | Fallback editor. Resolved when `VISUAL` is unset or empty. |
| `ZOPEN_SYSCONFDIR` | Overrides the directory searched for the system-wide config (default: `/etc`). Useful for staged installs or non-standard prefixes. |

Example: use a non-standard system config location:

```bash
ZOPEN_SYSCONFDIR=/opt/myapp/etc zopen myfile.py
```

---

## 9. Troubleshooting

### Wrong editor is opening

Run with `--verbose` to trace the resolution:

```bash
zopen --verbose --dry-run myfile.py
```

The output shows:
- The detected MIME type and detection method
- Which `[mime_types]` key matched (if any)
- Which `[extensions]` key matched (if any)
- Which strategy won (`prefer_mime`)
- The final resolved editor command

Then run `--list` to see the full effective config:

```bash
zopen --list
```

### MIME type is wrong

libmagic may misidentify some file types (e.g., short files, empty files).
Force the correct type with `--mime`:

```bash
zopen --mime text/x-python myscript
```

Or disable MIME-based lookup for that extension by only defining it in
`[extensions]` and setting `prefer_mime = false` for the project.

### `$EDITOR` resolves to `vi` but I want something else

Set the environment variables in your shell profile:

```bash
# ~/.bashrc or ~/.zshrc
export VISUAL=vim
export EDITOR=vim
```

Or hard-code the editor in your config:

```toml
[defaults]
editor = "vim"
```

### `python3-magic` is installed but MIME detection still uses `mimetypes`

Check that the Python binding and the system library are both present:

```bash
python3 -c "import magic; print(magic.from_file('/etc/hostname', mime=True))"
```

If this raises an error, install the system library:

```bash
sudo apt-get install libmagic1
```

### Config file is not being picked up

Verify the path and TOML syntax:

```bash
python3 -c "import tomllib; tomllib.load(open('$HOME/.config/zopen/config.toml', 'rb'))"
```

A parse error prints the line number. The config is silently ignored if the
file does not exist — `zopen --list` will then show only built-in defaults.
