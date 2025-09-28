#!/usr/bin/env python3
"""
SAGE License Vendor
Internal tool for SAGE team to generate and manage licenses
"""

import hashlib
import json
import secrets
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path

from license_core import LicenseConfig, LicenseCore

# Add shared components to path
shared_dir = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_dir))


class LicenseVendor:
    """Vendor license generation and management"""

    def __init__(self):
        self.core = LicenseCore()
        self.config = LicenseConfig()

    def generate_license_key(
        self, customer: str, days: int = 365, license_type: str = "COMM"
    ) -> str:
        """Generate a new license key"""
        # Generate random identifier
        alphabet = string.ascii_uppercase + string.digits
        random_id = "".join(secrets.choice(alphabet) for _ in range(4))

        # Calculate expiration time
        expire_date = datetime.now() + timedelta(days=days)
        year = expire_date.strftime("%Y")

        # Generate customer hash (first 4 chars of customer name hash)
        customer_hash = hashlib.md5(customer.encode()).hexdigest()[:4].upper()

        # Generate checksum
        data_to_sign = f"{license_type}{year}{customer_hash}{random_id}"
        checksum = hashlib.sha256(data_to_sign.encode()).hexdigest()[:4].upper()

        # Assemble license key: SAGE-COMM-YYYY-CUSTOMER-RANDOM-CHECKSUM
        license_key = f"{self.config.PREFIX}-{license_type}-{year}-{customer_hash}-{random_id}-{checksum}"

        return license_key

    def save_generated_license(self, license_key: str, customer: str, days: int):
        """Save generated license information"""
        info_file = self.config.GENERATED_LICENSES_FILE

        # Read existing records
        records = []
        if info_file.exists():
            try:
                with open(info_file, "r") as f:
                    records = json.load(f)
            except:
                records = []

        # Add new record
        expire_date = datetime.now() + timedelta(days=days)
        record = {
            "license_key": license_key,
            "customer": customer,
            "generated_at": datetime.now().isoformat(),
            "expires_at": expire_date.isoformat(),
            "valid_days": days,
        }
        records.append(record)

        # Save records
        with open(info_file, "w") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def list_generated_licenses(self):
        """List all generated licenses"""
        info_file = self.config.GENERATED_LICENSES_FILE

        if not info_file.exists():
            print("📝 No licenses have been generated yet")
            return

        try:
            with open(info_file, "r") as f:
                records = json.load(f)

            if not records:
                print("📝 No licenses have been generated yet")
                return

            print("🔑 Generated Licenses:")
            print("")
            for i, record in enumerate(records, 1):
                generated = datetime.fromisoformat(record["generated_at"])
                expires = datetime.fromisoformat(record["expires_at"])

                status = "✅ Valid" if datetime.now() < expires else "❌ Expired"

                print(f"{i}. Customer: {record['customer']}")
                print(f"   Key: {record['license_key']}")
                print(f"   Generated: {generated.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Expires: {expires.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Status: {status}")
                print("")

        except Exception as e:
            print(f"❌ Failed to read license records: {e}")

    def revoke_license(self, license_key: str):
        """Revoke a specific license (mark as revoked)"""
        info_file = self.config.GENERATED_LICENSES_FILE

        if not info_file.exists():
            print("❌ No license records found")
            return False

        try:
            with open(info_file, "r") as f:
                records = json.load(f)

            # Find and mark as revoked
            for record in records:
                if record["license_key"] == license_key:
                    record["revoked"] = True
                    record["revoked_at"] = datetime.now().isoformat()

                    # Save updated records
                    with open(info_file, "w") as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)

                    print(f"✅ License {license_key} has been revoked")
                    return True

            print(f"❌ License {license_key} not found")
            return False

        except Exception as e:
            print(f"❌ Failed to revoke license: {e}")
            return False


def main():
    """CLI interface for vendor license operations"""
    vendor = LicenseVendor()

    if len(sys.argv) < 2:
        print("SAGE License Vendor Tool")
        print("")
        print("Usage:")
        print(
            "  sage-license-vendor generate <customer> [days]  # Generate license (default 365 days)"
        )
        print(
            "  sage-license-vendor list                        # List all generated licenses"
        )
        print("  sage-license-vendor revoke <license-key>        # Revoke a license")
        print("")
        print("Examples:")
        print("  sage-license-vendor generate 'Company ABC' 365")
        print("  sage-license-vendor generate 'Customer XYZ'     # Default 365 days")
        print("  sage-license-vendor revoke SAGE-COMM-2024-ABCD-EFGH-1234")
        return

    command = sys.argv[1]

    if command == "generate":
        if len(sys.argv) < 3:
            print("❌ Please provide customer name")
            print("Usage: sage-license-vendor generate <customer> [days]")
            print("Example: sage-license-vendor generate 'Company ABC' 365")
            return

        customer = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 365

        license_key = vendor.generate_license_key(customer, days)
        vendor.save_generated_license(license_key, customer, days)

        print("🎉 License generated successfully!")
        print(f"📧 Customer: {customer}")
        print(f"⏰ Valid for: {days} days")
        print(f"🔑 License Key: {license_key}")
        print("")
        print("💡 Customer can install with:")
        print(f"   sage-license-client install {license_key}")

    elif command == "list":
        vendor.list_generated_licenses()

    elif command == "revoke":
        if len(sys.argv) < 3:
            print("❌ Please provide license key")
            print("Usage: sage-license-vendor revoke <license-key>")
            return

        license_key = sys.argv[2]
        vendor.revoke_license(license_key)

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: generate, list, revoke")


if __name__ == "__main__":
    main()
