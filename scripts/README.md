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

Currently, `dev.py` is the only development script. Additional scripts may be added as needed for:
- Code generation
- Documentation building
- Deployment utilities
- Performance profiling

## Requirements

- Python 3.10+
- CMake (for building DEB packages)
- Git (for version control)
- Standard Unix tools (make, etc.)

The dev.py script handles Python dependency installation via pip.
