#!/usr/bin/env python3
"""ko - .ko Language Compiler CLI (standalone entry point)."""

import os
import sys
import subprocess

# Determine the directory where the executable/script lives
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

KO_HOME = APP_DIR
MODULES_DIR = os.path.join(os.path.expanduser("~"), ".ko", "modules")
KO_COMPILER = os.path.join(KO_HOME, "ko_compiler.py")

# Ensure modules directory exists
os.makedirs(MODULES_DIR, exist_ok=True)

# Ensure PYTHONPATH includes bundled modules
if KO_HOME not in sys.path:
    sys.path.insert(0, KO_HOME)

# Ensure Import.java is compiled
import_java = os.path.join(KO_HOME, "Import.java")
import_class = os.path.join(KO_HOME, "Import.class")
if os.path.exists(import_java) and not os.path.exists(import_class):
    try:
        subprocess.run(
            ["javac", import_java],
            capture_output=True,
            text=True,
            timeout=30
        )
    except Exception:
        pass


def show_help():
    print("""ko - .ko Language Compiler CLI

USAGE:
    ko [OPTIONS] <file.ko>
    ko --install <module_name>

OPTIONS:
    -h, --help      Show this help message
    --install       Install an external library from ko-studio.ai.studio
    --version       Show version information

EXAMPLES:
    ko program.ko                  Run a .ko program
    ko --install MyLibrary         Install an external library

For more information, visit: https://ko-studio.ai.studio
""")


def show_version():
    print("ko compiler v2.800")
    print("Copyright (c) 2026 ko-studio.ai.studio")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    args = sys.argv[1:]

    if args[0] in ("-h", "--help"):
        show_help()
        sys.exit(0)

    if args[0] == "--version":
        show_version()
        sys.exit(0)

    if args[0] == "--install":
        if len(args) < 2:
            print("Error: --install requires a module name", file=sys.stderr)
            sys.exit(1)
        from ko_compiler import _install_external_library
        success = _install_external_library(args[1])
        sys.exit(0 if success else 1)

    # Run the compiler
    from ko_compiler import run_ko_file
    source_file = args[0]

    if not os.path.exists(source_file):
        print(f"Error: File not found: {source_file}", file=sys.stderr)
        sys.exit(1)

    try:
        run_ko_file(source_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
