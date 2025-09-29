"""Core data structures and helpers for SAGE license management."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LicenseInfo:
    """Structured representation of a validated license."""

    type: str
    license_type: str
    year: int
    customer_hash: str
    expires_at: str
    features: List[str]
    validated: bool = False
    source: str = "file"


class LicenseConfig:
    """Centralised configuration values used by license tooling."""

    SAGE_CONFIG_DIR = Path.home() / ".sage"
    LICENSE_FILE = SAGE_CONFIG_DIR / "license.key"
    CONFIG_FILE = SAGE_CONFIG_DIR / "config.json"
    GENERATED_LICENSES_FILE = SAGE_CONFIG_DIR / "generated_licenses.json"

    PREFIX = "SAGE"
    COMMERCIAL_TYPE = "COMM"
    DEFAULT_VALIDITY_DAYS = 365
    COMMERCIAL_FEATURES = [
        "high-performance",
        "enterprise-db",
        "advanced-analytics",
        "priority-support",
    ]
    OPEN_SOURCE_FEATURES = ["basic-functionality", "community-support"]


class LicenseCore:
    """Low-level helpers shared by customer and vendor tooling."""

    def __init__(self) -> None:
        self.config = LicenseConfig()
        self.config.SAGE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Validation utilities
    # ------------------------------------------------------------------
    def validate_key_format(self, key: str) -> bool:
        parts = key.split("-")
        return (
            len(parts) == 6
            and parts[0] == self.config.PREFIX
            and parts[1] == self.config.COMMERCIAL_TYPE
            and len(parts[2]) == 4
            and parts[2].isdigit()
        )

    def parse_license_key(self, key: str) -> Optional[LicenseInfo]:
        parts = key.split("-")
        if len(parts) != 6:
            return None

        prefix, license_type, year_str, customer_hash, random_id, checksum = parts

        data_to_verify = f"{license_type}{year_str}{customer_hash}{random_id}"
        expected_checksum = hashlib.sha256(data_to_verify.encode()).hexdigest()[:4].upper()

        if checksum != expected_checksum:
            return None

        try:
            year = int(year_str)
        except ValueError:
            return None

        expires_at = datetime(year + 1, 12, 31).isoformat()

        return LicenseInfo(
            type="Commercial",
            license_type=license_type,
            year=year,
            customer_hash=customer_hash,
            expires_at=expires_at,
            features=list(LicenseConfig.COMMERCIAL_FEATURES),
            validated=True,
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def save_config(self, config: Dict[str, Any]) -> None:
        with open(self.config.CONFIG_FILE, "w", encoding="utf-8") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)

    def load_config(self) -> Dict[str, Any]:
        if not self.config.CONFIG_FILE.exists():
            return {}
        try:
            with open(self.config.CONFIG_FILE, "r", encoding="utf-8") as stream:
                return json.load(stream)
        except Exception:
            return {}


__all__ = ["LicenseCore", "LicenseConfig", "LicenseInfo"]
