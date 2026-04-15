---
layout: default
title: Z-Open Documentation
---

# Z-Open — Smart File Opener

**Automatically open files with the right application based on MIME type or file extension.**

A single-file Python application that intelligently launches appropriate applications for any file type through layered TOML configuration.

## Quick Links

- **[GitHub Repository](https://github.com/pilakkat1964/z-open)** - Source code and issue tracking
- **[Latest Release](https://github.com/pilakkat1964/z-open/releases)** - Download latest version

---

## 🚀 Quick Start

### Installation

```bash
# Using pip (simplest method)
pip install zopen

# Or using system package
sudo apt install zopen           # Ubuntu/Debian
brew install z-open             # macOS

# From source
git clone https://github.com/pilakkat1964/z-open.git
cd z-open
pip install -e .
```

### Basic Usage

```bash
# Open files with configured applications
zopen myfile.py              # Opens in configured editor for Python files
zo document.pdf              # Use 'zo' alias for quick access
zopen --list                 # Show all configured mappings
zopen --dry-run *.md         # Preview without opening
zopen --init-config          # Create user config

# Modern hierarchical CLI (new!)
zopen config list            # List all mappings
zopen config init            # Initialize config
zopen mime detect FILE       # Detect MIME type
zopen app list               # Show all applications
```

---

## 📚 Documentation

### Getting Started
- **[Installation Guide](user-guide.md#installation)** - Multiple installation methods
- **[Quick Reference](user-guide.md#quick-reference)** - Common commands and flags
- **[Configuration Guide](user-guide.md#configuration)** - Setup TOML files

### For Users
- **[User Guide](user-guide.md)** - Complete usage documentation
  - Installation (pip, system packages, from source)
  - CLI reference with all flags and options
  - Configuration format and examples
  - MIME type detection explained
  - Troubleshooting common issues

### For Developers & Agents
- **[Design Document](design.md)** - Architecture and internals
  - Modern modular architecture (Phases 1-4)
  - Configuration subsystem details
  - MIME detection with strategy pattern
  - Application resolution algorithm
  - Extension points and customization

- **[Development Guide](../DEVELOPMENT.md)** - Development workflow
  - Setup and daily development
  - Testing and validation
  - Building and packaging
  - Contributing guidelines
  - Using scripts/dev.py

- **[Build Guide](build.md)** - Build and packaging
  - Multiple build paths (pip, CMake, system packages)
  - Packaging for different distributions
  - Release checklist
  - CI/CD pipeline setup

- **[GitHub Actions CI/CD](github-actions.md)** - Automation workflows
  - Continuous Integration (testing, security)
  - Automated Release (multi-platform packaging)
  - GitHub Pages deployment
  - Security scanning

---

## 💡 Use Cases

### Web Developer
Switch between multiple applications for different file types:

```bash
zopen main.py         → vim (text/x-python)
zopen styles.css      → code (text/css)
zopen report.pdf      → evince (application/pdf)
zopen image.png       → feh (image/png)
```

### System Administrator
Configure applications for different file types and access them consistently across systems.

### DevOps Engineer
Set up project-specific application mappings in `.zopen.toml` for team consistency.

---

## 🎯 Key Features

✓ **Single-file application** - Easy deployment, no complex dependencies  
✓ **Python 3.10+** - Works with modern Python  
✓ **Layered configuration** - System-wide, user-global, and project-local  
✓ **MIME type detection** - Content-based (libmagic) or extension-based fallback  
✓ **Interactive modes** - Choose application, preview, or list options  
✓ **Modern CLI** - Hierarchical subcommands with config and mime tools  
✓ **Strategy pattern** - Extensible MIME detection with caching  
✓ **Performance** - Built-in caching for fast repeated operations  

---

## 🏗️ Architecture

Z-Open features a modern, modular architecture while maintaining a single-file deployment:

### Architecture Phases

- **Phase 1**: Domain-specific classes for app detection and execution
- **Phase 2**: Configuration classes with validation and caching (2-3x faster)
- **Phase 3**: MIME detection with strategy pattern and caching (5-10x faster)
- **Phase 4**: Modern CliBuilder for hierarchical command structure

### Key Design Principles

- Clean separation of concerns with ~33 well-organized classes
- 3,167 lines of maintainable, documented code
- Backward compatible with original CLI flags
- 100% backward compatible with existing configurations

---

## 🔧 System Requirements

**Required:**
- Python >= 3.10 (3.11+ recommended)

**Recommended:**
- `python-magic` (for accurate content-based MIME detection)

**Optional:**
- libmagic development files (for python-magic support)

---

## 📋 Configuration

Config files (TOML format) are loaded and merged in this order:

| Priority | Location | Purpose |
|----------|----------|---------|
| 1 | Built-in defaults | Always present |
| 2 | `/opt/etc/zopen/config.toml` | System-wide |
| 3 | `~/.config/zopen/config.toml` | User-global |
| 4 | `./.zopen.toml` in CWD | Project-local |
| 5 | `--config FILE` | Ad-hoc override |

### Example Configuration

```toml
[defaults]
app = "$EDITOR"              # Uses $VISUAL → $EDITOR → xdg-open
prefer_mime = true          # MIME wins over extension

[mime_types]
"text/x-python"   = "vim"
"application/pdf" = "evince"
"image"          = "feh"     # wildcard: all image/* types

[extensions]
".md"  = "code"
".mp4" = "vlc"
```

---

## 🛠️ Build & Development

Z-Open uses a streamlined development workflow:

### Development Workflow

```bash
# First time setup
./scripts/dev.py setup

# Daily development
./scripts/dev.py test

# Create packages
./scripts/dev.py package --version 0.7.0

# Create release
./scripts/dev.py release --version 0.7.0

# Full workflow
./scripts/dev.py full --version 0.7.0
```

### Build Commands

```bash
# Using pip (simplest)
pip install .
pip install ".[dev]"           # with dev dependencies

# Using CMake (for packages)
mkdir build && cd build
cmake ..
make
make package                   # creates DEB package
```

See [scripts/README.md](../scripts/README.md) for complete development tool documentation.

---

## 📊 Project Status

| Component | Status |
|-----------|--------|
| Core Functionality | ✓ Production Ready |
| Python Support | ✓ 3.10, 3.11, 3.12, 3.13 |
| Documentation | ✓ Complete |
| CI/CD | ✓ GitHub Actions |
| Security Scanning | ✓ Bandit Integration |
| Release Process | ✓ Automated |

---

## 📞 Support & Issues

Found a bug or have a feature request?

- **[Open an Issue](https://github.com/pilakkat1964/z-open/issues)** - Report bugs or request features
- **[Discussions](https://github.com/pilakkat1964/z-open/discussions)** - Ask questions and share ideas

---

## 📄 License

MIT License - Free for personal and commercial use

---

## 🙏 Acknowledgments

Z-Open was designed and built to explore intelligent application launching with a focus on:
- Clean code architecture
- Modern Python patterns
- AI-assisted development

**Key Learning Resources:**
- Layered configuration systems
- MIME type detection strategies
- CLI design with argparse
- TOML parsing and merging
- Performance optimization with caching

---

## 📱 Quick Navigation

- [Go to GitHub Repository](https://github.com/pilakkat1964/z-open)
- [View Full User Guide](user-guide.md)
- [Read Architecture Design](design.md)
- [Check Build Options](build.md)
- [See Development Guide](../DEVELOPMENT.md)
- [Browse Build Scripts](../scripts/README.md)

---

**Ready to simplify your file opening workflow?** Start with `zopen --init-config` or jump straight to the [Installation Guide](user-guide.md#installation)!
