"""Setup script for isage meta-package."""

from setuptools import setup

if __name__ == "__main__":
    print("\n=== SAGE Installation Guide ===\n")
    print("For LLM inference functionality, please install isagellm:")
    print("    pip install isagellm")
    print("\nFor full SAGE stack:")
    print("    pip install isage[all]")
    print()
    setup()
