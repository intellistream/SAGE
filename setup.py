"""Setup script for isage meta-package."""

from setuptools import setup

if __name__ == "__main__":
    print("\n=== SAGE Installation Guide ===\n")
    print("For the SAGE core stack (includes stream/runtime/serving/cli surfaces):")
    print("    pip install isage")
    print("\nFor optional adapters and data packages:")
    print("    pip install 'isage[full]'")
    print()
    setup()
