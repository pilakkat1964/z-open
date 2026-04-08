# cmake/packaging.cmake
#
# CPack configuration for the 'edit' package.
# Generates distributable archives and OS packages via:
#
#   cmake --build <build-dir> --target package
#   cpack --config <build-dir>/CPackConfig.cmake -G DEB
#   cpack --config <build-dir>/CPackConfig.cmake -G TGZ
#
# Supported generators:
#   DEB  — Debian/Ubuntu .deb (requires dpkg-deb)
#   RPM  — Red Hat/Fedora/SUSE .rpm (requires rpmbuild)
#   TGZ  — Portable gzip tarball (all platforms)

# ── Common package metadata ───────────────────────────────────────────────────
set(CPACK_PACKAGE_NAME              "${PROJECT_NAME}")
set(CPACK_PACKAGE_VERSION           "${PROJECT_VERSION}")
set(CPACK_PACKAGE_VERSION_MAJOR     "${PROJECT_VERSION_MAJOR}")
set(CPACK_PACKAGE_VERSION_MINOR     "${PROJECT_VERSION_MINOR}")
set(CPACK_PACKAGE_VERSION_PATCH     "${PROJECT_VERSION_PATCH}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "${PROJECT_DESCRIPTION}")
set(CPACK_PACKAGE_DESCRIPTION_FILE "${CMAKE_SOURCE_DIR}/README.md")
set(CPACK_PACKAGE_HOMEPAGE_URL      "${PROJECT_HOMEPAGE_URL}")
set(CPACK_RESOURCE_FILE_README      "${CMAKE_SOURCE_DIR}/README.md")

# Maintainer / vendor
set(CPACK_PACKAGE_CONTACT           "Maintainer <maintainer@example.com>")
set(CPACK_PACKAGE_VENDOR            "Example Project")

# Install prefix used inside the package.  /opt/${PROJECT_NAME} follows FHS §8
# for add-on application packages.
set(CPACK_PACKAGING_INSTALL_PREFIX  "/opt/${PROJECT_NAME}")

# Required so CPack stages files via DESTDIR into a temp directory instead of
# writing to absolute paths on the live filesystem.  Files installed to paths
# outside CMAKE_INSTALL_PREFIX (e.g. /opt/etc and /opt/bin) are handled via
# install(CODE) blocks that prepend $ENV{DESTDIR} manually.
set(CPACK_SET_DESTDIR ON)

# Default generators — override on command line with -G if needed
set(CPACK_GENERATOR "DEB;TGZ")

# Only include the Runtime and Config components in packages
# (Doc is optional — packages may choose to skip it)
set(CPACK_COMPONENTS_ALL Runtime Config Doc)

# ── DEB-specific ──────────────────────────────────────────────────────────────
set(CPACK_DEBIAN_PACKAGE_NAME           "zedit")
set(CPACK_DEBIAN_PACKAGE_SECTION        "utils")
set(CPACK_DEBIAN_PACKAGE_PRIORITY       "optional")
set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE   "all")  # Python: architecture-independent

# Runtime dependencies
set(CPACK_DEBIAN_PACKAGE_DEPENDS
    "python3 (>= 3.11)")

# Recommended extras (improves MIME detection accuracy)
set(CPACK_DEBIAN_PACKAGE_RECOMMENDS
    "python3-magic")

# Suggested extras
set(CPACK_DEBIAN_PACKAGE_SUGGESTS
    "vim | nano | emacs | micro")

# Conflicts / replaces with the traditional edit → vi symlink provided by
# some distros (e.g. nvi, vim-tiny).  Adjust if not desired.
# set(CPACK_DEBIAN_PACKAGE_CONFLICTS "vim-tiny (<< 2:9)")

set(CPACK_DEBIAN_PACKAGE_DESCRIPTION
    "Smart file editor launcher\n"
    " Opens files in the appropriate editor based on their MIME type\n"
    " (detected via libmagic or the mimetypes stdlib) or file extension.\n"
    " The editor mapping is fully configurable through TOML files at the\n"
    " system, user, and project level.")

# Maintainer scripts: postinst ensures /opt/bin exists; postrm cleans up symlinks
set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA
    "${CMAKE_SOURCE_DIR}/debian/postinst"
    "${CMAKE_SOURCE_DIR}/debian/postrm")

# Disable the auto-depends scanner (Python entry points confuse it)
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS OFF)

# ── RPM-specific ──────────────────────────────────────────────────────────────
set(CPACK_RPM_PACKAGE_NAME          "zedit")
set(CPACK_RPM_PACKAGE_GROUP         "Applications/Editors")
set(CPACK_RPM_PACKAGE_LICENSE       "MIT")
set(CPACK_RPM_PACKAGE_REQUIRES      "python3 >= 3.11")
set(CPACK_RPM_PACKAGE_SUGGESTS      "python3-magic")
set(CPACK_RPM_PACKAGE_ARCHITECTURE  "noarch")
set(CPACK_RPM_PACKAGE_DESCRIPTION
    "Opens files in the appropriate editor based on their MIME type\n"
    "(detected via libmagic or the mimetypes stdlib) or file extension.\n"
    "The editor mapping is fully configurable through TOML files at the\n"
    "system, user, and project level.")

# ── TGZ-specific ──────────────────────────────────────────────────────────────
set(CPACK_ARCHIVE_COMPONENT_INSTALL OFF)  # single archive for all components

# ── Activate CPack ────────────────────────────────────────────────────────────
include(CPack)

# ── Convenience targets ───────────────────────────────────────────────────────
# cmake --build <build-dir> --target deb
# cmake --build <build-dir> --target tarball
add_custom_target(deb
    COMMAND "${CMAKE_CPACK_COMMAND}" --config CPackConfig.cmake -G DEB
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
    DEPENDS ${CMAKE_BINARY_DIR}/CPackConfig.cmake
    COMMENT "Generating .deb package"
    VERBATIM
)

add_custom_target(tarball
    COMMAND "${CMAKE_CPACK_COMMAND}" --config CPackConfig.cmake -G TGZ
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
    DEPENDS ${CMAKE_BINARY_DIR}/CPackConfig.cmake
    COMMENT "Generating .tar.gz archive"
    VERBATIM
)
