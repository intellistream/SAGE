from __future__ import annotations

import argparse

from .rpc import DEFAULT_LANGCHAIN_RPC_PORT, serve_langchain_rpc_worker


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a LangChain RPC worker for distributed shared-workload experiments."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_LANGCHAIN_RPC_PORT)
    parser.add_argument("--node-id", default="unknown-node")
    args = parser.parse_args()

    serve_langchain_rpc_worker(host=args.host, port=args.port, node_id=args.node_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
