#!/usr/bin/env python3
"""Build a macOS .pkg installer for the ko compiler."""

import os
import sys
import subprocess
import plistlib
import tempfile
import shutil

def create_pkg():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    output_pkg = os.path.join(pkg_dir, 'dist', 'ko-compiler-2.800.pkg')
    version = '2.800'
    
    os.makedirs(os.path.dirname(output_pkg), exist_ok=True)
    
    # Create payload
    payload_dir = tempfile.mkdtemp(prefix='ko_payload_')
    try:
        # Create directory structure
        os.makedirs(os.path.join(payload_dir, 'usr/local/bin'))
        os.makedirs(os.path.join(payload_dir, 'usr/local/share/ko'))
        
        # Copy files
        shutil.copy(os.path.join(root_dir, 'ko_compiler.py'), 
                    os.path.join(payload_dir, 'usr/local/share/ko/'))
        shutil.copy(os.path.join(root_dir, 'Import.java'), 
                    os.path.join(payload_dir, 'usr/local/share/ko/'))
        
        # Copy Import.class if exists
        import_class = os.path.join(root_dir, 'Import.class')
        if os.path.exists(import_class):
            shutil.copy(import_class, os.path.join(payload_dir, 'usr/local/share/ko/'))
        
        # Copy test files
        test_src = os.path.join(root_dir, 'test_compiler')
        test_dst = os.path.join(payload_dir, 'usr/local/share/ko/test_compiler')
        if os.path.exists(test_src):
            shutil.copytree(test_src, test_dst)
        
        # Copy other Python files
        for py_file in ['ir.py', 'optimizer.py', 'semantic_analyzer.py']:
            src = os.path.join(root_dir, py_file)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(payload_dir, 'usr/local/share/ko/'))
        
        # Create ko wrapper
        ko_wrapper = '''#!/bin/bash
set -e
export KO_HOME="$(dirname "$(readlink -f "$0")")/../share/ko"
exec python3 "$KO_HOME/ko_compiler.py" "$@"
'''
        with open(os.path.join(payload_dir, 'usr/local/bin/ko'), 'w') as f:
            f.write(ko_wrapper)
        os.chmod(os.path.join(payload_dir, 'usr/local/bin/ko'), 0o755)
        
        # Create preinstall script
        preinstall = '''#!/bin/bash
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
'''
        preinstall_path = os.path.join(pkg_dir, 'preinstall')
        with open(preinstall_path, 'w') as f:
            f.write(preinstall)
        os.chmod(preinstall_path, 0o755)
        
        # Create postinstall script
        postinstall = '''#!/bin/bash
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
'''
        postinstall_path = os.path.join(pkg_dir, 'postinstall')
        with open(postinstall_path, 'w') as f:
            f.write(postinstall)
        os.chmod(postinstall_path, 0o755)
        
        # Try to use pkgbuild if available
        try:
            subprocess.run([
                'pkgbuild',
                '--root', payload_dir,
                '--identifier', 'ai.studio.ko',
                '--version', version,
                '--install-location', '/',
                '--preinstall', preinstall_path,
                '--postinstall', postinstall_path,
                output_pkg
            ], check=True)
            print(f"Created macOS .pkg: {output_pkg}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: create a tar.gz with instructions
            tar_output = output_pkg.replace('.pkg', '-macos.tar.gz')
            shutil.make_archive(tar_output.replace('.tar.gz', ''), 'gztar', payload_dir)
            print(f"Created macOS archive: {tar_output}")
            print("Note: Build .pkg on macOS using: pkgbuild --root ...")
    
    finally:
        shutil.rmtree(payload_dir, ignore_errors=True)
        # Cleanup scripts
        for script in ['preinstall', 'postinstall']:
            path = os.path.join(pkg_dir, script)
            if os.path.exists(path):
                os.remove(path)

if __name__ == '__main__':
    create_pkg()
