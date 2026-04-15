# zopen — Migration Guide

Guide for upgrading zopen to newer versions. Follow the appropriate section based on which version you're upgrading from.

---

## Table of Contents

1. [General Upgrade Process](#general-upgrade-process)
2. [Upgrading to v0.7.x](#upgrading-to-v07x)
3. [Upgrading to v0.6.x](#upgrading-to-v06x)
4. [Compatibility Notes](#compatibility-notes)
5. [Configuration Migration](#configuration-migration)
6. [Rollback Instructions](#rollback-instructions)

---

## General Upgrade Process

### Before Upgrading

1. **Backup your configuration:**
   ```bash
   cp -r ~/.config/zopen ~/.config/zopen.backup
   ```

2. **Note your current version:**
   ```bash
   zopen --version
   ```

3. **Review breaking changes** for the target version (see sections below)

### During Upgrade

**If installed via pip:**
```bash
pip install --upgrade zopen
```

**If installed via apt:**
```bash
sudo apt update
sudo apt upgrade zopen
```

**From source:**
```bash
git pull origin master
pip install -e .
```

### After Upgrading

1. **Verify the installation:**
   ```bash
   zopen --version
   zopen --help
   ```

2. **Test your configuration:**
   ```bash
   zopen --list
   zopen --dry-run testfile.txt
   ```

3. **If issues occur**, see [Rollback Instructions](#rollback-instructions)

---

## Upgrading to v0.7.x

**Current stable version**

### What's New in v0.7.x

- **Enhanced Configuration System**: New ConfigManager with layer-based loading
- **Improved MIME Detection**: Strategy pattern with caching for better performance
- **Better Error Messages**: More informative error reporting
- **API Stability**: Public API documented and stabilized
- **Modern CLI**: Hierarchical command structure

### Breaking Changes

None! v0.7.x maintains backward compatibility with v0.6.x configurations.

### Configuration Changes (Optional)

While not required, you can take advantage of new features:

**Old syntax (still works):**
```toml
[defaults]
editor = "$EDITOR"
prefer_mime = true

[mime_types]
"text/plain" = "vim"
```

**New optional features:**
```toml
[defaults]
editor = "$EDITOR"
prefer_mime = true
# New in v0.7: custom MIME mappings
# New in v0.7: extension resolution improvements

[mime_types]
"text/plain" = "vim"
# Base-type wildcards now work better:
"text" = "vim"     # Now properly handles text/* types
"image" = "gimp"   # Works for all image/* types

[extensions]
# Extension matching is now more robust
".py" = "vim"
```

### No Configuration Migration Required

Your existing `~/.config/zopen/config.toml` will work without changes.

---

## Upgrading to v0.6.x

**Previous stable version**

### From v0.5.x or Earlier

#### Breaking Changes

1. **Configuration location changed**
   - Old: `~/.zopen/config.toml` 
   - New: `~/.config/zopen/config.toml`

2. **System config location**
   - Old: `/opt/etc/zopen/config.toml`
   - New: `/etc/zopen/config.toml`

#### Migration Steps

1. **Move user configuration:**
   ```bash
   mkdir -p ~/.config/zopen
   cp ~/.zopen/config.toml ~/.config/zopen/config.toml
   ```

2. **Update system configuration** (if installed system-wide):
   ```bash
   sudo mkdir -p /etc/zopen
   sudo cp /opt/etc/zopen/config.toml /etc/zopen/config.toml
   ```

3. **Remove old configuration directories** (optional):
   ```bash
   rm -rf ~/.zopen
   ```

4. **Verify the migration:**
   ```bash
   zopen --list
   ```

#### Environment Variable Changes

If you used the `ZOPEN_CONFIG` environment variable:

**Old:**
```bash
export ZOPEN_CONFIG=~/.zopen/config.toml
```

**New:**
```bash
# No longer needed - just place config at ~/.config/zopen/config.toml
# Or use --config flag:
zopen --config /path/to/config.toml file.txt
```

#### Configuration Format Compatibility

The TOML format remains the same, so your configuration should work as-is after moving the file.

**Example migration for config.toml:**

```toml
# This works in both v0.5 and v0.6+
[defaults]
editor = "$EDITOR"
prefer_mime = true

[mime_types]
"text/plain"       = "vim"
"application/pdf"  = "evince"
"image/jpeg"       = "gimp"

[extensions]
".md"  = "typora"
".py"  = "vim"
```

---

## Compatibility Notes

### Python Version Requirements

| Version | Python | Status |
|---------|--------|--------|
| v0.7.x  | 3.11+  | Current |
| v0.6.x  | 3.10+  | LTS |
| v0.5.x  | 3.9+   | EOL |
| v0.4.x  | 3.8+   | EOL |

**To check your Python version:**
```bash
python --version
```

**If upgrading Python version:**
```bash
pip install --upgrade pip
pip install --upgrade zopen
```

### Dependency Changes

**v0.7.x:**
- `python-magic` (optional, recommended for accurate MIME detection)
- `tomllib` (bundled in Python 3.11+)

**v0.6.x and earlier:**
- `python-magic` (optional)
- `toml` package (if Python < 3.11)

**If your Python version is < 3.11 and you're on v0.6.x:**

The `toml` package is automatically installed. No action needed.

### Installed Paths

Configuration and data paths remain consistent across versions:

| Item | Path |
|------|------|
| System config | `/etc/zopen/config.toml` |
| User config | `~/.config/zopen/config.toml` |
| Project config | `.zopen.toml` (current directory) |
| Executable | `/usr/bin/zopen` (system) or `~/.local/bin/zopen` (pip) |

---

## Configuration Migration

### Automated Migration Tool

If available, use the migration script:

```bash
zopen --init-config
```

This creates a new default configuration at `~/.config/zopen/config.toml` without overwriting existing configs.

### Manual Configuration Checks

After upgrading, verify your configuration:

```bash
# List all effective mappings
zopen --list

# Test a file
zopen --verbose --dry-run testfile.txt

# Check for syntax errors
python3 -c "import tomllib; tomllib.load(open('$HOME/.config/zopen/config.toml', 'rb'))"
```

### Known Configuration Issues

#### Issue: "Config file not found" after upgrade

**Symptoms:**
```bash
$ zopen --list
# Shows only built-in defaults
```

**Solution:**
```bash
# Verify the new config location
ls -la ~/.config/zopen/config.toml

# If missing, create one
zopen --init-config

# Or copy from backup
cp ~/.config/zopen.backup/config.toml ~/.config/zopen/
```

#### Issue: "Invalid TOML" parsing error

**Symptoms:**
```bash
$ zopen --verbose --dry-run test.txt
ConfigError: Invalid TOML syntax
```

**Solution:**
1. Check for TOML syntax errors:
   ```bash
   python3 -c "import tomllib; tomllib.load(open('$HOME/.config/zopen/config.toml', 'rb'))"
   ```

2. Common issues:
   - Trailing commas in tables
   - Unquoted special characters
   - Mixed tabs and spaces

3. Validate your config:
   ```bash
   python3 << 'EOF'
   import tomllib
   with open('$HOME/.config/zopen/config.toml', 'rb') as f:
       try:
           config = tomllib.load(f)
           print("✓ Config is valid")
           print(f"  - MIME types: {len(config.get('mime_types', {}))}")
           print(f"  - Extensions: {len(config.get('extensions', {}))}")
       except tomllib.TOMLDecodeError as e:
           print(f"✗ Config error at line {e.lineno}: {e.msg}")
   EOF
   ```

---

## Rollback Instructions

If you need to revert to a previous version:

### Rollback from v0.7.x to v0.6.x

```bash
# Using pip
pip install 'zopen==0.6.4'

# Or using apt (if installed system-wide)
sudo apt install zopen=0.6.4-1

# Verify
zopen --version
```

### Rollback Configuration

Configuration is backward compatible, so no changes needed. However, if experiencing issues:

```bash
# Restore from backup
cp -r ~/.config/zopen.backup/* ~/.config/zopen/

# Or start fresh
rm ~/.config/zopen/config.toml
zopen --init-config
```

### Rollback from v0.6.x to v0.5.x

**⚠️ Warning:** v0.5.x uses different config paths.

1. **Restore old config location:**
   ```bash
   mkdir -p ~/.zopen
   cp ~/.config/zopen/config.toml ~/.zopen/config.toml
   ```

2. **Install old version:**
   ```bash
   pip install 'zopen==0.5.0'
   ```

3. **Verify:**
   ```bash
   zopen --version
   ```

---

## Version History

| Version | Release Date | Python | Status | Notes |
|---------|--------------|--------|--------|-------|
| v0.7.x  | 2024+        | 3.11+  | Current | Enhanced config system, improved MIME detection |
| v0.6.x  | 2024         | 3.10+  | LTS | Config location moved to XDG |
| v0.5.x  | 2023         | 3.9+   | EOL | Original TOML config system |
| v0.4.x  | 2023         | 3.8+   | EOL | Legacy JSON config |

---

## Getting Help

If you encounter issues during upgrade:

1. **Check the [FAQ](faq.md)** - Most common issues are documented
2. **Review [Troubleshooting](user-guide.md#9-troubleshooting)** - Solutions for common problems
3. **Run with verbose mode:**
   ```bash
   zopen --verbose --dry-run yourfile.txt
   ```
4. **Report an issue:** https://github.com/pilakkat1964/z-open/issues

---

## Checklist for Successful Upgrade

- [ ] Backed up configuration (`~/.config/zopen.backup`)
- [ ] Noted current version (`zopen --version`)
- [ ] Installed new version
- [ ] Verified new version (`zopen --version`)
- [ ] Tested configuration (`zopen --list`)
- [ ] Tested with sample file (`zopen --dry-run test.txt`)
- [ ] All tests pass, or issues documented

✅ **You're ready to use the upgraded version!**
