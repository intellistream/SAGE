#!/usr/bin/env python3
"""
SAGE License Client
Customer-facing license management tool
"""

import sys
from datetime import datetime
from pathlib import Path

from license_core import LicenseCore
from validation import LicenseValidator

# Add shared components to path
shared_dir = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_dir))


class LicenseClient:
    """Customer license management interface"""

    def __init__(self):
        self.core = LicenseCore()
        self.validator = LicenseValidator()

    def install_license(self, license_key: str) -> bool:
        """Install a license key"""
        try:
            # Validate key format
            if not self.core.validate_key_format(license_key):
                print("❌ Invalid license key format")
                return False

            # Parse license info
            license_info = self.core.parse_license_key(license_key)
            if not license_info:
                print("❌ License key parsing failed")
                return False

            # Save license key
            with open(self.core.config.LICENSE_FILE, "w") as f:
                f.write(license_key)

            # Save configuration
            config = {
                "license_type": "commercial",
                "installed_at": datetime.now().isoformat(),
                "expires_at": license_info.expires_at,
                "features": license_info.features,
            }

            self.core.save_config(config)

            print("✅ Commercial license installed successfully!")
            print(f"   Type: {license_info.type}")
            print(f"   Expires: {license_info.expires_at}")
            print(f"   Features: {', '.join(license_info.features)}")

            return True

        except Exception as e:
            print(f"❌ License installation failed: {e}")
            return False

    def remove_license(self) -> bool:
        """Remove the current license"""
        try:
            if self.core.config.LICENSE_FILE.exists():
                self.core.config.LICENSE_FILE.unlink()
            if self.core.config.CONFIG_FILE.exists():
                self.core.config.CONFIG_FILE.unlink()
            print("✅ License removed, switched to open-source version")
            return True
        except Exception as e:
            print(f"❌ License removal failed: {e}")
            return False

    def show_status(self) -> None:
        """Display license status"""
        info = self.validator.check_license_status()

        print("🔍 SAGE License Status")
        print("=" * 30)
        print(f"Type: {info['type']}")
        print(f"Source: {info['source']}")

        if info["has_license"]:
            print(f"Expires: {info.get('expires_at', 'N/A')}")
            print(f"Features: {', '.join(info.get('features', []))}")

            # Check expiration warning
            expires_str = info.get("expires_at")
            if expires_str and expires_str != "N/A":
                try:
                    expires = datetime.fromisoformat(expires_str)
                    days_left = (expires - datetime.now()).days
                    if days_left < 30:
                        print(f"⚠️  License expires in {days_left} days")
                except Exception:
                    pass
        else:
            print("Features: Open-source functionality")
            print("💡 Get commercial version: Contact intellistream@outlook.com")


def main():
    """CLI interface for customer license operations"""
    client = LicenseClient()

    if len(sys.argv) < 2:
        print("SAGE License Client")
        print("")
        print("Usage:")
        print("  sage-license-client install <license-key>   # Install license")
        print("  sage-license-client status                  # Check status")
        print("  sage-license-client remove                  # Remove license")
        print("")
        print("Example:")
        print("  sage-license-client install SAGE-COMM-2024-ABCD-EFGH-1234")
        return

    command = sys.argv[1]

    if command == "install":
        if len(sys.argv) < 3:
            print("❌ Please provide license key")
            print("Usage: sage-license-client install <license-key>")
            return

        license_key = sys.argv[2]
        client.install_license(license_key)

    elif command == "status":
        client.show_status()

    elif command == "remove":
        client.remove_license()

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: install, status, remove")


if __name__ == "__main__":
    main()
