# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""SAGE Gateway CLI entry point.

This module allows running the Gateway directly via `python -m sage.gateway`.
"""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from sage.common.config.ports import SagePorts


def main() -> int:
    """Run SAGE Gateway server."""
    parser = argparse.ArgumentParser(
        description="SAGE Gateway - Unified API Gateway",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=SagePorts.GATEWAY_DEFAULT,
        help="Port to bind the server to",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level",
    )
    parser.add_argument(
        "--enable-control-plane",
        action="store_true",
        default=True,
        help="Enable Control Plane engine management",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    # Set environment variables for the app
    import os

    os.environ["SAGE_GATEWAY_ENABLE_CONTROL_PLANE"] = str(args.enable_control_plane).lower()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("sage.gateway")
    logger.info(f"Starting SAGE Gateway on {args.host}:{args.port}")
    logger.info(f"Control Plane: {'enabled' if args.enable_control_plane else 'disabled'}")

    try:
        uvicorn.run(
            "sage.gateway.server:app",
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            reload=args.reload,
        )
        return 0
    except Exception as e:
        logger.error(f"Failed to start Gateway: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
