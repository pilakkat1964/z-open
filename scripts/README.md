# Z-Open Development Scripts

This directory contains utilities for streamlining the z-open development workflow.

## `dev.py` - Development Workflow Wrapper

A comprehensive tool for managing the entire development lifecycle from setup to release.

### Quick Start

```bash
# First time setup
./scripts/dev.py setup

# Daily development
./scripts/dev.py test

# Create packages
./scripts/dev.py package --version 0.7.0

# Release
./scripts/dev.py release --version 0.7.0
```

### Available Commands

#### `setup`
Set up the development environment with virtual environment and dependencies.

```bash
./scripts/dev.py setup
```

Creates:
- Virtual environment in `.venv/`
- Installs z-open with dev dependencies
- Ready for development and testing

#### `test`
Run tests and validations on the z-open codebase.

```bash
./scripts/dev.py test
```

Tests:
- Python syntax validation (py_compile)
- CLI help command
- CLI version command

#### `build`
Build the project locally using CMake (for creating DEB packages).

```bash
./scripts/dev.py build
```

Performs:
- CMake configuration
- Make build
- Creates build artifacts in `./build/`

#### `package`
Create distributable packages (DEB and source archive).

```bash
./scripts/dev.py package [--version VERSION] [--skip-deb] [--skip-source]
```

Options:
- `--version VERSION`: Specify package version (auto-detected from pyproject.toml if not given)
- `--skip-deb`: Skip DEB package creation (faster)
- `--skip-source`: Skip source archive creation

Creates:
- DEB package: `build/zopen-VERSION-Linux-amd64.deb`
- Source archive: `zopen-VERSION-source.tar.gz`

#### `release`
Create and publish a release to GitHub.

```bash
./scripts/dev.py release [--version VERSION] [--stage] [--no-wait]
```

Workflow:
1. Reviews git status
2. Creates release commit
3. Creates git tag (e.g., `v0.7.0`)
4. Pushes to GitHub
5. GitHub Actions automatically builds the release

Options:
- `--version VERSION`: Release version (auto-detected from pyproject.toml if not given)
- `--stage`: Creates staging release (adds `-stage` suffix for QA)
- `--no-wait`: Don't wait for GitHub Actions completion
- `--commit-msg MSG`: Custom commit message
- `--timeout SECONDS`: Timeout for GitHub Actions polling (default: 300s)

#### `full`
Run complete workflow: test → build → package → release.

```bash
./scripts/dev.py full --version 0.7.0
```

Runs all steps sequentially, stopping on first failure.

### Global Options

- `-v, --verbose`: Show detailed command output
- `--dry-run`: Show commands without executing them

### Examples

**Typical development session:**
```bash
# Make changes to zopen.py, config files, etc.

# Test your changes
./scripts/dev.py test

# When ready to release
./scripts/dev.py full --version 0.7.0
```

**Package without release:**
```bash
./scripts/dev.py test
./scripts/dev.py build
./scripts/dev.py package --version 0.7.0
```

**Create staging release for QA:**
```bash
./scripts/dev.py release --version 0.7.0 --stage
```

**Dry-run (see what would happen):**
```bash
./scripts/dev.py full --version 0.7.0 --dry-run
```

**Verbose output:**
```bash
./scripts/dev.py test --verbose
```

## Other Scripts

### `release.py` - Automated Release Script

A specialized tool for creating releases with synchronized version updates across all files.
This is the **recommended method** for creating releases as it ensures all version files stay in sync.

#### Quick Start

```bash
# Simple release
./scripts/release.py 0.6.6

# With custom changelog message
./scripts/release.py 0.6.6 --message "Added new features and bugfixes"

# Dry-run (see what would happen without making changes)
./scripts/release.py 0.6.6 --dry-run

# Verbose output
./scripts/release.py 0.6.6 --verbose
```

#### What It Does

The script automates the full release workflow in a single command:

1. **Validates** version format (X.Y.Z)
2. **Updates** version in all 3 locations:
   - `CMakeLists.txt` - project VERSION
   - `pyproject.toml` - [project] version
   - `debian/changelog` - adds new entry with timestamp
3. **Creates** git commit with all version updates
4. **Pushes** commit to `origin/master`
5. **Creates** annotated git tag
6. **Pushes** tag to origin (triggers GitHub Actions)

GitHub Actions then automatically:
- Builds the .deb package for amd64
- Creates install .tar.gz archive
- Generates source .tar.gz archive
- Creates GitHub Release with all assets

#### Usage Options

```bash
./scripts/release.py VERSION [OPTIONS]

positional arguments:
  VERSION               Release version (e.g., 0.6.6)

options:
  -h, --help            Show this help message
  -m, --message TEXT    Release message for changelog entry
  -d, --dry-run         Show what would be done without making changes
  -v, --verbose         Print detailed output
```

#### Examples

**Standard release:**
```bash
./scripts/release.py 0.6.6
# Prompts for confirmation, then creates release
```

**Release with custom changelog message:**
```bash
./scripts/release.py 0.6.6 --message "Performance improvements and new CLI options"
```

**Preview what would happen:**
```bash
./scripts/release.py 0.6.6 --dry-run
# Shows all changes that would be made
```

**Verbose with message:**
```bash
./scripts/release.py 0.6.6 --verbose --message "Release notes"
# Shows detailed output including generated changelog entry
```

#### Output Example

```
ℹ️ Starting z-open release automation...

============================================================
Release Confirmation: z-open 0.6.6
============================================================
  Version: 0.6.6
  Tag: v0.6.6
  Debian revision: 0.6.6-1
============================================================

📝 Updating version files...
ℹ️ Updated CMakeLists.txt to version 0.6.6
ℹ️ Updated pyproject.toml to version 0.6.6
ℹ️ Updated debian/changelog with version 0.6.6-1

💾 Committing changes...
ℹ️ Created commit: release: bump version to 0.6.6

📤 Pushing version commit...
ℹ️ Pushed version commit to origin/master

🏷️  Creating and pushing tag...
ℹ️ Created tag: v0.6.6
ℹ️ Pushed tag to origin: v0.6.6

============================================================
RELEASE SUMMARY
============================================================
  CMakeLists.txt            VERSION              → 0.6.6
  pyproject.toml            version              → 0.6.6
  debian/changelog          version              → 0.6.6-1

Next steps:
  1. GitHub Actions will build release assets
  2. Download from: https://github.com/pilakkat1964/z-open/releases/tag/v0.6.6
  3. Install via: sudo apt install ./zopen-0.6.6-Linux.deb
============================================================

✅ ✨ Release process complete!
ℹ️ GitHub Actions will now build the release assets.
```

#### Error Handling

The script includes validation for:
- **Invalid version format** - Must be X.Y.Z (e.g., 0.6.5)
- **Uncommitted changes** - Working tree must be clean
- **Duplicate tag** - Cannot create release with existing tag
- **Git operations** - Handles push/commit failures gracefully

#### Comparison with dev.py

| Feature | `release.py` | `dev.py release` |
|---------|-------------|-----------------|
| **Speed** | Fast (30s) | Slower (2-5m) |
| **Complexity** | Simple, focused | Complex, multi-step |
| **User confirmation** | Yes | Depends on options |
| **Changelog auto-generation** | Yes | No |
| **Dry-run support** | Yes | Yes |
| **Version sync** | Automatic | Manual |

**Recommendation:** Use `release.py` for standard releases. Use `dev.py release` for advanced scenarios like staging releases.

### `dev.py` - Development Workflow Wrapper

A comprehensive tool for managing the entire development lifecycle from setup to release.

Note: The `dev.py release` command is now superseded by `release.py` for most use cases.
Use `dev.py` for complex release scenarios like staging releases or custom commit messages.

## Requirements

- Python 3.10+
- CMake (for building DEB packages)
- Git (for version control)
- Standard Unix tools (make, etc.)

The dev.py script handles Python dependency installation via pip.
