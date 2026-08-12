#!/usr/bin/env python3
"""Test runner for .ko compiler test suite.

Discovers all test_*.ko files in test_compiler/ and runs them,
reporting pass/fail status and capturing output.
"""

import glob
import subprocess
import sys
from typing import List, Tuple

TEST_DIR = "test_compiler"
TEST_PATTERN = f"{TEST_DIR}/test_*.ko"


def run_test(path: str) -> Tuple[bool, str, str]:
    """Run a single .ko test file.

    Args:
        path: Path to the .ko test file.

    Returns:
        Tuple of (success, stdout, stderr).
    """
    try:
        result = subprocess.run(
            [sys.executable, "ko_compiler.py", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Test timed out after 30s"
    except Exception as e:
        return False, "", str(e)


def main() -> int:
    tests = sorted(glob.glob(TEST_PATTERN))
    if not tests:
        print(f"No tests found matching {TEST_PATTERN}")
        return 1

    results: List[Tuple[str, bool, str, str]] = []
    passed = 0
    failed = 0

    print("=" * 60)
    print("Running .ko Compiler Test Suite")
    print("=" * 60)

    for test in tests:
        name = test.split("/")[-1]
        ok, stdout, stderr = run_test(test)
        results.append((name, ok, stdout, stderr))
        if ok:
            passed += 1
        else:
            failed += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok and stderr:
            for line in stderr.strip().splitlines()[:5]:
                print(f"       {line}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
