"""
Studio routes (migrated from sage-studio backend) re-exported via Gateway.

We reuse the existing FastAPI app defined in
`sage.studio.config.backend.api` and attach its routes directly to the
Gateway application so we only need a single service (port 8000).

Only path-operation routes are imported; non-HTTP routes are ignored.
Root/health routes from the backend are skipped to avoid conflicts with
Gateway's own endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.routing import APIRoute

from sage.studio.config.backend import api as studio_api

studio_router = APIRouter()


for route in studio_api.app.routes:
    # Only copy standard HTTP routes
    if not isinstance(route, APIRoute):
        continue

    # Skip backend root/health to avoid clashing with Gateway
    if route.path in {"/", "/health"}:
        continue

    studio_router.add_api_route(
        path=route.path,
        endpoint=route.endpoint,
        methods=list(route.methods or []),
        name=route.name,
        response_model=route.response_model,
        dependencies=route.dependencies,
        response_model_exclude_none=route.response_model_exclude_none,
    )
