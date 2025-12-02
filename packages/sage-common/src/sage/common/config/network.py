"""Network detection and mirror configuration for SAGE.

This module provides automatic detection of network region (China mainland vs international)
and configures HuggingFace mirrors accordingly at runtime.
"""

from __future__ import annotations

import functools
import logging
import os
import urllib.request
from typing import Literal

logger = logging.getLogger(__name__)

# HuggingFace mirror URL for China mainland users
HF_MIRROR_CN = "https://hf-mirror.com"

# Detection endpoints with country code response
_DETECTION_ENDPOINTS = [
    "https://ipinfo.io/country",
    "https://ifconfig.co/country-iso",
    "https://ipapi.co/country/",
]


def _fetch_country_code(url: str, timeout: float = 3.0) -> str | None:
    """Fetch country code from a detection endpoint.

    Args:
        url: The endpoint URL that returns a country code.
        timeout: Request timeout in seconds.

    Returns:
        Two-letter country code (e.g., "CN", "US") or None on failure.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            code = response.read().decode("utf-8").strip().upper()
            # Validate that it looks like a country code
            if len(code) == 2 and code.isalpha():
                return code
    except Exception:  # noqa: BLE001 - best effort detection
        pass
    return None


@functools.lru_cache(maxsize=1)
def detect_china_mainland() -> bool:
    """Detect if the current network is in China mainland.

    Uses multiple public IP geolocation services with fallback.
    Results are cached for the lifetime of the process.

    Returns:
        True if detected in China mainland, False otherwise.
    """
    for endpoint in _DETECTION_ENDPOINTS:
        code = _fetch_country_code(endpoint)
        if code:
            is_china = code == "CN"
            logger.debug(
                "Network detection via %s: country=%s, is_china=%s", endpoint, code, is_china
            )
            return is_china
    # Fallback: check locale settings
    for env_var in ("LANG", "LC_ALL", "LC_CTYPE"):
        value = os.environ.get(env_var, "")
        if value.startswith("zh_"):
            logger.debug(
                "Network detection via locale %s=%s: assuming China mainland", env_var, value
            )
            return True
    logger.debug("Network detection failed to determine region, assuming international")
    return False


def get_hf_endpoint() -> str | None:
    """Get the appropriate HuggingFace endpoint based on network region.

    Returns:
        HF_MIRROR_CN for China mainland users, None for international users.
    """
    if detect_china_mainland():
        return HF_MIRROR_CN
    return None


def configure_hf_mirror(force: bool = False) -> str | None:
    """Configure HuggingFace mirror based on network detection.

    Sets the HF_ENDPOINT environment variable if needed.
    Skips configuration if HF_ENDPOINT is already set (unless force=True).

    Args:
        force: If True, override existing HF_ENDPOINT setting.

    Returns:
        The configured HF_ENDPOINT value, or None if using default.
    """
    current = os.environ.get("HF_ENDPOINT")

    if current and not force:
        logger.debug("HF_ENDPOINT already set to %s, skipping auto-configuration", current)
        return current

    endpoint = get_hf_endpoint()
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
        logger.info("Auto-configured HF_ENDPOINT=%s (China mainland network detected)", endpoint)
        return endpoint
    else:
        # Don't override if user has set it
        if current and not force:
            return current
        # Clear any previous setting if forcing and not in China
        if force and "HF_ENDPOINT" in os.environ:
            del os.environ["HF_ENDPOINT"]
        logger.debug("Using default HuggingFace endpoint (international network)")
        return None


def ensure_hf_mirror_configured() -> None:
    """Ensure HuggingFace mirror is configured based on network region.

    This is a convenience function that should be called early in CLI commands
    that need to download models from HuggingFace.
    """
    configure_hf_mirror(force=False)


NetworkRegion = Literal["china", "international"]


def get_network_region() -> NetworkRegion:
    """Get the detected network region.

    Returns:
        "china" for China mainland, "international" otherwise.
    """
    return "china" if detect_china_mainland() else "international"


__all__ = [
    "HF_MIRROR_CN",
    "detect_china_mainland",
    "get_hf_endpoint",
    "configure_hf_mirror",
    "ensure_hf_mirror_configured",
    "get_network_region",
    "NetworkRegion",
]
