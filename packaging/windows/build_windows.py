#!/usr/bin/env python3
"""Build Windows .exe installer for ko compiler v2.800 with auto-Java detection.

This script must be run on Windows with Python 3.8+ and PyInstaller installed.
It produces:
    dist/ko.exe                  - Standalone executable
    dist/ko-installer-2.800.exe  - Self-extracting installer with Java auto-detect
"""

import subprocess
import sys
import os
import shutil


def install_dependencies():
    """Install PyInstaller if not present."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_executable():
    """Build standalone ko.exe using PyInstaller."""
    print("[*] Building ko.exe with PyInstaller...")

    # Clean previous builds
    for d in ['build', 'dist']:
        if os.path.exists(d):
            shutil.rmtree(d)

    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ko_compiler.spec')
    spec_file = os.path.normpath(spec_file)

    if not os.path.exists(spec_file):
        print(f"[ERROR] Spec file not found: {spec_file}")
        sys.exit(1)

    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ])

    exe_path = os.path.join('dist', 'ko.exe')
    if not os.path.exists(exe_path):
        print("[ERROR] Build failed: ko.exe not found in dist/")
        sys.exit(1)

    print(f"[+] Built: {exe_path}")
    return exe_path


def create_installer():
    """Create self-extracting installer with Java auto-detection."""
    print("[*] Creating Windows installer...")

    source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'installer')
    dist_dir = 'dist'
    os.makedirs(dist_dir, exist_ok=True)

    exe_path = os.path.join(dist_dir, 'ko.exe')

    # Copy ko.exe to installer source directory
    installer_exe = os.path.join(source_dir, 'ko.exe')
    shutil.copy2(exe_path, installer_exe)

    # Create the self-extracting installer using the existing create_installer.py
    create_installer_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'create_installer.py'
    )

    output_installer = os.path.join(dist_dir, 'ko-installer-2.800.exe')

    subprocess.check_call([
        sys.executable, create_installer_script,
        source_dir,
        output_installer
    ])

    # Clean up the temporary ko.exe in installer dir
    if os.path.exists(installer_exe):
        os.remove(installer_exe)

    print(f"[+] Created installer: {output_installer}")


def main():
    print("=" * 50)
    print("  ko Compiler v2.800 - Windows Build")
    print("=" * 50)
    print()

    install_dependencies()
    build_executable()
    create_installer()

    print()
    print("=" * 50)
    print("  Build Complete!")
    print("=" * 50)
    print()
    print("Output files:")
    print(f"  dist/ko.exe                  - Standalone executable")
    print(f"  dist/ko-installer-2.800.exe  - Self-extracting installer")
    print()


if __name__ == '__main__':
    main()
