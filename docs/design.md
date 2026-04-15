---
layout: default
title: Z-Open Design and Architecture
---

# zopen — Design and Code Documentation

This document describes the internal architecture of `zopen`, the data
structures it uses, the responsibilities of every public function, and
the points at which the behaviour can be extended.

---

## Table of contents

1. [Overview](#1-overview)
2. [Module structure](#2-module-structure)
3. [Dependency graph](#3-dependency-graph)
4. [Constants and built-in defaults](#4-constants-and-built-in-defaults)
5. [Configuration subsystem](#5-configuration-subsystem)
   - 5.1 [Config schema](#51-config-schema)
   - 5.2 [Config loading pipeline](#52-config-loading-pipeline)
   - 5.3 [Deep-merge algorithm](#53-deep-merge-algorithm)
   - 5.4 [Public API](#54-public-api)
6. [MIME-type detection subsystem](#6-mime-type-detection-subsystem)
7. [Editor resolution subsystem](#7-editor-resolution-subsystem)
   - 7.1 [The `$EDITOR` sentinel](#71-the-editor-sentinel)
   - 7.2 [Resolution algorithm](#72-resolution-algorithm)
   - 7.3 [Public API](#73-public-api)
8. [CLI subsystem](#8-cli-subsystem)
   - 8.1 [Argument parser](#81-argument-parser)
   - 8.2 [`main()` control flow](#82-main-control-flow)
   - 8.3 [Multi-file grouping](#83-multi-file-grouping)
9. [Helper utilities](#9-helper-utilities)
10. [Error handling strategy](#10-error-handling-strategy)
11. [Extension points](#11-extension-points)
12. [Design decisions and trade-offs](#12-design-decisions-and-trade-offs)

---

## 1. Overview

`zopen` is intentionally a **single Python module** (`zopen.py`). The entire
application lives in one file to make it trivially deployable: copy the
file, mark it executable, done. Packaging (wheel, deb, tarball) is layered
on top but is not required to use the tool.

The application pipeline for every invocation is:

```
argv
  │
  ▼
build_parser() → parse_args()
  │
  ▼
load_config()          ← reads TOML files, deep-merges into one dict
  │
  ▼
for each FILE:
  detect_mime()        ← libmagic → mimetypes fallback
  resolve_editor()     ← mime lookup → ext lookup → fallback → sentinel
  group by editor
  │
  ▼
subprocess.run(editor + files)
```

---

## 2. Module structure

`zopen.py` is divided into clearly delimited sections, each introduced by a
separator comment:

| Section | Symbols | Purpose |
|---|---|---|
| Imports & compatibility shims | `tomllib`, `_libmagic`, `_HAVE_LIBMAGIC` | Optional dependency handling |
| Constants | `APP_NAME`, `_DEFAULT_CONFIG_TOML` | Hard-coded defaults |
| Config loading | `_parse_toml_str`, `_parse_toml_file`, `_deep_merge`, `_system_config_path`, `load_config` | Read and merge TOML |
| MIME detection | `detect_mime` | Identify file content type |
| Editor resolution | `_SENTINEL`, `_resolve_sentinel`, `resolve_editor` | Map type → editor command |
| Helper utilities | `write_default_config`, `print_mappings` | `--init-config`, `--list` |
| CLI | `build_parser`, `main` | Argument parsing and orchestration |

Symbols prefixed with a single underscore (`_`) are internal and not part of
any public API.

---

## 3. Dependency graph

```
main()
├── build_parser()                  [argparse stdlib]
├── load_config()
│   ├── _parse_toml_str()           [tomllib stdlib / tomli]
│   ├── _parse_toml_file()          [tomllib stdlib / tomli]
│   ├── _system_config_path()       [os, pathlib]
│   └── _deep_merge()               [pure Python]
├── detect_mime()
│   ├── magic.from_file()           [python-magic — optional]
│   └── mimetypes.guess_type()      [mimetypes stdlib]
├── resolve_editor()
│   ├── detect_mime()
│   └── _resolve_sentinel()         [os.environ]
└── subprocess.run()                [subprocess stdlib]
```

External runtime dependencies:

| Package | Import | Required | Notes |
|---|---|---|---|
| `tomllib` | `import tomllib` | Python ≥ 3.11 — built-in | Older Python: install `tomli` |
| `python-magic` | `import magic` | No | Improves MIME accuracy; graceful fallback |

All other imports (`argparse`, `mimetypes`, `os`, `subprocess`, `sys`,
`pathlib`, `typing`) are Python standard library.

---

## 4. Constants and built-in defaults

### `APP_NAME = "zopen"`

The application's canonical name. Used to construct config paths
(`~/.config/zopen/`, `/opt/etc/zopen/`) and in help text. Changing this string is
the only modification needed to fork the tool under a different name.

### `_DEFAULT_CONFIG_TOML: str`

A TOML string embedded verbatim in the module. It is the lowest-priority
configuration layer — always present, never absent, never read from disk.

All editor values in the built-in defaults are the `"$EDITOR"` sentinel,
meaning the tool defers to the user's `$VISUAL` / `$EDITOR` environment
variables by default. This makes the tool useful out of the box even before
any config file is written.

The string is also written to disk verbatim (with an added header comment)
by `write_default_config()` when the user runs `--init-config`.

---

## 5. Configuration subsystem

### 5.1 Config schema

The merged config is a plain Python `dict[str, Any]` with the following
top-level keys (all optional; defaults apply when absent):

```python
{
    "defaults": {
        "editor":      str,   # editor command or "$EDITOR" sentinel
        "prefer_mime": bool,  # MIME wins over extension when both match
    },
    "mime_types": {
        str: str,             # MIME type string → editor command
        # e.g. "text/x-python": "vim"
    },
    "extensions": {
        str: str,             # lowercase dotted extension → editor command
        # e.g. ".py": "vim"
    },
}
```

There is intentionally no validation schema or Pydantic model. Unrecognised
keys are silently ignored so that future config versions remain backward
compatible with older binaries.

### 5.2 Config loading pipeline

```
_DEFAULT_CONFIG_TOML (str)
        │  _parse_toml_str()
        ▼
    base dict
        │  _deep_merge()
        ▼
/opt/etc/zopen/config.toml  (if it exists)
        │  _deep_merge()
        ▼
~/.config/zopen/config.toml  (if it exists)
        │  _deep_merge()
        ▼
./.zopen.toml  (if it exists in CWD)
        │  _deep_merge()
        ▼
--config FILE  (if --config was passed)
        │  _deep_merge()
        ▼
  final merged dict  →  returned to caller
```

Each layer is optional (except the built-in defaults). Missing files are
silently skipped. Parse errors in user or system configs propagate as
`tomllib.TOMLDecodeError` exceptions and are not caught — they produce a
traceback so the user can find and fix the problem.

### 5.3 Deep-merge algorithm

`_deep_merge(base, override)` creates a shallow copy of `base` then walks
`override`:

- If both `base[key]` and `override[key]` are dicts → recurse.
- Otherwise → `override[key]` replaces `base[key]`.

This means:

- `[mime_types]` and `[extensions]` tables from multiple files are merged
  key-by-key (entries from higher-priority files win; entries only in
  lower-priority files are kept).
- Scalar values (strings, booleans) in `[defaults]` are replaced outright.

The function never mutates its inputs; it always returns a new dict.

### 5.4 Public API

#### `load_config(extra_config: Path | None = None) -> dict[str, Any]`

Returns the fully-merged configuration dictionary. Reads all applicable
config files from disk in priority order.

| Parameter | Type | Description |
|---|---|---|
| `extra_config` | `Path \| None` | If supplied, this file is loaded and merged last (highest priority). Corresponds to `--config FILE`. |

**Returns:** merged config dict.  
**Raises:** `tomllib.TOMLDecodeError` if any config file is malformed.  
**Side effects:** reads files from disk.

#### `_system_config_path() -> Path`

Returns the path to the system-wide config file. Respects the
`ZOPEN_SYSCONFDIR` environment variable so that staged installs (e.g., during
`dpkg-buildpackage` or `cmake --install DESTDIR=...`) point at the correct
prefix.

#### `_deep_merge(base, override) -> dict`

Internal. Recursively merges `override` into a copy of `base`. See §5.3.

---

## 6. MIME-type detection subsystem

#### `detect_mime(path: Path) -> str | None`

Attempts to determine the MIME type of the file at `path`. Returns the MIME
type string (e.g. `"text/x-python"`) or `None` if detection fails.

Detection order:

1. **libmagic** (`python-magic`): calls `magic.from_file(str(path), mime=True)`.
   This reads the file's content and magic bytes. Any exception is caught and
   silently suppressed so that detection falls through to step 2.

2. **`mimetypes.guess_type`**: uses the filename/extension and the platform's
   MIME database. Returns `(mime, encoding)` — only `mime` is used.

`_HAVE_LIBMAGIC` is a module-level boolean set at import time. It is checked
inside `detect_mime()` on every call rather than being baked into the function
via a closure, so that tests can monkeypatch it.

---

## 7. Editor resolution subsystem

### 7.1 The `$EDITOR` sentinel

`_SENTINEL = "$EDITOR"` is a string constant. Any editor value equal to this
sentinel is **not passed to the shell** — it is expanded in Python by
`_resolve_sentinel()`:

```python
def _resolve_sentinel(value: str) -> str:
    if value != _SENTINEL:
        return value
    return (
        os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or "vi"
    )
```

The sentinel is never expanded during config loading — only immediately before
the editor command is returned from `resolve_editor()`. This means `--list`
can show both the configured value (`$EDITOR sentinel`) and the resolved value
side by side.

### 7.2 Resolution algorithm

`resolve_editor` performs a **lookup with two independent keys** — MIME type
and file extension — then applies a tiebreak:

```
input:  file_path, config dict, mime_override, verbose flag

1. mime_type ← mime_override  OR  detect_mime(file_path)

2. mime_editor ← mime_types.get(mime_type)
                 OR mime_types.get(mime_type.split("/")[0])   # base type

3. ext_editor  ← extensions.get(file_path.suffix.lower())

4. chosen ←
     if mime_editor and ext_editor:
         prefer_mime → mime_editor, else → ext_editor
     elif mime_editor: mime_editor
     elif ext_editor:  ext_editor
     else:             defaults.editor

5. return _resolve_sentinel(chosen)
```

Step 2's base-type fallback (`"text"`, `"image"`, `"application"`, …) lets
one config entry cover an entire family of MIME types without listing each
subtype explicitly.

### 7.3 Public API

#### `resolve_editor(file_path, cfg, *, mime_override=None, verbose=False) -> str`

| Parameter | Type | Description |
|---|---|---|
| `file_path` | `Path` | Path to the file being opened. Used for MIME detection and extension extraction. |
| `cfg` | `dict[str, Any]` | Merged config as returned by `load_config()`. |
| `mime_override` | `str \| None` | If given, skip MIME detection and use this value instead. Corresponds to `--mime TYPE`. |
| `verbose` | `bool` | If `True`, print resolution trace to stderr. |

**Returns:** a fully-resolved editor command string (sentinel already expanded),
ready to be split and passed to `subprocess.run`.  
**Raises:** nothing (all lookups use `.get()` with fallbacks).

---

## 8. CLI subsystem

### 8.1 Argument parser

`build_parser() -> argparse.ArgumentParser`

Constructs and returns the parser. Uses `RawDescriptionHelpFormatter` so the
epilog (which lists config file paths) preserves its layout.

The parser is built in a separate function (not inline in `main`) so it can
be called independently in tests, documentation generators, and shell
completion scripts.

### 8.2 `main()` control flow

```python
def main(argv: list[str] | None = None) -> int
```

| Step | Action |
|---|---|
| 1 | `parse_args(argv)` — `argv=None` means use `sys.argv[1:]` |
| 2 | `--init-config` → `write_default_config()` → return 0 |
| 3 | `load_config(args.config)` — build merged config |
| 4 | `--list` → `print_mappings(cfg)` → return 0 |
| 5 | No files → `print_help()` → return 1 |
| 6 | For each file: `resolve_editor()` → group by editor |
| 7 | For each group: `subprocess.run(editor + files)` |
| 8 | Return 0 if all editors succeeded, else last non-zero exit code |

`main` accepts an optional `argv` list so that it can be called directly in
unit tests without forking a subprocess:

```python
from zopen import main
assert main(["--dry-run", "test.py"]) == 0
```

### 8.3 Multi-file grouping

When multiple files are passed, they are grouped into **consecutive runs**
that share the same resolved editor:

```python
groups: list[tuple[str, list[str]]] = []
for file_arg in args.files:
    editor_cmd = resolve_editor(...)
    if groups and groups[-1][0] == editor_cmd:
        groups[-1][1].append(file_arg)
    else:
        groups.append((editor_cmd, [file_arg]))
```

Files that map to the same editor are passed together in one invocation
(`vim a.py b.py`). Files that map to different editors cause separate,
sequential invocations. The order of files on the command line is preserved.

The "consecutive run" approach (rather than grouping all files by editor
globally) preserves order semantics: `zopen a.py README.md b.py` with `.py →
vim` and `.md → typora` will launch `vim a.py`, then `typora README.md`,
then `vim b.py` — not `vim a.py b.py` then `typora README.md`.

---

## 9. Helper utilities

### `write_default_config(path: Path) -> None`

Writes the built-in defaults as a commented TOML file to `path`, creating
parent directories with `mkdir -p` semantics. Used by `--init-config`.

The written file prepends a header comment block explaining the config
locations and editor value syntax, then appends `_DEFAULT_CONFIG_TOML`
verbatim. This means the on-disk format always stays in sync with the
compiled-in defaults.

### `print_mappings(cfg: dict[str, Any]) -> None`

Formats and prints the effective MIME-type table, extension table, fallback
editor, and `prefer_mime` flag to stdout. Each editor value is shown in both
its raw form and its resolved form when it is the `$EDITOR` sentinel.

---

## 10. Error handling strategy

| Situation | Behaviour |
|---|---|
| Config file does not exist | Silently skipped; no error. |
| Config file is malformed TOML | `TOMLDecodeError` propagates; Python prints a traceback with the line number. |
| MIME detection raises any exception | Caught inside `detect_mime()`; falls through to the next detection method silently. |
| Editor binary not found | `subprocess.run` raises `FileNotFoundError` — not caught; Python prints a traceback. The editor value is wrong and the user must fix their config. |
| Editor exits non-zero | Captured; `main()` returns that exit code after processing remaining files. |

The design prefers **fail loudly on programmer errors** (bad config, missing
binary) and **fail silently on detection uncertainty** (MIME detection
exceptions are recoverable).

---

## 11. Extension points

The module is designed to be imported and used programmatically. All
public-facing functions accept typed arguments and return plain Python values.

### Programmatic use

```python
from pathlib import Path
from edit import load_config, resolve_editor, detect_mime

cfg = load_config()
editor = resolve_editor(Path("report.pdf"), cfg)
print(f"would open with: {editor}")

mime = detect_mime(Path("data"))
print(f"detected MIME: {mime}")
```

### Adding a new config source

Insert a new `_deep_merge` call inside `load_config()`. For example, to read
from an XDG config directory:

```python
xdg_cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
xdg_path = xdg_cfg / APP_NAME / "config.toml"
if xdg_path.exists():
    cfg = _deep_merge(cfg, _parse_toml_file(xdg_path))
```

(The current implementation already uses `~/.config/zopen/config.toml`, which
is the standard XDG user config location.)

### Replacing the MIME detection backend

`detect_mime()` can be monkey-patched or subclassed in tests:

```python
import zopen
zopen.detect_mime = lambda path: "text/x-python"  # always return Python
```

For a more robust extension, replace the module-level `_HAVE_LIBMAGIC` flag
and provide a custom detection function before calling `resolve_editor`.

### Supporting new config file formats

Add a new `_parse_*` function and call it in `load_config()`. The merged dict
structure is format-agnostic — only the parser needs to change.

---

## 12. Design decisions and trade-offs

### Single-file module

**Decision:** everything in `zopen.py`, no sub-package.  
**Rationale:** the tool is small enough that the complexity of a package
(`__init__.py`, `__main__.py`, relative imports) outweighs the benefit.
A single file is trivially deployable and readable in one sitting.  
**Trade-off:** if the tool grows significantly, splitting into a package
(`config.py`, `detector.py`, `resolver.py`, `cli.py`) would improve
maintainability.

### No validation of config values

**Decision:** unrecognised config keys are silently ignored; editor values
are not validated at load time.  
**Rationale:** validation at load time would fail on config files written for
future versions of the tool. Runtime failures (missing editor binary) are
surfaced by the OS naturally.  
**Trade-off:** typos in key names (e.g. `mime_type` instead of `mime_types`)
are silently ignored. `--list` is the tool's self-diagnostic for this.

### `$EDITOR` as a string sentinel rather than a shell variable

**Decision:** `"$EDITOR"` is a special string, not evaluated by a shell.  
**Rationale:** passing editor values through a shell introduces quoting
complexity and a security surface. By doing the environment lookup in Python,
the behaviour is explicit, testable, and consistent across shells.  
**Trade-off:** shell features (e.g. `${EDITOR:-vim}`, command substitution)
cannot be used in config editor values.

### Deep-merge rather than file replacement

**Decision:** higher-priority config files extend lower-priority ones
key-by-key; they do not replace entire tables.  
**Rationale:** system admins who set `/opt/etc/zopen/config.toml` typically want
users to be able to add personal mappings, not just override the whole file.  
**Trade-off:** there is no way to explicitly delete a lower-priority entry
(only overwrite it with `"$EDITOR"` to neutralise it).

### No shell quoting for editor flags

**Decision:** `editor_cmd.split()` is used to split the editor command string.  
**Rationale:** simple and predictable; supports the common case of
`"code --wait"` or `"vim -p"` without a shell.  
**Trade-off:** editor paths or flag values containing spaces cannot be
expressed. This is an acceptable limitation for the expected use cases.
