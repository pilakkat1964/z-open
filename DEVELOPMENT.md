# Z-Open Development Workflow - Complete Guide

## Overview

The z-open project is a smart file opener application that launches files in the right application based on MIME type or file extension. This guide covers the development workflow for contributing to z-open.

### Architecture

Z-Open follows a modern, modular architecture while maintaining a single-file deployment model:

- **Phase 1**: Domain-specific classes for app detection and execution
- **Phase 2**: Configuration classes with validation and caching
- **Phase 3**: MIME detection classes using strategy pattern with caching
- **Phase 4**: CliBuilder for modern hierarchical CLI

This design ensures clean separation of concerns while keeping deployment simple (`zopen.py`, 3,167 lines).

## Quick Start

### ⚡ Quickest Path (Automated with dev.py)

Z-Open includes `scripts/dev.py`, a workflow wrapper that automates virtual environment setup and common tasks:

```bash
# Clone the repository and enter directory
git clone git@github.com:pilakkat1964/z-open.git
cd z-open

# One-time setup (creates venv with uv or standard venv, installs dependencies)
./scripts/dev.py setup

# Test your changes
./scripts/dev.py test

# When ready to release
./scripts/release.py 0.7.0
```

See `scripts/README.md` for complete documentation on all available commands.

### Manual Virtual Environment Setup

If you prefer to manage the virtual environment yourself:

#### **Option 1: Using uv (Fast & Recommended)**

```bash
# Clone the repository
git clone git@github.com:pilakkat1964/z-open.git
cd z-open

# Use the provided activation script (automatic venv setup)
source scripts/activate.sh

# Verify setup
python --version
python zopen.py --help
```

#### **Option 2: Using standard venv**

```bash
# Clone the repository
git clone git@github.com:pilakkat1964/z-open.git
cd z-open

# Create virtual environment manually
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Verify setup
python zopen.py --help
python zopen.py config list
```

### Running Commands in Virtual Environment

Once your venv is set up, use one of these approaches:

**Approach 1: Activate then run (recommended for interactive development)**
```bash
source scripts/activate.sh
python zopen.py --help
pytest
cmake --build build --target deb
```

**Approach 2: Use the with-venv wrapper (for one-off commands)**
```bash
scripts/with-venv python zopen.py --help
scripts/with-venv pytest
scripts/with-venv pip install somepackage
```

**Approach 3: Use dev.py wrapper (for release workflows)**
```bash
./scripts/dev.py test
./scripts/dev.py build
./scripts/release.py 0.7.0
```

## Virtual Environment Management

### ⚠️ Important: Always Use Virtual Environment

The project **must** use a virtual environment for:
- ✅ **Portability** - Works across different systems without system Python conflicts
- ✅ **Consistency** - Same dependencies in CI/CD and local development
- ✅ **Isolation** - Project dependencies don't affect system Python
- ✅ **Reproducibility** - Exact same environment for all developers

### Automatic Setup

The `scripts/activate.sh` script automatically:
1. Checks if `.venv` exists
2. Creates it using `uv` (if available) or standard `venv`
3. Installs/upgrades pip, setuptools, wheel
4. Installs project dependencies from `pyproject.toml[dev]`
5. Activates the virtual environment

```bash
# Automatic setup
source scripts/activate.sh
```

### Manual Setup

If you need to set it up manually:

```bash
# Using uv (fast, recommended)
uv venv .venv --python 3.10
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or using standard venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Verification

After setup, verify everything works:

```bash
# Check Python version
python --version  # Should be 3.10+

# Check venv location
which python      # Should show path to .venv/bin/python

# Run basic tests
python zopen.py --help
python zopen.py --version
python -m pytest --version
```

### Daily Development

Using the wrapper:

```bash
# Make changes to zopen.py or config files

# Test your changes
./scripts/dev.py test

# Create packages and review
./scripts/dev.py package --version 0.7.0
```

Or manually (if not using the wrapper):

```bash
# Make changes to zopen.py or config files

# Test manually
python zopen.py --help
python zopen.py app list
python zopen.py mime list

# For configuration changes, test the config system
python -c "from zopen import ConfigManager; ConfigManager().get_mime_handlers('text/plain')"
```

### Create a Release

Using the wrapper (recommended):

```bash
# Run complete workflow: test → build → package → release
./scripts/dev.py full --version 0.7.0

# Or just create a release (if you've already tested)
./scripts/dev.py release --version 0.7.0

# View the released version at:
# https://github.com/pilakkat1964/z-open/releases/tag/v0.7.0
```

Manual process:

```bash
# Update version in pyproject.toml
# Add release notes to docs/CHANGELOG.md (or README.md)

# Create a tag and push (GitHub Actions handles the rest)
git tag v0.7.0
git push origin master
git push origin v0.7.0

# View the released version at:
# https://github.com/pilakkat1964/z-open/releases/tag/v0.7.0
```

## Development Workflow Patterns

### Bug Fix Workflow

```bash
# 1. Create a branch for the bug
git checkout -b fix/issue-description

# 2. Make changes to zopen.py
# - Find the relevant class (use grep: grep -n "class ClassName" zopen.py)
# - Make minimal, focused changes

# 3. Test the fix manually
python zopen.py [relevant command/option]

# 4. Review changes
git diff zopen.py

# 5. Commit
git commit -am "fix: brief description of bug and solution"

# 6. Push and create PR
git push origin fix/issue-description
gh pr create --title "Fix: ..." --body "Fixes #123"
```

### Feature Addition Workflow

```bash
# 1. Create a branch for the feature
git checkout -b feature/feature-name

# 2. Plan the implementation:
#    - Which class should be modified?
#    - Does it need a new class?
#    - Will it need caching (like MIME detection)?

# 3. Implement incrementally
#    - Add the core functionality
#    - Add docstrings
#    - Add error handling

# 4. Test thoroughly
python zopen.py [test the new feature]

# 5. Update documentation if needed
#    - docs/design.md (architecture changes)
#    - README.md (usage examples)
#    - docs/user-guide.md (user-facing features)

# 6. Commit and push
git commit -am "feat: description of new feature"
git push origin feature/feature-name
gh pr create --title "Feature: ..." --body "Adds support for ..."
```

### Configuration Extension Workflow

```bash
# Adding new MIME handlers or application mappings

# 1. Create a branch
git checkout -b config/add-handlers

# 2. Update config files in config/ directory
#    - config/mimes.yaml: Add MIME type mappings
#    - config/apps.yaml: Add application definitions

# 3. Test the new configuration
python -c "from zopen import ConfigManager; \
cm = ConfigManager(); \
print(cm.get_mime_handlers('new/mimetype'))"

# 4. Verify z-open finds and uses the new handlers
python zopen.py app list
python zopen.py mime list

# 5. Document in README.md if it's a user-facing addition
# 6. Commit and push
git commit -am "config: add support for new MIME types"
```

## Architecture Understanding

### Key Classes

**zopen.py** contains ~33 classes organized in these groups:

#### Core Execution (Lines ~200-500)
- `AppDetector`: Detects installed applications on system
- `AppExecutor`: Executes applications with proper arguments
- `FileOpener`: Main orchestrator for opening files

#### Configuration System (Phase 2)
- `ConfigManager`: Loads and caches configuration
- `MimeConfigHandler`: Validates MIME configuration
- `AppConfigHandler`: Validates application configuration
- Related handler classes for config validation

#### MIME Detection (Phase 3)
- `MimeDetector`: Strategy pattern for MIME detection
- `FileMagicMimeDetector`: Uses libmagic (primary)
- `ExtensionMimeDetector`: Fallback detection
- `ContentMagicMimeDetector`: Content-based detection

#### CLI System (Phase 4)
- `CliBuilder`: Hierarchical CLI structure
- `ConfigCommand`: Handles config operations
- `MimeCommand`: Handles MIME operations
- `AppCommand`: Handles app operations
- `UtilCommand`: Utility operations

Find classes using:
```bash
grep -n "^class " zopen.py
```

### Common Modifications

**To add a new MIME detection strategy:**
```python
class CustomMimeDetector(MimeDetector):
    """Custom MIME detection strategy"""
    
    def detect(self, file_path):
        # Implementation
        pass
    
    def supports(self, file_path):
        # Check if this detector can handle this file
        return True
```

**To add a new CLI command:**
```python
class NewCommand(CliBuilder):
    """New command implementation"""
    
    def build(self, subparsers):
        # Add subparser and arguments
        parser = subparsers.add_parser('newcmd', help='...')
        # Add your arguments
        return parser
```

**To add configuration validation:**
```python
class NewConfigHandler(ConfigValidator):
    """Validates new configuration"""
    
    def validate(self, config_dict):
        # Add validation logic
        return config_dict
```

## Testing

### Local Testing Guide

Before committing changes, ensure you're in the virtual environment and run the following tests:

#### **Quick Verification** (for small changes)

```bash
# Activate venv first
source scripts/activate.sh

# Basic functionality check
python zopen.py --help
python zopen.py --version

# Quick config check
python zopen.py config list
```

#### **Full Testing Workflow** (before committing)

**Step 1: Run Unit Tests (if available)**

```bash
# If tests exist in tests/ directory
scripts/with-venv pytest -v

# Or if you have activated the venv
pytest -v

# Run with coverage report
pytest --cov=zopen --cov-report=html
# View report at htmlcov/index.html
```

**Step 2: Manual CLI Testing**

```bash
# Test core commands
python zopen.py --help
python zopen.py --version
python zopen.py util diagnose

# Test configuration system
python zopen.py config list
python zopen.py config get mime
python zopen.py config validate

# Test MIME detection
python zopen.py mime list
python zopen.py mime detect /etc/passwd
python zopen.py mime detect ~/.bashrc

# Test app detection
python zopen.py app list
python zopen.py app find text/plain
python zopen.py app find text/html

# Test actual file opening (in dry-run mode if available)
python zopen.py /etc/hosts
python zopen.py ~/.bashrc
```

**Step 3: Test Configuration Changes**

If you modified config files or configuration logic:

```bash
# Verify configuration loads without errors
python -c "from zopen import ConfigManager; \
    cm = ConfigManager(); \
    print('Loaded:', len(cm.config), 'configuration sections')"

# Check specific configuration
python -c "from zopen import ConfigManager; \
    cm = ConfigManager(); \
    handlers = cm.get_mime_handlers('text/plain'); \
    print('Handlers for text/plain:', handlers)"

# List all MIME types
python zopen.py mime list | head -20
```

**Step 4: Test Code Changes**

For changes to specific classes:

```bash
# Test MIME detection strategies
python -c "from zopen import MimeDetector; \
    detector = MimeDetector(); \
    mime = detector.detect('/etc/hosts'); \
    print('Detected MIME type:', mime)"

# Test app detection
python -c "from zopen import AppDetector; \
    detector = AppDetector(); \
    apps = detector.find_apps('firefox'); \
    print('Found apps:', apps)"

# Test app execution (without actually opening files)
python -c "from zopen import AppExecutor; \
    exec = AppExecutor(); \
    print('Executable ready to test')"
```

#### **Full Regression Test Checklist**

Before creating a release, run this complete checklist:

```bash
# Ensure you're in the venv
source scripts/activate.sh

# 1. Run automated tests (if available)
pytest -v --tb=short

# 2. Check linting (if available)
ruff check zopen.py

# 3. Check type hints (if used)
mypy zopen.py --ignore-missing-imports

# 4. Test all CLI commands
python zopen.py --help
python zopen.py --version
python zopen.py util diagnose
python zopen.py config list
python zopen.py config get mime
python zopen.py config get apps
python zopen.py config validate
python zopen.py mime list
python zopen.py app list

# 5. Test file operations
python zopen.py /etc/hosts
python zopen.py ~/.bashrc
python zopen.py /usr/share/pixmaps/*.png

# 6. Build packages
mkdir -p build
cd build
cmake ..
make package
ls -lah *.deb
cd ..

# 7. Test package installation (optional, if you want to test the actual installer)
# sudo dpkg -i build/*.deb
# zopen --help
# sudo dpkg -r zopen
```

#### **Automated Test Execution**

Using the dev.py wrapper for automated testing:

```bash
# Run just the tests
./scripts/dev.py test

# Run full workflow (test → build → package)
./scripts/dev.py full --version 0.7.0

# View available dev.py commands
./scripts/dev.py help
```

#### **Adding Automated Tests (Future)**

If automated unit tests are added to the `tests/` directory, they can be run with:

```bash
# Quick test run
pytest

# Verbose with coverage
pytest -v --cov=zopen --cov-report=html

# Run specific test file
pytest tests/test_mime_detection.py -v

# Run specific test
pytest tests/test_mime_detection.py::TestMimeDetector::test_detect_text -v
```

### Manual Testing Checklist (Quick Reference)

Before committing changes:

```bash
# 1. Basic functionality
python zopen.py --help
python zopen.py --version

# 2. Configuration commands
python zopen.py config list
python zopen.py config get mime

# 3. MIME commands
python zopen.py mime list
python zopen.py mime detect /path/to/file

# 4. App commands
python zopen.py app list
python zopen.py app find text/plain

# 5. Utility commands
python zopen.py util diagnose

# 6. Test with actual file opening
python zopen.py /path/to/test.txt
```

## Build and Packaging

### Local Build

```bash
# CMake is used for packaging and distribution
mkdir -p build
cd build
cmake ..
make
cd ..

# Creates DEB package in build/
ls -la build/*.deb
```

### Creating Release Packages

GitHub Actions automatically creates packages on release:

1. **DEB Package**: `zopen-VERSION-Linux-amd64.deb`
   - Installs zopen.py to `/usr/local/bin/`
   - Installs man page
   - Includes dependencies

2. **Source Archive**: `zopen-VERSION-source.tar.gz`
   - Complete source code
   - CMakeLists.txt, config files, documentation

### Manual Package Creation

```bash
# Build locally
cd build
cmake ..
make package

# Creates .deb package
ls *.deb
```

## Version Management

Version is defined in `pyproject.toml`:

```toml
[project]
version = "0.7.0"
```

When releasing:

1. Update version in `pyproject.toml`
2. Create git tag: `git tag v0.7.0`
3. Push tag: `git push origin v0.7.0`
4. GitHub Actions automatically creates the release

## Documentation

### Files to Update

When making changes, update relevant documentation:

- **README.md**: User-facing features and usage
- **docs/user-guide.md**: Detailed usage instructions
- **docs/design.md**: Architecture and design decisions
- **docs/build.md**: Build and compilation instructions
- **docs/github-actions.md**: CI/CD and release process
- **DEVELOPMENT.md** (this file): Development workflow

### Running Docs Locally

```bash
# Docs use Jekyll Slate theme
# Preview at: https://pilakkat1964.github.io/z-open/

# Or build locally (requires Jekyll)
cd docs
bundle install
bundle exec jekyll serve --source . --destination ../_site
# View at http://localhost:4000/z-open/
```

## GitHub Actions and CI/CD

### Release Workflow (`.github/workflows/release.yml`)

Triggered when you push a git tag (e.g., `v0.7.0`):

1. Builds DEB package for Linux amd64
2. Creates source archive
3. Generates SHA256SUMS checksums
4. Creates GitHub Release with all assets
5. Publishes to releases page

### GitHub Pages Workflow (`.github/workflows/pages.yml`)

Automatically triggered when docs are updated:

1. Builds Jekyll from `/docs` folder
2. Deploys to GitHub Pages
3. Available at: https://pilakkat1964.github.io/z-open/

### Future: CI Workflow

Planned enhancement:
- Test on Python 3.10, 3.11, 3.12, 3.13
- Linting with ruff
- Security scanning with bandit
- Coverage reports

## Common Tasks

### View Recent Commits

```bash
git log --oneline -10
```

### Check Branch Status

```bash
git status
git branch -a
```

### Review Changes Before Commit

```bash
git diff zopen.py
git diff config/
```

### Undo Changes

```bash
# Undo unstaged changes
git checkout zopen.py

# Undo staged changes
git reset HEAD zopen.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

### Merge Latest Changes

```bash
# Update master from remote
git fetch origin
git merge origin/master

# Or rebase your branch
git rebase origin/master
```

## Troubleshooting

### Import Errors

```bash
# If zopen.py can't be imported:
# 1. Ensure Python 3.10+ is used
python3 --version

# 2. Check if zopen.py is in the current directory
ls -la zopen.py

# 3. Try running directly
python3 zopen.py --help
```

### Configuration Issues

```bash
# If config loading fails:
python zopen.py config list

# Enable verbose output (if implemented):
python zopen.py --verbose config list
```

### MIME Detection Issues

```bash
# Test MIME detection
python zopen.py mime detect /path/to/file

# Check what detector is being used
python -c "from zopen import MimeDetector; print(MimeDetector().detect('/path/to/file'))"
```

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions about development
- **Code Comments**: Read inline documentation in zopen.py
- **AGENTS.md**: Comprehensive project architecture guide

## Code Style

Z-Open follows these conventions:

- **Python**: PEP 8, 4-space indentation
- **Naming**: snake_case for functions/variables, CamelCase for classes
- **Docstrings**: Include for all public classes and methods
- **Comments**: Explain "why", not "what"
- **Line Length**: Max 100 characters (match existing code)

Example:

```python
class MyClass:
    """Brief description of the class.
    
    Longer description if needed, explaining the purpose
    and usage of this class.
    """
    
    def my_method(self, param1, param2):
        """Brief description of what the method does.
        
        Args:
            param1: Description of param1
            param2: Description of param2
            
        Returns:
            Description of return value
        """
        # Do work
        return result
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes following the workflow patterns above
4. Test thoroughly
5. Commit with clear messages
6. Push to your fork
7. Create a pull request

See GitHub for current issues and feature requests.

---

**Last Updated:** 2026-04-15  
**Z-Open Version:** 0.6.4  
**Python Support:** 3.10+  
**Project:** Smart file opener with MIME-type aware application launching
