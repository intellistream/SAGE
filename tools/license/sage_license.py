#!/usr/bin/env python3
"""
SAGE License Manager
Unified executable for license operations
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'shared'))
sys.path.insert(0, str(current_dir / 'client'))
sys.path.insert(0, str(current_dir / 'vendor'))

# Make scripts executable
os.chmod(current_dir / 'client' / 'license_client.py', 0o755)
os.chmod(current_dir / 'vendor' / 'license_vendor.py', 0o755)

def show_help():
    """Show help information"""
    print("SAGE License Manager")
    print("=" * 50)
    print("")
    print("🏢 Customer Commands:")
    print("  install <license-key>     Install a commercial license")
    print("  status                    Check current license status")
    print("  remove                    Remove current license")
    print("")
    print("🏭 Vendor Commands (SAGE Team Only):")
    print("  generate <customer> [days] Generate new license (default: 365 days)")
    print("  list                      List all generated licenses")
    print("  revoke <license-key>      Revoke a specific license")
    print("")
    print("📝 Examples:")
    print("  # Customer operations")
    print("  python sage_license.py install SAGE-COMM-2024-ABCD-EFGH-1234")
    print("  python sage_license.py status")
    print("")
    print("  # Vendor operations")
    print("  python sage_license.py generate 'Company ABC' 365")
    print("  python sage_license.py list")
    print("")
    print("🔗 Legacy Compatibility:")
    print("  Old scripts/sage-license.py is deprecated.")
    print("  Use this tool instead for all license operations.")


def run_client_command(command, args):
    """Run customer-facing license command"""
    import subprocess
    
    client_script = current_dir / 'client' / 'license_client.py'
    cmd = [sys.executable, str(client_script), command] + args
    
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running client command: {e}")
        return 1


def run_vendor_command(command, args):
    """Run vendor license command"""
    import subprocess
    
    vendor_script = current_dir / 'vendor' / 'license_vendor.py'
    cmd = [sys.executable, str(vendor_script), command] + args
    
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running vendor command: {e}")
        return 1


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return 0
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # Customer commands
    if command in ['install', 'status', 'remove']:
        return run_client_command(command, args)
    
    # Vendor commands
    elif command in ['generate', 'list', 'revoke']:
        return run_vendor_command(command, args)
    
    # Help command
    elif command in ['help', '--help', '-h']:
        show_help()
        return 0
    
    else:
        print(f"❌ Unknown command: {command}")
        print("")
        show_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
