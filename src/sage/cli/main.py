#!/usr/bin/env python3
"""Main-repo owned CLI entrypoint for SAGE."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from importlib.metadata import entry_points

from sage._version import __version__
from sage.cli.commands.apps.chat import add_chat_parser, add_index_parser
from sage.foundation import SagePorts, get_user_paths
from sage.runtime import get_runtime_backend
from sage.serving import (
    SageServeConfig,
    build_sagellm_gateway_command,
    infer_module_availability,
    probe_gateway,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sage",
        description="SAGE — stream-first inference service system",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="Show SAGE version information")
    sub.add_parser("status", help="Show local SAGE status summary")
    sub.add_parser("doctor", help="Run a lightweight environment diagnostic")

    sub.add_parser("verify", help="Run a built-in core surface smoke verification")

    runtime_parser = sub.add_parser("runtime", help="Inspect runtime backend status")
    runtime_sub = runtime_parser.add_subparsers(dest="runtime_command")
    runtime_sub.add_parser("nodes", help="List visible runtime nodes")

    serve_parser = sub.add_parser("serve", help="Serving integration helpers")
    serve_sub = serve_parser.add_subparsers(dest="serve_command")
    gateway = serve_sub.add_parser("gateway", help="Print or probe the gateway contract")
    gateway.add_argument("--host", default="127.0.0.1")
    gateway.add_argument("--port", type=int, default=SagePorts.SAGELLM_GATEWAY)
    gateway.add_argument("--model", default=None)
    gateway.add_argument("--control-plane", action="store_true")
    gateway.add_argument("--probe", action="store_true")
    gateway.add_argument("--json", action="store_true")

    add_chat_parser(sub)
    add_index_parser(sub)
    _load_cli_plugins(sub)

    return parser


def _load_cli_plugins(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Load external CLI plugins from the ``sage.cli.plugins`` entry point group."""
    for ep in sorted(entry_points(group="sage.cli.plugins"), key=lambda item: item.name):
        try:
            register_command = ep.load()
            register_command(subparsers)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to load SAGE CLI plugin '{ep.name}' from '{ep.value}': {exc}"
            ) from exc


def _print_status() -> int:
    paths = get_user_paths()
    gateway_cfg = SageServeConfig()
    probe = probe_gateway(gateway_cfg)

    print("SAGE status")
    print(f"- version        : {__version__}")
    print(f"- config dir     : {paths.config_dir}")
    print(f"- data dir       : {paths.data_dir}")
    print(f"- state dir      : {paths.state_dir}")
    print(f"- gateway module : {'available' if infer_module_availability() else 'missing'}")
    if probe.ok:
        print(f"- gateway        : healthy ({probe.url})")
    else:
        error = probe.error or f"status={probe.status_code}"
        print(f"- gateway        : unavailable ({error})")
    return 0


def _print_doctor() -> int:
    gateway_module = infer_module_availability()
    print("SAGE doctor")
    print(f"- sagellm_gateway importable : {gateway_module}")
    try:
        backend = get_runtime_backend()
        nodes = backend.list_nodes()
        print(f"- runtime backend            : ok ({len(nodes)} node(s))")
    except Exception as exc:  # noqa: BLE001
        print(f"- runtime backend            : unavailable ({exc})")
    return 0


def _print_version() -> int:
    print(f"SAGE {__version__}")
    return 0


def _runtime_nodes() -> int:
    backend = get_runtime_backend()
    nodes = backend.list_nodes()
    print(
        json.dumps(
            [
                {
                    "node_id": node.node_id,
                    "address": node.address,
                    "is_schedulable": node.is_schedulable,
                    "resource_summary": node.resource_summary,
                }
                for node in nodes
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _serve_gateway(args: argparse.Namespace) -> int:
    config = SageServeConfig(
        host=args.host,
        port=args.port,
        model=args.model,
        enable_control_plane=args.control_plane,
    )
    if args.probe:
        result = probe_gateway(config)
        payload = {
            "ok": result.ok,
            "url": result.url,
            "status_code": result.status_code,
            "payload": result.payload,
            "error": result.error,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload)
        return 0 if result.ok else 1

    payload = {
        "command": build_sagellm_gateway_command(config),
        "base_url": config.base_url,
        "health_url": config.health_url,
        "log_file": str(config.log_file),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload)
    return 0


def _verify_core() -> int:
    print("SAGE verify")
    print(f"- version : {__version__}")
    try:
        import sage.cli  # noqa: F401
        import sage.foundation  # noqa: F401
        import sage.runtime  # noqa: F401
        import sage.serving  # noqa: F401
        import sage.stream  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"- core    : failed ({exc})")
        return 1
    print("- core    : ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    parsed_argv = list(argv) if argv is not None else None
    args, unknown = parser.parse_known_args(parsed_argv)

    if args.command is None:
        return _print_status()
    if args.command == "version":
        return _print_version()
    if args.command == "status":
        return _print_status()
    if args.command == "doctor":
        return _print_doctor()
    if args.command == "verify":
        return _verify_core()
    if args.command == "runtime" and args.runtime_command == "nodes":
        return _runtime_nodes()
    if args.command == "serve" and args.serve_command == "gateway":
        return _serve_gateway(args)
    if hasattr(args, "_handler"):
        if hasattr(args, "studio_args") and unknown:
            args.studio_args = list(args.studio_args or []) + list(unknown)
        return args._handler(args)
    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
