"""Framework-agnostic edge runtime helpers."""

from __future__ import annotations

EDGE_SERVICE_NAME = "SAGE Edge"


def normalize_mount_path(llm_prefix: str | None) -> str:
    """Normalize and validate the gateway mount path."""
    if llm_prefix is None:
        return "/"

    prefix = llm_prefix.strip()
    if prefix == "":
        return "/"
    if not prefix.startswith("/"):
        raise ValueError("llm_prefix must start with '/'")

    if prefix != "/":
        prefix = prefix.rstrip("/")
        if prefix == "":
            return "/"

    return prefix


def probe_payload(status: str, llm_mounted: bool, llm_prefix: str | None) -> dict[str, str | bool]:
    """Build the standardized edge probe payload."""
    return {
        "status": status,
        "service": EDGE_SERVICE_NAME,
        "llm_mounted": llm_mounted,
        "llm_prefix": llm_prefix or "/",
    }
