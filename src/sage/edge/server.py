"""Edge server entrypoint."""

from __future__ import annotations

import argparse
import importlib
import os
from typing import Any

from sage.edge.app import create_app
from sage.foundation.config.ports import SagePorts

_DEFAULT_GATEWAY_APP_SPECS = (
    "sagellm_gateway.server:app",
    "sagellm_gateway:app",
    "sage.llm.gateway.server:app",
)


def _iter_gateway_app_specs() -> tuple[str, ...]:
    override = os.getenv("SAGE_EDGE_GATEWAY_APP")
    if not override:
        return _DEFAULT_GATEWAY_APP_SPECS
    return (override, *[spec for spec in _DEFAULT_GATEWAY_APP_SPECS if spec != override])


def _load_attr(module_spec: str) -> Any:
    module_name, _, attr_name = module_spec.partition(":")
    if not module_name or not attr_name:
        raise ImportError(f"Invalid gateway app spec: {module_spec}")

    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise ImportError(f"Gateway module '{module_name}' does not export '{attr_name}'") from exc


def _load_llm_gateway_app() -> Any:
    """Load the external gateway ASGI app from known integration entrypoints."""
    failures: list[str] = []
    for module_spec in _iter_gateway_app_specs():
        try:
            return _load_attr(module_spec)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{module_spec} -> {exc}")

    joined = "; ".join(failures)
    raise ImportError(f"Unable to load a gateway ASGI app. Tried: {joined}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SAGE edge aggregator")
    parser.add_argument(
        "--host",
        default=os.getenv("SAGE_EDGE_HOST", "0.0.0.0"),
        help="Host interface to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SAGE_EDGE_PORT", SagePorts.EDGE_DEFAULT)),
        help="Port to bind (defaults to SagePorts.EDGE_DEFAULT)",
    )
    parser.add_argument(
        "--llm-prefix",
        type=str,
        default=os.getenv("SAGE_EDGE_LLM_PREFIX"),
        help="Optional path prefix for gateway routes (default: /)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Start edge shell without mounting an LLM gateway",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SAGE_EDGE_LOG_LEVEL", "info"),
        help="Uvicorn log level (debug, info, warning, error)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    mount_llm = not args.no_llm
    llm_app = _load_llm_gateway_app() if mount_llm else None
    app = create_app(mount_llm=mount_llm, llm_prefix=args.llm_prefix, llm_app=llm_app)

    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "sage.edge requires uvicorn support. Install 'isage[serving-edge]' or 'isage[full]'."
        ) from exc

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
