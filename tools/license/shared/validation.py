"""
License Validation Module
"""

import os
from datetime import datetime
from typing import Any, Dict

from license_core import LicenseCore


class LicenseValidator:
    """License validation and status checking"""

    def __init__(self):
        self.core = LicenseCore()

    def check_license_status(self) -> Dict[str, Any]:
        """Check current license status from all sources"""
        # Check environment variable first
        env_key = os.getenv("SAGE_LICENSE_KEY")
        if env_key:
            info = self.core.parse_license_key(env_key)
            if info:
                return {
                    "has_license": True,
                    "source": "environment",
                    "type": "commercial",
                    **info.__dict__,
                }

        # Check license file
        if self.core.config.LICENSE_FILE.exists():
            try:
                with open(self.core.config.LICENSE_FILE, "r") as f:
                    file_key = f.read().strip()

                info = self.core.parse_license_key(file_key)
                if info:
                    return {
                        "has_license": True,
                        "source": "file",
                        "type": "commercial",
                        **info.__dict__,
                    }
            except Exception:
                pass

        # No license, return open-source
        return {"has_license": False, "source": "none", "type": "open-source"}

    def has_valid_license(self) -> bool:
        """Quick check if there's a valid license"""
        status = self.check_license_status()
        if not status["has_license"]:
            return False

        # Check expiration
        expires_str = status.get("expires_at")
        if expires_str and expires_str != "N/A":
            try:
                expires = datetime.fromisoformat(expires_str)
                return datetime.now() < expires
            except Exception:
                pass

        return True

    def get_license_features(self) -> list:
        """Get available license features"""
        status = self.check_license_status()
        if status["has_license"]:
            return status.get("features", [])
        return ["open-source"]

    def validate_feature_access(self, feature: str) -> bool:
        """Check if a specific feature is available"""
        features = self.get_license_features()
        return feature in features or "enterprise" in features
