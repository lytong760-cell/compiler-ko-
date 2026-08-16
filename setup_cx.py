import sys
import os
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "sys", "subprocess", "json", "re", "glob", "tempfile", "shutil", "hashlib", "argparse", "typing", "dataclasses", "enum", "ast"],
    "includes": ["ko_compiler", "ir", "optimizer", "semantic_analyzer"],
    "include_files": [
        ("ko_compiler.py", "ko_compiler.py"),
        ("Import.java", "Import.java"),
        ("Import.class", "Import.class"),
        ("ir.py", "ir.py"),
        ("optimizer.py", "optimizer.py"),
        ("semantic_analyzer.py", "semantic_analyzer.py"),
        ("test_compiler", "test_compiler"),
    ],
    "build_exe": "dist_cx",
}

setup(
    name="ko",
    version="2.800",
    description=".ko Language Compiler",
    options={"build_exe": build_exe_options},
    executables=[Executable("ko_cli.py", base=None, target_name="ko")]
)
