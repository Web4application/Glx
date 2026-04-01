#!/bin/bash
# Automated Wayland RPM builder with auto-update and checksum validation

set -euo pipefail

# --- Configuration ---
BUILD_DIR="$HOME/rpmbuild"
SPEC_FILE="wayland.spec"
RELEASE="alt1"
MESA_EPOCH="4"
EGL_VER="18.1.0"

# --- Ensure directories exist ---
mkdir -p "$BUILD_DIR"/{SOURCES,SPECS,BUILD,RPMS,SRPMS}

# --- Fetch latest Wayland version and source URL ---
echo "Checking latest Wayland release..."
LATEST_INFO=$(curl -s https://wayland.freedesktop.org/releases.html | grep -oP 'wayland-\K[0-9]+\.[0-9]+\.[0-9]+(?=\.tar\.xz)' | head -n1)
MAIN_VER="$LATEST_INFO"
SOURCE_URL="https://wayland.freedesktop.org/releases/wayland-$MAIN_VER.tar.xz"

# --- Download source if missing ---
cd "$BUILD_DIR/SOURCES"
if [ ! -f "wayland-$MAIN_VER.tar.xz" ]; then
    echo "Downloading Wayland $MAIN_VER..."
    curl -LO "$SOURCE_URL"
fi

# --- Validate checksum using SHA256 ---
CHECKSUM_URL="https://wayland.freedesktop.org/releases/sha256sums.txt"
SHA256_CHECKSUM=$(curl -s "$CHECKSUM_URL" | grep "wayland-$MAIN_VER.tar.xz" | awk '{print $1}')

echo "Validating checksum..."
DOWNLOADED_SHA=$(sha256sum "wayland-$MAIN_VER.tar.xz" | awk '{print $1}')
if [ "$DOWNLOADED_SHA" != "$SHA256_CHECKSUM" ]; then
    echo "ERROR: Checksum mismatch! Exiting."
    exit 1
else
    echo "Checksum OK ✅"
fi

# --- Generate spec file dynamically ---
cat > "$BUILD_DIR/SPECS/$SPEC_FILE" <<EOF
%define main_ver $MAIN_VER
%define egl_ver $EGL_VER
%define mesa_epoch $MESA_EPOCH
Name: wayland
Version: %main_ver
Release: $RELEASE
Summary: Wayland protocol libraries
Group: System/X11
License: MIT
Url: http://wayland.freedesktop.org/

Source: wayland-%{main_ver}.tar.xz

BuildRequires: doxygen libexpat-devel libffi-devel libxml2-devel xsltproc docbook-style-xsl

%description
Wayland protocol library and headers for client/server communication.

# Sub-packages
%package devel
Summary: Common headers for Wayland
Group: Development/C

%package -n libwayland-client
Summary: Wayland client library
Group: System/Libraries

%package -n libwayland-client-devel
Summary: Development files for Wayland client library
Group: Development/C
Requires: libwayland-client = %EVR

%package -n libwayland-server
Summary: Wayland server library
Group: System/Libraries

%package -n libwayland-server-devel
Summary: Development files for Wayland server library
Group: Development/C
Requires: libwayland-server = %EVR

%prep
%setup -q

%build
%add_optflags -D_FILE_OFFSET_BITS=64
%autoreconf
%configure --disable-static
%make_build

%install
%makeinstall_std

%check
%make check

%files devel
%{_includedir}/wayland*

%files -n libwayland-client
%{_libdir}/libwayland-client.so.*

%files -n libwayland-client-devel
%{_includedir}/wayland-client*.h
%{_libdir}/libwayland-client.so
%{_pkgconfigdir}/wayland-client.pc

%files -n libwayland-server
%{_libdir}/libwayland-server.so.*

%files -n libwayland-server-devel
%{_includedir}/wayland-server*.h
%{_libdir}/libwayland-server.so
%{_pkgconfigdir}/wayland-server.pc
EOF

# --- Build RPMs ---
cd "$BUILD_DIR"
echo "Building RPM packages..."
rpmbuild --define "_topdir $BUILD_DIR" -ba SPECS/$SPEC_FILE

echo "✅ All RPM packages built successfully in $BUILD_DIR/RPMS/"
