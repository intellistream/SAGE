"""
SAGE Enterprise Installation Manager

This module provides utilities for installing and validating SAGE enterprise features
based on license status. It integrates with the existing license management system.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class SAGEEnterpriseInstaller:
    """Manages enterprise feature installation and validation."""

    def __init__(self):
        self.project_root = self._find_project_root()
        self.license_validator = None
        self._init_license_system()

    def _find_project_root(self) -> Optional[Path]:
        """Find SAGE project root."""
        current = Path.cwd()

        # Check common locations
        possible_roots = [
            current,
            current.parent,
            current.parent.parent,
            Path(__file__).parent.parent.parent,  # From package location
            Path(os.environ.get("SAGE_PROJECT_ROOT", "")),
        ]

        for root in possible_roots:
            if root and root.exists():
                if (root / "tools" / "license").exists() and (
                    root / "packages"
                ).exists():
                    return root

        return None

    def _init_license_system(self):
        """Initialize license validation system."""
        if not self.project_root:
            return

        license_tools_dir = self.project_root / "tools" / "license"
        if not license_tools_dir.exists():
            return

        # Add license tools to path
        sys.path.insert(0, str(license_tools_dir))
        sys.path.insert(0, str(license_tools_dir / "shared"))

        try:
            from shared.validation import LicenseValidator

            self.license_validator = LicenseValidator()
        except ImportError:
            pass

    def check_license_status(self) -> Dict[str, Any]:
        """Check current license status."""
        if not self.license_validator:
            return {
                "has_license": False,
                "type": "open-source",
                "features": ["basic-functionality"],
                "commercial_enabled": False,
                "message": "License system not available",
            }

        try:
            status = self.license_validator.check_license_status()
            features = self.license_validator.get_license_features()
            has_valid = self.license_validator.has_valid_license()

            # Check for enterprise features
            enterprise_features = [
                "high-performance",
                "enterprise-db",
                "advanced-analytics",
                "enterprise",
            ]
            commercial_enabled = has_valid and any(
                f in features for f in enterprise_features
            )

            return {
                "has_license": status.get("has_license", False),
                "type": status.get("type", "open-source"),
                "source": status.get("source", "none"),
                "features": features,
                "commercial_enabled": commercial_enabled,
                "expires_at": status.get("expires_at"),
                "message": "License validation successful",
            }
        except Exception as e:
            return {
                "has_license": False,
                "type": "open-source",
                "features": ["basic-functionality"],
                "commercial_enabled": False,
                "message": f"License check failed: {e}",
            }

    def install_enterprise_features(self, license_key: str = None) -> Dict[str, Any]:
        """Install enterprise features if license allows."""
        # Set license key if provided
        if license_key:
            os.environ["SAGE_LICENSE_KEY"] = license_key

        # Check license
        license_status = self.check_license_status()

        if not license_status["commercial_enabled"]:
            return {
                "status": "failed",
                "message": "No valid commercial license found. Enterprise features require a valid license.",
                "license_status": license_status,
            }

        print("✅ Valid commercial license found")
        print(f"📄 Licensed features: {', '.join(license_status['features'])}")

        # Install enterprise packages
        enterprise_packages = [
            "intellistream-sage-kernel[enterprise]",
            "intellistream-sage-middleware[enterprise]",
        ]

        results = []
        for package in enterprise_packages:
            print(f"📦 Installing {package}...")

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print(f"✅ Successfully installed {package}")
                    results.append({"package": package, "status": "success"})
                else:
                    print(f"❌ Failed to install {package}")
                    results.append(
                        {"package": package, "status": "failed", "error": result.stderr}
                    )
            except Exception as e:
                print(f"❌ Error installing {package}: {e}")
                results.append(
                    {"package": package, "status": "failed", "error": str(e)}
                )

        successful = sum(1 for r in results if r["status"] == "success")

        return {
            "status": "success" if successful > 0 else "failed",
            "installed_packages": successful,
            "total_packages": len(enterprise_packages),
            "results": results,
            "license_status": license_status,
        }

    def validate_enterprise_installation(self) -> Dict[str, Any]:
        """Validate that enterprise features are properly installed."""
        validation_tests = [
            {
                "name": "sage.middleware.enterprise",
                "test": "from sage.middleware.enterprise import sage_db",
                "description": "Enterprise database middleware",
            },
        ]

        results = []
        for test in validation_tests:
            try:
                exec(test["test"])
                results.append(
                    {
                        "component": test["name"],
                        "status": "available",
                        "description": test["description"],
                    }
                )
            except ImportError as e:
                results.append(
                    {
                        "component": test["name"],
                        "status": "not_available",
                        "description": test["description"],
                        "error": str(e),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "component": test["name"],
                        "status": "error",
                        "description": test["description"],
                        "error": str(e),
                    }
                )

        available_count = sum(1 for r in results if r["status"] == "available")

        return {
            "total_components": len(results),
            "available_components": available_count,
            "license_status": self.check_license_status(),
            "components": results,
        }

    def get_installation_command(self, mode: str = "standard") -> str:
        """Get the appropriate installation command based on mode."""
        if mode == "enterprise":
            # requirements-commercial.txt的位置被挪到scripts/requirements里边了
            return "pip install -r scripts/requirements/requirements-commercial.txt"
        elif mode == "dev":
            return "pip install -e .[enterprise]"
        elif mode == "individual":
            return "pip install intellistream-sage-kernel[enterprise] intellistream-sage-middleware[enterprise] intellistream-sage-userspace[enterprise]"
        else:
            return "pip install -r scripts/requirements/requirements.txt"


def check_enterprise_features() -> Dict[str, Any]:
    """Convenience function to check enterprise features."""
    installer = SAGEEnterpriseInstaller()
    license_status = installer.check_license_status()
    validation = installer.validate_enterprise_installation()

    return {
        "license": license_status,
        "installation": validation,
        "summary": {
            "enterprise_enabled": license_status["commercial_enabled"],
            "components_available": f"{validation['available_components']}/{validation['total_components']}",
        },
    }


def install_enterprise(license_key: str = None) -> Dict[str, Any]:
    """Convenience function to install enterprise features."""
    installer = SAGEEnterpriseInstaller()
    return installer.install_enterprise_features(license_key)


def main():
    """Command line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Enterprise Installation Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check status
    check_parser = subparsers.add_parser(
        "check", help="Check license and installation status"
    )

    # Install enterprise
    install_parser = subparsers.add_parser(
        "install", help="Install enterprise features"
    )
    install_parser.add_argument("--license-key", help="License key to use")

    # Validate installation
    validate_parser = subparsers.add_parser(
        "validate", help="Validate enterprise installation"
    )

    # Show installation commands
    commands_parser = subparsers.add_parser(
        "commands", help="Show installation commands"
    )
    commands_parser.add_argument(
        "--mode",
        choices=["standard", "enterprise", "dev", "individual"],
        default="enterprise",
        help="Installation mode",
    )

    args = parser.parse_args()

    installer = SAGEEnterpriseInstaller()

    if args.command == "check":
        status = check_enterprise_features()
        print("\n🔍 SAGE Enterprise Status")
        print("=" * 40)
        print(f"License Type: {status['license']['type']}")
        print(
            f"Enterprise Enabled: {'✅ Yes' if status['license']['commercial_enabled'] else '❌ No'}"
        )
        print(f"Available Features: {', '.join(status['license']['features'])}")
        print(f"Components Available: {status['summary']['components_available']}")

    elif args.command == "install":
        result = installer.install_enterprise_features(args.license_key)
        print(f"\n📦 Installation Result: {result['status']}")
        if result["status"] == "success":
            print(
                f"✅ Installed {result['installed_packages']}/{result['total_packages']} packages"
            )
        else:
            print("❌ Installation failed - check license status")

    elif args.command == "validate":
        validation = installer.validate_enterprise_installation()
        print("\n🧪 Enterprise Installation Validation")
        print("=" * 45)
        for component in validation["components"]:
            status_icon = "✅" if component["status"] == "available" else "❌"
            print(f"{status_icon} {component['component']}: {component['description']}")

    elif args.command == "commands":
        cmd = installer.get_installation_command(args.mode)
        print(f"\n💡 Installation command for {args.mode} mode:")
        print(f"   {cmd}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
