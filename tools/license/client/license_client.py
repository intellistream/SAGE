#!/usr/bin/env python3
"""
import logging
SAGE License Client
Customer-facing license management tool
"""

import sys
from datetime import datetime
from pathlib import Path

# Add shared components to path
shared_dir = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_dir))

from license_core import LicenseCore
from validation import LicenseValidator


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
                logging.info("❌ Invalid license key format")
                return False

            # Parse license info
            license_info = self.core.parse_license_key(license_key)
            if not license_info:
                logging.info("❌ License key parsing failed")
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

            logging.info("✅ Commercial license installed successfully!")
            logging.info(f"   Type: {license_info.type}")
            logging.info(f"   Expires: {license_info.expires_at}")
            logging.info(f"   Features: {', '.join(license_info.features)}")

            return True

        except Exception as e:
            logging.info(f"❌ License installation failed: {e}")
            return False

    def remove_license(self) -> bool:
        """Remove the current license"""
        try:
            if self.core.config.LICENSE_FILE.exists():
                self.core.config.LICENSE_FILE.unlink()
            if self.core.config.CONFIG_FILE.exists():
                self.core.config.CONFIG_FILE.unlink()
            logging.info("✅ License removed, switched to open-source version")
            return True
        except Exception as e:
            logging.info(f"❌ License removal failed: {e}")
            return False

    def show_status(self) -> None:
        """Display license status"""
        info = self.validator.check_license_status()

        logging.info("🔍 SAGE License Status")
        logging.info("=" * 30)
        logging.info(f"Type: {info['type']}")
        logging.info(f"Source: {info['source']}")

        if info["has_license"]:
            logging.info(f"Expires: {info.get('expires_at', 'N/A')}")
            logging.info(f"Features: {', '.join(info.get('features', []))}")

            # Check expiration warning
            expires_str = info.get("expires_at")
            if expires_str and expires_str != "N/A":
                try:
                    expires = datetime.fromisoformat(expires_str)
                    days_left = (expires - datetime.now()).days
                    if days_left < 30:
                        logging.info(f"⚠️  License expires in {days_left} days")
                except:
                    pass
        else:
            logging.info("Features: Open-source functionality")
            logging.info("💡 Get commercial version: Contact intellistream@outlook.com")


def main():
    """CLI interface for customer license operations"""
    client = LicenseClient()

    if len(sys.argv) < 2:
        logging.info("SAGE License Client")
        logging.info("")
        logging.info("Usage:")
        logging.info("  sage-license-client install <license-key>   # Install license")
        logging.info("  sage-license-client status                  # Check status")
        logging.info("  sage-license-client remove                  # Remove license")
        logging.info("")
        logging.info("Example:")
        logging.info("  sage-license-client install SAGE-COMM-2024-ABCD-EFGH-1234")
        return

    command = sys.argv[1]

    if command == "install":
        if len(sys.argv) < 3:
            logging.info("❌ Please provide license key")
            logging.info("Usage: sage-license-client install <license-key>")
            return

        license_key = sys.argv[2]
        client.install_license(license_key)

    elif command == "status":
        client.show_status()

    elif command == "remove":
        client.remove_license()

    else:
        logging.info(f"❌ Unknown command: {command}")
        logging.info("Available commands: install, status, remove")


if __name__ == "__main__":
    main()
