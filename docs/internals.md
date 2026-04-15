---
layout: default
title: Z-Open Code Internals
---

# zopen Code Architecture and Internals

This document supplements the inline code comments in `zopen.py` and explains the overall architecture and key design decisions.

---

## Code Organization

The `zopen.py` file (3,167 lines) is organized into clear sections:

### Core Sections

1. **Module Header** (lines 1-50)
   - Comprehensive docstring
   - Import statements
   - Compatibility shims for Python < 3.11

2. **Constants & Defaults** (lines 52-250)
   - Built-in configuration
   - System-wide defaults
   - Application candidate lists
   - Error messages and templates

3. **Configuration System** (lines 427-707)
   - `ConfigError`: Exception for config errors
   - `ConfigSchema`: Configuration validation
   - `ConfigDefaults`: Default values management
   - `ConfigCache`: Caching layer
   - `ConfigProvider`: Central configuration provider
   - `XdgIntegration`: XDG Base Directory support

4. **MIME Detection** (lines 825-1292)
   - `MimeDetectionResult`: Detection result data
   - `MimeDetectionStrategy`: Strategy pattern base
   - `LibmagicDetectionStrategy`: Content-based detection
   - `ExtensionDetectionStrategy`: Extension-based fallback
   - `CustomMappingDetectionStrategy`: Config-based detection
   - `MimeDetectionStatistics`: Statistics tracking
   - `MimeDetectionCache`: Performance optimization
   - `EnhancedMimeDetector`: Advanced detection features
   - `MimeDetector`: Main MIME detection interface

5. **Configuration I/O** (lines 1293-1540)
   - `TomlSerializer`: TOML reading/writing
   - `ConfigIO`: File I/O operations
   - `ConfigManager`: Main configuration management

6. **Application Resolution** (lines 1541-1708)
   - `SentinelResolver`: `$EDITOR` sentinel resolution
   - `AppResolver`: Application mapping resolution

7. **Public API** (lines 1709-1805)
   - Functions for external use (imports)
   - Internal helper functions

8. **Configuration Tools** (lines 1807-2260)
   - `ConfigGenerator`: Generate default config
   - `ConfigInit`: Interactive config initialization
   - `DisplayFormatter`: Output formatting
   - `write_default_config`: Config file creation
   - `print_mappings`: Pretty-print configuration

9. **CLI System** (lines 2261-2900+)
   - `CliHandlers`: Main command handlers
   - `build_parser`: Argument parser creation
   - `main`: Entry point
   - Subcommand handlers

---

## Key Design Patterns

### 1. Strategy Pattern (MIME Detection)

The `MimeDetectionStrategy` abstract base class allows multiple detection strategies:

```
MimeDetectionStrategy (ABC)
├── LibmagicDetectionStrategy (content-based, accurate)
├── ExtensionDetectionStrategy (extension-based, fast)
└── CustomMappingDetectionStrategy (config-based)
```

**Why:** Allows flexibility in detection methods and easy addition of new strategies.

**Usage:** `EnhancedMimeDetector` chains these strategies with caching.

---

### 2. Layered Configuration

Configuration is loaded and merged in precedence order:

```
Layer 1: Built-in defaults
    ↓ (deep-merge with)
Layer 2: System config (/etc/zopen/config.toml)
    ↓ (deep-merge with)
Layer 3: User config (~/.config/zopen/config.toml)
    ↓ (deep-merge with)
Layer 4: Project config (./.zopen.toml)
    ↓ (deep-merge with)
Layer 5: Command-line override (--config FILE)
    ↓
Result: Final effective configuration
```

**Why:** Allows configuration at multiple scopes with sensible precedence.

**Implementation:** `ConfigManager.load_layers()` returns `list[ConfigLayer]`

---

### 3. Caching for Performance

Multiple caching layers improve performance:

- **ConfigCache**: Caches parsed TOML files
- **MimeDetectionCache**: Caches MIME detection results
- **Both**: 5-10x performance improvement for repeated operations

**Why:** File I/O and MIME detection are expensive; caching is critical for CLI responsiveness.

**Trade-off:** Cache is in-memory only (cleared on new process).

---

### 4. Sentinel Value Resolution

The special `$EDITOR` value is resolved at runtime:

```
"$EDITOR"
    → Check $VISUAL env var
    → Check $EDITOR env var
    → Fall back to "vi"
```

**Why:** Allows configuration to reference user's preferred editor without hardcoding.

**Implementation:** `SentinelResolver.resolve()` handles the logic.

---

## Module Dependencies

```
zopen.py
├── Python stdlib: argparse, pathlib, subprocess, tomllib, mimetypes
├── Optional: magic (python3-magic for accurate MIME detection)
└── No external dependencies for core functionality
```

**Why:** Minimizes deployment complexity; single-file deployment is a feature.

---

## Class Hierarchy

### Configuration Classes

```
ConfigError (Exception)

ConfigSchema
├── Validates TOML structure
└── Handles type checking

ConfigDefaults
├── Manages default values
└── Provides fallbacks

ConfigCache
├── In-memory caching
└── Expiration tracking

ConfigProvider
├── Central config access
├── Manages all layers
└── Integrates with ConfigCache

ConfigManager
├── Factory for ConfigProvider
├── Static methods for global access
└── Implements ConfigSchema

ConfigIO
├── TOML file I/O
├── Path resolution
└── User config management

XdgIntegration
├── XDG Base Directory support
├── Environment variable handling
└── Path normalization
```

### MIME Detection Classes

```
MimeDetectionResult
├── Encapsulates detection output
├── Includes confidence level
└── Tracks detection method

MimeDetectionStrategy (ABC)
├── LibmagicDetectionStrategy
├── ExtensionDetectionStrategy
└── CustomMappingDetectionStrategy

MimeDetectionStatistics
├── Tracks detection metrics
└── Performance monitoring

MimeDetectionCache
├── Caches results
├── Manages expiration
└── Reports hit rate

EnhancedMimeDetector
├── Chains multiple strategies
├── Implements caching
└── Collects statistics

MimeDetector
├── Main public interface
└── Creates EnhancedMimeDetector
```

### Application Resolution Classes

```
SentinelResolver
├── Resolves $EDITOR sentinel
├── Checks environment variables
└── Falls back to defaults

AppResolver
├── Main resolution logic
├── Implements prefer_mime logic
├── Collects candidate applications
└── Returns best match
```

### CLI Classes

```
CliHandlers
├── Main command router
├── Subcommand handlers
└── Output formatting

ConfigGenerator
├── Generates default config
├── TOML formatting
└── Comment generation

ConfigInit
├── Interactive setup
├── User prompts
└── Config creation

DisplayFormatter
├── Pretty-printing
├── Color support
└── Formatting utilities
```

---

## Key Algorithms

### 1. Configuration Deep-Merge

```python
def _deep_merge(base, override):
    # Recursively merge nested dictionaries
    # Later values override earlier ones
    # Lists and strings are replaced (not merged)
```

**Example:**
```python
base = {'defaults': {'editor': 'vim'}, 'types': {'text': 'vim'}}
override = {'types': {'pdf': 'evince'}}
result = {'defaults': {'editor': 'vim'}, 'types': {'text': 'vim', 'pdf': 'evince'}}
```

---

### 2. MIME Detection Strategy Chain

```
For file path:
1. Try LibmagicDetectionStrategy (if python-magic available)
   └─ Read file content, get accurate MIME type
2. Try CustomMappingDetectionStrategy (config-based)
   └─ Check if file matches config rules
3. Fall back to ExtensionDetectionStrategy
   └─ Check file extension with mimetypes module
4. Return best result with confidence level
```

---

### 3. Application Resolution

```
For file with MIME type and extension:
1. Check if prefer_mime is true
   └─ If yes, look up MIME in config first
2. Look up extension in config
3. Check base MIME type (e.g., 'text' for 'text/plain')
4. Fall back to default app or sentinel
5. Resolve sentinel ($EDITOR) to actual command
6. Return command string
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Load config | O(n) | n = number of config layers |
| Detect MIME (cached) | O(1) | Constant-time lookup |
| Detect MIME (uncached) | O(f) | f = file size (for libmagic) |
| Resolve app | O(m) | m = number of MIME types in config |
| Deep-merge configs | O(n) | n = total config size |

### Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| Config cache | O(n) | n = number of unique paths seen |
| MIME cache | O(m) | m = number of unique MIME results |
| Configuration object | O(c) | c = config file size |

---

## Testing Strategy

The codebase supports testing through:

1. **Direct module import** - All classes are importable
2. **CLI interface** - `--dry-run` and `--verbose` for non-destructive testing
3. **Configuration inspection** - `--list` and `--verbose --dry-run` for debugging
4. **Public API** - All public functions are testable

**Example test:**
```python
from zopen import load_config, detect_mime, resolve_app, load_config_layers
from pathlib import Path

# Test config loading
config = load_config()
assert 'defaults' in config

# Test MIME detection
mime = detect_mime(Path('test.py'))
assert mime == 'text/x-python'

# Test app resolution
layers = load_config_layers()
app = resolve_app(Path('test.py'), layers)
assert app is not None
```

---

## Extension Points

### Adding a New MIME Detection Strategy

```python
class CustomStrategy(MimeDetectionStrategy):
    def detect(self, path: Path) -> MimeDetectionResult | None:
        # Your detection logic
        return MimeDetectionResult(
            mime_type="...",
            detection_method="custom",
            confidence="high"
        )

# Register in EnhancedMimeDetector if needed
```

### Custom Application Mapping

Users can add application mappings in configuration:

```toml
[mime_types]
"application/custom" = "my-app"

[extensions]
".custom" = "my-app"
```

---

## Error Handling

### Exception Hierarchy

```
Exception
└── ConfigError
    └── Configuration-specific errors
```

### Error Handling Strategy

1. **Config errors**: Raise `ConfigError` with descriptive message
2. **Missing files**: Silently skip (return None or empty dict)
3. **Environment errors**: Use `sys.exit()` with error message
4. **Invalid arguments**: argparse handles with automatic --help

---

## Future Improvement Opportunities

### Performance
- Persistent cache across invocations
- Parallel MIME detection for multiple files
- Memory-mapped file access for large files

### Features
- Plugin system for custom detection strategies
- Database of file associations
- Interactive UI for app selection
- Watch mode for automatic opening

### Code Quality
- Type hints for all functions (currently partial)
- More comprehensive logging
- Performance profiling instrumentation
- Additional test coverage

---

## Related Documentation

- [Design Document](design) - High-level architecture
- [Development Guide](../DEVELOPMENT) - Contributing guidelines
- [API Documentation](api) - Public API reference
