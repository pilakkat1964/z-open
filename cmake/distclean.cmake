# cmake/distclean.cmake
#
# Invoked by the 'distclean' build target.  Removes Python-generated artifacts
# from the source tree, then deletes the CMake build directory, restoring the
# tree to a state equivalent to a fresh 'git clone'.
#
# Design notes:
#   * Source-tree cleanup runs FIRST so that it succeeds even when the build
#     directory is the current working directory of the calling make process.
#   * The build directory is removed via a freshly-spawned cmake -E rm process
#     whose CWD is SOURCE_DIR.  This avoids the Linux restriction that prevents
#     deleting a directory while it is the CWD of any running process.
#   * The GLOB for archives is intentionally narrow (zopen-* prefix) to avoid
#     accidentally deleting unrelated files in the source root.
#
# Variables expected from the caller (set via -D on the cmake -P command line):
#   SOURCE_DIR  -- absolute path to the project source root
#   BUILD_DIR   -- absolute path to the CMake build directory

if(NOT DEFINED SOURCE_DIR OR NOT DEFINED BUILD_DIR)
    message(FATAL_ERROR "distclean.cmake requires SOURCE_DIR and BUILD_DIR")
endif()

# ── Python caches and generated directories in the source root ────────────────
# Only top-level directories are targeted here to avoid accidentally deleting
# nested directories that share a name (the GLOB_RECURSE version is unsafe).
foreach(_rel
    __pycache__
    zopen.egg-info
    edit.egg-info
    .eggs
    dist
)
    set(_path "${SOURCE_DIR}/${_rel}")
    if(EXISTS "${_path}" OR IS_SYMLINK "${_path}")
        message(STATUS "distclean: removing ${_path}")
        file(REMOVE_RECURSE "${_path}")
    endif()
endforeach()

# ── Loose package archives in the source root ─────────────────────────────────
# Narrow glob: only files whose name starts with "zopen-" and ends with
# .tar.gz or .deb, sitting directly in the source root (not recursive).
file(GLOB _archives
    "${SOURCE_DIR}/zopen-*.tar.gz"
    "${SOURCE_DIR}/zopen-*.deb"
)
foreach(_f ${_archives})
    if(NOT IS_DIRECTORY "${_f}")
        message(STATUS "distclean: removing ${_f}")
        file(REMOVE "${_f}")
    endif()
endforeach()

# ── Remove the build directory ────────────────────────────────────────────────
# Spawn a fresh cmake process from SOURCE_DIR so the build directory is not
# the CWD of the deleting process.  cmake -E rm is available since CMake 3.17.
if(EXISTS "${BUILD_DIR}")
    message(STATUS "distclean: removing ${BUILD_DIR}")
    execute_process(
        COMMAND "${CMAKE_COMMAND}" -E rm -rf "${BUILD_DIR}"
        WORKING_DIRECTORY "${SOURCE_DIR}"
        RESULT_VARIABLE _rc
    )
    if(NOT _rc EQUAL 0)
        message(WARNING
            "distclean: could not fully remove ${BUILD_DIR} (exit ${_rc}).\n"
            "You may need to remove it manually: rm -rf ${BUILD_DIR}")
    endif()
else()
    message(STATUS "distclean: ${BUILD_DIR} already absent")
endif()

message(STATUS "distclean: done")
