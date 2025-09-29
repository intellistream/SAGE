"""Customer-facing license management helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.console import Console

from .core import LicenseConfig, LicenseCore
from .validator import LicenseValidator


class LicenseClient:
    """Wraps common install/remove/status operations."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.core = LicenseCore()
        self.validator = LicenseValidator()

    def install_license(self, license_key: str) -> bool:
        if not self.core.validate_key_format(license_key):
            self.console.print("❌ [red]Invalid license key format[/red]")
            return False

        info = self.core.parse_license_key(license_key)
        if not info:
            self.console.print("❌ [red]Unable to parse license key[/red]")
            return False

        try:
            with open(self.core.config.LICENSE_FILE, "w", encoding="utf-8") as stream:
                stream.write(license_key)

            config = {
                "license_type": "commercial",
                "installed_at": datetime.now().isoformat(),
                "expires_at": info.expires_at,
                "features": info.features,
            }
            self.core.save_config(config)
        except Exception as exc:
            self.console.print(f"❌ [red]Failed to persist license: {exc}[/red]")
            return False

        self.console.print("✅ [green]Commercial license installed successfully[/green]")
        self.console.print(f" • 类型: {info.type}")
        self.console.print(f" • 到期时间: {info.expires_at}")
        self.console.print(f" • 功能: {', '.join(info.features)}")
        return True

    def remove_license(self) -> bool:
        try:
            if self.core.config.LICENSE_FILE.exists():
                self.core.config.LICENSE_FILE.unlink()
            if self.core.config.CONFIG_FILE.exists():
                self.core.config.CONFIG_FILE.unlink()
        except Exception as exc:
            self.console.print(f"❌ [red]License removal failed: {exc}[/red]")
            return False

        self.console.print("✅ 已移除许可证，回退到开源版本")
        return True

    def show_status(self) -> None:
        info = self.validator.check_license_status()

        self.console.rule("SAGE 许可证状态")
        self.console.print(f"类型: {info.get('type', 'unknown')}")
        self.console.print(f"来源: {info.get('source', 'unknown')}")

        if info.get("has_license"):
            expires = info.get("expires_at", "N/A")
            features = info.get("features", [])
            self.console.print(f"到期时间: {expires}")
            self.console.print(f"功能: {', '.join(features) if features else '无'}")

            if expires and expires not in ("N/A", None):
                try:
                    expires_dt = datetime.fromisoformat(expires)
                    days_left = (expires_dt - datetime.now()).days
                    if days_left < 30:
                        self.console.print(f"⚠️  许可证将在 {days_left} 天后过期")
                except Exception:
                    pass
        else:
            self.console.print(
                "功能: "
                + ", ".join(LicenseConfig.OPEN_SOURCE_FEATURES)
            )
            self.console.print("💡 商业版咨询: intellistream@outlook.com")


__all__ = ["LicenseClient"]
