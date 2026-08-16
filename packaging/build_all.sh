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

WINDOWS_DIR="$SCRIPT_DIR/windows"
INSTALLER_DIR="$WINDOWS_DIR/installer"
rm -rf "$INSTALLER_DIR"
mkdir -p "$INSTALLER_DIR"

# Copy all necessary files
cp "$ROOT_DIR/ko_compiler.py" "$INSTALLER_DIR/"
cp "$ROOT_DIR/Import.java" "$INSTALLER_DIR/" 2>/dev/null || true
cp "$ROOT_DIR/Import.class" "$INSTALLER_DIR/" 2>/dev/null || true
cp -r "$ROOT_DIR/test_compiler" "$INSTALLER_DIR/" 2>/dev/null || true
cp -r "$ROOT_DIR/ir.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp -r "$ROOT_DIR/optimizer.py" "$INSTALLER_DIR/" 2>/dev/null || true
cp -r "$ROOT_DIR/semantic_analyzer.py" "$INSTALLER_DIR/" 2>/dev/null || true

# Create Windows CLI batch file
cat > "$INSTALLER_DIR/ko.bat" << 'BATCH'
@echo off
setlocal enabledelayedexpansion
set "KO_HOME=%~dp0"
set "PATH=%KO_HOME%;%PATH%"

if "%~1"=="" (
    ko --help
    exit /b 1
)

if "%~1"=="--install" (
    if "%~2"=="" (
        echo Error: --install requires a module name >&2
        exit /b 1
    )
    echo Installing library: %~2 >&2
    python "%KO_HOME%ko_compiler.py" --install "%~2"
    exit /b %ERRORLEVEL%
)

if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help

if "%~1"=="--version" (
    echo ko compiler v2.800
    echo Copyright (c) 2026 ko-studio.ai.studio
    exit /b 0
)

python "%KO_HOME%ko_compiler.py" %*
exit /b %ERRORLEVEL%

:show_help
echo ko - .ko Language Compiler CLI
echo.
echo USAGE:
echo     ko [OPTIONS] ^<file.ko^>
echo     ko --install ^<module_name^>
echo.
echo OPTIONS:
echo     -h, --help      Show this help message
echo     --install       Install an external library
echo     --version       Show version information
echo.
echo EXAMPLES:
echo     ko program.ko                  Run a .ko program
echo     ko --install MyLibrary         Install an external library
echo.
echo For more information, visit: https://ko-studio.ai.studio
exit /b 0
BATCH

# Create installer Python script
cat > "$WINDOWS_DIR/create_installer.py" << 'PYEOF'
import zipfile
import os
import sys

def create_windows_installer():
    source_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    zip_file = output_file.replace('.exe', '.zip')
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.pyc') or file == 'create_installer.py':
                    continue
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, source_dir)
                zf.write(filepath, arcname)
    
    batch_stub = b'''@echo off
chcp 65001 >nul
setlocal
set "INSTALL_DIR=%USERPROFILE%\\.ko"
set "PATH=%INSTALL_DIR%;%PATH%"

echo ==========================================
echo   ko Compiler v2.800 Installer
echo ==========================================
echo.
echo This will install the .ko compiler to: %INSTALL_DIR%
echo.

set "EXTRACT_DIR=%TEMP%\\ko_install_%RANDOM%"
mkdir "%EXTRACT_DIR%" >nul 2>&1

echo Extracting files...
powershell -Command "Expand-Archive -Path '%~f0' -DestinationPath '%EXTRACT_DIR%' -Force" >nul 2>&1

echo Installing...
xcopy /E /I /Y "%EXTRACT_DIR%\\*" "%INSTALL_DIR%\\" >nul
rmdir /S /Q "%EXTRACT_DIR%" >nul 2>&1

echo.
echo Installation complete!
echo You can now use 'ko' from anywhere in the terminal.
echo.
echo To get started:
echo   ko --help
echo   ko program.ko
echo.
pause
exit /b 0
'''
    
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    with open(output_file, 'wb') as f:
        f.write(batch_stub + zip_content)
    
    os.remove(zip_file)
    print(f"Created: {output_file}")

if __name__ == '__main__':
    create_windows_installer()
PYEOF

python3 "$WINDOWS_DIR/create_installer.py" "$INSTALLER_DIR" "$WINDOWS_DIR/dist/ko-setup-v$VERSION.exe"
echo "  Windows installer: $WINDOWS_DIR/dist/ko-setup-v$VERSION.exe"

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
