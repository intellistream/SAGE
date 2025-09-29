"""Vendor-side helpers for generating and tracking licenses."""

from __future__ import annotations

import hashlib
import json
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional

from rich.console import Console

from .core import LicenseConfig, LicenseCore


class LicenseVendor:
    """Utilities for the SAGE team to manage commercial licenses."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.core = LicenseCore()
        self.config = LicenseConfig()

    # ------------------------------------------------------------------
    # License generation
    # ------------------------------------------------------------------
    def generate_license_key(
        self,
        customer: str,
        days: int = LicenseConfig.DEFAULT_VALIDITY_DAYS,
        license_type: str = LicenseConfig.COMMERCIAL_TYPE,
    ) -> str:
        alphabet = string.ascii_uppercase + string.digits
        random_id = "".join(secrets.choice(alphabet) for _ in range(4))

        expire_date = datetime.now() + timedelta(days=days)
        year = expire_date.strftime("%Y")
        customer_hash = hashlib.md5(customer.encode()).hexdigest()[:4].upper()

        data_to_sign = f"{license_type}{year}{customer_hash}{random_id}"
        checksum = hashlib.sha256(data_to_sign.encode()).hexdigest()[:4].upper()

        return f"{self.config.PREFIX}-{license_type}-{year}-{customer_hash}-{random_id}-{checksum}"

    def save_generated_license(self, license_key: str, customer: str, days: int) -> None:
        records = []
        path = self.config.GENERATED_LICENSES_FILE

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as stream:
                    records = json.load(stream)
            except Exception:
                records = []

        expire_date = datetime.now() + timedelta(days=days)
        records.append(
            {
                "license_key": license_key,
                "customer": customer,
                "generated_at": datetime.now().isoformat(),
                "expires_at": expire_date.isoformat(),
                "valid_days": days,
            }
        )

        with open(path, "w", encoding="utf-8") as stream:
            json.dump(records, stream, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------
    def list_generated_licenses(self) -> List[dict]:
        path = self.config.GENERATED_LICENSES_FILE
        if not path.exists():
            return []

        try:
            with open(path, "r", encoding="utf-8") as stream:
                return json.load(stream)
        except Exception:
            return []

    def revoke_license(self, license_key: str) -> bool:
        path = self.config.GENERATED_LICENSES_FILE
        if not path.exists():
            return False

        try:
            with open(path, "r", encoding="utf-8") as stream:
                records = json.load(stream)
        except Exception:
            return False

        updated = False
        for record in records:
            if record.get("license_key") == license_key:
                record["revoked"] = True
                record["revoked_at"] = datetime.now().isoformat()
                updated = True

        if updated:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(records, stream, indent=2, ensure_ascii=False)
        return updated

    # ------------------------------------------------------------------
    # Console helpers
    # ------------------------------------------------------------------
    def print_license_records(self, records: List[dict]) -> None:
        if not records:
            self.console.print("📝 尚未生成任何许可证")
            return

        for idx, record in enumerate(records, 1):
            generated = datetime.fromisoformat(record["generated_at"])
            expires = datetime.fromisoformat(record["expires_at"])
            status = "✅ 有效" if datetime.now() < expires else "❌ 已过期"
            if record.get("revoked"):
                status = "⛔ 已吊销"

            self.console.print(f"{idx}. 客户: {record['customer']}")
            self.console.print(f"   Key: {record['license_key']}")
            self.console.print(f"   生成时间: {generated:%Y-%m-%d %H:%M:%S}")
            self.console.print(f"   到期时间: {expires:%Y-%m-%d %H:%M:%S}")
            self.console.print(f"   状态: {status}\n")


__all__ = ["LicenseVendor"]
