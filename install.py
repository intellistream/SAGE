#!/usr/bin/env python3
"""
SAGE Framework Installation Script
==================================

Professional installation and management tool for the SAGE framework.
Supports both minimal (Python-only) and full (Docker + C++) installations.

Usage:
    python install.py                # Interactive menu
    python install.py --minimal      # Direct minimal installation
    python install.py --full         # Direct full installation
    python install.py --native-cpp   # Direct native C++ installation (without Docker)
    python install.py --uninstall    # Direct uninstallation
    python install.py --help         # Show help
"""

import argparse
import sys
from pathlib import Path

# Add installation modules to Python path
sys.path.insert(0, str(Path(__file__).parent / "installation"))

from modules import SageInstaller


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SAGE Framework Installation Script")
    parser.add_argument('--minimal', action='store_true', help='Run minimal setup directly')
    parser.add_argument('--full', action='store_true', help='Run full setup directly')
    parser.add_argument('--native-cpp', action='store_true', help='Run native C++ setup directly (without Docker)')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall SAGE completely')
    parser.add_argument('--status', action='store_true', help='Show installation status')
    parser.add_argument('--help-sage', action='store_true', help='Show SAGE help information')
    parser.add_argument('--env-name', type=str, default='sage', 
                       help='Name for the conda environment (default: sage)')
    
    args = parser.parse_args()
    
    installer = SageInstaller(conda_env_name=args.env_name)
    
    try:
        if args.minimal:
            installer.minimal_setup()
        elif args.full:
            installer.full_setup()
        elif args.native_cpp:
            installer.native_cpp_setup()
        elif args.uninstall:
            installer.uninstall_sage()
        elif args.status:
            installer.menu_handler.show_status()
        elif args.help_sage:
            installer.menu_handler.show_help()
        else:
            installer.main_menu()
    except KeyboardInterrupt:
        print(f"\nInstallation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        installer.print_error(f"Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
