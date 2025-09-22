#!/usr/bin/env python3
"""
import logging
SAGE License Manager
Unified executable for license operations
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "shared"))
sys.path.insert(0, str(current_dir / "client"))
sys.path.insert(0, str(current_dir / "vendor"))

# Make scripts executable
os.chmod(current_dir / "client" / "license_client.py", 0o755)
os.chmod(current_dir / "vendor" / "license_vendor.py", 0o755)


def show_help():
    """Show help information"""
    logging.info("SAGE License Manager")
    logging.info("=" * 50)
    logging.info("")
    logging.info("🏢 Customer Commands:")
    logging.info("  install <license-key>     Install a commercial license")
    logging.info("  status                    Check current license status")
    logging.info("  remove                    Remove current license")
    logging.info("")
    logging.info("🏭 Vendor Commands (SAGE Team Only):")
    logging.info(
        "  generate <customer> [days] Generate new license (default: 365 days)"
    )
    logging.info("  list                      List all generated licenses")
    logging.info("  revoke <license-key>      Revoke a specific license")
    logging.info("")
    logging.info("📝 Examples:")
    logging.info("  # Customer operations")
    logging.info("  python sage_license.py install SAGE-COMM-2024-ABCD-EFGH-1234")
    logging.info("  python sage_license.py status")
    logging.info("")
    logging.info("  # Vendor operations")
    logging.info("  python sage_license.py generate 'Company ABC' 365")
    logging.info("  python sage_license.py list")
    logging.info("")
    logging.info("🔗 Legacy Compatibility:")
    logging.info("  Old scripts/sage-license.py is deprecated.")
    logging.info("  Use this tool instead for all license operations.")


def run_client_command(command, args):
    """Run customer-facing license command"""
    import subprocess

    client_script = current_dir / "client" / "license_client.py"
    cmd = [sys.executable, str(client_script), command] + args

    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        logging.info(f"❌ Error running client command: {e}")
        return 1


def run_vendor_command(command, args):
    """Run vendor license command"""
    import subprocess

    vendor_script = current_dir / "vendor" / "license_vendor.py"
    cmd = [sys.executable, str(vendor_script), command] + args

    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        logging.info(f"❌ Error running vendor command: {e}")
        return 1


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return 0

    command = sys.argv[1]
    args = sys.argv[2:]

    # Customer commands
    if command in ["install", "status", "remove"]:
        return run_client_command(command, args)

    # Vendor commands
    elif command in ["generate", "list", "revoke"]:
        return run_vendor_command(command, args)

    # Help command
    elif command in ["help", "--help", "-h"]:
        show_help()
        return 0

    else:
        logging.info(f"❌ Unknown command: {command}")
        logging.info("")
        show_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
