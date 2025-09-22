"""
License Configuration
Constants and configuration for license management
"""

from pathlib import Path


class LicenseConfig:
    """License configuration constants"""

    # Directories
    SAGE_CONFIG_DIR = Path.home() / ".sage"
    LICENSE_FILE = SAGE_CONFIG_DIR / "license.key"
    CONFIG_FILE = SAGE_CONFIG_DIR / "config.json"
    GENERATED_LICENSES_FILE = SAGE_CONFIG_DIR / "generated_licenses.json"

    # License format constants
    PREFIX = "SAGE"
    COMMERCIAL_TYPE = "COMM"
    DEFAULT_VALIDITY_DAYS = 365

    # Feature definitions
    COMMERCIAL_FEATURES = [
        "high-performance",
        "enterprise-db",
        "advanced-analytics",
        "priority-support",
    ]

    OPEN_SOURCE_FEATURES = ["basic-functionality", "community-support"]
