#!/usr/bin/env python3
"""
SAGE Libs Package Setup

This setup includes optional LibAMM (C++ extension) support.
When installing with 'pip install .[amm]', LibAMM will be automatically compiled.
"""

import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def build_libamm():
    """Build LibAMM C++ extension if 'amm' extra is requested"""
    # Check if we're installing with [amm] extra
    # This is a heuristic - check if torch is being installed
    if 'amm' not in sys.argv and '--extras-require' not in ''.join(sys.argv):
        return
    
    libamm_dir = Path(__file__).parent / "src" / "sage" / "libs" / "libamm"
    
    if not libamm_dir.exists():
        print("⚠️  LibAMM source directory not found, skipping compilation")
        return
    
    print("=" * 70)
    print("🔧 Building LibAMM C++ extension...")
    print("=" * 70)
    
    try:
        # Run pip install for LibAMM
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", str(libamm_dir)],
            cwd=str(libamm_dir)
        )
        print("✅ LibAMM built successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ LibAMM build failed: {e}")
        print("⚠️  You can manually build it later:")
        print(f"    cd {libamm_dir}")
        print("    pip install .")
        # Don't fail the main installation


class CustomDevelop(develop):
    """Custom develop command to build LibAMM in development mode"""
    def run(self):
        develop.run(self)
        build_libamm()


class CustomInstall(install):
    """Custom install command to build LibAMM"""
    def run(self):
        install.run(self)
        build_libamm()


if __name__ == "__main__":
    setup(
        cmdclass={
            'develop': CustomDevelop,
            'install': CustomInstall,
        }
    )
