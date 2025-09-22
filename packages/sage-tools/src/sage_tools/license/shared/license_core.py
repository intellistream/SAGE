"""
import logging
SAGE License Core Components
Shared license management functionality
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class LicenseInfo:
    """License information structure"""

    type: str
    license_type: str
    year: int
    customer_hash: str
    expires_at: str
    features: list
    validated: bool = False
    source: str = "file"


class LicenseConfig:
    """License configuration constants"""

    SAGE_CONFIG_DIR = Path.home() / ".sage"
    LICENSE_FILE = SAGE_CONFIG_DIR / "license.key"
    CONFIG_FILE = SAGE_CONFIG_DIR / "config.json"
    GENERATED_LICENSES_FILE = SAGE_CONFIG_DIR / "generated_licenses.json"

    # License format: SAGE-COMM-YYYY-XXXX-XXXX-XXXX
    PREFIX = "SAGE"
    COMMERCIAL_TYPE = "COMM"
    DEFAULT_VALIDITY_DAYS = 365


class LicenseCore:
    """Core license management functionality"""

    def __init__(self):
        self.config = LicenseConfig()
        # Ensure config directory exists
        self.config.SAGE_CONFIG_DIR.mkdir(exist_ok=True)

    def validate_key_format(self, key: str) -> bool:
        """Validate license key format"""
        parts = key.split("-")
        return (
            len(parts) == 6
            and parts[0] == self.config.PREFIX
            and parts[1] == self.config.COMMERCIAL_TYPE
            and len(parts[2]) == 4
            and parts[2].isdigit()
        )

    def parse_license_key(self, key: str) -> Optional[LicenseInfo]:
        """Parse license key information"""
        try:
            parts = key.split("-")

            if len(parts) != 6:
                return None

            prefix, license_type, year, customer_hash, random_id, checksum = parts

            # Verify checksum
            data_to_verify = f"{license_type}{year}{customer_hash}{random_id}"
            expected_checksum = (
                hashlib.sha256(data_to_verify.encode()).hexdigest()[:4].upper()
            )

            if checksum != expected_checksum:
                logging.info("⚠️  License checksum verification failed")
                return None

            # Calculate expiration time
            license_year = int(year)
            expires_at = datetime(license_year + 1, 12, 31)

            return LicenseInfo(
                type="Commercial",
                license_type=license_type,
                year=license_year,
                customer_hash=customer_hash,
                expires_at=expires_at.isoformat(),
                features=["high-performance", "enterprise-db", "advanced-analytics"],
                validated=True,
            )

        except Exception as e:
            logging.info(f"⚠️  License parsing error: {e}")
            return None

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save license configuration"""
        with open(self.config.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self) -> Dict[str, Any]:
        """Load license configuration"""
        if self.config.CONFIG_FILE.exists():
            try:
                with open(self.config.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}
