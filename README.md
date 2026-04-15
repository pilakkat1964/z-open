# zopen — smart file editor launcher

> **About this project:** `zopen` was designed and built to explore the power of
> AI-assisted development. The entire codebase was written primarily using
> **Claude Sonnet 4.6** (the "medium" model) accessed through **GitHub Copilot**.

`zopen` opens files in the right editor automatically. It detects each file's
MIME type (via **libmagic** or the `mimetypes` stdlib) and maps it to an editor
through a layered TOML configuration — system-wide, per-user, and per-project.

```
zopen main.py          → vim          (text/x-python mapping)
zopen report.pdf       → evince       (application/pdf mapping)
zopen image.png        → gimp         (image/png mapping)
zopen README.md        → typora       (.md extension mapping)
```

---

## Quick start

**Using uv (fast, recommended):**
```bash
# Install uv if you don't have it
# See: https://docs.astral.sh/uv/getting-started/

# Install zopen
uv pip install .                   # from source
uv pip install ".[magic]"          # with accurate content-based MIME detection

# Use
uv run zopen myfile.py            # open with the configured editor
```

**Using pip:**
```bash
# Install
pip install .                     # from source
pip install ".[magic]"            # with accurate content-based MIME detection

# Use
zopen myfile.py                   # open with the configured editor
```

**Additional commands:**
```bash
zopen --dry-run *.md              # preview without opening
zopen --list                      # show all configured mappings
zopen --init-config               # scaffold ~/.config/zopen/config.toml
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
| 2 | `/etc/zopen/config.toml` | System-wide (installed by OS package) |
| 3 | `~/.config/zopen/config.toml` | User-global |
| 4 | `./.zopen.toml` in CWD | Project-local |
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

## Installation & Dependencies

| Package | Required | Purpose |
|---|---|---|
| Python >= 3.10 | Yes | Language runtime (3.11+ for tomllib) |
| **uv** | Recommended | Fast Python package management |
| `pip` or `uv pip` | Yes | Package installation |
| `python-magic` | Recommended | Content-based MIME detection via libmagic |

**Installation methods:**

```bash
# Fastest: using uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh    # Install uv
uv pip install .                                     # Install zopen

# Standard: using pip
pip install .

# Development: create virtual environment first
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"    # Editable install with dev tools
```

Without `python-magic` the app falls back to extension-based guessing.
