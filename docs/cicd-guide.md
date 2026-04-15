---
layout: default
title: Z-Open CI/CD & Release Guide
---

# zopen — CI/CD & Release Guide

> **Audience:** This guide is written for contributors and maintainers who are
> new to GitHub Actions and the GitHub release workflow.  No prior CI/CD
> experience is assumed.

---

## Table of Contents

1. [What is CI/CD?](#1-what-is-cicd)
2. [Key concepts](#2-key-concepts)
3. [How zopen's release pipeline works](#3-how-zedits-release-pipeline-works)
4. [Step-by-step: publishing a new release](#4-step-by-step-publishing-a-new-release)
5. [What happens on GitHub automatically](#5-what-happens-on-github-automatically)
6. [The release assets explained](#6-the-release-assets-explained)
7. [Monitoring a running workflow](#7-monitoring-a-running-workflow)
8. [Troubleshooting](#8-troubleshooting)
9. [Local build (without CI)](#9-local-build-without-ci)

---

## 1. What is CI/CD?

**CI** stands for *Continuous Integration* — automatically building and testing
code every time a change is pushed.

**CD** stands for *Continuous Delivery* (or *Deployment*) — automatically
packaging and publishing software so users can install it without manual steps.

Together, CI/CD replaces the error-prone human process of:

```
developer builds on their laptop → manually zips files → uploads to a server
```

with a fully automated, reproducible process that runs on GitHub's servers every
time you push a tag.

---

## 2. Key concepts

| Concept | What it means |
|---------|---------------|
| **GitHub Actions** | GitHub's built-in CI/CD platform.  Free for public repositories. |
| **Workflow** | A YAML file in `.github/workflows/` that describes *what to do* and *when to do it*. |
| **Job** | A unit of work inside a workflow.  Each job runs on a fresh virtual machine. |
| **Step** | A single command (or reusable action) inside a job. |
| **Trigger** | The event that starts a workflow (e.g. pushing a tag). |
| **Tag** | A named pointer to a specific Git commit, used to mark releases (e.g. `v0.5.0`). |
| **GitHub Release** | A page on GitHub that lists a specific version, its changelog, and downloadable files. |
| **Asset** | A file attached to a GitHub release (e.g. a `.tar.gz` archive). |
| **Action** | A reusable, community-supplied workflow step (e.g. `actions/checkout@v4`). |
| **Runner** | The virtual machine GitHub spins up to execute a job (`ubuntu-latest` = Ubuntu Linux). |

---

## 3. How zopen's release pipeline works

### Workflow file location

```
.github/
└── workflows/
    └── release.yml    ← the entire CI/CD definition lives here
```

### Trigger: push a version tag

The workflow starts **only** when a tag whose name starts with `v` is pushed to
the repository:

```yaml
on:
  push:
    tags:
      - 'v*'
```

Tags like `v0.5.0`, `v1.0.0`, `v2.3.1-beta` all match.  Regular branch pushes
(e.g. pushing to `master`) do **not** trigger this workflow.

### Pipeline diagram

```
Developer pushes tag v0.5.0
        │
        ▼
GitHub detects the tag push
        │
        ▼
GitHub Actions starts a fresh Ubuntu VM
        │
        ├─ Step 1: Checkout source code
        │
        ├─ Step 2: Set up Python 3.11
        │
        ├─ Step 3: Install cmake + python3-magic
        │
        ├─ Step 4: Extract version number from tag ("v0.5.0" → "0.5.0")
        │
        ├─ Step 5: Configure build  (cmake -B build)
        │
        ├─ Step 6: Build install archive  → zopen-0.5.0-Linux.tar.gz
        │
        ├─ Step 7: Build source archive   → zopen-0.5.0-source.tar.gz
        │
        ├─ Step 8: Resolve asset filenames
        │
        └─ Step 9: Create GitHub Release
                   • Title: "zopen v0.5.0"
                   • Auto-generated changelog
                   • Attaches both .tar.gz files as downloadable assets
```

### Permissions

The workflow is granted **write access to repository contents** so it can create
the release:

```yaml
permissions:
  contents: write
```

This is the minimum permission required; no other GitHub resources are touched.

---

## 4. Step-by-step: publishing a new release

### Prerequisites

- Git installed and configured on your machine.
- You have push access to `proteus-cpi/zopen`.
- The `gh` CLI is installed (optional — only needed if you want to create a
  release locally without pushing a tag).

### Step 1 — Update the version number

Update the version in **all three locations**:

1. **`CMakeLists.txt`** — update the `VERSION` field:
   ```cmake
   project(zopen
       VERSION      0.6.5   # ← change this
       ...
   )
   ```

2. **`pyproject.toml`** — update the `version` field:
   ```toml
   [project]
   version = "0.6.5"   # ← change this
   ```

3. **`debian/changelog`** — add a new entry at the top (use `dch` or edit manually):
   ```bash
   dch -v 0.6.5-1 "Release 0.6.5 - <description of changes>"
   ```
   Or edit `debian/changelog` directly:
   ```
   zopen (0.6.5-1) unstable; urgency=low

     * Release 0.6.5 - Your release notes here
     * Multiple bullet points if needed

    -- Maintainer <maintainer@example.com>  DATE
   ```

Commit all version changes:

```bash
git add CMakeLists.txt pyproject.toml debian/changelog
git commit -m "release: bump version to 0.6.5"
```

### Step 2 — Push the version commit

```bash
git push origin master
```

### Step 3 — Create and push the tag

The tag name **must** start with `v` followed by the version number:

```bash
git tag -a v0.6.5 -m "Release 0.6.5 - Your release description"
git push origin v0.6.5
```

That single `git push origin v0.6.5` command is the only manual action required
to trigger the entire release pipeline.

### Step 4 — (Optional) Monitor the workflow

Monitor progress at:

```
https://github.com/pilakkat1964/z-open/actions/workflows/release.yml
```

When the workflow succeeds, the release is published automatically at:

```
https://github.com/pilakkat1964/z-open/releases/tag/v0.6.5
```

### Alternative: Manual release dispatch (via GitHub UI)

If you need to create a release manually without pushing a tag:

1. Go to **Actions** → **Release** workflow
2. Click **Run workflow**
3. Enter the version tag (e.g., `v0.6.5`) in the input field
4. Click **Run workflow**

The release will be created with the same artifacts as an automated release.

---

## 5. What happens on GitHub automatically

Once the tag is pushed GitHub Actions:

1. **Provisions a fresh Ubuntu virtual machine** — nothing from previous runs
   can affect the build.  This guarantees reproducibility.

2. **Checks out the exact commit** the tag points to — users always get the
   code that matches the version number.

3. **Installs all build dependencies** — `cmake` and `python3-magic` are
   installed fresh each time.

4. **Runs CMake** to configure the project and generate a CPack configuration.

5. **Runs CPack** (via the `tarball` CMake target) to create the install
   archive.  CPack stages files into a temporary directory under
   `/opt/zopen/...` without touching the runner's real filesystem.

6. **Runs `git archive`** to produce a clean source tarball — this contains
   only the files tracked by Git (no build artefacts, no editor swap files).

7. **Creates the GitHub Release** using the
    [`softprops/action-gh-release`](https://github.com/softprops/action-gh-release)
    action, which:
    - Sets the release title to `zopen vX.Y.Z`
    - Auto-generates a changelog from commit messages since the previous tag
    - Uploads all three release assets (see below)

---

## 6. The release assets explained

Each release ships three archives:

### `zopen-X.Y.Z-Linux.deb` — Debian package (amd64)

This is the **recommended package for Linux users**.  Install via:

```bash
sudo apt install ./zopen-0.6.5-Linux.deb
```

Or download and install directly:

```bash
wget https://github.com/pilakkat1964/z-open/releases/download/v0.6.5/zopen-0.6.5-Linux.deb
sudo apt install ./zopen-0.6.5-Linux.deb
```

**Includes:**
- Pre-built binary under `/opt/zopen/bin/zopen`
- System configuration at `/opt/etc/zopen/config.toml`
- Automatic installation of launcher scripts
- Easy uninstall via `apt remove zopen`

### `zopen-X.Y.Z-Linux.tar.gz` — Install archive

This is the **ready-to-use binary distribution**.  It contains the full
directory tree that gets installed under `/opt/zopen`, pre-laid-out so you can
extract it directly to `/`:

```
opt/
└── zopen/
    ├── bin/
    │   └── zopen          ← main executable
    ├── share/
    │   └── doc/zopen/     ← documentation
    └── etc/zopen/         ← default config
```

**To install:**

```bash
sudo tar -xzf zopen-0.6.5-Linux.tar.gz -C /
```

**To uninstall:**

```bash
sudo rm -rf /opt/zopen
```

### `zopen-X.Y.Z-source.tar.gz` — Source archive

This is a **clean snapshot of the source code** at the tagged commit.  It is
equivalent to what you would get from `git clone`, minus the `.git` history.
Use this if you want to inspect the code, build from source on a different
platform, or audit the release.

**To build from source:**

```bash
tar -xzf zopen-0.6.5-source.tar.gz
cd zopen-0.6.5-source/
cmake -B build -DCMAKE_INSTALL_PREFIX=/opt/zopen -DZOPEN_BUILD_WHEEL=OFF
cmake --build build --target tarball   # or: --target deb
```

---

## 7. Monitoring a running workflow

1. Go to **https://github.com/pilakkat1964/z-open/actions**
2. Click the workflow run that appeared after you pushed the tag.
3. Click any step to expand its log output in real time.
4. A green tick (✓) means the step passed; a red cross (✗) means it failed.

You will also receive a GitHub notification email when the workflow finishes
(pass or fail), provided email notifications are enabled in your GitHub
account settings.

---

## 8. Troubleshooting

### Workflow did not start

- Verify the tag name starts with `v`: `git tag -l` lists all local tags.
- Verify the tag was actually pushed to GitHub: check the **Tags** tab on the
  repository page.
- Check the **Actions** tab for any workflow run (even a failed one) triggered
  by the tag.

### Build step failed

Click the failed step in the Actions UI to read the full log.  Common causes:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `cmake: command not found` | apt-get step failed | Check network connectivity of the runner |
| `CPack: package not generated` | CMakeLists.txt syntax error | Fix locally, commit, re-tag |
| `Permission denied` on release creation | `contents: write` missing | Ensure the `permissions:` block is in the workflow |
| Tag already exists | You tried to re-push an existing tag | Delete old tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z` |

### Re-running after a fix

If the workflow fails and you push a fix to the same tag, you need to **delete
and re-create the tag** because a tag is an immutable pointer:

```bash
# Delete tag locally and on GitHub
git tag -d v0.6.0
git push origin :refs/tags/v0.6.0

# Re-tag after fixing the code
git add <changed files>
git commit -m "fix: ..."
git tag v0.6.0
git push && git push origin v0.6.0
```

---

## 9. Local build (without CI)

You can produce the same release assets on your own machine without pushing a
tag.  This is useful for testing packaging changes before publishing.

```bash
# Configure
cmake -B build -DCMAKE_INSTALL_PREFIX=/opt/zopen

# Build install archive
cmake --build build --target tarball
# → build/zopen-X.Y.Z-Linux.tar.gz

# Build source archive
VERSION=$(grep -m1 'VERSION' CMakeLists.txt | awk '{print $2}')
git archive --format=tar.gz \
  --prefix="zopen-${VERSION}-source/" \
  -o "zopen-${VERSION}-source.tar.gz" \
  HEAD
# → zopen-X.Y.Z-source.tar.gz

# Optionally create a GitHub release manually (requires gh CLI)
gh release create vX.Y.Z \
  --title "zopen vX.Y.Z" \
  --notes "Release notes here" \
  build/zopen-X.Y.Z-Linux.tar.gz \
  zopen-X.Y.Z-source.tar.gz
```

> **Tip:** Always prefer the automated CI path for official releases.  Local
> builds may include uncommitted files or differ from the tagged source,
> breaking reproducibility.
