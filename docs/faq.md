# zopen — Frequently Asked Questions

This guide addresses common questions, unexpected behaviors, and advanced scenarios not covered in the main user guide.

---

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Configuration & Mappings](#configuration--mappings)
3. [MIME Type Detection](#mime-type-detection)
4. [Editor Resolution](#editor-resolution)
5. [File Handling](#file-handling)
6. [Scripting & Automation](#scripting--automation)
7. [Troubleshooting](#troubleshooting)
8. [Performance & Optimization](#performance--optimization)
9. [Integration with Tools](#integration-with-tools)

---

## Installation & Setup

### Q: Which installation method should I use?

**A:** Choose based on your use case:

| Scenario | Method | Command |
|----------|--------|---------|
| System-wide, Debian/Ubuntu | Debian package | `sudo apt install zopen` |
| User-level, no sudo needed | pip (user) | `pip install --user zopen` |
| Development/contributing | Editable | `pip install -e .` |
| Isolated, reproducible environment | Virtual environment | `python -m venv venv && pip install zopen` |
| One-off testing | Direct Python | `python zopen.py --help` |

### Q: I installed via pip but `zopen` is not in my PATH

**A:** The pip binary may be installed to a directory not in your PATH.

```bash
# Find where pip installed it
pip show -f zopen | grep Location

# Check if the bin directory is in PATH
echo $PATH

# If not, either:
# 1. Add it to PATH in ~/.bashrc:
export PATH="$PATH:$HOME/.local/bin"

# 2. Or create a symlink in a directory that IS in PATH:
ln -s $(python -m pip show -f zopen | grep Location | cut -d' ' -f2)/bin/zopen ~/bin/zopen
```

### Q: How do I uninstall zopen completely?

**A:** Depends on your installation method:

```bash
# If installed via pip
pip uninstall zopen

# If installed via apt
sudo apt remove zopen        # keeps config files
sudo apt purge zopen         # removes everything including config

# If from source (editable)
pip uninstall zopen
rm -rf /path/to/z-open/.venv  # if you used a venv
```

---

## Configuration & Mappings

### Q: How do I configure zopen for my team's project?

**A:** Create a `.zopen.toml` in your project root:

```toml
# .zopen.toml (commit to version control)
[defaults]
prefer_mime = true

[mime_types]
"text/x-python"     = "vim"
"text/x-java"       = "code"
"text/html"         = "firefox"
"application/json"  = "vim"

[extensions]
".Dockerfile"  = "vim"
".env"         = "code"
```

Then commit it to git. All team members using zopen will automatically use these mappings.

**Tip:** To override for a specific machine, create `~/.config/zopen/config.toml` (user-level) or `/etc/zopen/config.toml` (system-level). These take precedence over the project config.

### Q: I have many extensions but they all map to the same editor. Can I simplify?

**A:** Yes, use base-type wildcards in `[mime_types]`:

```toml
[mime_types]
"text"      = "vim"           # All text/* types → vim
"image"     = "gimp"          # All image/* types → gimp
"audio"     = "mpv"           # All audio/* types → mpv
"video"     = "vlc"           # All video/* types → vlc
```

This is much cleaner than listing every `text/plain`, `text/html`, `text/css`, etc. separately.

### Q: Can I pass editor flags in the config?

**A:** Yes! Editor values can include flags and arguments:

```toml
[mime_types]
"text/x-python"  = "vim -c ':set number'"
"text/markdown"  = "code --new-window"
"application/pdf" = "evince --fullscreen"
```

These flags are passed to the editor as-is. Be careful with quoting and escaping.

### Q: How do I use `$EDITOR` in my config but override it for specific types?

**A:** Mix the sentinel with specific mappings:

```toml
[defaults]
editor = "$EDITOR"     # Fallback for unmapped files

[mime_types]
"application/pdf" = "evince"     # PDF always opens in evince
"image/jpeg"      = "gimp"       # JPEG always opens in gimp
# Everything else falls back to $EDITOR
```

### Q: Can I reload the config without restarting my shell?

**A:** zopen reads the config fresh on every invocation, so changes take effect immediately. Just re-run the command:

```bash
# Edit your config
vim ~/.config/zopen/config.toml

# Next zopen command automatically uses the new config
zopen myfile.py
```

No restart needed!

---

## MIME Type Detection

### Q: How does zopen decide between MIME type and file extension?

**A:** It depends on the `prefer_mime` setting:

```toml
[defaults]
prefer_mime = true    # MIME wins if both match (default)
```

**Example:**
- File: `archive.tar` 
- MIME detected: `application/x-tar`
- Extension: `.tar`
- If `prefer_mime = true`: uses `[mime_types]` entry
- If `prefer_mime = false`: uses `[extensions]` entry

### Q: My file has no extension. How does zopen handle it?

**A:** Without an extension, zopen falls back to MIME-based detection if available:

```bash
zopen Makefile          # No extension, uses MIME type
zopen README            # No extension, uses MIME type
zopen .gitignore        # No extension, uses MIME type
```

If MIME detection fails (no `python3-magic`), it falls back to the `editor` sentinel in `[defaults]`.

### Q: Can I force a specific MIME type for a file?

**A:** Yes, use the `--mime` flag:

```bash
zopen --mime text/x-python myscript
```

This is useful for files with misleading extensions or content.

### Q: Why is my `.json` file being detected as `text/plain` instead of `application/json`?

**A:** If using `mimetypes` module (no `python3-magic`), extension-based detection is inherently limited.

Install `python3-magic` for accurate content-based detection:

```bash
sudo apt-get install python3-magic libmagic1
```

Then verify:

```bash
zopen --verbose --dry-run myfile.json
```

The output should show `application/json` detected via libmagic.

---

## Editor Resolution

### Q: My config says `editor = "$EDITOR"` but `vi` opens instead of my preferred editor

**A:** The `$EDITOR` sentinel resolves in this order:

1. `$VISUAL` environment variable (if set and non-empty)
2. `$EDITOR` environment variable (if set and non-empty)
3. `vi` (hardcoded fallback)

**Fix:**

```bash
# Set both in your shell profile (~/.bashrc, ~/.zshrc, etc.)
export VISUAL=vim
export EDITOR=vim
```

Then reload your shell:

```bash
source ~/.bashrc
```

Or verify they're set:

```bash
echo $VISUAL
echo $EDITOR
```

### Q: I want different editors for different project types

**A:** Use project-level `.zopen.toml` files:

```
my-python-project/
├── .zopen.toml      # Maps Python files to vim
└── src/
    ├── main.py
    └── utils.py

my-java-project/
├── .zopen.toml      # Maps Java files to IntelliJ
└── src/
    ├── Main.java
    └── Utils.java
```

**Content of `my-python-project/.zopen.toml`:**
```toml
[mime_types]
"text/x-python" = "vim"
```

**Content of `my-java-project/.zopen.toml`:**
```toml
[mime_types]
"text/x-java" = "idea"
```

### Q: Can I see which config file was used for a file?

**A:** Use `--verbose --dry-run`:

```bash
zopen --verbose --dry-run myfile.py
```

The output includes:
- Which MIME type was detected (and by which method)
- Which config file matched
- The resolved editor command

---

## File Handling

### Q: Can I open multiple files at once?

**A:** Yes! zopen groups files by editor and opens them together:

```bash
zopen file1.py file2.py file3.py
# Opens all three in the same vim session
```

For files mapping to different editors:

```bash
zopen document.pdf image.png script.py
# Opens PDF in evince, PNG in gimp, script in vim
# Each in separate process
```

### Q: How does zopen handle symbolic links?

**A:** MIME detection reads through symlinks:

```bash
ln -s /etc/hostname mylink
zopen mylink           # Opens with MIME type of /etc/hostname content
```

### Q: What if a file doesn't exist?

**A:** zopen will attempt to open it anyway. The editor may create it (e.g., vim):

```bash
zopen nonexistent.txt
# vim opens and creates the file if you save
```

Use `--dry-run` to preview what would happen:

```bash
zopen --dry-run nonexistent.txt
```

### Q: Can I open files from stdin?

**A:** Not directly. But you can redirect to a temp file:

```bash
curl https://example.com/file.pdf | zopen <(cat)
# Or save first:
curl https://example.com/file.pdf > /tmp/file.pdf && zopen /tmp/file.pdf
```

---

## Scripting & Automation

### Q: How do I use zopen in a shell script?

**A:** Import the Python module and use the public API:

```python
#!/usr/bin/env python3
from zopen import load_config, detect_mime, resolve_editor

config = load_config()
mime = detect_mime('myfile.py')
editor_cmd = resolve_editor(mime, 'myfile.py', config)
print(f"Would open with: {editor_cmd}")
```

See [API Documentation](api.md) for full details.

### Q: I want to open a file but not block the shell. How?

**A:** Use `&` to background the process:

```bash
zopen myfile.py &
```

Or use `nohup` to detach from the terminal:

```bash
nohup zopen myfile.py &
```

### Q: Can I create an alias for common operations?

**A:** Yes! Add to your shell profile:

```bash
# Open with a specific editor
alias zopen-vim='zopen --editor vim'
alias zopen-code='zopen --editor code'

# Open and list config
alias zopen-config='zopen --list'

# Open with verbose output
alias zopen-debug='zopen --verbose --dry-run'
```

### Q: How do I pipe output from one command to zopen?

**A:** You can't pipe directly to zopen (it expects file paths), but you can create a temp file:

```bash
# Method 1: temp file
git diff > /tmp/diff.patch && zopen /tmp/diff.patch

# Method 2: process substitution (bash)
zopen <(git diff)

# Method 3: Write to a named pipe
mkfifo /tmp/mypipe
git diff > /tmp/mypipe &
zopen /tmp/mypipe
```

---

## Troubleshooting

### Q: zopen --help shows usage but I'm confused about something

**A:** Read the detailed guides:

| Topic | Guide |
|-------|-------|
| Installation, CLI, config format | [User Guide](user-guide.md) |
| Internal architecture, module structure | [Design Documentation](design.md) |
| Building, packaging, releases | [Build Guide](build.md) |
| Programmatic use | [API Documentation](api.md) |
| Real-world workflows | [Examples & Recipes](examples.md) |

### Q: zopen works fine in my terminal but fails in a cron job

**A:** Environment variables like `$EDITOR` and `$HOME` may not be set in cron.

```bash
# In your crontab, explicitly set environment:
EDITOR=vim
VISUAL=vim
HOME=/home/username

# Then your zopen commands:
0 9 * * * zopen /var/log/myapp.log
```

Or use absolute paths and hard-code the editor:

```bash
0 9 * * * /usr/bin/zopen --editor vim /var/log/myapp.log
```

### Q: zopen sometimes hangs when opening a file

**A:** This usually means the editor is waiting for input. 

**Diagnosis:**
```bash
zopen --verbose --dry-run myfile.py
```

If the output shows the correct editor but the process hangs:
1. Check if the editor is actually running: `ps aux | grep vim`
2. The editor may be waiting for other processes. Try backgrounding: `zopen myfile.py &`

### Q: I get a "command not found" error for my editor

**A:** The editor command is not in your PATH:

```bash
# Verify the editor exists and is in PATH
which vim
which code
which evince

# If not found, install it or use the full path in config:
[mime_types]
"text/x-python" = "/usr/bin/vim"
```

### Q: Config file parsing fails silently

**A:** Test the TOML syntax manually:

```bash
python3 -c "import tomllib; print(tomllib.load(open('$HOME/.config/zopen/config.toml', 'rb')))"
```

Common issues:
- Trailing commas in tables
- Quotes around keys that should be unquoted
- Invalid escape sequences

### Q: zopen --list shows unexpected mappings

**A:** Check the config precedence. Configs are deep-merged in this order:

1. Built-in defaults
2. `/etc/zopen/config.toml`
3. `~/.config/zopen/config.toml`
4. `.zopen.toml` (current directory)

To see which config won:

```bash
zopen --verbose --dry-run myfile.py
```

To debug each layer separately:

```bash
# See built-in defaults only
ZOPEN_SYSCONFDIR=/nonexistent zopen --list

# See defaults + system config
# (requires looking at the code or checking /etc/zopen/config.toml)
```

---

## Performance & Optimization

### Q: zopen takes a long time to start

**A:** MIME detection via libmagic can be slow on large files.

**Solutions:**

1. Prefer extension-based detection (faster):
```toml
[defaults]
prefer_mime = false     # Use extension instead
```

2. Disable MIME detection for known extensions:
```toml
[extensions]
".mp4"  = "vlc"        # Don't probe this file
".pdf"  = "evince"     # Don't probe this file

[mime_types]
"text" = "vim"         # Only probe text files
```

3. Profile with `--verbose`:
```bash
time zopen --verbose --dry-run largefile.bin
```

### Q: Why does `python3-magic` sometimes fail?

**A:** Both the Python module and system library must be installed:

```bash
# Install both
sudo apt-get install python3-magic libmagic1

# Verify
python3 -c "import magic; print('OK')"
file -L /etc/hostname    # System libmagic works
```

---

## Integration with Tools

### Q: Can I use zopen with `fzf` (fuzzy finder)?

**A:** Yes! Create a script that combines them:

```bash
#!/bin/bash
# fzf-zopen: fuzzy select files and open with zopen

find . -type f | fzf --multi | xargs zopen
```

Save as `fzf-zopen` and make executable:
```bash
chmod +x fzf-zopen
./fzf-zopen
```

### Q: How do I use zopen with `git add -p` or other git workflows?

**A:** Git doesn't directly invoke zopen, but you can manually review files before committing:

```bash
# Review changed files interactively
for file in $(git diff --name-only); do
    zopen "$file"
done
```

Or in a git alias:

```bash
git config --global alias.review '!for f in $(git diff --name-only); do zopen "$f"; done'
git review
```

### Q: Can I use zopen as a file handler in a file manager?

**A:** Yes, if your file manager supports custom handlers. Examples:

**GNOME Files (Nautilus):**
1. Right-click a file → Properties → Open With
2. Select "Other Application"
3. Enter: `/usr/bin/zopen %f`

**Thunar (XFCE):**
1. Edit → Configure Custom Actions
2. Create action that runs: `zopen %f`

**Ranger (CLI file manager):**
```bash
# Add to ~/.config/ranger/rc.conf
map x zopen %f
```

---

## Still have questions?

- Check the [User Guide](user-guide.md) for detailed CLI and config documentation
- Review [Examples & Recipes](examples.md) for real-world workflows
- Read [Design Documentation](design.md) to understand the internals
- Check the [Troubleshooting](user-guide.md#9-troubleshooting) section in the user guide
