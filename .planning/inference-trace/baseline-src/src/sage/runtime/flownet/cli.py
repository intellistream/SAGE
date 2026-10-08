from __future__ import annotations

import argparse
import sys

from sage.runtime.flownet.node import cli as node_cli

_ROUTE_PREFIXES: dict[tuple[str, str], list[str]] = {
    ("node", "start"): ["start"],
    ("node", "inspect"): ["inspect"],
    ("node", "join"): ["join"],
    ("node", "leave"): ["leave"],
    ("node", "stop"): ["stop"],
    ("node", "restart"): ["restart"],
    ("cluster", "plan"): ["cluster", "plan"],
    ("cluster", "start"): ["cluster", "start"],
    ("cluster", "up"): ["cluster", "up"],
    ("cluster", "down"): ["cluster", "down"],
    ("cluster", "inspect"): ["cluster", "inspect"],
    ("cluster", "status"): ["cluster", "status"],
    ("cluster", "join"): ["cluster", "join"],
    ("cluster", "leave"): ["cluster", "leave"],
    ("cluster", "reconcile"): ["cluster", "reconcile"],
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flownet",
        description="FlowNet infrastructure CLI for node and cluster lifecycle/diagnostics.",
    )
    subparsers = parser.add_subparsers(dest="group", required=True)

    node_parser = subparsers.add_parser(
        "node",
        help="Node lifecycle and diagnostics.",
    )
    node_subparsers = node_parser.add_subparsers(dest="command", required=True)
    node_subparsers.add_parser(
        "start",
        add_help=False,
        help="Start a node runtime.",
    )
    node_subparsers.add_parser(
        "inspect",
        add_help=False,
        help="Inspect a running node.",
    )
    node_subparsers.add_parser(
        "join",
        add_help=False,
        help="Start local node runtime and join existing seeds.",
    )
    node_subparsers.add_parser(
        "leave",
        add_help=False,
        help="Leave membership from a running node.",
    )
    node_subparsers.add_parser(
        "stop",
        add_help=False,
        help="Stop a running node.",
    )
    node_subparsers.add_parser(
        "restart",
        add_help=False,
        help="Restart local node runtime.",
    )

    cluster_parser = subparsers.add_parser(
        "cluster",
        help="Cluster inventory lifecycle and diagnostics.",
    )
    cluster_subparsers = cluster_parser.add_subparsers(dest="command", required=True)
    cluster_subparsers.add_parser(
        "plan",
        add_help=False,
        help="Resolve inventory into normalized node plan.",
    )
    cluster_subparsers.add_parser(
        "start",
        add_help=False,
        help="Start one cluster node from inventory by node_id.",
    )
    cluster_subparsers.add_parser(
        "up",
        add_help=False,
        help="Auto-ssh bootstrap all nodes from inventory.",
    )
    cluster_subparsers.add_parser(
        "down",
        add_help=False,
        help="Auto-ssh stop all nodes from inventory.",
    )
    cluster_subparsers.add_parser(
        "inspect",
        add_help=False,
        help="Inspect all or selected nodes from inventory.",
    )
    cluster_subparsers.add_parser(
        "status",
        add_help=False,
        help="Alias of cluster inspect --view cluster.",
    )
    cluster_subparsers.add_parser(
        "join",
        add_help=False,
        help="Hot-join one inventory node.",
    )
    cluster_subparsers.add_parser(
        "leave",
        add_help=False,
        help="Leave one inventory node with soft/hard mode.",
    )
    cluster_subparsers.add_parser(
        "reconcile",
        add_help=False,
        help="Compare desired/observed and optionally repair drift.",
    )
    return parser


def _resolve_forward_args(
    *,
    group: str,
    command: str,
    remainder: list[str],
) -> list[str]:
    if group == "cluster" and command == "status":
        return ["cluster", "inspect", *remainder, "--view", "cluster"]
    prefix = _ROUTE_PREFIXES.get((group, command))
    if prefix is None:
        raise ValueError(f"unsupported command route: {group} {command}")
    return [*prefix, *remainder]


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else list(sys.argv[1:])
    parser = _build_parser()
    try:
        known, remainder = parser.parse_known_args(args)
    except SystemExit as exc:
        return int(exc.code)

    group = str(getattr(known, "group", "") or "").strip()
    command = str(getattr(known, "command", "") or "").strip()
    if not group or not command:
        parser.print_help()
        return 2

    forwarded = _resolve_forward_args(
        group=group,
        command=command,
        remainder=remainder,
    )
    try:
        return int(node_cli.main(forwarded))
    except SystemExit as exc:
        return int(exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
