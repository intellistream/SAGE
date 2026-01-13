#!/usr/bin/env python3
"""Check minimal required dependencies for SAGE packages.

This script helps identify the truly required dependencies by attempting
to import each SAGE package and catching ImportError to find missing deps.

Usage:
    python tools/scripts/check_minimal_deps.py

Requires a clean Python environment (no SAGE deps installed).
"""

import subprocess
from pathlib import Path


def run_import_test(env_name: str, module: str) -> tuple[bool, str]:
    """Try to import a module and return (success, error_message)."""
    cmd = [
        "conda",
        "run",
        "-n",
        env_name,
        "python",
        "-c",
        f"import {module}; print(f'{module} OK')",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, ""
    # Extract the missing module from ImportError
    stderr = result.stderr
    if "No module named" in stderr:
        # Extract module name
        import re

        match = re.search(r"No module named '([^']+)'", stderr)
        if match:
            return False, match.group(1)
    return False, stderr


def install_package(env_name: str, package: str) -> bool:
    """Install a package in the test environment."""
    cmd = ["conda", "run", "-n", env_name, "pip", "install", package, "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def find_minimal_deps(env_name: str, module: str) -> list[str]:
    """Find minimal dependencies needed to import a module."""
    deps = []
    max_iterations = 50  # Safety limit

    for _ in range(max_iterations):
        success, missing = run_import_test(env_name, module)
        if success:
            break
        if not missing or "No module named" not in missing:
            print(f"  Unexpected error: {missing[:200]}")
            break

        # Map common internal names to pip package names
        package_map = {
            "yaml": "pyyaml",
            "sklearn": "scikit-learn",
            "cv2": "opencv-python",
            "PIL": "pillow",
            "dotenv": "python-dotenv",
        }
        pip_name = package_map.get(missing.split(".")[0], missing.split(".")[0])

        print(f"  Installing: {pip_name}")
        if install_package(env_name, pip_name):
            deps.append(pip_name)
        else:
            print(f"  Failed to install {pip_name}")
            break

    return deps


def main():
    """Main entry point."""
    env_name = "sage-test-minimal"
    sage_root = Path(__file__).parent.parent.parent

    # SAGE packages to test (in dependency order)
    packages = [
        ("sage-common", "sage.common"),
        ("sage-platform", "sage.platform"),
        ("sage-kernel", "sage.kernel"),
        ("sage-libs", "sage.libs"),
        ("sage-middleware", "sage.middleware"),
        ("sage-cli", "sage.cli"),
        ("sage-tools", "sage.tools"),
    ]

    print("=" * 60)
    print("SAGE Minimal Dependencies Checker")
    print("=" * 60)
    print(f"Test environment: {env_name}")
    print()

    all_deps = {}

    for pkg_name, module_name in packages:
        print(f"\n[{pkg_name}] Testing {module_name}...")

        # Install package without deps
        pkg_path = sage_root / "packages" / pkg_name
        if not pkg_path.exists():
            print(f"  Package not found: {pkg_path}")
            continue

        cmd = [
            "conda",
            "run",
            "-n",
            env_name,
            "pip",
            "install",
            "-e",
            str(pkg_path),
            "--no-deps",
            "-q",
        ]
        subprocess.run(cmd, capture_output=True)

        # Find minimal deps
        deps = find_minimal_deps(env_name, module_name)
        all_deps[pkg_name] = deps

        success, _ = run_import_test(env_name, module_name)
        status = "✅" if success else "❌"
        print(f"  {status} {module_name} - requires: {deps if deps else 'none'}")

    print("\n" + "=" * 60)
    print("Summary: Minimal Dependencies")
    print("=" * 60)
    for pkg, deps in all_deps.items():
        print(f"{pkg}: {', '.join(deps) if deps else '(none)'}")


if __name__ == "__main__":
    main()
