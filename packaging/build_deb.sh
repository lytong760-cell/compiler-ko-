#!/bin/bash
set -e

VERSION="2.800"
PACKAGE_NAME="ko-compiler_${VERSION}_all.deb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$SCRIPT_DIR/dist"

echo "=========================================="
echo "Building ${PACKAGE_NAME}..."
echo "=========================================="
echo ""

# Create dist directory
mkdir -p "$DIST_DIR"

# Create temporary build directory
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/ko/usr/local/bin"
mkdir -p "$TMPDIR/ko/usr/local/share/ko"
mkdir -p "$TMPDIR/ko/DEBIAN"

# Copy compiler files
echo "[1/4] Copying compiler files..."
cp "$ROOT_DIR/ko_compiler.py" "$TMPDIR/ko/usr/local/share/ko/"
cp "$ROOT_DIR/Import.java" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp "$ROOT_DIR/Import.class" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true
cp "$ROOT_DIR/ko_cli.py" "$TMPDIR/ko/usr/local/share/ko/" 2>/dev/null || true

# Copy supporting modules
for py_file in ir.py optimizer.py semantic_analyzer.py; do
    if [ -f "$ROOT_DIR/$py_file" ]; then
        cp "$ROOT_DIR/$py_file" "$TMPDIR/ko/usr/local/share/ko/"
    fi
done

# Copy test files
if [ -d "$ROOT_DIR/test_compiler" ]; then
    cp -r "$ROOT_DIR/test_compiler" "$TMPDIR/ko/usr/local/share/ko/"
fi

# Copy deb-specific files from packaging/deb
echo "[2/4] Copying package metadata..."
cp "$SCRIPT_DIR/deb/ko/DEBIAN/control" "$TMPDIR/ko/DEBIAN/"
cp "$SCRIPT_DIR/deb/ko/DEBIAN/postinst" "$TMPDIR/ko/DEBIAN/"
cp "$SCRIPT_DIR/deb/ko/usr/local/bin/ko" "$TMPDIR/ko/usr/local/bin/"

# Set permissions
echo "[3/4] Setting permissions..."
chmod 755 "$TMPDIR/ko"
chmod 755 "$TMPDIR/ko/DEBIAN"
chmod 644 "$TMPDIR/ko/DEBIAN/control"
chmod 755 "$TMPDIR/ko/DEBIAN/postinst"
chmod 755 "$TMPDIR/ko/usr/local/bin/ko"

# Clean pycache
find "$TMPDIR/ko" -name "*.pyc" -delete
find "$TMPDIR/ko" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Build the package
echo "[4/4] Building .deb package..."
dpkg-deb --build "$TMPDIR/ko" "$DIST_DIR/$PACKAGE_NAME"

echo ""
echo "=========================================="
echo "  Build Complete!"
echo "=========================================="
echo ""
echo "Package: $DIST_DIR/$PACKAGE_NAME"
echo ""
echo "Install with:"
echo "  sudo dpkg -i $DIST_DIR/$PACKAGE_NAME"
echo ""
echo "Or use apt:"
echo "  sudo apt install $DIST_DIR/$PACKAGE_NAME"
echo ""
