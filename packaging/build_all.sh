#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$SCRIPT_DIR/dist"
VERSION="2.800"

mkdir -p "$DIST_DIR"

echo "=========================================="
echo "Building ko-compiler v$VERSION packages"
echo "=========================================="

# ==========================================
# 1. Windows .exe installer
# ==========================================
echo ""
echo "[1/3] Building Windows installer..."
echo ""
echo "NOTE: Windows .exe must be built on Windows with Python 3.8+."
echo "      Run: python packaging/windows/build_windows.py"
echo ""

# Prepare Windows installer source files
WINDOWS_DIR="$SCRIPT_DIR/windows"
INSTALLER_DIR="$WINDOWS_DIR/installer"
rm -rf "$INSTALLER_DIR"
mkdir -p "$INSTALLER_DIR"

# Copy all necessary files for Windows build
cp "$ROOT_DIR/ko_compiler.py" "$INSTALLER_DIR/"
cp "$ROOT_DIR/Import.java" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/Import.class" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/ko_cli.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/ir.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/optimizer.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/semantic_analyzer.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/ko_compiler.spec" "$INSTALLER_DIR/" 2>/dev/null || true
if [ -d "$ROOT_DIR/test_compiler" ]; then
    cp -r "$ROOT_DIR/test_compiler" "$INSTALLER_DIR/"
fi

echo "  Windows source prepared at: $INSTALLER_DIR"
echo "  To build on Windows:"
echo "    cd packaging/windows"
echo "    python build_windows.py"
echo ""

# ==========================================
# 2. Debian .deb package
# ==========================================
echo ""
echo "[2/3] Building Debian package..."

TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/ko/usr/local/bin"
mkdir -p "$TMPDIR/ko/usr/local/share/ko"
mkdir -p "$TMPDIR/ko/DEBIAN"
chmod 755 "$TMPDIR/ko"
chmod 755 "$TMPDIR/ko/DEBIAN"

cp "$ROOT_DIR/ko_compiler.py" "$TMPDIR/ko/usr/local/share/ko/"
cp "$ROOT_DIR/Import.java" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp "$ROOT_DIR/Import.class" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/test_compiler" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/ir.py" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/optimizer.py" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/semantic_analyzer.py" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true

cat > "$TMPDIR/ko/usr/local/bin/ko" << 'WRAPPER'
#!/bin/bash
set -e
export KO_HOME="$(dirname "$(readlink -f "$0")")/../share/ko"
exec python3 "$KO_HOME/ko_compiler.py" "$@"
WRAPPER
chmod +x "$TMPDIR/ko/usr/local/bin/ko"

cat > "$TMPDIR/ko/DEBIAN/control" << 'CONTROL'
Package: ko-compiler
Version: 2.800
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), default-jre (>= 11)
Maintainer: ko-studio.ai.studio <support@ko-studio.ai.studio>
Description: .ko Language Compiler and Interpreter
 The .ko programming language compiler with support for external libraries
 from ko-studio.ai.studio.
CONTROL
chmod 644 "$TMPDIR/ko/DEBIAN/control"

cat > "$TMPDIR/ko/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e
mkdir -p "$HOME/.ko/modules"
if [ ! -f "$HOME/.ko/modules/Random.ko" ]; then
    echo '# Built-in Random module' > "$HOME/.ko/modules/Random.ko"
fi
if [ ! -f "$HOME/.ko/modules/Os.ko" ]; then
    echo '# Built-in OS module' > "$HOME/.ko/modules/Os.ko"
fi
if [ ! -f "$HOME/.ko/modules/Website.ko" ]; then
    echo '# Built-in Website module' > "$HOME/.ko/modules/Website.ko"
fi
chmod +x /usr/local/bin/ko
echo "ko compiler installed successfully!"
echo "Run 'ko --help' to get started."
POSTINST
chmod 755 "$TMPDIR/ko/DEBIAN/postinst"

cat > "$TMPDIR/ko/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
set -e
echo "ko compiler removed."
PRERM
chmod 755 "$TMPDIR/ko/DEBIAN/prerm"

dpkg-deb --build "$TMPDIR/ko" "$DIST_DIR/ko-compiler_${VERSION}_all.deb"
echo "  Debian package: $DIST_DIR/ko-compiler_${VERSION}_all.deb"
rm -rf "$TMPDIR"

# ==========================================
# 3. macOS .pkg installer
# ==========================================
echo ""
echo "[3/3] Building macOS package..."

MACOS_DIR="$SCRIPT_DIR/macos"
PKG_ROOT="$MACOS_DIR/pkg_root"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/usr/local/bin"
mkdir -p "$PKG_ROOT/usr/local/share/ko"

cp "$ROOT_DIR/ko_compiler.py" "$PKG_ROOT/usr/local/share/ko/"
cp "$ROOT_DIR/Import.java" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true
cp "$ROOT_DIR/Import.class" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/test_compiler" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/ir.py" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/optimizer.py" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true
cp -r "$ROOT_DIR/semantic_analyzer.py" "$PKG_ROOT/usr/local/share/ko/" 2>/dev/null || true

cat > "$PKG_ROOT/usr/local/bin/ko" << 'WRAPPER'
#!/bin/bash
set -e
export KO_HOME="$(dirname "$(readlink -f "$0")")/../share/ko"
exec python3 "$KO_HOME/ko_compiler.py" "$@"
WRAPPER
chmod +x "$PKG_ROOT/usr/local/bin/ko"

cat > "$MACOS_DIR/preinstall" << 'PREINSTALL'
#!/bin/bash
set -e
echo "=========================================="
echo "   ko Compiler v2.800 Installer"
echo "=========================================="
echo ""
echo "This will install the .ko compiler to: /usr/local"
echo ""
mkdir -p "$HOME/.ko/modules"
if [ ! -f "$HOME/.ko/modules/Random.ko" ]; then
    echo '# Built-in Random module' > "$HOME/.ko/modules/Random.ko"
fi
if [ ! -f "$HOME/.ko/modules/Os.ko" ]; then
    echo '# Built-in OS module' > "$HOME/.ko/modules/Os.ko"
fi
if [ ! -f "$HOME/.ko/modules/Website.ko" ]; then
    echo '# Built-in Website module' > "$HOME/.ko/modules/Website.ko"
fi
PREINSTALL

cat > "$MACOS_DIR/postinstall" << 'POSTINSTALL'
#!/bin/bash
set -e
chmod +x /usr/local/bin/ko
echo ""
echo "Installation complete!"
echo "You can now use 'ko' from anywhere in the terminal."
echo ""
echo "To get started:"
echo "  ko --help"
echo "  ko program.ko"
echo ""
POSTINSTALL

chmod +x "$MACOS_DIR/preinstall" "$MACOS_DIR/postinstall"

if command -v pkgbuild &> /dev/null; then
    pkgbuild --root "$PKG_ROOT" \
             --identifier "ai.studio.ko" \
             --version "$VERSION" \
             --install-location "/" \
             --preinstall "$MACOS_DIR/preinstall" \
             --postinstall "$MACOS_DIR/postinstall" \
             "$DIST_DIR/ko-compiler-${VERSION}.pkg"
    echo "  macOS package: $DIST_DIR/ko-compiler-${VERSION}.pkg"
else
    tar -czf "$DIST_DIR/ko-compiler-${VERSION}-macos.tar.gz" -C "$MACOS_DIR" pkg_root
    echo "  macOS archive: $DIST_DIR/ko-compiler-${VERSION}-macos.tar.gz"
    echo "  (pkgbuild not available on this system)"
fi

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Packages created in: $DIST_DIR"
ls -lh "$DIST_DIR"
