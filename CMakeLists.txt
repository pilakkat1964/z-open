cmake_minimum_required(VERSION 3.20)

project(zopen
    VERSION      0.6.3
    DESCRIPTION  "Smart file editor launcher"
    HOMEPAGE_URL "https://github.com/proteus-cpi/zopen"
    LANGUAGES    NONE        # Python only — no C/C++ compiler needed
)

# ── Standard install directories (bin, lib, share, etc, doc …) ───────────────
# GNUInstallDirs needs at least one known arch to set LIBDIR; since this is a
# Python-only project (LANGUAGES NONE) we supply a sensible default ourselves.
if(NOT DEFINED CMAKE_INSTALL_LIBDIR)
    set(CMAKE_INSTALL_LIBDIR "lib" CACHE STRING "Object code libraries (lib)")
endif()
include(GNUInstallDirs)

# Default prefix: self-contained /opt/<package> tree — no root required and
# keeps all package files out of system-managed directories.
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "/opt/${PROJECT_NAME}"
        CACHE PATH "Installation root (default: /opt/${PROJECT_NAME})" FORCE)
endif()

# ── Python interpreter ────────────────────────────────────────────────────────
find_package(Python3 REQUIRED COMPONENTS Interpreter)

message(STATUS "Python: ${Python3_EXECUTABLE} (${Python3_VERSION})")

# ── Options ───────────────────────────────────────────────────────────────────
option(ZOPEN_BUILD_WHEEL
    "Build a Python wheel during the 'all' target (requires python-build)"
    ON)

option(ZOPEN_INSTALL_VIA_PIP
    "Install the Python package via pip instead of copying the script directly"
    OFF)

# The 'zo' alias saves a keystroke.  It is installed inside the package bin dir
# (/opt/${PROJECT_NAME}/bin) to avoid conflicts with other tools.
# Run  `zopen --install-alias`  to create the symlink interactively.
# Set ZOPEN_INSTALL_ZO_ALIAS=OFF to suppress the automatic CMake install step.
option(ZOPEN_INSTALL_ZO_ALIAS
    "Install a 'zo' symlink pointing at the 'zopen' binary (into CMAKE_INSTALL_BINDIR)"
    ON)

# Configuration directory: /opt/etc per FHS §8 for /opt packages.
# Override with -DZOPEN_SYSCONFDIR=... if a different location is preferred.
set(ZOPEN_SYSCONFDIR "/opt/etc"
    CACHE PATH
    "Parent directory for system-wide configuration files (e.g. /opt/etc or /usr/local/etc)")

# /opt/bin symlink: shared /opt executables directory — add /opt/bin to PATH
# once to reach all installed /opt packages.
option(ZOPEN_INSTALL_OPTBIN_SYMLINK
    "Install a symlink /opt/bin/zopen → <prefix>/bin/edit (staged into packages via DESTDIR)"
    ON)

# /usr/local/bin symlink: optional system-wide convenience entry point.
# Skipped gracefully if /usr/local/bin is not writable (e.g. non-root install).
option(ZOPEN_INSTALL_USRLOCAL_SYMLINK
    "Install a symlink /usr/local/bin/zopen → <prefix>/bin/edit (may require sudo)"
    ON)

# PATH helpers — append to ~/.bashrc only during real installs, not make package.
option(ZOPEN_UPDATE_PATH_OPTBIN
    "Add /opt/bin to PATH in ~/.bashrc if not already present"
    ON)

option(ZOPEN_UPDATE_PATH_LOCALBIN
    "Add ~/.local/bin to PATH in ~/.bashrc if not already present"
    ON)

# ── Wheel build target ────────────────────────────────────────────────────────
# Produces dist/edit-<version>-py3-none-any.whl
if(ZOPEN_BUILD_WHEEL)
    set(_WHEEL_STAMP "${CMAKE_BINARY_DIR}/dist/.stamp")

    add_custom_command(
        OUTPUT  "${_WHEEL_STAMP}"
        COMMAND "${Python3_EXECUTABLE}" -m build
                    --wheel
                    --no-isolation
                    --outdir "${CMAKE_BINARY_DIR}/dist"
        COMMAND "${CMAKE_COMMAND}" -E touch "${_WHEEL_STAMP}"
        DEPENDS
            "${CMAKE_SOURCE_DIR}/zopen.py"
            "${CMAKE_SOURCE_DIR}/pyproject.toml"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Building Python wheel for ${PROJECT_NAME} ${PROJECT_VERSION}"
        VERBATIM
    )

    add_custom_target(wheel ALL DEPENDS "${_WHEEL_STAMP}")
endif()

# ── Installation ──────────────────────────────────────────────────────────────
#
# Two mutually exclusive strategies:
#
#   ZOPEN_INSTALL_VIA_PIP=OFF  (default)
#     CMake copies the script and config directly.  This is the right choice
#     for distribution packages that handle Python paths themselves (e.g. dh).
#
#   ZOPEN_INSTALL_VIA_PIP=ON
#     CMake delegates to pip.  Useful for direct developer installs where you
#     want the full Python entry-points / .dist-info metadata.
#
if(ZOPEN_INSTALL_VIA_PIP)
    # pip-based install — drives pyproject.toml / setuptools
    install(CODE
        "execute_process(
            COMMAND \"${Python3_EXECUTABLE}\" -m pip install
                        --no-deps
                        --no-build-isolation
                        --prefix \"\${CMAKE_INSTALL_PREFIX}\"
                        \"${CMAKE_SOURCE_DIR}\"
            RESULT_VARIABLE _pip_rc
        )
        if(NOT _pip_rc EQUAL 0)
            message(FATAL_ERROR \"pip install failed (exit code \${_pip_rc})\")
        endif()"
        COMPONENT Runtime
    )
else()
    # Direct install — CMake owns the installed layout
    install(
        PROGRAMS    "${CMAKE_SOURCE_DIR}/zopen.py"
        DESTINATION "${CMAKE_INSTALL_BINDIR}"
        RENAME      zopen
        COMPONENT   Runtime
    )
endif()

# 'zo' symlink — points at the installed 'zopen' binary.
# The symlink goes into CMAKE_INSTALL_FULL_BINDIR (e.g. /opt/zopen/bin).
if(ZOPEN_INSTALL_ZO_ALIAS)
    install(CODE
        "set(_bindir \"\$ENV{DESTDIR}${CMAKE_INSTALL_FULL_BINDIR}\")
        set(_link \"\${_bindir}/zo\")
        file(MAKE_DIRECTORY \"\${_bindir}\")
        # Warn if a 'zo' already exists at this path and is not our symlink.
        if(EXISTS \"\${_link}\" OR IS_SYMLINK \"\${_link}\")
            execute_process(
                COMMAND \"${CMAKE_COMMAND}\" -E env readlink \"\${_link}\"
                OUTPUT_VARIABLE _target OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
            )
            if(NOT \"\${_target}\" STREQUAL \"zopen\")
                message(WARNING \"'zo' already exists at \${_link} (→ \${_target}); skipping alias.\")
                return()
            else()
                message(STATUS \"'zo' alias already in place: \${_link} → zopen\")
                return()
            endif()
        endif()
        execute_process(
            COMMAND \"${CMAKE_COMMAND}\" -E create_symlink zopen \"\${_link}\"
            RESULT_VARIABLE _rc
        )
        if(NOT _rc EQUAL 0)
            message(WARNING \"Could not create zo symlink in \${_bindir}\")
        else()
            message(STATUS \"Symlinking: \${_link} → zopen\")
        endif()"
        COMPONENT Runtime
    )
endif()

# /opt/bin/zopen symlink — staged into packages via DESTDIR, or created directly
# on the filesystem for local installs.  /opt/bin is the conventional shared
# executables directory for /opt packages (add it to PATH once for all of them).
if(ZOPEN_INSTALL_OPTBIN_SYMLINK)
    install(CODE
        "set(_dd \"\$ENV{DESTDIR}\")
        set(_dir \"\${_dd}/opt/bin\")
        set(_link \"\${_dir}/${PROJECT_NAME}\")
        set(_target \"${CMAKE_INSTALL_FULL_BINDIR}/${PROJECT_NAME}\")
        file(MAKE_DIRECTORY \"\${_dir}\")
        if(IS_SYMLINK \"\${_link}\")
            execute_process(
                COMMAND \"${CMAKE_COMMAND}\" -E env readlink \"\${_link}\"
                OUTPUT_VARIABLE _cur OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET
            )
            if(\"\${_cur}\" STREQUAL \"\${_target}\")
                message(STATUS \"Symlink already in place: \${_link} → \${_target}\")
            else()
                message(WARNING \"Skipping /opt/bin/${PROJECT_NAME}: symlink exists pointing elsewhere (→ \${_cur})\")
            endif()
        elseif(EXISTS \"\${_link}\")
            message(WARNING \"Skipping /opt/bin/${PROJECT_NAME}: a regular file already exists at that path\")
        else()
            execute_process(
                COMMAND \"${CMAKE_COMMAND}\" -E create_symlink \"\${_target}\" \"\${_link}\"
                RESULT_VARIABLE _rc
            )
            if(_rc EQUAL 0)
                message(STATUS \"Symlink: \${_link} → \${_target}\")
            else()
                message(WARNING \"Could not create /opt/bin/${PROJECT_NAME} symlink (check write access to /opt/bin)\")
            endif()
        endif()"
        COMPONENT Runtime
    )
endif()

# /usr/local/bin/edit symlink — optional system-wide entry point.  Staged into
# packages via DESTDIR; skips gracefully if not writable on a direct install.
if(ZOPEN_INSTALL_USRLOCAL_SYMLINK)
    install(CODE
        "set(_dd \"\$ENV{DESTDIR}\")
        set(_dir \"\${_dd}/usr/local/bin\")
        set(_link \"\${_dir}/${PROJECT_NAME}\")
        set(_target \"${CMAKE_INSTALL_FULL_BINDIR}/${PROJECT_NAME}\")
        file(MAKE_DIRECTORY \"\${_dir}\")
        if(IS_SYMLINK \"\${_link}\")
            execute_process(
                COMMAND \"${CMAKE_COMMAND}\" -E env readlink \"\${_link}\"
                OUTPUT_VARIABLE _cur OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET
            )
            if(\"\${_cur}\" STREQUAL \"\${_target}\")
                message(STATUS \"Symlink already in place: \${_link} → \${_target}\")
            else()
                message(WARNING \"Skipping /usr/local/bin/${PROJECT_NAME}: symlink exists pointing elsewhere (→ \${_cur})\")
            endif()
        elseif(EXISTS \"\${_link}\")
            message(WARNING \"Skipping /usr/local/bin/${PROJECT_NAME}: a regular file already exists at that path\")
        else()
            execute_process(
                COMMAND \"${CMAKE_COMMAND}\" -E create_symlink \"\${_target}\" \"\${_link}\"
                RESULT_VARIABLE _rc
            )
            if(_rc EQUAL 0)
                message(STATUS \"Symlink: \${_link} → \${_target}\")
            else()
                message(WARNING \"Could not create /usr/local/bin/${PROJECT_NAME} symlink (try with sudo, or set ZOPEN_INSTALL_USRLOCAL_SYMLINK=OFF)\")
            endif()
        endif()"
        COMPONENT Runtime
    )
endif()
install(
    FILES       "${CMAKE_SOURCE_DIR}/config/default.toml"
    DESTINATION "${ZOPEN_SYSCONFDIR}/zopen"
    RENAME      config.toml
    COMPONENT   Config
)

# Package documentation
install(
    FILES       "${CMAKE_SOURCE_DIR}/README.md"
    DESTINATION "${CMAKE_INSTALL_DOCDIR}"
    COMPONENT   Doc
)

install(
    DIRECTORY   "${CMAKE_SOURCE_DIR}/docs/"
    DESTINATION "${CMAKE_INSTALL_DOCDIR}/docs"
    COMPONENT   Doc
    FILES_MATCHING PATTERN "*.md"
)

# ~/.bashrc PATH helpers — only run during real (non-package) installs.
# DESTDIR is set by CPack during `make package`; we skip in that case so that
# packaging never modifies the build host's shell configuration.
if(ZOPEN_UPDATE_PATH_OPTBIN)
    install(CODE
        "if(\"\$ENV{DESTDIR}\" STREQUAL \"\")
            set(_bashrc \"\$ENV{HOME}/.bashrc\")
            if(EXISTS \"\${_bashrc}\")
                file(READ \"\${_bashrc}\" _content)
            else()
                set(_content \"\")
            endif()
            if(NOT _content MATCHES \"/opt/bin\")
                file(APPEND \"\${_bashrc}\"
                    \"\\n# Added by ${PROJECT_NAME} installer\\nexport PATH=/opt/bin:$PATH\\n\")
                message(STATUS \"Added /opt/bin to PATH in \${_bashrc}\")
                message(STATUS \"Run 'source ~/.bashrc' or open a new terminal to apply.\")
            else()
                message(STATUS \"/opt/bin already present in \${_bashrc} — skipping PATH update\")
            endif()
        endif()"
        COMPONENT Runtime
    )
endif()

if(ZOPEN_UPDATE_PATH_LOCALBIN)
    install(CODE
        "if(\"\$ENV{DESTDIR}\" STREQUAL \"\")
            set(_bashrc \"\$ENV{HOME}/.bashrc\")
            if(EXISTS \"\${_bashrc}\")
                file(READ \"\${_bashrc}\" _content)
            else()
                set(_content \"\")
            endif()
            if(NOT _content MATCHES \"\\.local/bin\")
                file(APPEND \"\${_bashrc}\"
                    \"\\n# Added by ${PROJECT_NAME} installer\\nexport PATH=$HOME/.local/bin:$PATH\\n\")
                message(STATUS \"Added ~/.local/bin to PATH in \${_bashrc}\")
                message(STATUS \"Run 'source ~/.bashrc' or open a new terminal to apply.\")
            else()
                message(STATUS \"~/.local/bin already present in \${_bashrc} — skipping PATH update\")
            endif()
        endif()"
        COMPONENT Runtime
    )
endif()

# ── Clean targets ────────────────────────────────────────────────────────────
#
# clean     (built-in)  Remove files produced by the build targets.
#                       cmake --build <build-dir> --target clean
#
# distclean (custom)    Remove the entire build directory AND Python-generated
#                       caches / egg-info / loose package archives from the
#                       source tree, restoring it to a fresh-clone state.
#                       cmake --build <build-dir> --target distclean
#
add_custom_target(distclean
    COMMAND "${CMAKE_COMMAND}"
            -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
            -DBUILD_DIR=${CMAKE_BINARY_DIR}
            -P "${CMAKE_SOURCE_DIR}/cmake/distclean.cmake"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    COMMENT "Removing build directory and generated files (distclean)"
    VERBATIM
)

# ── Packaging (CPack) ─────────────────────────────────────────────────────────
include(cmake/packaging.cmake)
