# zopen — Python API Documentation

Guide for programmatic use of zopen. Import zopen as a Python module to integrate file opening functionality into your applications.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Core Functions](#core-functions)
4. [Configuration Management](#configuration-management)
5. [MIME Detection](#mime-detection)
6. [Application Resolution](#application-resolution)
7. [Advanced Usage](#advanced-usage)
8. [Complete Examples](#complete-examples)
9. [Error Handling](#error-handling)

---

## Introduction

The zopen module provides a clean Python API for determining which application should open a given file, based on MIME type or extension. This is useful for:

- Building file managers
- Creating IDE plugins
- Automating file processing workflows
- Integrating with shell scripts
- Building file monitoring services

### Key Concepts

- **MIME Detection**: Determines the content type of a file
- **Configuration Loading**: Reads layered TOML configuration from system, user, and project levels
- **Application Resolution**: Maps MIME types/extensions to application commands
- **Config Layers**: Different configuration scopes (built-in → system → user → project)

---

## Installation

### Option 1: Install from pip

```bash
pip install zopen
```

### Option 2: Development Install

```bash
git clone git@github.com:pilakkat1964/z-open.git
cd z-open
pip install -e .
```

### Option 3: Direct File

For deployment where packaging is not available, simply copy `zopen.py` to your project:

```bash
cp zopen.py /path/to/your/project/
```

---

## Core Functions

### `detect_mime(path: Path) -> str | None`

Detect the MIME type of a file using libmagic (if available) or extension-based guessing.

**Parameters:**
- `path` (Path or str): Path to the file

**Returns:**
- str: MIME type (e.g., `"text/plain"`, `"application/pdf"`)
- None: If detection fails

**Example:**

```python
from zopen import detect_mime
from pathlib import Path

mime = detect_mime(Path("document.pdf"))
print(mime)  # "application/pdf"

mime = detect_mime("script.py")
print(mime)  # "text/x-python"
```

**Notes:**
- Requires `python3-magic` for accurate content-based detection
- Falls back to extension guessing if libmagic is unavailable
- Returns None if the file doesn't exist or can't be read

---

## Configuration Management

### `load_config(extra_config: Path | None = None) -> dict[str, Any]`

Load and merge configuration from all layers (built-in, system, user, project).

**Parameters:**
- `extra_config` (Path, optional): Additional config file to load with highest priority

**Returns:**
- dict: Merged configuration dictionary

**Example:**

```python
from zopen import load_config
from pathlib import Path

# Load all configs with default precedence
config = load_config()

# Load with an additional override config
config = load_config(extra_config=Path("~/.config/zopen-custom.toml"))

# Inspect the configuration
print(config["defaults"])      # {'editor': 'vim', 'prefer_mime': True}
print(config["mime_types"])    # {'text/plain': 'vim', 'application/pdf': 'evince'}
print(config["extensions"])    # {'.py': 'vim', '.pdf': 'evince'}
```

---

### `load_config_layers(extra_config: Path | None = None) -> list[ConfigLayer]`

Load configuration but return each layer separately (for debugging).

**Parameters:**
- `extra_config` (Path, optional): Additional config file with highest priority

**Returns:**
- list[ConfigLayer]: List of config layers with source information

**Example:**

```python
from zopen import load_config_layers

layers = load_config_layers()
for layer in layers:
    print(f"Source: {layer.source}")
    print(f"Config: {layer.config}")
    print("---")

# Output:
# Source: built-in
# Config: {...default config...}
# ---
# Source: /etc/zopen/config.toml
# Config: {...system config...}
# ---
# Source: /home/user/.config/zopen/config.toml
# Config: {...user config...}
# ---
```

---

### `read_user_config() -> dict[str, Any]`

Read only the user-level configuration file (`~/.config/zopen/config.toml`).

**Returns:**
- dict: User configuration (empty dict if file doesn't exist)

**Example:**

```python
from zopen import read_user_config

user_cfg = read_user_config()
print(user_cfg)
```

---

### `save_user_config(data: dict[str, Any]) -> None`

Save configuration to the user-level config file.

**Parameters:**
- `data` (dict): Configuration to save

**Example:**

```python
from zopen import save_user_config

config = {
    "defaults": {
        "editor": "vim",
        "prefer_mime": True
    },
    "mime_types": {
        "text/plain": "vim",
        "application/pdf": "evince"
    }
}

save_user_config(config)
# Writes to ~/.config/zopen/config.toml
```

---

### `clear_config_cache() -> None`

Clear the internal configuration cache (useful for testing or long-running processes).

**Example:**

```python
from zopen import load_config, clear_config_cache

# Load config (cached)
config1 = load_config()

# Modify config file externally...

# Clear cache and reload
clear_config_cache()
config2 = load_config()  # Fresh read from disk
```

---

### `get_config_provider() -> ConfigProvider`

Get the ConfigProvider instance for advanced configuration operations.

**Returns:**
- ConfigProvider: Advanced configuration interface

**Example:**

```python
from zopen import get_config_provider

provider = get_config_provider()
# For advanced use cases (see Advanced Usage section)
```

---

## MIME Detection

### Advanced MIME Detection with MimeDetectionResult

Get detailed information about MIME detection:

**Example:**

```python
from zopen import MimeDetector
from pathlib import Path

detector = MimeDetector.create()
result = detector.detect_with_details(Path("document.pdf"))

print(f"MIME type: {result.mime_type}")
print(f"Detection method: {result.detection_method}")  # 'libmagic' or 'extension'
print(f"Confidence: {result.confidence}")  # 'high' or 'low'
```

---

## Application Resolution

### `resolve_app(file_path: Path, layers: list[ConfigLayer], *, mime_override: str | None = None, verbose: bool = False) -> str`

Resolve which application should open a file.

**Parameters:**
- `file_path` (Path or str): Path to the file
- `layers` (list[ConfigLayer]): Configuration layers (from `load_config_layers`)
- `mime_override` (str, optional): Force specific MIME type
- `verbose` (bool, optional): Print resolution details

**Returns:**
- str: Application command (e.g., `"vim"`, `"firefox"`)

**Example:**

```python
from zopen import resolve_app, load_config_layers
from pathlib import Path

layers = load_config_layers()
app = resolve_app(Path("script.py"), layers)
print(app)  # "vim"

# With verbose output
app = resolve_app(Path("script.py"), layers, verbose=True)
# Prints resolution trace

# Override MIME type
app = resolve_app(
    Path("unknown_file"),
    layers,
    mime_override="text/x-python"
)
print(app)  # "vim"
```

**Alias:** `resolve_editor` is an alias for `resolve_app`

---

### `collect_app_candidates(file_path: Path, layers: list[ConfigLayer], *, mime_override: str | None = None) -> list[tuple[str, str]]`

Get all possible application candidates for a file (for UI selection).

**Parameters:**
- `file_path` (Path or str): Path to the file
- `layers` (list[ConfigLayer]): Configuration layers
- `mime_override` (str, optional): Force specific MIME type

**Returns:**
- list[tuple[str, str]]: List of (app_name, reason) tuples

**Example:**

```python
from zopen import collect_app_candidates, load_config_layers
from pathlib import Path

layers = load_config_layers()
candidates = collect_app_candidates(Path("document.txt"), layers)

for app, reason in candidates:
    print(f"{app:20} - {reason}")

# Output:
# vim                  - MIME type match (text/plain)
# nano                 - Extension match (.txt)
# gedit                - Desktop default
```

---

## Advanced Usage

### Creating a File Monitor

Monitor files and open them automatically:

```python
from zopen import resolve_app, load_config_layers, detect_mime
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class AutoOpenHandler(FileSystemEventHandler):
    def __init__(self):
        self.layers = load_config_layers()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        mime = detect_mime(path)
        app = resolve_app(path, self.layers)
        
        print(f"Auto-opening {path} with {app}")
        # Could execute subprocess here
        # subprocess.run([app, str(path)])

# Usage
observer = Observer()
handler = AutoOpenHandler()
observer.schedule(handler, ".", recursive=True)
observer.start()
```

---

### Building a File Manager Integration

Example integration with a file manager UI:

```python
from zopen import resolve_app, load_config_layers, detect_mime
from pathlib import Path

class FileManagerIntegration:
    def __init__(self):
        self.layers = load_config_layers()
    
    def get_open_action(self, file_path: str):
        """Return action for 'Open' right-click menu"""
        path = Path(file_path)
        mime = detect_mime(path)
        app = resolve_app(path, self.layers, verbose=True)
        return f"Open with {app}"
    
    def get_open_with_options(self, file_path: str):
        """Return list for 'Open With' submenu"""
        path = Path(file_path)
        candidates = collect_app_candidates(path, self.layers)
        return [app for app, _ in candidates]

# Usage
fm = FileManagerIntegration()
print(fm.get_open_action("document.pdf"))
# Output: "Open with evince"

print(fm.get_open_with_options("document.txt"))
# Output: ["vim", "nano", "gedit"]
```

---

### Configuration-Aware File Processing

Process files based on configuration:

```python
from zopen import resolve_app, load_config_layers
from pathlib import Path
import subprocess

class FileProcessor:
    def __init__(self):
        self.layers = load_config_layers()
    
    def process_files(self, directory: Path):
        """Process all files in directory based on app resolution"""
        for file_path in directory.glob("**/*"):
            if file_path.is_file():
                app = resolve_app(file_path, self.layers)
                self.handle_file(file_path, app)
    
    def handle_file(self, file_path: Path, app: str):
        """Custom handling based on resolved app"""
        if app == "vim":
            print(f"Text file: {file_path}")
        elif app == "evince":
            print(f"PDF: {file_path}")
        else:
            print(f"Other ({app}): {file_path}")

# Usage
processor = FileProcessor()
processor.process_files(Path("./documents"))
```

---

## Complete Examples

### Example 1: Simple File Opener

```python
#!/usr/bin/env python3
"""Simple file opener using zopen API"""

import subprocess
from pathlib import Path
from zopen import resolve_app, load_config_layers

def open_file(file_path: str):
    """Open a file with the configured application"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: {path} does not exist")
        return False
    
    layers = load_config_layers()
    app = resolve_app(path, layers)
    
    try:
        subprocess.run([app, str(path)])
        return True
    except FileNotFoundError:
        print(f"Error: Application '{app}' not found")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python opener.py <file>")
        sys.exit(1)
    
    open_file(sys.argv[1])
```

---

### Example 2: Configuration Inspector

```python
#!/usr/bin/env python3
"""Inspect zopen configuration"""

from zopen import load_config_layers

def inspect_config():
    """Display configuration from all layers"""
    layers = load_config_layers()
    
    print("Configuration Layers:")
    print("=" * 60)
    
    for i, layer in enumerate(layers, 1):
        print(f"\n{i}. Source: {layer.source}")
        print(f"   Location: {layer.location}")
        
        if not layer.config:
            print("   (empty)")
            continue
        
        if "mime_types" in layer.config:
            print(f"   MIME mappings: {len(layer.config['mime_types'])}")
            for mime, app in list(layer.config["mime_types"].items())[:3]:
                print(f"     - {mime} → {app}")
            if len(layer.config["mime_types"]) > 3:
                print(f"     ... and {len(layer.config['mime_types']) - 3} more")

if __name__ == "__main__":
    inspect_config()
```

---

### Example 3: Batch File Processor

```python
#!/usr/bin/env python3
"""Process multiple files based on zopen configuration"""

from pathlib import Path
from zopen import resolve_app, detect_mime, load_config_layers

def process_directory(directory: str, dry_run: bool = True):
    """Process all files in directory"""
    path = Path(directory)
    layers = load_config_layers()
    
    files_by_app = {}
    
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        
        mime = detect_mime(file_path)
        app = resolve_app(file_path, layers)
        
        if app not in files_by_app:
            files_by_app[app] = []
        
        files_by_app[app].append(file_path)
    
    # Display results
    for app, files in sorted(files_by_app.items()):
        print(f"\n{app}: {len(files)} file(s)")
        for file_path in files[:3]:
            print(f"  - {file_path.relative_to(path)}")
        if len(files) > 3:
            print(f"  ... and {len(files) - 3} more")
    
    if not dry_run:
        print("\nWould process files above")

if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    process_directory(directory, dry_run=True)
```

---

## Error Handling

### Exception Types

**ConfigError**

Raised when configuration loading or parsing fails:

```python
from zopen import load_config, ConfigError

try:
    config = load_config()
except ConfigError as e:
    print(f"Configuration error: {e}")
```

---

### Handling Missing Files

```python
from zopen import detect_mime, resolve_app, load_config_layers
from pathlib import Path

def safe_open(file_path: str):
    """Safely determine how to open a file"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return None
    
    if not path.is_file():
        print(f"Not a file: {file_path}")
        return None
    
    try:
        mime = detect_mime(path)
        layers = load_config_layers()
        app = resolve_app(path, layers)
        return app
    except Exception as e:
        print(f"Error resolving application: {e}")
        return None
```

---

### Debugging with Verbose Mode

```python
from zopen import resolve_app, load_config_layers
from pathlib import Path

path = Path("mystery-file")
layers = load_config_layers()

# Enable verbose output for debugging
app = resolve_app(path, layers, verbose=True)
# Prints detailed resolution trace
```

---

## See Also

- [User Guide](user-guide.md) - CLI usage and configuration
- [Design Documentation](design.md) - Internal architecture
- [FAQ](faq.md) - Common questions
- [Examples & Recipes](examples.md) - Real-world workflows
