"""Edge aggregator app factory.

This module provides a minimal FastAPI shell that can optionally mount the LLM gateway
at `/` (default) or under a configurable prefix while keeping edge-level health/ready
endpoints available.
"""

from __future__ import annotations

from fastapi import FastAPI

EDGE_SERVICE_NAME = "SAGE Edge"


def _attach_health_routes(app: FastAPI, llm_prefix: str | None, llm_mounted: bool) -> None:
    """Attach /healthz and /readyz endpoints to the given app (idempotent)."""
    existing_paths = {route.path for route in app.router.routes}
    if "/healthz" not in existing_paths:

        @app.get("/healthz", include_in_schema=False)
        async def healthz():
            return {
                "status": "ok",
                "service": EDGE_SERVICE_NAME,
                "llm_mounted": llm_mounted,
                "llm_prefix": llm_prefix or "/",
            }

    if "/readyz" not in existing_paths:

        @app.get("/readyz", include_in_schema=False)
        async def readyz():
            return {
                "status": "ready",
                "service": EDGE_SERVICE_NAME,
                "llm_mounted": llm_mounted,
                "llm_prefix": llm_prefix or "/",
            }


def create_app(*, mount_llm: bool = True, llm_prefix: str | None = None) -> FastAPI:
    """Create an edge app.

    Args:
        mount_llm: Whether to mount the LLM gateway application.
        llm_prefix: Optional mount path for the LLM gateway (default `/`).

    Returns:
        A FastAPI application configured with health/ready endpoints and, optionally,
        the mounted LLM gateway application.
    """
    mount_path = llm_prefix or "/"

    if mount_llm and mount_path == "/":
        # Use the gateway app directly to preserve /v1/* while adding edge health endpoints.
        from sage.llm.gateway.server import app as gateway_app

        _attach_health_routes(gateway_app, llm_prefix=None, llm_mounted=True)
        gateway_app.state.edge_mount_path = mount_path
        return gateway_app

    edge_app = FastAPI(title=EDGE_SERVICE_NAME, version="0.1.0")
    _attach_health_routes(
        edge_app, llm_prefix=mount_path if mount_llm else None, llm_mounted=mount_llm
    )

    if mount_llm:
        from sage.llm.gateway.server import app as gateway_app

        edge_app.mount(mount_path, gateway_app)
        edge_app.state.edge_mount_path = mount_path

    return edge_app
