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

### Basic Usage

```bash
# Open a file with the configured application
zopen myfile.py              # Opens in configured editor for Python files
zo document.pdf              # Use 'zo' alias for quick access
zopen --list                 # Show all configured mappings
zopen --dry-run *.md         # Preview without opening
zopen --init-config          # Create user config
```

### Using Modern Commands

```bash
# Modern hierarchical CLI
zopen config list            # List all mappings
zopen config init            # Initialize config
zopen config map FILE        # Map MIME type for file

zopen mime detect FILE       # Detect MIME type
zopen mime strategies        # Show detection strategies

zopen app info FILE          # Show app resolution info
```

---

## 📚 Documentation

### Getting Started
- **[Installation Guide](user-guide.md#installation)** - Multiple installation methods
- **[Quick Reference](user-guide.md#quick-reference)** - Common commands and flags
- **[Configuration Guide](user-guide.md#configuration)** - Setup TOML files

### For Users
- **[User Guide](user-guide.md)** - Complete usage documentation
  - Installation (pip, uv, system packages)
  - CLI reference with all flags and options
  - Configuration format and examples
  - MIME type detection explained
  - Troubleshooting common issues

### For Developers & Agents
- **[Design Document](design.md)** - Architecture and internals
  - Module structure and dependency graph
  - Configuration subsystem details
  - MIME detection strategy (strategy pattern)
  - Application resolution algorithm
  - Extension points and customization

- **[Build Guide](build.md)** - Build and packaging
  - Multiple build paths (pip, wheel, CMake, system packages)
  - Packaging for different distributions
  - Release checklist
  - CI/CD pipeline setup

- **[GitHub Actions CI/CD](github-actions.md)** - Automation workflows
  - Continuous Integration (testing, linting)
  - Automated Release (multi-platform packaging)
  - GitHub Pages deployment
  - Security scanning

---

## 💡 Use Cases

### Web Developer
Switch between multiple applications for different file types:

```bash
zopen main.py         → vim (text/x-python)
zopen styles.css      → neovim (text/css)
zopen report.pdf      → evince (application/pdf)
zopen image.png       → gimp (image/png)
```

### System Administrator
Configure applications for different file types and access them consistently across systems.

### DevOps Engineer
Set up project-specific application mappings in `.zopen.toml` for team consistency.

---

## 🎯 Key Features

✓ **Single-file application** - Easy deployment, minimal dependencies  
✓ **Modern architecture** - 33 focused classes with strategy pattern  
✓ **Performance optimized** - 5-10x faster MIME detection with caching  
✓ **Layered configuration** - System-wide, user-global, and project-local  
✓ **MIME type detection** - Content-based (libmagic) or extension-based fallback  
✓ **Interactive modes** - Choose application, preview, or dump list  
✓ **Hierarchical CLI** - Modern subcommands (config, mime, app, util)  
✓ **100% backward compatible** - All legacy --flags still work  
✓ **Environment integration** - Respects system application defaults  

---

## 🏗️ Architecture Highlights

### Phases 1-4 Modernization

The z-open project has been comprehensively refactored:

**Phase 1: Modularization**
- Extracted 11 domain-specific classes from procedural code
- Clear separation of concerns

**Phase 2: Configuration System Extraction**
- 5 new configuration classes with validation and caching
- 2-3x faster config loading

**Phase 3: MIME Detection Enhancement**
- 8 new MIME detection classes using strategy pattern
- Optional caching and statistics tracking
- 5-10x faster detection for repeated files

**Phase 4: CLI Architecture Enhancement**
- Modern hierarchical command structure (zopen config, zopen mime, etc.)
- 100% backward compatible with original --flags

---

## 📋 Configuration

Config files (TOML format) are loaded and merged in this order:

| Priority | Location | Purpose |
|---|---|---|
| 1 | Built-in defaults | Always present |
| 2 | `/opt/etc/zopen/config.toml` | System-wide |
| 3 | `~/.config/zopen/config.toml` | User-global |
| 4 | `./.zopen.toml` in CWD | Project-local |
| 5 | `--config FILE` | Ad-hoc override |

### Example Configuration

```toml
[defaults]
app        = "xdg-open"   # Default fallback application
prefer_mime = true         # MIME wins over extension

[mime_types]
"text/x-python"   = "vim"
"application/pdf" = "evince"
"image"           = "gimp"    # wildcard: all image/* types

[extensions]
".md"  = "typora"
".mp4" = "vlc"
```

---

## 🔧 System Requirements

**Required:**
- Python >= 3.10 (for type hints)

**Recommended:**
- `python-magic` (for accurate content-based MIME detection)
- `uv` >= 0.11.0 (for faster dependency management)

**Optional:**
- libmagic development files (for `python-magic` support)

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

Z-open was designed and built to explore AI-assisted development using **Claude via GitHub Copilot**.

**Explore the code:** This is an excellent resource for learning Python patterns:
- Layered configuration systems with validation
- Strategy pattern for MIME type detection
- CLI design with hierarchical subcommands
- TOML parsing and deep merging
- Modern Python 3.10+ type hints
- Performance optimization with caching

---

## 📱 Quick Navigation

- [Go to GitHub Repository](https://github.com/pilakkat1964/z-open)
- [View Full User Guide](user-guide.md)
- [Read Architecture Design](design.md)
- [Check Build Options](build.md)
- [See CI/CD Guide](github-actions.md)

---

**Ready to simplify your file opening workflow?** Start with `zopen --init-config` or jump straight to the [Installation Guide](user-guide.md#installation)!
