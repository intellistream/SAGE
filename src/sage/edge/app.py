"""Edge service app factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.edge.core import EDGE_SERVICE_NAME, normalize_mount_path, probe_payload

if TYPE_CHECKING:
    from fastapi import FastAPI


def _require_fastapi() -> type[Any]:
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "sage.edge requires FastAPI support. Install 'isage[serving-edge]' or 'isage[full]'."
        ) from exc
    return FastAPI


def _attach_health_routes(app: Any, llm_prefix: str | None, llm_mounted: bool) -> None:
    """Attach edge-level health and readiness probes."""
    existing_paths = {route.path for route in app.router.routes}
    if "/healthz" not in existing_paths:

        @app.get("/healthz", include_in_schema=False)
        async def healthz() -> dict[str, str | bool]:
            return probe_payload("ok", llm_mounted, llm_prefix)

    if "/readyz" not in existing_paths:

        @app.get("/readyz", include_in_schema=False)
        async def readyz() -> dict[str, str | bool]:
            return probe_payload("ready", llm_mounted, llm_prefix)


def create_app(
    *,
    mount_llm: bool = True,
    llm_prefix: str | None = None,
    llm_app: Any | None = None,
) -> FastAPI:
    """Create the edge shell with optional mounted gateway application."""
    fastapi_cls = _require_fastapi()
    mount_path = normalize_mount_path(llm_prefix)

    edge_app = fastapi_cls(title=EDGE_SERVICE_NAME, version="1")
    _attach_health_routes(edge_app, llm_prefix=llm_prefix, llm_mounted=mount_llm)

    if not mount_llm:
        edge_app.state.edge_mount_path = mount_path
        return edge_app

    if llm_app is None:
        raise RuntimeError("mount_llm requires explicit llm_app injection")

    if mount_path == "/":
        edge_app.include_router(llm_app.router)
    else:
        edge_app.mount(mount_path, llm_app)

    edge_app.state.edge_mount_path = mount_path
    return edge_app
