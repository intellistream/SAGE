"""Utilities for managing SAGE enterprise feature enablement."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sage.tools.utils.env import find_project_root

ENTERPRISE_PACKAGES: List[str] = [
    "intellistream-sage-kernel[enterprise]",
    "intellistream-sage-middleware[enterprise]",
]
_ENTERPRISE_FEATURES = {
    "high-performance",
    "enterprise-db",
    "advanced-analytics",
    "enterprise",
}


class EnterpriseManager:
    """Encapsulates enterprise license inspection and installation logic."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or find_project_root()
        self.license_validator = self._init_license_system()

    # ------------------------------------------------------------------
    # License helpers
    # ------------------------------------------------------------------
    def _init_license_system(self):
        if not self.project_root:
            return None

        license_tools_dir = self.project_root / "tools" / "license"
        if not license_tools_dir.exists():
            return None

        for extra in (license_tools_dir, license_tools_dir / "shared"):
            if extra.exists():
                path_str = str(extra)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)

        try:  # pragma: no cover - dependent on enterprise addons
            from shared.validation import LicenseValidator

            return LicenseValidator()
        except Exception:
            return None

    def check_license_status(self) -> Dict[str, Any]:
        """Return current enterprise license status details."""

        if not self.license_validator:
            return {
                "has_license": False,
                "type": "open-source",
                "features": ["basic-functionality"],
                "commercial_enabled": False,
                "message": "License system not available",
                "source": "none",
            }

        try:
            status = self.license_validator.check_license_status()
            features = self.license_validator.get_license_features()
            has_valid = self.license_validator.has_valid_license()

            commercial_enabled = bool(_ENTERPRISE_FEATURES.intersection(features)) and has_valid

            return {
                "has_license": status.get("has_license", False),
                "type": status.get("type", "open-source"),
                "source": status.get("source", "none"),
                "features": features,
                "commercial_enabled": commercial_enabled,
                "expires_at": status.get("expires_at"),
                "message": "License validation successful",
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "has_license": False,
                "type": "open-source",
                "features": ["basic-functionality"],
                "commercial_enabled": False,
                "message": f"License check failed: {exc}",
                "source": "error",
            }

    # ------------------------------------------------------------------
    # Installation helpers
    # ------------------------------------------------------------------
    def install_enterprise_features(
        self,
        license_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Install enterprise extras for the core SAGE packages."""

        if license_key:
            os.environ["SAGE_LICENSE_KEY"] = license_key

        license_status = self.check_license_status()
        log: List[str] = []

        if not license_status["commercial_enabled"]:
            log.append("No valid commercial license available; aborting installation")
            return {
                "status": "failed",
                "message": "Enterprise features require a valid commercial license.",
                "license_status": license_status,
                "results": [],
                "installed_packages": 0,
                "total_packages": len(ENTERPRISE_PACKAGES),
                "logs": log,
            }

        results: List[Dict[str, Any]] = []
        for package in ENTERPRISE_PACKAGES:
            log.append(f"Installing {package}…")
            try:
                completed = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                )
            except Exception as exc:  # pragma: no cover - subprocess failure
                results.append({
                    "package": package,
                    "status": "error",
                    "error": str(exc),
                })
                log.append(f"Error installing {package}: {exc}")
                continue

            if completed.returncode == 0:
                results.append({"package": package, "status": "success"})
                log.append(f"Successfully installed {package}")
            else:
                results.append(
                    {
                        "package": package,
                        "status": "failed",
                        "error": completed.stderr.strip(),
                    }
                )
                log.append(f"Failed to install {package}")

        successful = sum(1 for r in results if r["status"] == "success")
        status = "success" if successful else "failed"

        return {
            "status": status,
            "installed_packages": successful,
            "total_packages": len(ENTERPRISE_PACKAGES),
            "results": results,
            "license_status": license_status,
            "logs": log,
        }

    def validate_enterprise_installation(self) -> Dict[str, Any]:
        """Validate that enterprise modules can be imported."""

        modules = (
            "sage.middleware.enterprise",
            "sage.kernel.enterprise",
            "sage.apps.enterprise",
        )

        details: List[Dict[str, Any]] = []
        available = 0

        for module_name in modules:
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                importlib.import_module(module_name)
            except ImportError as exc:
                details.append(
                    {
                        "component": module_name,
                        "status": "not_available",
                        "error": str(exc),
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive
                details.append(
                    {
                        "component": module_name,
                        "status": "error",
                        "error": str(exc),
                    }
                )
            else:
                details.append(
                    {
                        "component": module_name,
                        "status": "available",
                    }
                )
                available += 1

        return {
            "total_components": len(details),
            "available_components": available,
            "components": details,
            "license_status": self.check_license_status(),
        }

    def get_installation_command(self, mode: str = "standard") -> str:
        """Return the recommended pip command for the requested mode."""

        if mode == "enterprise":
            return "pip install -r scripts/requirements/requirements-commercial.txt"
        if mode == "dev":
            return "pip install -e .[enterprise]"
        if mode == "individual":
            return (
                "pip install intellistream-sage-kernel[enterprise] "
                "intellistream-sage-middleware[enterprise] "
                "intellistream-sage-userspace[enterprise]"
            )
        return "pip install -r scripts/requirements/requirements.txt"


# ----------------------------------------------------------------------
# Module level helpers
# ----------------------------------------------------------------------

def check_enterprise_features() -> Dict[str, Any]:
    manager = EnterpriseManager()
    license_status = manager.check_license_status()
    validation = manager.validate_enterprise_installation()
    summary = {
        "enterprise_enabled": license_status.get("commercial_enabled", False),
        "components_available": f"{validation['available_components']}/{validation['total_components']}",
    }
    return {
        "license": license_status,
        "installation": validation,
        "summary": summary,
    }


def install_enterprise(license_key: Optional[str] = None) -> Dict[str, Any]:
    manager = EnterpriseManager()
    return manager.install_enterprise_features(license_key)


__all__ = [
    "ENTERPRISE_PACKAGES",
    "EnterpriseManager",
    "check_enterprise_features",
    "install_enterprise",
]
