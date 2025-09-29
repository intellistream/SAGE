"""Validation helpers for SAGE licensing."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from .core import LicenseConfig, LicenseCore


class LicenseValidator:
    """Provides high-level checks for license availability and features."""

    def __init__(self) -> None:
        self.core = LicenseCore()

    def check_license_status(self) -> Dict[str, Any]:
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

        if self.core.config.LICENSE_FILE.exists():
            try:
                with open(self.core.config.LICENSE_FILE, "r", encoding="utf-8") as stream:
                    key = stream.read().strip()
                info = self.core.parse_license_key(key)
                if info:
                    return {
                        "has_license": True,
                        "source": "file",
                        "type": "commercial",
                        **info.__dict__,
                    }
            except Exception:
                pass

        return {"has_license": False, "source": "none", "type": "open-source"}

    def has_valid_license(self) -> bool:
        status = self.check_license_status()
        if not status.get("has_license"):
            return False

        expires_str = status.get("expires_at")
        if not expires_str or expires_str == "N/A":
            return True

        try:
            expires = datetime.fromisoformat(expires_str)
        except Exception:
            return True

        return datetime.now() < expires

    def get_license_features(self) -> List[str]:
        status = self.check_license_status()
        if status.get("has_license"):
            return status.get("features", [])
        return list(LicenseConfig.OPEN_SOURCE_FEATURES)

    def validate_feature_access(self, feature: str) -> bool:
        features = self.get_license_features()
        return feature in features or "enterprise" in features


__all__ = ["LicenseValidator"]
