#!/usr/bin/env python3
"""
Simple entry point for SAGE Development Toolkit.

This script provides quick access to the dev-toolkit from the project root.
For full functionality, install the package: pip install -e dev-toolkit/
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run sage-dev toolkit."""
    project_root = Path(__file__).parent
    dev_toolkit_path = project_root / "dev-toolkit"
    
    if not dev_toolkit_path.exists():
        print("❌ dev-toolkit directory not found!")
        sys.exit(1)
    
    # Try to run the installed package first
    try:
        subprocess.run([sys.executable, "-m", "sage_dev_toolkit"] + sys.argv[1:])
    except FileNotFoundError:
        print("⚠️  SAGE Dev Toolkit not installed.")
        print("🔧 Install with: pip install -e dev-toolkit/")
        print("📖 Or see dev-toolkit/README.md for setup instructions")
        sys.exit(1)

if __name__ == "__main__":
    main()
