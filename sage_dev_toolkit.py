#!/usr/bin/env python3
"""
SAGE Development Toolkit Entry Point
=====================================

This script provides a convenient entry point for the SAGE Development Toolkit
when running from the repository root. It automatically sets up the Python path
and configuration to work with the local development environment.

Usage:
    python sage_dev_toolkit.py [command] [options]
    
Examples:
    python sage_dev_toolkit.py test --mode diff
    python sage_dev_toolkit.py analyze --type summary
    python sage_dev_toolkit.py package list
    python sage_dev_toolkit.py report
    python sage_dev_toolkit.py interactive
"""

import sys
import os
from pathlib import Path

# Add the dev-toolkit src directory to Python path
toolkit_root = Path(__file__).parent / "dev-toolkit"
toolkit_src = toolkit_root / "src"

if toolkit_src.exists():
    sys.path.insert(0, str(toolkit_src))

try:
    from sage_dev_toolkit.cli.main import main
    
    if __name__ == "__main__":
        # Set default project root to current directory
        if not any(arg.startswith('--project-root') for arg in sys.argv):
            sys.argv.extend(['--project-root', str(Path.cwd())])
        
        # Set default config file if exists
        default_config = Path.cwd() / "dev-toolkit" / "config" / "default.yaml"
        if default_config.exists() and not any(arg.startswith('--config') for arg in sys.argv):
            sys.argv.extend(['--config', str(default_config)])
        
        main()
        
except ImportError as e:
    print(f"❌ Error importing SAGE Development Toolkit: {e}")
    print(f"📁 Toolkit source directory: {toolkit_src}")
    print(f"📄 Make sure the dev-toolkit is properly set up.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
