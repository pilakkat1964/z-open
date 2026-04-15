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
# Using uv (fastest - recommended)
uv pip install zopen

# Or using standard pip
pip install zopen

# Or using system package
sudo apt install zopen           # Ubuntu/Debian
brew install z-open             # macOS (if available)

# From source (development)
git clone https://github.com/pilakkat1964/z-open.git
cd z-open
uv venv
source .venv/bin/activate
uv pip install -e .
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

### Table of Contents
1. [Getting Started](#getting-started)
2. [User Documentation](#user-documentation)
3. [Developer Documentation](#developer-documentation)
4. [Advanced Topics](#advanced-topics)

### Getting Started
- **[Installation Guide](user-guide#1-installation)** - Multiple installation methods (pip, apt, from source)
- **[Quick Start](user-guide#2-quick-start)** - Common commands and basic usage
- **[Configuration Basics](user-guide#4-configuration)** - How to set up TOML config files

### User Documentation
- **[User Guide](user-guide)** - Complete usage reference
  - Installation (Debian, pip, tarball, editable)
  - CLI reference with all flags and options
  - Configuration format, examples, and deep-merge semantics
  - MIME type detection methods
  - Editor resolution logic
  - Common workflows
  - Environment variables and troubleshooting

- **[FAQ & Troubleshooting](faq)** - Common questions and solutions
  - Installation & setup issues
  - Configuration and mappings
  - MIME type detection problems
  - Editor resolution questions
  - File handling edge cases
  - Scripting and automation
  - Performance optimization
  - Integration with popular tools

- **[Examples & Recipes](examples)** - Real-world workflows
  - Developer workflows (Python, web, IDE-based)
  - Project team setups
  - System administration tasks
  - DevOps & automation
  - Media and content creation
  - Integration with git, fzf, ripgrep, Docker, Kubernetes, CI/CD
  - Advanced scenarios and tips

### Developer Documentation
- **[Python API Documentation](api)** - Programmatic use of zopen
  - Installation for development
  - Core functions (detect_mime, load_config, resolve_app)
  - Configuration management API
  - MIME detection advanced usage
  - Application resolution API
  - Complete examples (file opener, config inspector, batch processor)
  - Error handling and debugging

- **[Design Document](design)** - Architecture and internals
  - Modern modular architecture (Phases 1-4)
  - Module structure and organization
  - Dependency graph
  - Configuration subsystem details
  - MIME detection with strategy pattern
  - Application resolution algorithm
  - CLI subsystem and main control flow
  - Extension points and customization
  - Design decisions and trade-offs

- **[Development Guide](../DEVELOPMENT)** - Development workflow
  - Setup and daily development
  - Using the dev.py wrapper script
  - Testing and validation
  - Building and packaging
  - Creating releases
  - Contributing guidelines

- **[Build Guide](build)** - Build and packaging
  - Repository layout
  - Python packaging (pip/wheel)
  - CMake build system
  - CPack packaging (DEB, RPM, TGZ)
  - Debian native packaging (dpkg-buildpackage)
  - Choosing a packaging method
  - Versioning and release checklist

- **[GitHub Actions CI/CD](github-actions)** - Automation workflows
  - Continuous Integration (testing, security)
  - Automated Release (multi-platform packaging)
  - GitHub Pages deployment
  - Security scanning

### Advanced Topics
- **[Migration Guide](migration)** - Upgrading between versions
  - General upgrade process
  - v0.7.x upgrade path
  - v0.6.x upgrade path
  - Compatibility notes
  - Configuration migration
  - Rollback instructions
  - Version history

- **[CI/CD Pipeline Guide](cicd-guide)** - GitHub Actions and automation
  - Pipeline configuration
  - Security scanning setup
  - Release automation

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
# Using uv (fastest)
uv venv
source .venv/bin/activate
uv pip install .
uv pip install ".[dev]"           # with dev dependencies

# Using standard pip
pip install .
pip install ".[dev]"              # with dev dependencies

# Using CMake (for packages)
mkdir build && cd build
cmake ..
make
make package                       # creates DEB package
```

See [scripts/README.md](../scripts/README) for complete development tool documentation.

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

**Getting Started:**
- [Installation Guide](user-guide#1-installation) - Get zopen running in 5 minutes
- [Quick Start](user-guide#2-quick-start) - Common usage patterns

**Finding Answers:**
- [FAQ & Troubleshooting](faq) - Solutions to common problems
- [Examples & Recipes](examples) - Copy-paste solutions for real workflows

**For Developers:**
- [Python API](api) - Use zopen in your code
- [Architecture Design](design) - Understand the internals
- [Build Guide](build) - Package and deploy

**External Resources:**
- [GitHub Repository](https://github.com/pilakkat1964/z-open) - Source code and issue tracking
- [Development Guide](../DEVELOPMENT) - Contributing and development
- [Build Scripts](../scripts/README) - Automation tools

---

## 🎓 Documentation by Role

**I'm a user** → Start with [User Guide](user-guide), then explore [FAQ](faq) and [Examples](examples)

**I'm a sysadmin** → Check [System Administration recipes](examples#system-administration) and [FAQ](faq)

**I'm a developer** → Read [API Documentation](api) and [Design Document](design)

**I'm contributing code** → See [Development Guide](../DEVELOPMENT) and [Design Document](design)

**I'm upgrading zopen** → Read [Migration Guide](migration) first

---

**Ready to simplify your file opening workflow?** 
- Start here: `zopen --init-config`
- Or jump to: [Installation Guide](user-guide#1-installation)
- Need quick answers? Check the [FAQ](faq)

---

## 🔗 Related Z-Tools Projects

**Explore other tools in the z-tools ecosystem:**

- **[Z-Edit](http://pilakkat.mywire.org/z-edit/)** — Opens files with the right editor
- **[Z-Kitty Launcher](http://pilakkat.mywire.org/z-kitty-launcher/)** — Terminal session manager for Kitty
- **[RClone Mount Applete](https://pilakkat.mywire.org/z-rclone-mount-applete/)** — System tray manager for cloud storage

**[→ View Master Index](http://pilakkat.mywire.org/master-index/)** — Complete guide to all z-tools projects
