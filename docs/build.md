---
layout: default
title: Z-Open Build and Packaging Guide
---

# zopen — Build and Packaging Guide

This document covers every way to build, install, and package `zopen`,
from a quick developer pip install through to a signed Debian source package.

---

## Table of contents

1. [Repository layout](#1-repository-layout)
2. [Prerequisites](#2-prerequisites)
3. [Python packaging (pip / wheel)](#3-python-packaging-pip--wheel)
   - 3.1 [Building a wheel](#31-building-a-wheel)
   - 3.2 [Installing with pip](#32-installing-with-pip)
   - 3.3 [Editable / developer install](#33-editable--developer-install)
   - 3.4 [`pyproject.toml` reference](#34-pyprojecttoml-reference)
4. [CMake build system](#4-cmake-build-system)
   - 4.1 [Concepts](#41-concepts)
   - 4.2 [Configure step](#42-configure-step)
   - 4.3 [CMake options reference](#43-cmake-options-reference)
   - 4.4 [CMake install-directory variables](#44-cmake-install-directory-variables)
   - 4.5 [Build step](#45-build-step)
   - 4.6 [Install step](#46-install-step)
   - 4.7 [Installed file layout](#47-installed-file-layout)
   - 4.8 [CMake targets reference](#48-cmake-targets-reference)
5. [CPack packaging](#5-cpack-packaging)
   - 5.1 [Generating a `.deb` with CPack](#51-generating-a-deb-with-cpack)
   - 5.2 [Generating a `.tar.gz` with CPack](#52-generating-a-targz-with-cpack)
   - 5.3 [Generating an `.rpm` with CPack](#53-generating-an-rpm-with-cpack)
   - 5.4 [CPack variables reference](#54-cpack-variables-reference)
6. [Debian native packaging (`dpkg-buildpackage`)](#6-debian-native-packaging-dpkg-buildpackage)
   - 6.1 [How it works](#61-how-it-works)
   - 6.2 [Build the package](#62-build-the-package)
   - 6.3 [Inspect the package](#63-inspect-the-package)
   - 6.4 [Install and remove](#64-install-and-remove)
   - 6.5 [`debian/` directory reference](#65-debian-directory-reference)
   - 6.6 [Maintainer scripts](#66-maintainer-scripts)
   - 6.7 [Conffile handling](#67-conffile-handling)
   - 6.8 [Building a source package](#68-building-a-source-package)
7. [Choosing a packaging method](#7-choosing-a-packaging-method)
8. [Versioning and release checklist](#8-versioning-and-release-checklist)

---

## 1. Repository layout

```
zopen/
├── zopen.py                  # Application source (single Python module)
├── pyproject.toml           # Python packaging metadata (PEP 517/518/621)
├── CMakeLists.txt           # Top-level CMake configuration
├── cmake/
│   └── packaging.cmake      # CPack configuration (included by CMakeLists.txt)
├── config/
│   └── default.toml         # System-wide config installed to /opt/etc/zopen/
├── debian/
│   ├── changelog            # dpkg version history (required)
│   ├── control              # Package metadata and dependencies
│   ├── copyright            # Machine-readable licence statement
│   ├── rules                # Build recipe (Makefile driven by dh)
│   ├── source/
│   │   └── format           # Source package format declaration
│   ├── zopen.docs            # List of documentation files for dh_installdocs
│   ├── postinst             # Post-install maintainer script
│   └── postrm               # Post-remove maintainer script
├── docs/
│   ├── user-guide.md
│   ├── design.md
│   └── build.md             # This file
└── README.md
```

---

## 2. Prerequisites

### All build paths

| Tool | Minimum version | Purpose |
|---|---|---|
| Python | 3.11 | `tomllib` stdlib; running the app |
| pip | 22.0 | Python package installation |

### Python wheel builds

| Tool | Install | Purpose |
|---|---|---|
| `python-build` | `pip install build` or `apt install python3-build` | `python -m build` |
| `setuptools` | `pip install setuptools>=68` or `apt install python3-setuptools` | Build backend |

### CMake builds

| Tool | Minimum version | Install |
|---|---|---|
| CMake | 3.20 | `apt install cmake` / download from cmake.org |
| Make or Ninja | any | `apt install make` / `apt install ninja-build` |
| `python-build` | — | Required when `EDIT_BUILD_WHEEL=ON` (default) |

### Debian native packaging

| Tool | Install | Purpose |
|---|---|---|
| `debhelper` | `apt install debhelper` (≥ 13) | `dh` helper framework |
| `dh-python` | `apt install dh-python` | Python integration for `dh` |
| `python3-all` | `apt install python3-all` | All installed Python 3 interpreters |
| `python3-setuptools` | `apt install python3-setuptools` | Build backend |
| `fakeroot` | `apt install fakeroot` | Build as non-root |
| `dpkg-dev` | included in `dpkg` | `dpkg-buildpackage`, `dpkg-deb` |

Install everything at once on Debian/Ubuntu:

```bash
sudo apt-get install cmake debhelper dh-python python3-all \
     python3-setuptools python3-build fakeroot
```

### Optional runtime dependency (all methods)

```bash
sudo apt-get install python3-magic    # Debian/Ubuntu
pip install python-magic              # PyPI
```

---

## 3. Python packaging (pip / wheel)

### 3.1 Building a wheel

A wheel is a pre-built distribution archive (`.whl`). It contains the Python
module and entry-point metadata, ready for pip to install.

```bash
# Install the build frontend
pip install build

# Build a wheel (output goes to dist/)
python -m build --wheel

# Build both a wheel and a source distribution
python -m build
```

Output files:
```
dist/
├── zopen-0.5.0-py3-none-any.whl      # wheel
└── zopen-0.5.0.tar.gz                # source distribution
```

The wheel filename encodes:
- `zopen` — package name
- `0.5.0` — version
- `py3` — Python 3 compatible
- `none` — not ABI-specific (pure Python)
- `any` — not platform-specific

### 3.2 Installing with pip

```bash
# Install from the wheel file
pip install dist/zopen-0.5.0-py3-none-any.whl

# Install with the optional libmagic binding
pip install "dist/zopen-0.5.0-py3-none-any.whl[magic]"

# Install directly from source (builds wheel on the fly)
pip install .
pip install ".[magic]"

# Install for the current user only (no root needed)
pip install --user .

# Install into a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install .
```

After installation, the `zopen` command is available in the active
environment's `bin/` directory.

### 3.3 Editable / developer install

An editable install creates a link back to the source file so changes take
effect immediately without reinstalling:

```bash
pip install -e .
```

### 3.4 `pyproject.toml` reference

```toml
[build-system]
requires      = ["setuptools>=68"]   # minimum version for pyproject.toml support
build-backend = "setuptools.build_meta"

[project]
name            = "zopen"
version         = "0.1.0"
description     = "Smart file editor launcher …"
readme          = "README.md"        # shown on PyPI
requires-python = ">=3.11"           # tomllib requires 3.11
license         = "MIT"              # SPDX expression
keywords        = ["editor", "mime", "launcher", "cli"]
dependencies    = []                 # no mandatory runtime deps

[project.optional-dependencies]
magic = ["python-magic"]             # install with pip install ".[magic]"

[project.scripts]
zopen = "zopen:main"                 # creates bin/zopen → calls zopen.main()

[tool.setuptools]
py-modules = ["edit"]                # only package the zopen.py module
```

Key points:

- `py-modules = ["edit"]` tells setuptools to install only `zopen.py`, not any
  other `.py` files it might find in the directory.
- `[project.scripts]` defines the console entry point. pip generates a
  thin wrapper script at install time that calls `zopen.main()`.
- `dependencies = []` — there are no mandatory runtime dependencies.
  `python-magic` is listed under `[project.optional-dependencies]`.

---

## 4. CMake build system

### 4.1 Concepts

CMake manages the build in three separate phases:

| Phase | Command | What happens |
|---|---|---|
| Configure | `cmake -S . -B build` | Detects Python, evaluates options, writes Makefiles |
| Build | `cmake --build build` | Runs the `wheel` custom target |
| Install | `cmake --install build` | Copies files to the prefix |

CMake also drives CPack (§5) and is used internally by `dpkg-buildpackage`
via the `pybuild` build system (§6).

### 4.2 Configure step

```bash
# Minimal — installs to /usr/local by default
cmake -S . -B build

# System install (Debian convention: binary under /usr, config under /etc)
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr

# Custom prefix (e.g. /opt/zopen)
cmake -S . -B build \
      -DCMAKE_INSTALL_PREFIX=/opt/zopen \
      -DZEDIT_SYSCONFDIR=/opt/zopen/etc

# Skip building the wheel (faster if you only need cmake --install)
cmake -S . -B build -DEDIT_BUILD_WHEEL=OFF

# Use pip instead of direct file copy for the install step
cmake -S . -B build -DEDIT_INSTALL_VIA_PIP=ON

# Use Ninja instead of Make
cmake -S . -B build -G Ninja
```

### 4.3 CMake options reference

All options are set with `-D<OPTION>=<VALUE>` on the configure command line.

| Option | Type | Default | Description |
|---|---|---|---|
| `CMAKE_INSTALL_PREFIX` | PATH | `/usr/local` | Root of the installation tree. Use `/usr` for system packages. |
| `EDIT_BUILD_WHEEL` | BOOL | `ON` | Build a Python wheel as part of the `all` target. Requires `python -m build`. |
| `EDIT_INSTALL_VIA_PIP` | BOOL | `OFF` | Install via `pip install --prefix` instead of copying the script directly. Creates `.dist-info` metadata. |
| `ZOPEN_SYSCONFDIR` | PATH | `/etc` when prefix is `/usr`; `${prefix}/etc` otherwise | Directory that receives `zopen/config.toml`. Override to place the config outside the prefix. |
| `CMAKE_INSTALL_LIBDIR` | STRING | `lib` | Set automatically to the multiarch path by `dh`. Pre-set here to suppress a GNUInstallDirs warning on `LANGUAGES NONE` projects. |

### 4.4 CMake install-directory variables

These variables are set by `include(GNUInstallDirs)` and control where each
component is installed. They are relative to `CMAKE_INSTALL_PREFIX` unless
they start with `/`.

| Variable | Resolved path (prefix `/usr`) | Description |
|---|---|---|
| `CMAKE_INSTALL_BINDIR` | `/usr/bin` | Executables |
| `CMAKE_INSTALL_SYSCONFDIR` | `/etc` (set by GNUInstallDirs when prefix = `/usr`) | System config; overridden by `ZOPEN_SYSCONFDIR` |
| `CMAKE_INSTALL_DOCDIR` | `/usr/share/doc/zopen` | Package documentation |
| `CMAKE_INSTALL_DATADIR` | `/usr/share` | Read-only architecture-independent data |

### 4.5 Build step

```bash
cmake --build build                      # build all targets (wheel by default)
cmake --build build --target wheel       # build only the wheel
cmake --build build --target deb         # build wheel then generate .deb
cmake --build build --target tarball     # build wheel then generate .tar.gz
cmake --build build --target clean       # remove files produced by build targets
cmake --build build --target distclean   # remove build dir + Python caches/archives
cmake --build build -j4                  # parallel build (4 jobs)
cmake --build build --verbose            # print full commands
```

The `wheel` target runs:

```bash
python3 -m build --wheel --no-isolation --outdir <build-dir>/dist
```

It is driven by a `add_custom_command` with these declared dependencies:

- `zopen.py`
- `pyproject.toml`

CMake only rebuilds the wheel when one of these files changes (checked by
timestamp).

### 4.6 Install step

```bash
# Install to the configured prefix
cmake --install build

# Install to a different prefix (overrides configure-time default)
cmake --install build --prefix /usr/local

# Staged install (useful for packaging — files go under DESTDIR)
DESTDIR=/tmp/staging cmake --install build --prefix /usr

# Install only specific components
cmake --install build --component Runtime
cmake --install build --component Config
cmake --install build --component Doc
```

**DESTDIR behaviour:** the install destination is
`${DESTDIR}${CMAKE_INSTALL_PREFIX}/<relative-path>`. For example, with
`DESTDIR=/tmp/staging` and prefix `/usr`, the binary lands at
`/tmp/staging/opt/zopen/bin/zopen`. The `ZOPEN_SYSCONFDIR` path (e.g. `/etc`) is
always absolute, so config ends up at `/tmp/staging/opt/etc/zopen/config.toml`.

### 4.7 Installed file layout

With `CMAKE_INSTALL_PREFIX=/usr`:

```
/opt/zopen/bin/zopen                    ← zopen.py (renamed, chmod +x)
/opt/etc/zopen/config.toml            ← config/default.toml (renamed)
/opt/zopen/share/doc/zopen/README.md    ← README.md
```

With `CMAKE_INSTALL_PREFIX=/usr/local`:

```
/usr/local/bin/zopen
/usr/local/opt/etc/zopen/config.toml
/opt/zopen/share/doc/zopen/README.md
```

### 4.8 CMake targets reference

| Target | Type | Description |
|---|---|---|
| `wheel` | Custom (ALL) | Build Python wheel via `python -m build`. |
| `deb` | Custom | Run CPack with the DEB generator. |
| `tarball` | Custom | Run CPack with the TGZ generator. |
| `package` | CPack built-in | Run CPack with all configured generators (DEB + TGZ). |
| `install` | CMake built-in | Install all components to the prefix. |
| `clean` | CMake built-in | Remove files produced by build targets (wheel, packages, etc.). |
| `distclean` | Custom | Remove the build directory **and** source-tree artifacts (`__pycache__`, `*.egg-info`, loose `zopen-*.tar.gz`/`.deb` archives). Restores the source tree to a fresh-clone state. See `cmake/distclean.cmake`. |

---

## 5. CPack packaging

CPack is CMake's packaging tool. It uses the same `install()` rules to
determine the package contents, then wraps them with the generator's
metadata format.

Configuration lives in `cmake/packaging.cmake`, which is `include()`d at the
end of `CMakeLists.txt`.

### 5.1 Generating a `.deb` with CPack

```bash
# Configure with /usr prefix (required for correct /etc placement)
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr

# Build the wheel first (default), then generate the .deb
cmake --build build --target deb

# Or invoke cpack directly from the build directory
cd build
cpack -G DEB

# Specify a custom output directory
cpack -G DEB --config CPackConfig.cmake -B /tmp/packages
```

Output: `build/zopen-0.5.0-Linux.deb`

The CPack DEB generator creates the package by:

1. Running `cmake --install` into a staging directory.
2. Adding the `DEBIAN/control` file from the CPack variables.
3. Adding `DEBIAN/postinst` and `DEBIAN/postrm` from
   `CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA`.
4. Running `dpkg-deb --build`.

The resulting package differs from the `dpkg-buildpackage` package (§6)
in a few ways:

| Feature | CPack DEB | `dpkg-buildpackage` |
|---|---|---|
| Python `.dist-info` metadata | No | Yes (via pybuild) |
| Automatic `python3:any` dependency | No | Yes (via `dh_python3`) |
| `changelog.Debian.gz` in doc dir | No | Yes |
| `conffiles` registration | No (not automatic) | Yes (automatic for `/etc/`) |
| Suitable for Debian upload | No | Yes |

Use CPack DEB for quick self-contained packages. Use `dpkg-buildpackage` for
packages intended for Debian/Ubuntu repositories.

### 5.2 Generating a `.tar.gz` with CPack

```bash
cmake --build build --target tarball
# or
cd build && cpack -G TGZ
```

Output: `build/zopen-0.5.0-Linux.tar.gz`

The tarball contains a pre-staged tree rooted at `.` mirroring what
`cmake --install` would place at the prefix. Unpack with:

```bash
tar -xzf zopen-0.5.0-Linux.tar.gz -C /usr/local --strip-components=1
```

### 5.3 Generating an `.rpm` with CPack

RPM generation is configured in `cmake/packaging.cmake` but requires
`rpmbuild` to be installed:

```bash
sudo apt-get install rpm   # Debian/Ubuntu
# or
sudo dnf install rpm-build # Fedora/RHEL
```

```bash
cd build && cpack -G RPM
```

Output: `build/zopen-0.5.0-Linux.rpm`

### 5.4 CPack variables reference

All variables are set in `cmake/packaging.cmake`.

#### Common variables

| Variable | Value | Description |
|---|---|---|
| `CPACK_PACKAGE_NAME` | `zopen` | Package name |
| `CPACK_PACKAGE_VERSION` | `0.5.0` | Taken from `project(VERSION ...)` |
| `CPACK_PACKAGE_CONTACT` | `Maintainer <...>` | Maintainer string |
| `CPACK_PACKAGE_VENDOR` | `Example Project` | Vendor name |
| `CPACK_PACKAGING_INSTALL_PREFIX` | `/usr` | Prefix used inside the package |
| `CPACK_GENERATOR` | `DEB;TGZ` | Default generators |
| `CPACK_COMPONENTS_ALL` | `Runtime Config Doc` | Components included in packages |

#### DEB-specific variables

| Variable | Value | Description |
|---|---|---|
| `CPACK_DEBIAN_PACKAGE_ARCHITECTURE` | `all` | `all` = architecture-independent |
| `CPACK_DEBIAN_PACKAGE_DEPENDS` | `python3 (>= 3.11)` | Mandatory runtime deps |
| `CPACK_DEBIAN_PACKAGE_RECOMMENDS` | `python3-magic` | Strongly recommended |
| `CPACK_DEBIAN_PACKAGE_SUGGESTS` | `vim \| nano \| …` | Optional suggestions |
| `CPACK_DEBIAN_PACKAGE_SECTION` | `utils` | Debian archive section |
| `CPACK_DEBIAN_PACKAGE_SHLIBDEPS` | `OFF` | Disable shared-library scanner |
| `CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA` | `debian/postinst debian/postrm` | Extra maintainer scripts |

#### RPM-specific variables

| Variable | Value | Description |
|---|---|---|
| `CPACK_RPM_PACKAGE_ARCHITECTURE` | `noarch` | Architecture-independent |
| `CPACK_RPM_PACKAGE_LICENSE` | `MIT` | SPDX licence identifier |
| `CPACK_RPM_PACKAGE_REQUIRES` | `python3 >= 3.11` | Mandatory runtime deps |
| `CPACK_RPM_PACKAGE_GROUP` | `Applications/Editors` | RPM group classification |

---

## 6. Debian native packaging (`dpkg-buildpackage`)

This is the correct method for producing packages intended for a Debian or
Ubuntu repository. It produces a proper `.deb` with full Python integration
(entry-point scripts, `.dist-info`, `python3:any` dependency).

### 6.1 How it works

`dpkg-buildpackage` reads `debian/rules` and calls `dh` (debhelper). The
`dh` command sequences through a series of helper commands:

```
dh_auto_configure  → cmake (via pybuild --buildsystem=cmake)
dh_auto_build      → cmake --build (builds the wheel)
dh_auto_test       → skipped (override_dh_auto_test)
dh_auto_install    → cmake --install DESTDIR=debian/zopen/
                     + install config/default.toml (override)
dh_python3         → rewrites shebang, computes python3:any dep
dh_installdocs     → installs README.md and copyright
dh_installchangelogs → compresses and installs changelog
dh_compress        → compresses man pages, changelogs
dh_fixperms        → sets standard file permissions
dh_installdeb      → installs DEBIAN/control, conffiles, postinst, postrm
dh_gencontrol      → generates final DEBIAN/control with substitution vars
dh_builddeb        → calls dpkg-deb --build
```

`pybuild --buildsystem=cmake` runs CMake in a private build directory
(`.pybuild/cpython3_3.12_edit/build/`) and passes Debian-standard variables:

```
-DCMAKE_INSTALL_PREFIX=/usr
-DCMAKE_INSTALL_SYSCONFDIR=/etc
-DCMAKE_INSTALL_LOCALSTATEDIR=/var
-DCMAKE_INSTALL_LIBDIR=lib/x86_64-linux-gnu
```

This is why the CMake `ZOPEN_SYSCONFDIR` logic (§4.3) correctly resolves
to `/etc` during the Debian build even though the source tree's own
`build/` directory was configured with a different prefix.

### 6.2 Build the package

```bash
# Binary-only package, no GPG signing (typical for local builds)
dpkg-buildpackage -us -uc -b

# Source + binary, no signing
dpkg-buildpackage -us -uc

# Binary only, sign with your GPG key
dpkg-buildpackage -b

# Equivalent with debuild
debuild -us -uc -b

# Parallel build
dpkg-buildpackage -us -uc -b -j4

# Skip tests
DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -us -uc -b
```

The output files are placed in the **parent directory** of the source tree:

```
../zedit_0.5.0-1_all.deb          # binary package
../edit_0.1.0-1_amd64.buildinfo  # build metadata
../edit_0.1.0-1_amd64.changes    # upload description
```

### 6.3 Inspect the package

```bash
# Package metadata
dpkg-deb --info ../zedit_0.5.0-1_all.deb

# File list
dpkg-deb --contents ../zedit_0.5.0-1_all.deb

# Extract everything to a directory
dpkg-deb -x ../zedit_0.5.0-1_all.deb /tmp/zopen-extracted

# Inspect the control scripts
dpkg-deb -e ../zedit_0.5.0-1_all.deb /tmp/zopen-control
ls /tmp/zopen-control/

# Verify the conffiles list
cat /tmp/zopen-control/conffiles
```

### 6.4 Install and remove

```bash
# Install (also satisfies dependencies from apt)
sudo dpkg -i ../zedit_0.5.0-1_all.deb
sudo apt-get install -f    # fix any unsatisfied deps

# Or with apt (if you have a local repo set up)
sudo apt-get install zopen

# Remove (keeps conffiles)
sudo apt-get remove zopen

# Remove and purge all conffiles (including /opt/etc/zopen/config.toml)
sudo apt-get purge zopen

# Check installed files
dpkg -L zopen

# Check package status
dpkg -s zopen
```

### 6.5 `debian/` directory reference

#### `debian/changelog`

Required by `dpkg`. Must follow exact format. Parse with:

```bash
dpkg-parsechangelog
```

Format:

```
<source-name> (<version>-<debian-revision>) <distribution>; urgency=<level>

  * Change entry.

 -- Maintainer Name <email>  Day, DD Mon YYYY HH:MM:SS +ZZZZ
```

When releasing a new version, prepend a new entry with `dch` or edit manually.

#### `debian/control`

Defines the **source package** (build metadata) and one or more **binary
packages** (what gets installed).

| Field | Stanza | Description |
|---|---|---|
| `Source` | Source | Source package name |
| `Section` | Source | Debian archive section (`utils`, `python`, …) |
| `Priority` | Source | `optional` for most packages |
| `Maintainer` | Source | `Name <email>` |
| `Build-Depends` | Source | Packages needed at build time |
| `Standards-Version` | Source | Debian Policy version this package conforms to |
| `Rules-Requires-Root` | Source | `no` = can build without root (uses fakeroot) |
| `Package` | Binary | Binary package name |
| `Architecture` | Binary | `all` for pure Python packages |
| `Depends` | Binary | Runtime dependencies. `${python3:Depends}` is filled in by `dh_python3`. `${misc:Depends}` by debhelper. |
| `Recommends` | Binary | Installed by default unless `--no-install-recommends` |
| `Suggests` | Binary | Presented to user but not installed automatically |

#### `debian/rules`

A Makefile processed by `dpkg-buildpackage`. The single `%:` rule delegates
everything to `dh`:

```makefile
export PYBUILD_NAME = zopen    # tells pybuild which Python package this is

%:
    dh $@ --with python3 --buildsystem=pybuild
```

`override_dh_auto_install` is used to install the config file in addition to
what pybuild's cmake install does:

```makefile
override_dh_auto_install:
    dh_auto_install
    install -Dm 0644 config/default.toml \
        debian/edit/opt/etc/zopen/config.toml
```

`override_dh_auto_test` suppresses test failures (since no test suite exists):

```makefile
override_dh_auto_test:
    $(MAKE) -C . test 2>/dev/null || true
```

**Important:** `debian/rules` uses **real tabs** for indentation (Makefile
requirement). Spaces will cause `missing separator` errors.

#### `debian/copyright`

Machine-readable DEP-5 format. Must list every licence in the package.
Checked by `lintian`.

#### `debian/source/format`

`3.0 (quilt)` — the standard modern source format. Allows patches to be
managed with `quilt`.

#### `debian/zopen.docs`

One filename per line; `dh_installdocs` copies these to
`/opt/zopen/share/doc/zopen/`. Currently contains `README.md`.

#### `debian/postinst` / `debian/postrm`

See §6.6 below.

### 6.6 Maintainer scripts

Two maintainer scripts are shipped:

**`debian/postinst`** — runs after the package is installed or upgraded.
The `configure` action ensures `/opt/etc/zopen` exists:

```sh
case "$1" in
    configure)
        if [ ! -d /opt/etc/zopen ]; then mkdir -p /opt/etc/zopen; fi
        ;;
esac
```

The `#DEBHELPER#` token is replaced by debhelper-generated code (e.g., from
`dh_installdebconf`).

**`debian/postrm`** — runs after the package is removed. The `purge`
action removes the config directory:

```sh
case "$1" in
    purge)
        if [ -d /opt/etc/zopen ]; then rm -rf /opt/etc/zopen; fi
        ;;
esac
```

Maintainer script actions are called with these arguments:

| Script | Argument | When |
|---|---|---|
| `postinst` | `configure <old-version>` | After fresh install or upgrade |
| `postrm` | `remove` | After `apt remove` |
| `postrm` | `purge` | After `apt purge` |

> **These scripts are also used by CPack DEB** via
> `CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA`.

### 6.7 Conffile handling

`/opt/etc/zopen/config.toml` is installed by both the cmake install rule and the
`override_dh_auto_install` rule. `dh_installdebconf` / `dh_installdeb`
automatically adds any file under `debian/zopen/etc/` to `DEBIAN/conffiles`:

```
/opt/etc/zopen/config.toml
```

This tells `dpkg` that:
- The file is a configuration file managed by the package.
- If the sysadmin has modified it and a new package version ships a different
  default, `dpkg` will prompt: *"keep the local version or install the package
  maintainer's version?"*
- `apt remove` keeps the file; only `apt purge` removes it.

### 6.8 Building a source package

A source package is required to upload to a Debian or Ubuntu archive.

```bash
# Full source + binary build with signing
dpkg-buildpackage

# Source only (produces .dsc + .debian.tar.xz + .orig.tar.xz)
dpkg-buildpackage -S

# Create the orig tarball first (if not already present)
git archive HEAD --prefix=zopen-0.5.0/ | gzip > ../edit_0.1.0.orig.tar.gz

# Use debuild for a more complete workflow
debuild -S -sa    # -sa = include orig tarball even if unchanged
```

---

## 7. Choosing a packaging method

| Scenario | Recommended method |
|---|---|
| Quick developer install on any platform | `pip install .` |
| Install with full Python metadata (`.dist-info`) | `pip install .` or `cmake -DEDIT_INSTALL_VIA_PIP=ON` |
| System install without a package manager | `cmake --install` with `--prefix /usr/local` |
| Local `.deb` for distribution to Debian/Ubuntu systems | `dpkg-buildpackage -us -uc -b` |
| `.deb` for upload to a Debian/Ubuntu repository | `dpkg-buildpackage` (with GPG signing) |
| Cross-platform tarball | `cmake --build build --target tarball` (CPack TGZ) |
| RPM for Fedora/RHEL/SUSE | `cmake --build build` + `cpack -G RPM` |
| CI: build artefact for testing | `python -m build --wheel` |

---

## 8. Versioning and release checklist

The version number appears in these files and must be updated consistently:

| File | Field | Current value |
|---|---|---|
| `pyproject.toml` | `[project] version` | `0.6.5` |
| `CMakeLists.txt` | `project(zopen VERSION ...)` | `0.6.5` |
| `debian/changelog` | First entry version | `0.6.5-1` |

The `debian/changelog` version has a **Debian revision** suffix (`-1`). It is
incremented independently of the upstream version for packaging-only changes.

### Release steps

1. **Update the version** in all three files above.

2. **Add a `debian/changelog` entry** (use `dch` or edit manually):
   ```bash
   dch -v 0.2.0-1 "New upstream release."
   ```

3. **Tag the release** in version control:
   ```bash
   git tag -s v0.2.0 -m "Release 0.2.0"
   ```

4. **Build and test all artefacts**:
   ```bash
   # Clean slate — use the distclean target if a build dir already exists,
   # or just remove it manually for a first-time build
   cmake --build build --target distclean   # or: rm -rf build

   # Python wheel
   python -m build --wheel
   pip install dist/zopen-0.2.0-py3-none-any.whl
   zopen --version   # confirm

   # CMake + CPack
   cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr
   cmake --build build
   cmake --build build --target deb
   dpkg-deb --info build/zopen-0.2.0-Linux.deb

   # dpkg-buildpackage
   dpkg-buildpackage -us -uc -b
   dpkg-deb --info ../edit_0.2.0-1_all.deb
   ```

5. **Run `lintian`** to check the Debian package for policy violations:
   ```bash
   lintian ../edit_0.2.0-1_all.deb
   lintian --pedantic ../edit_0.2.0-1_all.deb
   ```

6. **Upload** wheel to PyPI:
   ```bash
   twine upload dist/zopen-0.2.0-py3-none-any.whl
   ```

7. **Upload** `.dsc` to a Debian repository (if applicable):
   ```bash
   dput <repository> ../edit_0.2.0-1_amd64.changes
   ```
