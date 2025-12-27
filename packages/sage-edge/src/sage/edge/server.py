"""Edge server entrypoint.

Supports running as `python -m sage.edge.server` or via the `sage-edge` console script.
"""

from __future__ import annotations

import argparse
import os

import uvicorn

from sage.common.config.ports import SagePorts
from sage.edge.app import create_app


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
        help="Optional mount prefix for the LLM gateway (default: /)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Start edge shell without mounting the LLM gateway",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SAGE_EDGE_LOG_LEVEL", "info"),
        help="Uvicorn log level (debug, info, warning, error)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    app = create_app(mount_llm=not args.no_llm, llm_prefix=args.llm_prefix)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
