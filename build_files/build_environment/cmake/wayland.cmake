# SPDX-FileCopyrightText: 2022-2023 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

set(WAYLAND_PKG_ENV "PKG_CONFIG_PATH=${LIBDIR}/expat/lib/pkgconfig:${LIBDIR}/xml2/lib/pkgconfig:${LIBDIR}/ffi/lib/pkgconfig:$PKG_CONFIG_PATH")

set(WAYLAND_EXTRA_OPTIONS
  -Ddocumentation=false
  -Dtests=false
)

ExternalProject_Add(external_wayland
  URL file://${PACKAGE_DIR}/${WAYLAND_FILE}
  DOWNLOAD_DIR ${DOWNLOAD_DIR}
  URL_HASH ${WAYLAND_HASH_TYPE}=${WAYLAND_HASH}
  PREFIX ${BUILD_DIR}/wayland

  # Use `-E` so the `PKG_CONFIG_PATH` can be defined to link against our own LIBEXPAT/LIBXML2/FFI.
  CONFIGURE_COMMAND ${CONFIGURE_ENV} &&
    ${CMAKE_COMMAND} -E env ${WAYLAND_PKG_ENV}
    ${MESON} setup
      --prefix ${LIBDIR}/wayland
      # Splendor WP-0 fix (2026-08-08): pin libdir to `lib64`. The harvest below
      # and vulkan/weston/wayland_protocols all expect `wayland/lib64` (the
      # Rocky/RHEL default). On Ubuntu/Debian aarch64 meson otherwise defaults to
      # multiarch `lib/aarch64-linux-gnu`, so the `wayland/lib64` harvest fails.
      --libdir lib64
      ${MESON_BUILD_TYPE}
      ${WAYLAND_EXTRA_OPTIONS}
      .
      ../external_wayland

  BUILD_COMMAND ninja
  INSTALL_COMMAND ninja install
)

add_dependencies(
  external_wayland
  external_expat
  external_xml2
  external_ffi

  # Needed for `MESON`.
  external_python_site_packages
)

harvest(external_wayland wayland/bin wayland/bin "wayland-scanner")
harvest(external_wayland wayland/include wayland/include "*.h")
# Only needed for running the WESTON compositor.
harvest(external_wayland wayland/lib64 wayland/lib64 "*")
