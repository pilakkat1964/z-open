---
layout: default
title: Z-Open GitHub Actions CI/CD
---

# GitHub Actions CI/CD Guide

This document describes the continuous integration and continuous deployment workflows for z-open.

## Workflows Overview

### 1. Release Workflow (`release.yml`)

**Triggers:** Push to git tags matching `v*` pattern (e.g., `v0.6.5`)

**What it does:**
- Builds source archive (tar.gz)
- Builds Debian package for amd64
- Creates GitHub Release with all assets
- Generates release notes automatically

**Assets Created:**
- `zopen-X.Y.Z-source.tar.gz` - Source code archive
- `zopen-X.Y.Z-Linux-amd64.deb` - Debian package for 64-bit systems
- `zopen-X.Y.Z-Linux-amd64.tar.gz` - Installable tarball

### 2. GitHub Pages Workflow (Automatic)

**Triggers:** Push to master branch

**What it does:**
- Builds Jekyll site from `/docs` folder
- Publishes to GitHub Pages automatically
- Uses Slate theme for professional documentation

**Configuration:**
- Source: `docs/` directory
- Theme: `jekyll-theme-slate`
- Config file: `_config.yml`

---

## Release Process

### Automated Release Steps

1. **Create a Release Commit**
   ```bash
   # Make your changes and commit
   git add .
   git commit -m "feat: add new feature"
   ```

2. **Create a Version Tag**
   ```bash
   # Create an annotated tag (triggers release workflow)
   git tag -a v0.6.5 -m "Release v0.6.5"
   git push origin v0.6.5
   ```

3. **GitHub Actions Runs Automatically**
   - Check Actions tab: https://github.com/pilakkat1964/z-open/actions
   - Workflow builds and publishes release
   - Assets appear on Releases page

4. **Verify Release**
   - Download and test assets
   - Check GitHub Pages documentation
   - Announce release on Discussions/Issues

### Release Workflow Files

**Location:** `.github/workflows/release.yml`

**Key Steps:**
1. Checkout code with full history
2. Set up Python 3.11
3. Install build dependencies (cmake, python3-magic)
4. Extract version from tag
5. Build CMake targets (tarball, deb)
6. Create source archive
7. Publish GitHub Release with all assets

---

## GitHub Pages Setup

### Configuration Files

**`_config.yml`** - Jekyll configuration
```yaml
theme: jekyll-theme-slate
source: docs
title: Z-Open
description: Smart file opener...
```

**`_layouts/default.html`** - Custom layout template
- Customizable header/footer
- Links to GitHub repository
- Download buttons

### Documentation Files

**`docs/index.md`** - Landing page
- Quick start guide
- Feature highlights
- Links to other docs

**`docs/user-guide.md`** - User documentation
- Installation instructions
- CLI reference
- Configuration guide

**`docs/design.md`** - Architecture documentation
- System design
- Subsystem descriptions
- Extension points

**`docs/build.md`** - Build documentation
- Build methods
- Packaging guide
- Release checklist

**`docs/cicd-guide.md`** - CI/CD guide (this document)

### Publishing

Pages are **published automatically** when you push to master:

1. Push commits to master
2. GitHub Actions builds Jekyll site
3. Site published at: `https://pilakkat1964.github.io/z-open/`

**Note:** GitHub Pages is enabled in repository settings:
- Source: `Deploy from branch`
- Branch: `master` (using `/docs` folder via `_config.yml`)

---

## Deployment Matrix

| Component | Platform | Build Tool | Artifact |
|-----------|----------|-----------|----------|
| Source | Any | git | `.tar.gz` |
| Debian | Linux amd64 | CMake + cpack | `.deb` |
| Install | Any | CMake | `.tar.gz` |
| Docs | GitHub | Jekyll | Web Pages |

---

## Manual Release Creation

If GitHub Actions doesn't trigger automatically:

### Method 1: Manual Tag Push
```bash
# Create and push tag manually
git tag -a v0.6.5 -m "Release v0.6.5"
git push origin v0.6.5
```

### Method 2: Manual Asset Creation
```bash
# Build locally
cmake -B build -DCMAKE_INSTALL_PREFIX=/opt/zopen
cmake --build build --target tarball
cmake --build build --target deb

# Create source archive
git archive --format=tar.gz --prefix="zopen-0.6.5-source/" \
  -o zopen-0.6.5-source.tar.gz HEAD

# Create GitHub Release manually via web UI
# - Go to: https://github.com/pilakkat1964/z-open/releases/new
# - Select tag: v0.6.5
# - Upload artifacts
# - Publish
```

---

## Troubleshooting

### Release Workflow Fails

1. **Check Actions tab:** https://github.com/pilakkat1964/z-open/actions
2. **View workflow logs:** Click failing workflow → see error details
3. **Common issues:**
   - Missing build dependencies: Install via apt-get
   - CMake errors: Ensure CMake >= 3.20 available
   - Tag format: Must be `vX.Y.Z` (e.g., `v0.6.5`)

### GitHub Pages Not Updating

1. **Check Pages settings:** Settings → Pages
2. **Verify source:** Should be `master` branch (root or `/docs`)
3. **Check `_config.yml`:** Must have `source: docs`
4. **Verify Jekyll builds:** Check Actions logs for build errors

### Assets Not Appearing

1. **Check CMake build:** Look for `build/zopen-*.tar.gz` and `build/zopen-*.deb`
2. **Verify git archive:** Source tarball should be created
3. **Check release action:** See if `softprops/action-gh-release` ran successfully

---

## CI/CD Best Practices

### Before Creating a Release

✓ Update version number if needed  
✓ Update CHANGELOG  
✓ Run tests locally: `python -m pytest tests/`  
✓ Build locally: `cmake -B build && cmake --build build`  
✓ Test packages: Extract and verify functionality  

### After Release

✓ Announce on Discussions  
✓ Update README.md with download links  
✓ Tag release in project milestones  
✓ Plan next release tasks  

---

## GitHub Actions Limits

- **Free tier:** 2,000 minutes per month
- **Retention:** 90 days for workflow logs
- **Concurrent jobs:** 20 per account
- **Job timeout:** 35 minutes (jobs that exceed are terminated)

z-open workflows are lightweight and should use < 5 minutes per run.

---

## Future Enhancements

Potential workflow improvements:
- Multi-platform builds (arm64, i386)
- Automated security scanning (bandit)
- Code coverage reports
- Performance benchmarking
- Documentation spell-check

---

## Quick Reference

### Create and Push a Release

```bash
# 1. Make changes and commit
git add .
git commit -m "Your message"

# 2. Create version tag
git tag -a v0.6.5 -m "Release v0.6.5"

# 3. Push tag (triggers release workflow)
git push origin v0.6.5

# 4. Monitor GitHub Actions
# Visit: https://github.com/pilakkat1964/z-open/actions

# 5. Verify release
# Visit: https://github.com/pilakkat1964/z-open/releases
```

### Publish Documentation

```bash
# Documentation publishes automatically on master push
# URL: https://pilakkat1964.github.io/z-open/

# To preview locally:
gem install bundler jekyll
cd /path/to/z-open
bundle exec jekyll serve
# Then open: http://localhost:4000/z-open/
```

---

## Related Documentation

- **[Build Guide](build)** - Building and packaging
- **[Design Document](design)** - Architecture overview
- **[User Guide](user-guide)** - Usage documentation

---

**Last Updated:** 2026-04-15
