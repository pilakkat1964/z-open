# zopen — Examples & Recipes

Real-world workflows and practical examples for common scenarios. Each recipe is a self-contained, copy-paste-ready solution.

---

## Table of Contents

1. [Developer Workflows](#developer-workflows)
2. [Project Team Setup](#project-team-setup)
3. [System Administration](#system-administration)
4. [DevOps & Automation](#devops--automation)
5. [Media & Content](#media--content)
6. [Integration with Popular Tools](#integration-with-popular-tools)
7. [Advanced Scenarios](#advanced-scenarios)

---

## Developer Workflows

### Recipe: Python Development Environment

Configure zopen for a Python project with multiple file types:

**`.zopen.toml` in your project root:**

```toml
[defaults]
prefer_mime = true
editor = "$EDITOR"

[mime_types]
"text/x-python"     = "vim"
"text/x-shellscript" = "vim"
"text/plain"        = "vim"
"application/json"  = "vim"
"text/x-yaml"       = "vim"

[extensions]
".env"              = "vim"
".md"               = "code"
".pdf"              = "evince"
".png"              = "gimp"
```

**Usage:**

```bash
# All open in vim (configured in .zopen.toml)
zopen main.py
zopen requirements.txt
zopen .env

# Markdown opens in code (from config)
zopen README.md

# PDFs open in evince
zopen docs/architecture.pdf
```

**Commit to git:**
```bash
git add .zopen.toml
git commit -m "Add zopen configuration for Python development"
```

All team members automatically get the same editor mappings.

---

### Recipe: Web Development (JavaScript/HTML/CSS)

Setup for a web project:

**`.zopen.toml`:**

```toml
[defaults]
prefer_mime = true

[mime_types]
"text/javascript"    = "code"
"text/html"          = "code"
"text/css"           = "code"
"application/json"   = "code"
"text/x-yaml"        = "code"
"text/plain"         = "code"

[extensions]
".jsx"               = "code"
".tsx"               = "code"
".env.local"         = "code"
".png"               = "firefox"
".pdf"               = "firefox"
```

**Usage:**

```bash
zopen src/App.jsx       # Opens in VS Code
zopen package.json      # Opens in VS Code
zopen docs/api.pdf      # Opens in Firefox
```

---

### Recipe: IDE-Based Workflow

Force all code to open in your IDE:

**`~/.config/zopen/config.toml` (user-level):**

```toml
[defaults]
editor = "idea"    # IntelliJ IDEA for everything

[mime_types]
"image" = "eog"    # Eye of GNOME for images
"video" = "vlc"    # VLC for videos
```

**Or for VS Code:**

```toml
[defaults]
editor = "code --new-window"
```

**Or for Vim enthusiasts:**

```toml
[defaults]
editor = "vim"

[mime_types]
"image" = "feh"
```

---

### Recipe: Quick File Preview Without Editing

Create an alias to see what would open without actually opening it:

**Add to `~/.bashrc` or `~/.zshrc`:**

```bash
alias zopen-preview='zopen --verbose --dry-run'
```

**Usage:**

```bash
$ zopen-preview mystery-file.bin
Detected MIME: application/x-tar
Mapped to editor: tar -xf
Command would be: tar -xf mystery-file.bin

# Now decide if you actually want to run it:
zopen mystery-file.bin
```

---

## Project Team Setup

### Recipe: Consistent Configuration Across Teams

Ensure all developers use the same editor mappings:

**`.zopen.toml` (committed to git):**

```toml
# Team-wide editor mappings
[defaults]
prefer_mime = true

[mime_types]
"text/x-python"      = "vim"
"text/x-java"        = "code"
"text/x-shellscript"  = "vim"
"application/json"   = "vim"
"text/x-yaml"        = "vim"
"application/pdf"    = "evince"

[extensions]
".Dockerfile"  = "vim"
".env"         = "code"    # Sensitive files in VS Code for better UI
```

**How developers use it:**

```bash
git clone <repo>
cd <repo>
zopen main.py          # Uses config from .zopen.toml
```

**Override for individual machine:**

Create `~/.config/zopen/config.toml` for personal preferences (user-level config takes precedence):

```toml
# ~/.config/zopen/config.toml (user-specific, not in git)
[defaults]
prefer_mime = false     # I prefer extension matching

[extensions]
".md" = "notion"        # My personal preference
```

---

### Recipe: Environment-Specific Configurations

Different configs for dev/staging/prod:

**`.zopen.dev.toml`:**
```toml
[defaults]
editor = "vim"    # Dev environment
```

**`.zopen.prod.toml`:**
```toml
[defaults]
editor = "less"   # Prod: read-only viewer (prevents accidents)
prefer_mime = false
```

**Usage:**

```bash
# In development
zopen --config .zopen.dev.toml config.yaml

# In production
zopen --config .zopen.prod.toml config.yaml
```

---

## System Administration

### Recipe: Log File Analysis

Setup for quickly opening log files with syntax highlighting:

**`~/.config/zopen/config.toml`:**

```toml
[defaults]
prefer_mime = false    # Extensions are more reliable for logs

[extensions]
".log"           = "vim"
".conf"          = "vim"
".yml"           = "vim"
".yaml"          = "vim"
"/var/log/*"     = "less"    # View-only for system logs
```

**Usage:**

```bash
# Application logs: open in vim for editing
zopen /home/user/app.log

# System logs: open in less for safe viewing
zopen /var/log/syslog

# Config files: open in vim
zopen /etc/nginx/nginx.conf
```

---

### Recipe: Configuration File Management

Manage configs across multiple servers:

**On each server, create `~/.config/zopen/config.toml`:**

```toml
[defaults]
editor = "vim"

[extensions]
".conf"  = "vim"
".yaml"  = "vim"
".json"  = "jq"        # jq for JSON viewing/filtering
".xml"   = "vim"
".sh"    = "vim"
```

**Then quickly review and edit:**

```bash
zopen /etc/postgresql/postgresql.conf
zopen /etc/nginx/sites-available/mysite
zopen /etc/systemd/system/myservice.service
```

---

### Recipe: System Auditing Script

Use zopen in a bash script to review system configuration:

**`audit.sh`:**

```bash
#!/bin/bash
# Review important system files

echo "Reviewing sudoers configuration..."
zopen /etc/sudoers

echo "Reviewing SSH configuration..."
zopen /etc/ssh/sshd_config

echo "Reviewing sysctl configuration..."
zopen /etc/sysctl.conf

echo "Reviewing crontab..."
zopen /etc/crontab
```

**Usage:**

```bash
chmod +x audit.sh
./audit.sh
```

---

## DevOps & Automation

### Recipe: Docker Development Workflow

Quick access to Docker-related files:

**`.zopen.toml` in Docker project:**

```toml
[defaults]
prefer_mime = false

[extensions]
".Dockerfile"     = "code"
"docker-compose" = "code"
".dockerignore"   = "vim"
".env"            = "code"
".yml"            = "code"
```

**Usage:**

```bash
zopen Dockerfile
zopen docker-compose.yml
zopen .env
```

---

### Recipe: Kubernetes Configuration Review

Manage Kubernetes manifests:

**`~/.config/zopen/config.toml`:**

```toml
[mime_types]
"application/x-yaml" = "code"    # K8s manifests in VS Code

[extensions]
".yaml"  = "code"
".yml"   = "code"
```

**Usage in your K8s project:**

```bash
zopen deployment.yaml
zopen service.yaml
zopen configmap.yaml
```

---

### Recipe: CI/CD Pipeline Debugging

Quickly access pipeline configuration files:

**`.zopen.toml` in CI/CD repo:**

```toml
[extensions]
".github/workflows/*"  = "code"
".gitlab-ci.yml"       = "code"
".circleci/config.yml" = "code"
"Jenkinsfile"          = "code"
"cloudbuild.yaml"      = "code"
```

**Usage:**

```bash
zopen .github/workflows/build.yml
zopen .gitlab-ci.yml
```

---

## Media & Content

### Recipe: Content Creator Setup

For writers, designers, and content teams:

**`~/.config/zopen/config.toml`:**

```toml
[mime_types]
"text/markdown"    = "typora"     # Markdown editor
"text/plain"       = "typora"
"text/html"        = "firefox"    # Preview in browser
"image"            = "krita"      # Image editor
"video"            = "kdenlive"   # Video editor
"audio"            = "audacity"   # Audio editor

[extensions]
".docx"  = "libreoffice"
".xlsx"  = "libreoffice"
".pptx"  = "libreoffice"
".pdf"   = "evince"
".psd"   = "krita"
```

---

### Recipe: Blog Publishing Workflow

Manage blog posts with zopen:

**Project structure:**

```
my-blog/
├── .zopen.toml
├── posts/
│   ├── 2024-01-15-intro.md
│   └── 2024-02-20-advanced.md
└── assets/
    └── images/
```

**`.zopen.toml`:**

```toml
[mime_types]
"text/markdown" = "typora"

[extensions]
".md"  = "typora"
".png" = "gimp"
".jpg" = "gimp"
```

**Workflow:**

```bash
# Edit blog post
zopen posts/2024-01-15-intro.md

# Edit featured image
zopen assets/images/featured.png
```

---

## Integration with Popular Tools

### Recipe: Git Workflow Integration

Open changed files in your default editor:

**Add to `~/.bashrc` or `~/.zshrc`:**

```bash
# Review all changed files (one by one)
zopen-review-changes() {
    git diff --name-only | xargs -I {} sh -c "echo 'Review: {}'; zopen {}"
}

# Review staged changes
zopen-review-staged() {
    git diff --cached --name-only | xargs -I {} sh -c "echo 'Review: {}'; zopen {}"
}

# Open all changed files at once
zopen-open-all-changes() {
    git diff --name-only | xargs zopen
}
```

**Usage:**

```bash
zopen-review-changes      # One by one
zopen-open-all-changes    # All at once
```

---

### Recipe: fzf (Fuzzy Finder) Integration

Fuzzy search and open files:

**Add to `~/.bashrc` or `~/.zshrc`:**

```bash
# Find and open files with fzf
alias zfzf='find . -type f | fzf | xargs zopen'

# Find and open tracked files (git)
alias zgit='git ls-files | fzf | xargs zopen'

# Find and open recent files
alias zrecent='ls -t /home/$USER | fzf | xargs zopen'
```

**Usage:**

```bash
zfzf          # Search all files
zgit          # Search git-tracked files
zrecent       # Search recent files
```

---

### Recipe: ripgrep + zopen for Code Search

Find and open files by content:

**Add to `~/.bashrc` or `~/.zshrc`:**

```bash
# Search code and open matching files
zgrep-open() {
    pattern=$1
    rg --files-with-matches "$pattern" | fzf | xargs zopen
}
```

**Usage:**

```bash
zgrep-open "TODO"           # Find all TODOs and open the file
zgrep-open "function_name"  # Find function definitions
```

---

## Advanced Scenarios

### Recipe: Conditional Editor Selection

Different editors based on file size:

**Create `~/.local/bin/smart-editor.sh`:**

```bash
#!/bin/bash
file="$1"
size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)

if [ "$size" -gt 1000000 ]; then
    # Large file: use lightweight editor
    less "$file"
else
    # Small file: use feature-rich editor
    vim "$file"
fi
```

**In config, reference the wrapper:**

```toml
[defaults]
editor = "/home/user/.local/bin/smart-editor.sh"
```

---

### Recipe: Audit Trail for Important Files

Log every time certain files are opened:

**Create `~/.local/bin/zopen-audit.sh`:**

```bash
#!/bin/bash
# Log file opens to audit trail
file="$1"
echo "[$(date)] Opened: $file by $(whoami)" >> /var/log/zopen-audit.log

# Then open normally
zopen "$file"
```

**Usage:**

```bash
~/.local/bin/zopen-audit.sh /etc/passwd
```

---

### Recipe: Remote File Editing Over SSH

Open remote files on your local machine:

**Script `zopen-ssh`:**

```bash
#!/bin/bash
# Usage: zopen-ssh user@host:/path/to/file

remote_spec="$1"
user_host="${remote_spec%:*}"
file_path="${remote_spec#*:}"

# Copy file locally
scp "$remote_spec" /tmp/zopen-remote-$$

# Open locally
zopen "/tmp/zopen-remote-$$"

# Offer to copy back
read -p "Save changes back to remote? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    scp "/tmp/zopen-remote-$$" "$remote_spec"
fi

# Clean up
rm "/tmp/zopen-remote-$$"
```

**Usage:**

```bash
zopen-ssh user@example.com:/etc/nginx/nginx.conf
```

---

### Recipe: Batch Processing Files

Apply zopen to many files with filtering:

**`.zopen.toml` for batch processing:**

```toml
[mime_types]
"application/pdf" = "convert -density 150 {} {}.png"    # Convert to PNG
"image/jpeg"      = "convert {} -resize 800x600 {}"     # Resize images
"text/plain"      = "dos2unix {}"                        # Fix line endings
```

**Batch script:**

```bash
#!/bin/bash
for file in *.pdf; do
    echo "Processing: $file"
    zopen "$file"
done
```

---

### Recipe: Integration with Custom Tools

Extend zopen with your own tools:

**Create `~/.zopen.toml` with custom handlers:**

```toml
[extensions]
".sql"     = "mycustomsql-viewer"      # Your custom SQL viewer
".proto"   = "protobuf-editor"         # Your protobuf editor
".graphql" = "graphql-playground"      # Your GraphQL tool
```

**Your custom tool receives the file path as argument:**

```bash
#!/bin/bash
# mycustomsql-viewer - custom SQL viewer
sql_file="$1"

# Validate SQL
sqlcheck "$sql_file"

# Format
sqlformat "$sql_file" --output-file "$sql_file.formatted"

# Then edit
vim "$sql_file"
```

**Usage:**

```bash
zopen query.sql           # Uses your custom handler
```

---

### Recipe: Environment-Based Configuration

Different configs for different machines:

**In `~/.bashrc` or `~/.zshrc`:**

```bash
# Load environment-specific zopen config
if [ "$HOSTNAME" = "production-server" ]; then
    export ZOPEN_CONFIG_PREFERENCE="prod"
elif [ "$HOSTNAME" = "staging-server" ]; then
    export ZOPEN_CONFIG_PREFERENCE="staging"
else
    export ZOPEN_CONFIG_PREFERENCE="dev"
fi

# Create zopen alias that uses the right config
alias zopen="zopen --config ~/.zopen.$ZOPEN_CONFIG_PREFERENCE.toml"
```

**Usage:**

```bash
# Automatically picks config based on hostname
zopen config.yaml
```

---

## Tips & Tricks

### Timing Commands

Benchmark how fast zopen opens files:

```bash
time zopen largefile.bin
```

### Debugging Editor Resolution

Trace the exact editor selection process:

```bash
zopen --verbose --dry-run mystery-file
```

### Piping Through Less

For large config output:

```bash
zopen --list | less
```

### Creating Workflows

Combine multiple zopen commands in a shell function:

```bash
# Function to review all config files
review-configs() {
    for file in $(find /etc -name "*.conf" -o -name "*.yaml" -o -name "*.toml"); do
        echo "=== $file ==="
        zopen "$file"
    done
}
```

---

## Need Help?

- Found a bug or have a suggestion? Submit an issue or PR at [github.com/pilakkat1964/z-open](https://github.com/pilakkat1964/z-open)
- Check [FAQ](faq.md) for common questions
- Review [User Guide](user-guide.md) for detailed CLI documentation
- Explore [Design Documentation](design.md) for internals
