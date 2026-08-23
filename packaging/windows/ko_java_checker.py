#!/usr/bin/env python3
"""Check Java runtime and auto-install if missing.

This utility checks if Java 11+ is installed. If not, it offers to download
and install the Eclipse Adoptium Temurin JDK 17 silently.

Usage:
    python ko_java_checker.py
    python ko_java_checker.py --check-only
"""

import subprocess
import sys
import os
import tempfile
import urllib.request
import urllib.error
import re
import platform


JAVA_MIN_VERSION = 11
JAVA_DOWNLOAD_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.msi"
JAVA_INSTALLER_NAME = "OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.msi"


def check_java():
    """Check if Java 11+ is installed.

    Returns:
        tuple: (is_available, version_string)
    """
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version_line = result.stderr.split('\n')[0]
        match = re.search(r'version "([^"]+)"', version_line)
        if match:
            version_str = match.group(1)
            version_parts = version_str.split('.')
            major_version = int(version_parts[0])
            return major_version >= JAVA_MIN_VERSION, version_str
        return False, "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False, "not found"


def download_java(destination):
    """Download Java 17 installer to destination path.

    Args:
        destination: Path where the installer will be saved.

    Returns:
        bool: True if download succeeded, False otherwise.
    """
    print(f"[*] Downloading Java 17 from Adoptium...")
    print(f"    URL: {JAVA_DOWNLOAD_URL}")

    try:
        # Create request with headers
        req = urllib.request.Request(
            JAVA_DOWNLOAD_URL,
            headers={
                'User-Agent': 'ko-compiler/2.800',
                'Accept': 'application/octet-stream',
            }
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            total_size = 0
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    total_size += len(chunk)
                    if total_size % (5 * 1024 * 1024) == 0:
                        print(f"    Downloaded {total_size // (1024*1024)} MB...")

        print(f"[+] Download complete: {destination}")
        return True

    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to download Java: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Download error: {e}")
        return False


def install_java(installer_path):
    """Silently install Java from MSI installer.

    Args:
        installer_path: Path to the MSI installer.

    Returns:
        bool: True if installation succeeded, False otherwise.
    """
    print("[*] Installing Java Runtime Environment...")
    print("    This may take a few minutes...")

    try:
        # Silent install with Adoptium recommended options
        cmd = [
            "msiexec", "/i", installer_path,
            "/qn", "/norestart",
            "ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJavaHome,FeatureOracleJavaSoft",
            "INSTALLDIR=C:\\Program Files\\Eclipse Adoptium\\jdk-17"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=True
        )

        print("[+] Java installed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Java installation failed (exit code {e.returncode})")
        if e.stderr:
            print(f"    {e.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print("[ERROR] Java installation timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Installation error: {e}")
        return False


def update_path():
    """Add Java bin directory to system PATH if not already present."""
    java_bin = r"C:\Program Files\Eclipse Adoptium\jdk-17\bin"

    try:
        import winreg

        # Open system environment variables
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0, winreg.KEY_ALL_ACCESS
        ) as key:
            try:
                path_value, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                path_value = ""

            paths = [p.strip() for p in path_value.split(';') if p.strip()]
            if java_bin not in paths:
                paths.append(java_bin)
                new_path = ';'.join(paths)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"[+] Added Java to PATH: {java_bin}")
            else:
                print(f"[+] Java already in PATH")

        # Notify system of environment change
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Environment", SMTO_ABORTIFHUNG, 5000, None
        )

    except Exception as e:
        print(f"[!] Could not update PATH: {e}")
        print(f"    Please add manually: {java_bin}")


def main():
    check_only = "--check-only" in sys.argv

    print("=" * 50)
    print("  ko Compiler - Java Runtime Checker")
    print("=" * 50)
    print()

    has_java, version = check_java()

    if has_java:
        print(f"[+] Java {version} detected")
        if not check_only:
            print()
            print("The ko compiler can use Java for:")
            print("  - Module imports (Random, Os, Website)")
            print("  - External library installation")
        return 0

    print("[-] Java runtime not found or version too old")
    print(f"    This compiler requires Java {JAVA_MIN_VERSION} or higher.")
    print()

    if check_only:
        return 1

    if platform.system() != "Windows":
        print("[!] Auto-install is only supported on Windows.")
        print("    Please install Java manually from: https://adoptium.net/temurin/releases/")
        return 1

    response = input("Download and install Java 17 now? [Y/n]: ").strip().lower()
    if response not in ('', 'y', 'yes'):
        print()
        print("Please install Java manually from:")
        print("  https://adoptium.net/temurin/releases/")
        return 1

    print()

    # Create temp directory for download
    temp_dir = tempfile.mkdtemp(prefix="ko_java_install_")
    installer_path = os.path.join(temp_dir, JAVA_INSTALLER_NAME)

    try:
        if not download_java(installer_path):
            print()
            print("Please install Java manually from:")
            print("  https://adoptium.net/temurin/releases/")
            return 1

        if not install_java(installer_path):
            print()
            print("Please install Java manually from:")
            print("  https://adoptium.net/temurin/releases/")
            return 1

        update_path()

        print()
        print("=" * 50)
        print("  Java Installation Complete!")
        print("=" * 50)
        print()
        print("Please restart your terminal and run the installer again.")
        print("Or run 'refreshenv' to update your current PATH.")

    finally:
        # Cleanup
        if os.path.exists(installer_path):
            try:
                os.remove(installer_path)
            except Exception:
                pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
