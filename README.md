# zedit — smart file editor launcher

`zedit` opens files in the right editor automatically. It detects each file's
MIME type (via **libmagic** or the `mimetypes` stdlib) and maps it to an editor
through a layered TOML configuration — system-wide, per-user, and per-project.

```
zedit main.py          → vim          (text/x-python mapping)
zedit report.pdf       → evince       (application/pdf mapping)
zedit image.png        → gimp         (image/png mapping)
zedit README.md        → typora       (.md extension mapping)
```

---

## Quick start

```bash
# Install
pip install .                   # from source
pip install ".[magic]"          # with accurate content-based MIME detection

# Use
zedit myfile.py                  # open with the configured editor
ze myfile.py                    # same — 'ze' is a symlink/alias for 'zedit'
zedit --dry-run *.md             # preview without opening
zedit --list                     # show all configured mappings
zedit --init-config              # scaffold ~/.config/zedit/config.toml
```

---

## Documentation

| Document | Contents |
|---|---|
| [docs/user-guide.md](docs/user-guide.md) | Installation, CLI reference, configuration format, MIME detection, examples, troubleshooting |
| [docs/design.md](docs/design.md) | Architecture, module internals, public API, data-flow, design decisions |
| [docs/build.md](docs/build.md) | All build paths: pip/wheel, CMake, CPack (DEB/RPM/TGZ), `dpkg-buildpackage`, release checklist |

---

## Configuration at a glance

Config files are TOML, loaded and deep-merged in this order:

| Priority | Location | Purpose |
|---|---|---|
| 1 | Built-in defaults | Always present |
| 2 | `/etc/zedit/config.toml` | System-wide (installed by OS package) |
| 3 | `~/.config/zedit/config.toml` | User-global |
| 4 | `./.zedit.toml` in CWD | Project-local |
| 5 | `--config FILE` | Ad-hoc override |

```toml
[defaults]
editor      = "$EDITOR"   # resolved via $VISUAL -> $EDITOR -> vi
prefer_mime = true         # MIME wins over extension when both match

[mime_types]
"text/x-python"   = "vim"
"application/pdf" = "evince"
"image"           = "gimp"    # base-type wildcard: all image/* types

[extensions]
".md"  = "typora"
".mp4" = "vlc"
```

---

## Dependencies

| Package | Required | Purpose |
|---|---|---|
| Python >= 3.11 | Yes | `tomllib` in stdlib |
| `python-magic` | Recommended | Content-based MIME detection via libmagic |

Without `python-magic` the app falls back to extension-based guessing.
