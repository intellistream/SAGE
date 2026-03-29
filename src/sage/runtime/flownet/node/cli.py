from __future__ import annotations

import argparse
import json
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from sage.runtime.flownet.client import bootstrap_node_runtime, build_http_node_control_caller
from sage.runtime.flownet.node.cluster_inventory import (
    format_cluster_plan_text,
    resolve_cluster_inventory,
)
from sage.runtime.flownet.node.cluster_target import resolve_cluster_target


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flownet",
        description="FlowNet node runtime bootstrap and inspect CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser(
        "start",
        help="Start a node runtime and optionally join seeds.",
    )
    start_parser.add_argument("--node-id", required=True, help="Local node id.")
    start_parser.add_argument("--bind", required=True, help="Node bind address host:port.")
    start_parser.add_argument(
        "--seed",
        action="append",
        default=[],
        help="Seed node address (supports node_id@host:port). Repeatable.",
    )
    start_parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Node metadata k=v pair. Repeatable.",
    )
    start_parser.add_argument("--join-timeout", type=float, default=3.0)
    start_parser.add_argument("--gossip-interval", type=float, default=1.0)
    start_parser.add_argument("--offline-timeout", type=float, default=8.0)
    start_parser.add_argument("--http-timeout", type=float, default=2.0)
    start_parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Optional runtime duration in seconds; 0 means wait until interrupted.",
    )
    start_parser.set_defaults(handler=_cmd_start)

    join_parser = subparsers.add_parser(
        "join",
        help="Start a node runtime and require at least one seed.",
    )
    join_parser.add_argument("--node-id", required=True, help="Local node id.")
    join_parser.add_argument("--bind", required=True, help="Node bind address host:port.")
    join_parser.add_argument(
        "--seed",
        action="append",
        default=[],
        help="Seed node address (supports node_id@host:port). Repeatable.",
    )
    join_parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Node metadata k=v pair. Repeatable.",
    )
    join_parser.add_argument("--join-timeout", type=float, default=3.0)
    join_parser.add_argument("--gossip-interval", type=float, default=1.0)
    join_parser.add_argument("--offline-timeout", type=float, default=8.0)
    join_parser.add_argument("--http-timeout", type=float, default=2.0)
    join_parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Optional runtime duration in seconds; 0 means wait until interrupted.",
    )
    join_parser.set_defaults(handler=_cmd_join)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a running node via node-control endpoint.",
    )
    inspect_parser.add_argument("--node", required=True, help="Target node address host:port.")
    inspect_parser.add_argument(
        "--view",
        choices=["cluster", "gossip", "contract", "nodes", "actors", "topics"],
        default="cluster",
        help="Inspect view to query.",
    )
    inspect_parser.add_argument("--schema", default="v1", help="Cluster view schema.")
    inspect_parser.add_argument("--timeout", type=float, default=2.0)
    inspect_parser.set_defaults(handler=_cmd_inspect)

    leave_parser = subparsers.add_parser(
        "leave",
        help="Request a running node to leave membership (soft/hard).",
    )
    leave_parser.add_argument("--node", required=True, help="Target node address host:port.")
    leave_parser.add_argument(
        "--mode",
        choices=["soft", "hard"],
        default="soft",
        help="Leave mode.",
    )
    leave_parser.add_argument("--timeout", type=float, default=2.0)
    leave_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until target node-control endpoint is unreachable.",
    )
    leave_parser.add_argument(
        "--wait-timeout",
        type=float,
        default=20.0,
        help="Wait timeout seconds.",
    )
    leave_parser.add_argument(
        "--wait-interval",
        type=float,
        default=0.5,
        help="Wait polling interval seconds.",
    )
    leave_parser.set_defaults(handler=_cmd_leave)

    stop_parser = subparsers.add_parser(
        "stop",
        help="Request a running node to stop (hard leave).",
    )
    stop_parser.add_argument("--node", required=True, help="Target node address host:port.")
    stop_parser.add_argument("--timeout", type=float, default=2.0)
    stop_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until target node-control endpoint is unreachable.",
    )
    stop_parser.add_argument(
        "--wait-timeout",
        type=float,
        default=20.0,
        help="Wait timeout seconds.",
    )
    stop_parser.add_argument(
        "--wait-interval",
        type=float,
        default=0.5,
        help="Wait polling interval seconds.",
    )
    stop_parser.set_defaults(handler=_cmd_stop)

    restart_parser = subparsers.add_parser(
        "restart",
        help="Stop target node then start local node runtime again.",
    )
    restart_parser.add_argument("--node", required=True, help="Target node address host:port.")
    restart_parser.add_argument("--node-id", required=True, help="Local node id.")
    restart_parser.add_argument("--bind", required=True, help="Node bind address host:port.")
    restart_parser.add_argument(
        "--seed",
        action="append",
        default=[],
        help="Seed node address (supports node_id@host:port). Repeatable.",
    )
    restart_parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Node metadata k=v pair. Repeatable.",
    )
    restart_parser.add_argument("--join-timeout", type=float, default=3.0)
    restart_parser.add_argument("--gossip-interval", type=float, default=1.0)
    restart_parser.add_argument("--offline-timeout", type=float, default=8.0)
    restart_parser.add_argument("--http-timeout", type=float, default=2.0)
    restart_parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Optional runtime duration in seconds; 0 means wait until interrupted.",
    )
    restart_parser.add_argument(
        "--stop-timeout",
        type=float,
        default=2.0,
        help="Node-control timeout when stopping previous node.",
    )
    restart_parser.add_argument(
        "--stop-wait-timeout",
        type=float,
        default=20.0,
        help="Wait timeout for previous node stop.",
    )
    restart_parser.add_argument(
        "--stop-wait-interval",
        type=float,
        default=0.5,
        help="Wait polling interval for previous node stop.",
    )
    restart_parser.set_defaults(handler=_cmd_restart)

    cluster_parser = subparsers.add_parser(
        "cluster",
        help="Node-list-first cluster inventory utilities.",
    )
    cluster_subparsers = cluster_parser.add_subparsers(
        dest="cluster_command",
        required=True,
    )

    cluster_plan_parser = cluster_subparsers.add_parser(
        "plan",
        help="Resolve inventory into normalized node plan.",
    )
    cluster_plan_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_plan_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_plan_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_plan_parser.add_argument(
        "--require-ssh-target",
        action="store_true",
        help="Fail when ssh_target is missing.",
    )
    cluster_plan_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format.",
    )
    cluster_plan_parser.set_defaults(handler=_cmd_cluster_plan)

    cluster_start_parser = cluster_subparsers.add_parser(
        "start",
        help="Start one cluster node from inventory by node_id.",
    )
    cluster_start_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_start_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_start_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_start_parser.add_argument(
        "--node-id",
        required=True,
        help="Node id to start from inventory.",
    )
    cluster_start_parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Extra metadata k=v pair. Repeatable and overrides inventory values.",
    )
    cluster_start_parser.add_argument("--join-timeout", type=float, default=3.0)
    cluster_start_parser.add_argument("--gossip-interval", type=float, default=1.0)
    cluster_start_parser.add_argument("--offline-timeout", type=float, default=8.0)
    cluster_start_parser.add_argument("--http-timeout", type=float, default=2.0)
    cluster_start_parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Optional runtime duration in seconds; 0 means wait until interrupted.",
    )
    cluster_start_parser.set_defaults(handler=_cmd_cluster_start)

    cluster_up_parser = cluster_subparsers.add_parser(
        "up",
        help="Auto-ssh bootstrap all nodes from inventory.",
    )
    cluster_up_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_up_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_up_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_up_parser.add_argument(
        "--remote-repo-root",
        required=True,
        help="Remote repository root path.",
    )
    cluster_up_parser.add_argument(
        "--remote-inventory-path",
        default="",
        help="Inventory path on remote machines. Defaults to --inventory value.",
    )
    cluster_up_parser.add_argument(
        "--remote-python",
        default="python",
        help="Python executable on remote machines.",
    )
    cluster_up_parser.add_argument(
        "--remote-work-root",
        default="/tmp/flownet_cluster_cli",
        help="Remote work root for pid/log files.",
    )
    cluster_up_parser.add_argument(
        "--ssh-user",
        default="",
        help=(
            "Optional ssh username override. When empty, use inventory ssh.user/"
            "nodes[].ssh_user. Prepended when ssh_target has no user."
        ),
    )
    cluster_up_parser.add_argument(
        "--ssh-port",
        type=int,
        default=22,
        help="SSH port.",
    )
    cluster_up_parser.add_argument(
        "--ssh-identity-file",
        default="",
        help=(
            "Optional ssh private key path override. When empty, use inventory "
            "ssh.identity_file/nodes[].ssh_identity_file."
        ),
    )
    cluster_up_parser.add_argument(
        "--ssh-connect-timeout",
        type=float,
        default=10.0,
        help="SSH connect timeout seconds.",
    )
    cluster_up_parser.add_argument(
        "--ssh-strict-host-key-checking",
        default="accept-new",
        help="StrictHostKeyChecking value.",
    )
    cluster_up_parser.add_argument(
        "--ssh-extra-opt",
        action="append",
        default=[],
        help="Extra ssh option(s). Repeatable.",
    )
    cluster_up_parser.add_argument("--join-timeout", type=float, default=3.0)
    cluster_up_parser.add_argument("--gossip-interval", type=float, default=1.0)
    cluster_up_parser.add_argument("--offline-timeout", type=float, default=8.0)
    cluster_up_parser.add_argument("--http-timeout", type=float, default=2.0)
    cluster_up_parser.add_argument(
        "--health-timeout",
        type=float,
        default=20.0,
        help="Per-node healthz wait timeout seconds.",
    )
    cluster_up_parser.add_argument(
        "--convergence-timeout",
        type=float,
        default=30.0,
        help="Membership convergence timeout seconds.",
    )
    cluster_up_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ssh commands only.",
    )
    cluster_up_parser.set_defaults(handler=_cmd_cluster_up)

    cluster_down_parser = cluster_subparsers.add_parser(
        "down",
        help="Auto-ssh stop all nodes from inventory.",
    )
    cluster_down_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_down_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_down_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_down_parser.add_argument(
        "--remote-work-root",
        default="/tmp/flownet_cluster_cli",
        help="Remote work root for pid/log files.",
    )
    cluster_down_parser.add_argument(
        "--ssh-user",
        default="",
        help=(
            "Optional ssh username override. When empty, use inventory ssh.user/"
            "nodes[].ssh_user. Prepended when ssh_target has no user."
        ),
    )
    cluster_down_parser.add_argument(
        "--ssh-port",
        type=int,
        default=22,
        help="SSH port.",
    )
    cluster_down_parser.add_argument(
        "--ssh-identity-file",
        default="",
        help=(
            "Optional ssh private key path override. When empty, use inventory "
            "ssh.identity_file/nodes[].ssh_identity_file."
        ),
    )
    cluster_down_parser.add_argument(
        "--ssh-connect-timeout",
        type=float,
        default=10.0,
        help="SSH connect timeout seconds.",
    )
    cluster_down_parser.add_argument(
        "--ssh-strict-host-key-checking",
        default="accept-new",
        help="StrictHostKeyChecking value.",
    )
    cluster_down_parser.add_argument(
        "--ssh-extra-opt",
        action="append",
        default=[],
        help="Extra ssh option(s). Repeatable.",
    )
    cluster_down_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ssh commands only.",
    )
    cluster_down_parser.set_defaults(handler=_cmd_cluster_down)

    cluster_inspect_parser = cluster_subparsers.add_parser(
        "inspect",
        help="Inspect all or selected nodes from inventory.",
    )
    cluster_inspect_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_inspect_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_inspect_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_inspect_parser.add_argument(
        "--node-id",
        default="",
        help="Optional node id filter. Empty means inspect all nodes.",
    )
    cluster_inspect_parser.add_argument(
        "--view",
        choices=["cluster", "gossip", "contract", "nodes", "actors", "topics"],
        default="cluster",
        help="Inspect view to query.",
    )
    cluster_inspect_parser.add_argument(
        "--entry-node",
        default="",
        help="Optional entry node address for observed state (host:port).",
    )
    cluster_inspect_parser.add_argument("--schema", default="v1", help="Cluster view schema.")
    cluster_inspect_parser.add_argument("--timeout", type=float, default=2.0)
    cluster_inspect_parser.set_defaults(handler=_cmd_cluster_inspect)

    cluster_status_parser = cluster_subparsers.add_parser(
        "status",
        help="Alias of cluster inspect --view cluster with desired/observed/drift summary.",
    )
    cluster_status_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_status_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_status_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_status_parser.add_argument(
        "--entry-node",
        default="",
        help="Optional entry node address for observed state (host:port).",
    )
    cluster_status_parser.add_argument("--schema", default="v1", help="Cluster view schema.")
    cluster_status_parser.add_argument("--timeout", type=float, default=2.0)
    cluster_status_parser.set_defaults(handler=_cmd_cluster_status)

    cluster_join_parser = cluster_subparsers.add_parser(
        "join",
        help="Hot-join one inventory node on target host via SSH.",
    )
    cluster_join_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_join_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_join_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_join_parser.add_argument(
        "--target",
        required=True,
        help="Target ssh host (host or user@host).",
    )
    cluster_join_parser.add_argument(
        "--node-id",
        default="",
        help="Optional node id filter when multiple rows share target host.",
    )
    cluster_join_parser.add_argument(
        "--entry-node",
        default="",
        help="Optional entry node address for wait/observed checks.",
    )
    cluster_join_parser.add_argument(
        "--remote-repo-root",
        required=True,
        help="Remote repository root path.",
    )
    cluster_join_parser.add_argument(
        "--remote-inventory-path",
        default="",
        help="Inventory path on remote machine. Defaults to --inventory value.",
    )
    cluster_join_parser.add_argument(
        "--remote-python",
        default="python",
        help="Python executable on remote machine.",
    )
    cluster_join_parser.add_argument(
        "--remote-work-root",
        default="/tmp/flownet_cluster_cli",
        help="Remote work root for pid/log files.",
    )
    cluster_join_parser.add_argument(
        "--ssh-user",
        default="",
        help=(
            "Optional ssh username override. When empty, use inventory ssh.user/"
            "nodes[].ssh_user. Prepended when ssh_target has no user."
        ),
    )
    cluster_join_parser.add_argument("--ssh-port", type=int, default=22, help="SSH port.")
    cluster_join_parser.add_argument(
        "--ssh-identity-file",
        default="",
        help=(
            "Optional ssh private key path override. When empty, use inventory "
            "ssh.identity_file/nodes[].ssh_identity_file."
        ),
    )
    cluster_join_parser.add_argument(
        "--ssh-connect-timeout",
        type=float,
        default=10.0,
        help="SSH connect timeout seconds.",
    )
    cluster_join_parser.add_argument(
        "--ssh-strict-host-key-checking",
        default="accept-new",
        help="StrictHostKeyChecking value.",
    )
    cluster_join_parser.add_argument(
        "--ssh-extra-opt",
        action="append",
        default=[],
        help="Extra ssh option(s). Repeatable.",
    )
    cluster_join_parser.add_argument("--join-timeout", type=float, default=3.0)
    cluster_join_parser.add_argument("--gossip-interval", type=float, default=1.0)
    cluster_join_parser.add_argument("--offline-timeout", type=float, default=8.0)
    cluster_join_parser.add_argument("--http-timeout", type=float, default=2.0)
    cluster_join_parser.add_argument(
        "--health-timeout",
        type=float,
        default=20.0,
        help="Per-node healthz wait timeout seconds.",
    )
    cluster_join_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until node is observed healthy in cluster view.",
    )
    cluster_join_parser.add_argument(
        "--wait-timeout",
        type=float,
        default=30.0,
        help="Cluster wait timeout seconds.",
    )
    cluster_join_parser.add_argument(
        "--wait-interval",
        type=float,
        default=0.5,
        help="Cluster wait polling interval seconds.",
    )
    cluster_join_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ssh commands only.",
    )
    cluster_join_parser.set_defaults(handler=_cmd_cluster_join)

    cluster_leave_parser = cluster_subparsers.add_parser(
        "leave",
        help="Leave one inventory node from cluster with soft/hard mode.",
    )
    cluster_leave_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_leave_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_leave_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_leave_parser.add_argument(
        "--node-id",
        required=True,
        help="Node id to leave.",
    )
    cluster_leave_parser.add_argument(
        "--mode",
        choices=["soft", "hard"],
        required=True,
        help="Leave mode.",
    )
    cluster_leave_parser.add_argument(
        "--entry-node",
        default="",
        help="Optional entry node address for wait/observed checks.",
    )
    cluster_leave_parser.add_argument(
        "--remote-work-root",
        default="/tmp/flownet_cluster_cli",
        help="Remote work root for pid/log files.",
    )
    cluster_leave_parser.add_argument(
        "--ssh-user",
        default="",
        help=(
            "Optional ssh username override. When empty, use inventory ssh.user/"
            "nodes[].ssh_user. Prepended when ssh_target has no user."
        ),
    )
    cluster_leave_parser.add_argument("--ssh-port", type=int, default=22, help="SSH port.")
    cluster_leave_parser.add_argument(
        "--ssh-identity-file",
        default="",
        help=(
            "Optional ssh private key path override. When empty, use inventory "
            "ssh.identity_file/nodes[].ssh_identity_file."
        ),
    )
    cluster_leave_parser.add_argument(
        "--ssh-connect-timeout",
        type=float,
        default=10.0,
        help="SSH connect timeout seconds.",
    )
    cluster_leave_parser.add_argument(
        "--ssh-strict-host-key-checking",
        default="accept-new",
        help="StrictHostKeyChecking value.",
    )
    cluster_leave_parser.add_argument(
        "--ssh-extra-opt",
        action="append",
        default=[],
        help="Extra ssh option(s). Repeatable.",
    )
    cluster_leave_parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Node-control timeout seconds.",
    )
    cluster_leave_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until node is not healthy in observed view.",
    )
    cluster_leave_parser.add_argument(
        "--wait-timeout",
        type=float,
        default=30.0,
        help="Cluster wait timeout seconds.",
    )
    cluster_leave_parser.add_argument(
        "--wait-interval",
        type=float,
        default=0.5,
        help="Cluster wait polling interval seconds.",
    )
    cluster_leave_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ssh commands only.",
    )
    cluster_leave_parser.set_defaults(handler=_cmd_cluster_leave)

    cluster_reconcile_parser = cluster_subparsers.add_parser(
        "reconcile",
        help="Compare desired inventory with observed view and optionally repair drift.",
    )
    cluster_reconcile_parser.add_argument(
        "--cluster",
        default="",
        help="Cluster profile name for context resolution.",
    )
    cluster_reconcile_parser.add_argument(
        "--inventory",
        default="",
        help="Inventory yaml path (preferred).",
    )
    cluster_reconcile_parser.add_argument(
        "--seed-strategy",
        default="full-mesh",
        help="Seed derivation strategy (default: full-mesh).",
    )
    cluster_reconcile_parser.add_argument(
        "--entry-node",
        default="",
        help="Optional entry node address for observed state.",
    )
    cluster_reconcile_parser.add_argument("--timeout", type=float, default=2.0)
    cluster_reconcile_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repair actions (default: report-only).",
    )
    cluster_reconcile_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until missing/offline-desired drift is converged.",
    )
    cluster_reconcile_parser.add_argument(
        "--wait-timeout",
        type=float,
        default=30.0,
        help="Cluster wait timeout seconds.",
    )
    cluster_reconcile_parser.add_argument(
        "--wait-interval",
        type=float,
        default=0.5,
        help="Cluster wait polling interval seconds.",
    )
    cluster_reconcile_parser.add_argument(
        "--remote-repo-root",
        default="",
        help="Remote repository root path (required when --apply triggers join/start).",
    )
    cluster_reconcile_parser.add_argument(
        "--remote-inventory-path",
        default="",
        help="Inventory path on remote machine. Defaults to --inventory value.",
    )
    cluster_reconcile_parser.add_argument(
        "--remote-python",
        default="python",
        help="Python executable on remote machine.",
    )
    cluster_reconcile_parser.add_argument(
        "--remote-work-root",
        default="/tmp/flownet_cluster_cli",
        help="Remote work root for pid/log files.",
    )
    cluster_reconcile_parser.add_argument(
        "--ssh-user",
        default="",
        help=(
            "Optional ssh username override. When empty, use inventory ssh.user/"
            "nodes[].ssh_user. Prepended when ssh_target has no user."
        ),
    )
    cluster_reconcile_parser.add_argument("--ssh-port", type=int, default=22, help="SSH port.")
    cluster_reconcile_parser.add_argument(
        "--ssh-identity-file",
        default="",
        help=(
            "Optional ssh private key path override. When empty, use inventory "
            "ssh.identity_file/nodes[].ssh_identity_file."
        ),
    )
    cluster_reconcile_parser.add_argument(
        "--ssh-connect-timeout",
        type=float,
        default=10.0,
        help="SSH connect timeout seconds.",
    )
    cluster_reconcile_parser.add_argument(
        "--ssh-strict-host-key-checking",
        default="accept-new",
        help="StrictHostKeyChecking value.",
    )
    cluster_reconcile_parser.add_argument(
        "--ssh-extra-opt",
        action="append",
        default=[],
        help="Extra ssh option(s). Repeatable.",
    )
    cluster_reconcile_parser.add_argument("--join-timeout", type=float, default=3.0)
    cluster_reconcile_parser.add_argument("--gossip-interval", type=float, default=1.0)
    cluster_reconcile_parser.add_argument("--offline-timeout", type=float, default=8.0)
    cluster_reconcile_parser.add_argument("--http-timeout", type=float, default=2.0)
    cluster_reconcile_parser.add_argument(
        "--health-timeout",
        type=float,
        default=20.0,
        help="Per-node healthz wait timeout seconds.",
    )
    cluster_reconcile_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ssh commands only for apply actions.",
    )
    cluster_reconcile_parser.set_defaults(handler=_cmd_cluster_reconcile)

    return parser


def _cmd_start(args: argparse.Namespace) -> int:
    metadata = _parse_metadata_pairs(args.metadata)
    handle = bootstrap_node_runtime(
        node_id=args.node_id,
        bind_address=args.bind,
        seeds=list(args.seed or []),
        metadata=metadata,
        join_timeout=float(args.join_timeout),
        gossip_interval=float(args.gossip_interval),
        offline_timeout=float(args.offline_timeout),
        http_timeout=float(args.http_timeout),
    )
    return _run_started_node(
        handle=handle,
        duration=float(args.duration),
    )


def _cmd_join(args: argparse.Namespace) -> int:
    if not list(args.seed or []):
        raise ValueError("node join requires at least one --seed")
    return _cmd_start(args)


def _cmd_leave(args: argparse.Namespace) -> int:
    node_address = str(args.node or "").strip()
    if not node_address:
        raise ValueError("node must be non-empty")
    mode = str(args.mode or "soft").strip().lower() or "soft"
    if mode not in {"soft", "hard"}:
        raise ValueError(f"unsupported leave mode: {mode!r}")

    caller = build_http_node_control_caller(timeout_s=float(args.timeout))
    result = caller(
        "node_leave",
        mode=mode,
        node_address=node_address,
    )
    result_payload = result if isinstance(result, dict) else {}

    waited = False
    if bool(getattr(args, "wait", False)):
        waited = True
        _wait_node_unreachable(
            caller=caller,
            node_address=node_address,
            timeout_s=float(args.wait_timeout),
            interval_s=float(args.wait_interval),
        )

    print(
        json.dumps(
            {
                "ok": True,
                "op": "node_leave",
                "node_address": node_address,
                "mode": mode,
                "waited": waited,
                "stop_strategy": result_payload.get("stop_strategy"),
                "peer_notify_mode": result_payload.get("peer_notify_mode"),
                "peer_notify_attempted": result_payload.get("peer_notify_attempted"),
                "peer_notify_succeeded": result_payload.get("peer_notify_succeeded"),
                "peer_notify_failed": result_payload.get("peer_notify_failed"),
                "leave_counters": result_payload.get("leave_counters"),
                "result": result_payload if isinstance(result, dict) else result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    leave_args = argparse.Namespace(
        node=getattr(args, "node", ""),
        mode="hard",
        timeout=float(getattr(args, "timeout", 2.0)),
        wait=bool(getattr(args, "wait", False)),
        wait_timeout=float(getattr(args, "wait_timeout", 20.0)),
        wait_interval=float(getattr(args, "wait_interval", 0.5)),
    )
    return _cmd_leave(leave_args)


def _cmd_restart(args: argparse.Namespace) -> int:
    stop_args = argparse.Namespace(
        node=getattr(args, "node", ""),
        mode="hard",
        timeout=float(getattr(args, "stop_timeout", 2.0)),
        wait=True,
        wait_timeout=float(getattr(args, "stop_wait_timeout", 20.0)),
        wait_interval=float(getattr(args, "stop_wait_interval", 0.5)),
    )
    _cmd_leave(stop_args)
    return _cmd_start(args)


def _run_started_node(
    *,
    handle: Any,
    duration: float,
    extra_payload: dict[str, Any] | None = None,
) -> int:
    stop_event = threading.Event()

    def _stop(_signum: int, _frame: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    payload: dict[str, Any] = {
        "ok": True,
        "status": handle.status,
        "node_id": handle.node_id,
        "bind_address": handle.local_address,
        "seed_address": handle.attached_node_address,
    }
    if extra_payload:
        payload.update(dict(extra_payload))
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )

    try:
        if duration > 0:
            stop_event.wait(timeout=duration)
        else:
            while not stop_event.wait(timeout=1.0):
                pass
    finally:
        handle.shutdown()
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    node_address = str(args.node or "").strip()
    caller = build_http_node_control_caller(timeout_s=float(args.timeout))
    view = str(args.view or "cluster").strip().lower()
    payload = _run_inspect_call(
        caller=caller,
        node_address=node_address,
        view=view,
        schema=str(args.schema or "v1"),
    )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_cluster_plan(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args)
    output_format = str(args.format or "json").strip().lower()
    if output_format == "text":
        print(format_cluster_plan_text(plan))
    else:
        print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def _cmd_cluster_start(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args)
    node_id = str(args.node_id or "").strip()
    if not node_id:
        raise ValueError("node_id must be non-empty")

    rows = plan.get("nodes")
    if not isinstance(rows, list):
        raise ValueError("cluster plan nodes is not a list")
    selected: dict[str, Any] | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("node_id") or "").strip() == node_id:
            selected = row
            break
    if selected is None:
        raise ValueError(f"node_id not found in cluster inventory: {node_id!r}")

    bind_address = str(selected.get("bind_address") or "").strip()
    if not bind_address:
        raise ValueError(f"node missing bind_address: {node_id!r}")
    seeds = [
        str(item).strip() for item in (selected.get("seed_addresses") or []) if str(item).strip()
    ]
    metadata: dict[str, str] = {}
    for field in ("resource_metadata", "metadata"):
        raw = selected.get(field)
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            metadata_key = str(key or "").strip()
            metadata_value = str(value or "").strip()
            if not metadata_key or not metadata_value:
                continue
            metadata[metadata_key] = metadata_value
    metadata.update(_parse_metadata_pairs(args.metadata))

    handle = bootstrap_node_runtime(
        node_id=node_id,
        bind_address=bind_address,
        seeds=seeds,
        metadata=metadata,
        join_timeout=float(args.join_timeout),
        gossip_interval=float(args.gossip_interval),
        offline_timeout=float(args.offline_timeout),
        http_timeout=float(args.http_timeout),
    )
    return _run_started_node(
        handle=handle,
        duration=float(args.duration),
        extra_payload={
            "source": "cluster_inventory",
            "inventory_source": dict(plan.get("source") or {}),
            "seed_strategy": str(plan.get("seed_strategy") or ""),
            "seed_source": str(selected.get("seed_source") or ""),
            "seed_addresses": seeds,
            "metadata": metadata,
        },
    )


def _cmd_cluster_up(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args, require_ssh_target=True)
    nodes = _plan_nodes(plan)
    remote_repo_root = str(args.remote_repo_root or "").strip()
    if not remote_repo_root:
        raise ValueError("remote_repo_root must be non-empty")
    remote_inventory_path = str(args.remote_inventory_path or "").strip()
    if not remote_inventory_path:
        remote_inventory_path = str(args.inventory or "").strip()
    if not remote_inventory_path:
        raise ValueError("remote inventory path is required when using --inventory")

    for row in nodes:
        node_id = str(row.get("node_id") or "").strip()
        ssh_user, identity_file = _resolve_node_ssh_auth(args=args, row=row)
        ssh_base = _build_ssh_base_args(args=args, identity_file=identity_file)
        ssh_target = _qualify_ssh_target(str(row.get("ssh_target") or "").strip(), ssh_user)
        bind_address = str(row.get("bind_address") or "").strip()
        if not node_id or not ssh_target or not bind_address:
            raise ValueError("cluster up node row is missing node_id/ssh_target/bind_address")
        start_args = [
            str(args.remote_python or "python"),
            "-m",
            "flownet.node.cli",
            "cluster",
            "start",
            "--node-id",
            node_id,
            "--seed-strategy",
            str(args.seed_strategy or "full-mesh"),
            "--join-timeout",
            str(float(args.join_timeout)),
            "--gossip-interval",
            str(float(args.gossip_interval)),
            "--offline-timeout",
            str(float(args.offline_timeout)),
            "--http-timeout",
            str(float(args.http_timeout)),
        ]
        start_args.extend(["--inventory", remote_inventory_path])
        start_cmd = shlex.join(start_args)
        up_script = (
            "set -euo pipefail\n"
            f"PID_FILE={shlex.quote(str(args.remote_work_root) + '/pids/' + node_id + '.pid')}\n"
            f"LOG_FILE={shlex.quote(str(args.remote_work_root) + '/logs/' + node_id + '.log')}\n"
            'mkdir -p "$(dirname "${PID_FILE}")" "$(dirname "${LOG_FILE}")"\n'
            'if [[ -f "${PID_FILE}" ]]; then\n'
            '  old_pid="$(cat "${PID_FILE}" || true)"\n'
            '  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then\n'
            f'    echo "node_already_running:{node_id}:pid=${{old_pid}}"\n'
            "    exit 0\n"
            "  fi\n"
            "fi\n"
            f"cd {shlex.quote(remote_repo_root)}\n"
            "export PYTHONPATH='src:flownet/src:'\"${PYTHONPATH:-}\"\n"
            f'nohup {start_cmd} >"${{LOG_FILE}}" 2>&1 < /dev/null &\n'
            'new_pid="$!"\n'
            'echo "${new_pid}" >"${PID_FILE}"\n'
            f'echo "node_started:{node_id}:pid=${{new_pid}}"\n'
        )
        _ssh_run(
            ssh_base=ssh_base,
            target=ssh_target,
            script=up_script,
            dry_run=bool(args.dry_run),
        )
        health_script = (
            f"{shlex.quote(str(args.remote_python or 'python'))} - {shlex.quote(bind_address)} "
            f"{shlex.quote(str(float(args.health_timeout)))} <<'PY'\n"
            "import json\n"
            "import sys\n"
            "import time\n"
            "from urllib import request\n"
            "address = sys.argv[1]\n"
            "timeout_s = float(sys.argv[2])\n"
            "deadline = time.time() + timeout_s\n"
            "while time.time() < deadline:\n"
            "    try:\n"
            "        with request.urlopen(f'http://{address}/healthz', timeout=1.0) as resp:\n"
            "            payload = json.loads(resp.read().decode('utf-8'))\n"
            "        if bool(payload.get('ok')):\n"
            "            raise SystemExit(0)\n"
            "    except Exception:\n"
            "        time.sleep(0.2)\n"
            "raise SystemExit(1)\n"
            "PY\n"
        )
        _ssh_run(
            ssh_base=ssh_base,
            target=ssh_target,
            script=health_script,
            dry_run=bool(args.dry_run),
        )

    coordinator_user, coordinator_identity_file = _resolve_node_ssh_auth(
        args=args,
        row=nodes[0],
    )
    coordinator_target = _qualify_ssh_target(
        str(nodes[0].get("ssh_target") or "").strip(),
        coordinator_user,
    )
    coordinator_ssh_base = _build_ssh_base_args(
        args=args,
        identity_file=coordinator_identity_file,
    )
    addresses_json = json.dumps(
        [str(row.get("bind_address") or "") for row in nodes], ensure_ascii=False
    )
    convergence_script = (
        "set -euo pipefail\n"
        f"cd {shlex.quote(remote_repo_root)}\n"
        "export PYTHONPATH='src:flownet/src:'\"${PYTHONPATH:-}\"\n"
        f"{shlex.quote(str(args.remote_python or 'python'))} - "
        f"{shlex.quote(str(float(args.convergence_timeout)))} "
        f"{shlex.quote(str(len(nodes)))} "
        f"{shlex.quote(addresses_json)} <<'PY'\n"
        "import json\n"
        "import sys\n"
        "import time\n"
        "from sage.runtime.flownet import build_http_node_control_caller\n"
        "timeout_s = float(sys.argv[1])\n"
        "expected = int(sys.argv[2])\n"
        "addresses = json.loads(sys.argv[3])\n"
        "caller = build_http_node_control_caller(timeout_s=2.0)\n"
        "deadline = time.time() + timeout_s\n"
        "while time.time() < deadline:\n"
        "    ok = True\n"
        "    for addr in addresses:\n"
        "        try:\n"
        "            view = caller('cluster_view_snapshot', schema='v1', node_address=addr)\n"
        "            total = int((view.get('health_summary') or {}).get('total', 0))\n"
        "            if total < expected:\n"
        "                ok = False\n"
        "                break\n"
        "        except Exception:\n"
        "            ok = False\n"
        "            break\n"
        "    if ok:\n"
        "        raise SystemExit(0)\n"
        "    time.sleep(0.4)\n"
        "raise SystemExit(1)\n"
        "PY\n"
    )
    _ssh_run(
        ssh_base=coordinator_ssh_base,
        target=coordinator_target,
        script=convergence_script,
        dry_run=bool(args.dry_run),
    )
    print(
        json.dumps(
            {
                "ok": True,
                "op": "cluster_up",
                "node_count": len(nodes),
                "seed_strategy": str(plan.get("seed_strategy") or ""),
                "dry_run": bool(args.dry_run),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cluster_down(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args, require_ssh_target=True)
    nodes = _plan_nodes(plan)
    remote_work_root = str(args.remote_work_root or "").strip()
    if not remote_work_root:
        raise ValueError("remote_work_root must be non-empty")

    for row in nodes:
        node_id = str(row.get("node_id") or "").strip()
        ssh_user, identity_file = _resolve_node_ssh_auth(args=args, row=row)
        ssh_base = _build_ssh_base_args(args=args, identity_file=identity_file)
        ssh_target = _qualify_ssh_target(str(row.get("ssh_target") or "").strip(), ssh_user)
        if not node_id or not ssh_target:
            raise ValueError("cluster down node row is missing node_id/ssh_target")
        down_script = (
            "set -euo pipefail\n"
            f"PID_FILE={shlex.quote(remote_work_root + '/pids/' + node_id + '.pid')}\n"
            'if [[ -f "${PID_FILE}" ]]; then\n'
            '  pid="$(cat "${PID_FILE}" || true)"\n'
            '  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then\n'
            '    kill "${pid}" >/dev/null 2>&1 || true\n'
            "    sleep 0.5\n"
            '    if kill -0 "${pid}" >/dev/null 2>&1; then\n'
            '      kill -9 "${pid}" >/dev/null 2>&1 || true\n'
            "    fi\n"
            "  fi\n"
            '  rm -f "${PID_FILE}"\n'
            "fi\n"
        )
        _ssh_run(
            ssh_base=ssh_base,
            target=ssh_target,
            script=down_script,
            dry_run=bool(args.dry_run),
        )
    print(
        json.dumps(
            {
                "ok": True,
                "op": "cluster_down",
                "node_count": len(nodes),
                "dry_run": bool(args.dry_run),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cluster_inspect(args: argparse.Namespace) -> int:
    plan = _resolve_optional_cluster_plan_from_args(args)
    node_id_filter = str(args.node_id or "").strip()
    view = str(args.view or "cluster").strip().lower()
    schema = str(args.schema or "v1").strip() or "v1"
    timeout_s = float(args.timeout)
    caller = build_http_node_control_caller(timeout_s=timeout_s)
    entry_node = _resolve_cluster_entry_node(args=args, plan=plan)

    selected: list[dict[str, Any]] = []
    if plan is not None:
        rows = plan.get("nodes")
        if not isinstance(rows, list):
            raise ValueError("cluster plan nodes is not a list")
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_node_id = str(row.get("node_id") or "")
            if node_id_filter and row_node_id != node_id_filter:
                continue
            selected.append(row)
        if node_id_filter and not selected:
            raise ValueError(f"node_id not found in cluster inventory: {node_id_filter!r}")
    else:
        if not entry_node:
            raise ValueError("cluster target missing: set --inventory or --entry-node")
        selected.append(
            {
                "node_id": node_id_filter or "entry-node",
                "bind_address": entry_node,
                "seed_addresses": [],
            }
        )

    inspections: list[dict[str, Any]] = []
    for row in selected:
        bind_address = str(row.get("bind_address") or "").strip()
        if not bind_address:
            raise ValueError(f"node missing bind_address: {row.get('node_id')!r}")
        payload = _run_inspect_call(
            caller=caller,
            node_address=bind_address,
            view=view,
            schema=schema,
        )
        inspections.append(
            {
                "node_id": str(row.get("node_id") or ""),
                "bind_address": bind_address,
                "seed_addresses": list(row.get("seed_addresses") or []),
                "payload": payload,
            }
        )

    out: dict[str, Any] = {
        "schema_version": "flownet.node.cluster.inspect.v1",
        "view": view,
        "schema": schema,
        "node_count": len(inspections),
        "nodes": inspections,
    }
    include_cluster_state = False
    if view == "cluster":
        for row in inspections:
            payload = row.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("nodes"), list):
                include_cluster_state = True
                break

    if include_cluster_state:
        state = _build_cluster_state_model(
            plan=plan,
            entry_node=entry_node,
            inspections=inspections,
            caller=caller,
            schema=schema,
        )
        out.update(state)

    print(
        json.dumps(
            out,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cluster_status(args: argparse.Namespace) -> int:
    inspect_args = argparse.Namespace(
        cluster=str(getattr(args, "cluster", "") or ""),
        inventory=str(getattr(args, "inventory", "") or ""),
        seed_strategy=str(getattr(args, "seed_strategy", "full-mesh") or "full-mesh"),
        node_id="",
        view="cluster",
        schema=str(getattr(args, "schema", "v1") or "v1"),
        timeout=float(getattr(args, "timeout", 2.0)),
        entry_node=str(getattr(args, "entry_node", "") or ""),
    )
    return _cmd_cluster_inspect(inspect_args)


def _cmd_cluster_join(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args, require_ssh_target=True)
    nodes = _plan_nodes(plan)
    requested_target = str(args.target or "").strip()
    requested_node_id = str(args.node_id or "").strip()
    if not requested_target:
        raise ValueError("target must be non-empty")

    matched_rows = [
        row
        for row in nodes
        if _is_ssh_target_match(str(row.get("ssh_target") or ""), requested_target)
    ]
    if requested_node_id:
        matched_rows = [
            row
            for row in matched_rows
            if str(row.get("node_id") or "").strip() == requested_node_id
        ]
    if not matched_rows:
        raise ValueError(
            "target/node-id not found in inventory; pass --inventory row with ssh_target and bind_address"
        )
    if len(matched_rows) > 1:
        raise ValueError(
            "target matches multiple inventory rows; please disambiguate with --node-id"
        )
    row = matched_rows[0]
    node_id = str(row.get("node_id") or "").strip()
    bind_address = str(row.get("bind_address") or "").strip()
    if not node_id or not bind_address:
        raise ValueError("inventory node is missing node_id/bind_address")

    entry_node = _resolve_cluster_entry_node(args=args, plan=plan)
    caller = build_http_node_control_caller(timeout_s=float(args.http_timeout))
    dry_run = bool(args.dry_run)

    idempotent = False
    pre_view: dict[str, Any] | None = None
    if not dry_run:
        try:
            pre_view = _fetch_cluster_view_snapshot(
                caller=caller,
                entry_node=entry_node,
                schema="v1",
            )
            observed = _index_observed_nodes(pre_view)
            row_payload = observed.get(node_id)
            if (
                row_payload is not None
                and str(row_payload.get("health") or "").strip().lower() == "healthy"
            ):
                idempotent = True
        except Exception:
            pre_view = None

    if not idempotent or dry_run:
        _cluster_start_remote_node(
            args=args,
            plan=plan,
            row=row,
            dry_run=dry_run,
        )

    waited = False
    final_view: dict[str, Any] | None = pre_view
    if bool(args.wait) and not dry_run:
        waited = True
        final_view = _wait_cluster_node_health(
            caller=caller,
            entry_node=entry_node,
            node_id=node_id,
            timeout_s=float(args.wait_timeout),
            interval_s=float(args.wait_interval),
        )
    elif final_view is None and not dry_run:
        try:
            final_view = _fetch_cluster_view_snapshot(
                caller=caller,
                entry_node=entry_node,
                schema="v1",
            )
        except Exception:
            final_view = None

    try:
        state_model = _build_cluster_state_model(
            plan=plan,
            entry_node=entry_node,
            inspections=[],
            caller=caller,
            schema="v1",
            preferred_snapshot=(
                final_view
                if not dry_run
                else {
                    "schema_version": "v1",
                    "generated_at": time.time(),
                    "view_epoch": 0,
                    "health_summary": {"healthy": 0, "degraded": 0, "total": 0},
                    "nodes": [],
                }
            ),
        )
    except Exception:
        state_model = {
            "desired": _desired_state_payload(plan),
            "observed": {
                "entry_node": entry_node,
                "generated_at": None,
                "view_epoch": None,
                "health_summary": {},
                "node_count": 0,
                "nodes": [],
            },
            "drift": _compute_cluster_drift(
                desired_nodes=_desired_nodes_from_plan(plan),
                observed_nodes=[],
            ),
        }
    print(
        json.dumps(
            {
                "ok": True,
                "op": "cluster_join",
                "node_id": node_id,
                "target": requested_target,
                "bind_address": bind_address,
                "idempotent": idempotent,
                "waited": waited,
                "dry_run": dry_run,
                **state_model,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cluster_leave(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(args, require_ssh_target=True)
    row = _select_plan_node(plan, node_id=str(args.node_id or "").strip())
    node_id = str(row.get("node_id") or "").strip()
    bind_address = str(row.get("bind_address") or "").strip()
    if not node_id or not bind_address:
        raise ValueError("inventory node is missing node_id/bind_address")
    mode = str(args.mode or "").strip().lower()
    if mode not in {"soft", "hard"}:
        raise ValueError(f"unsupported leave mode: {mode!r}")

    entry_node = _resolve_cluster_entry_node(args=args, plan=plan)
    caller = build_http_node_control_caller(timeout_s=float(args.timeout))
    dry_run = bool(args.dry_run)

    if mode == "soft" and not dry_run:
        caller(
            "node_leave",
            mode="soft",
            node_address=bind_address,
        )
    if mode == "soft":
        _cluster_stop_remote_node(
            args=args,
            row=row,
            mode="soft",
            dry_run=dry_run,
        )
    else:
        _cluster_stop_remote_node(
            args=args,
            row=row,
            mode="hard",
            dry_run=dry_run,
        )

    waited = False
    final_view: dict[str, Any] | None = None
    if bool(args.wait) and not dry_run:
        waited = True
        final_view = _wait_cluster_node_not_healthy(
            caller=caller,
            entry_node=entry_node,
            node_id=node_id,
            timeout_s=float(args.wait_timeout),
            interval_s=float(args.wait_interval),
        )
    elif not dry_run:
        try:
            final_view = _fetch_cluster_view_snapshot(
                caller=caller,
                entry_node=entry_node,
                schema="v1",
            )
        except Exception:
            final_view = None

    try:
        state_model = _build_cluster_state_model(
            plan=plan,
            entry_node=entry_node,
            inspections=[],
            caller=caller,
            schema="v1",
            preferred_snapshot=(
                final_view
                if not dry_run
                else {
                    "schema_version": "v1",
                    "generated_at": time.time(),
                    "view_epoch": 0,
                    "health_summary": {"healthy": 0, "degraded": 0, "total": 0},
                    "nodes": [],
                }
            ),
        )
    except Exception:
        state_model = {
            "desired": _desired_state_payload(plan),
            "observed": {
                "entry_node": entry_node,
                "generated_at": None,
                "view_epoch": None,
                "health_summary": {},
                "node_count": 0,
                "nodes": [],
            },
            "drift": _compute_cluster_drift(
                desired_nodes=_desired_nodes_from_plan(plan),
                observed_nodes=[],
            ),
        }
    print(
        json.dumps(
            {
                "ok": True,
                "op": "cluster_leave",
                "node_id": node_id,
                "mode": mode,
                "waited": waited,
                "dry_run": dry_run,
                **state_model,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cluster_reconcile(args: argparse.Namespace) -> int:
    plan = _resolve_cluster_plan_from_args(
        args,
        require_ssh_target=bool(args.apply),
    )
    entry_node = _resolve_cluster_entry_node(args=args, plan=plan)
    caller = build_http_node_control_caller(timeout_s=float(args.timeout))

    initial_view = _fetch_cluster_view_snapshot(
        caller=caller,
        entry_node=entry_node,
        schema="v1",
    )
    desired_nodes = _desired_nodes_from_plan(plan)
    drift = _compute_cluster_drift(
        desired_nodes=desired_nodes,
        observed_nodes=_observed_nodes_from_snapshot(initial_view),
    )
    actions: list[dict[str, Any]] = []

    if bool(args.apply):
        for row in drift.get("missing", []):
            node_id = str(row.get("node_id") or "").strip()
            if not node_id:
                continue
            node_row = _select_plan_node(plan, node_id=node_id)
            _cluster_start_remote_node(
                args=args,
                plan=plan,
                row=node_row,
                dry_run=bool(args.dry_run),
            )
            actions.append({"action": "start_missing", "node_id": node_id})

        for row in drift.get("offline_desired", []):
            node_id = str(row.get("node_id") or "").strip()
            if not node_id:
                continue
            node_row = _select_plan_node(plan, node_id=node_id)
            _cluster_stop_remote_node(
                args=args,
                row=node_row,
                mode="hard",
                dry_run=bool(args.dry_run),
            )
            _cluster_start_remote_node(
                args=args,
                plan=plan,
                row=node_row,
                dry_run=bool(args.dry_run),
            )
            actions.append({"action": "restart_offline", "node_id": node_id})

    waited = False
    final_view = initial_view
    final_drift = drift
    if bool(args.wait):
        waited = True
        final_view, final_drift = _wait_cluster_drift(
            caller=caller,
            entry_node=entry_node,
            desired_nodes=desired_nodes,
            timeout_s=float(args.wait_timeout),
            interval_s=float(args.wait_interval),
        )
    else:
        try:
            final_view = _fetch_cluster_view_snapshot(
                caller=caller,
                entry_node=entry_node,
                schema="v1",
            )
            final_drift = _compute_cluster_drift(
                desired_nodes=desired_nodes,
                observed_nodes=_observed_nodes_from_snapshot(final_view),
            )
        except Exception:
            final_view = initial_view
            final_drift = drift

    print(
        json.dumps(
            {
                "ok": True,
                "op": "cluster_reconcile",
                "apply": bool(args.apply),
                "waited": waited,
                "actions": actions,
                "desired": _desired_state_payload(plan),
                "observed": _observed_state_payload(entry_node=entry_node, snapshot=final_view),
                "drift": final_drift,
                "dry_run": bool(args.dry_run),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _resolve_cluster_plan_from_args(
    args: argparse.Namespace,
    *,
    require_ssh_target: bool | None = None,
) -> dict[str, Any]:
    _apply_cluster_target_to_args(args)
    resolved_require_ssh_target = require_ssh_target
    if resolved_require_ssh_target is None:
        resolved_require_ssh_target = bool(getattr(args, "require_ssh_target", False))
    inventory = str(getattr(args, "inventory", "") or "").strip()
    if not inventory:
        raise ValueError(
            "cluster inventory unresolved: set --inventory or --cluster, "
            "or set FLOWNET_CLUSTER / ~/.flownet/config.yaml"
        )
    return resolve_cluster_inventory(
        inventory_path=inventory or None,
        seed_strategy=str(getattr(args, "seed_strategy", "full-mesh") or "full-mesh"),
        require_ssh_target=bool(resolved_require_ssh_target),
    )


def _resolve_optional_cluster_plan_from_args(
    args: argparse.Namespace,
    *,
    require_ssh_target: bool = False,
) -> dict[str, Any] | None:
    _apply_cluster_target_to_args(args)
    inventory = str(getattr(args, "inventory", "") or "").strip()
    if not inventory:
        return None
    return resolve_cluster_inventory(
        inventory_path=inventory or None,
        seed_strategy=str(getattr(args, "seed_strategy", "full-mesh") or "full-mesh"),
        require_ssh_target=bool(require_ssh_target),
    )


def _resolve_cluster_entry_node(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any] | None,
) -> str:
    _apply_cluster_target_to_args(args)
    entry_node = str(getattr(args, "entry_node", "") or "").strip()
    if entry_node:
        return entry_node
    if plan is None:
        return ""
    rows = _plan_nodes(plan)
    bind = str(rows[0].get("bind_address") or "").strip()
    if not bind:
        raise ValueError("entry node bind_address is empty in cluster plan")
    return bind


def _resolve_cluster_target_from_args(
    args: argparse.Namespace,
) -> dict[str, str] | None:
    try:
        return resolve_cluster_target(
            entry_node=str(getattr(args, "entry_node", "") or "").strip() or None,
            inventory=str(getattr(args, "inventory", "") or "").strip() or None,
            cluster=str(getattr(args, "cluster", "") or "").strip() or None,
        )
    except ValueError as exc:
        if str(exc).startswith("cluster target unresolved:"):
            return None
        raise


def _apply_cluster_target_to_args(args: argparse.Namespace) -> None:
    target = _resolve_cluster_target_from_args(args)
    if target is None:
        return
    if hasattr(args, "inventory") and not str(getattr(args, "inventory", "") or "").strip():
        resolved_inventory = str(target.get("inventory") or "").strip()
        if resolved_inventory:
            args.inventory = resolved_inventory
    if hasattr(args, "entry_node") and not str(getattr(args, "entry_node", "") or "").strip():
        resolved_entry = str(target.get("entry_node") or "").strip()
        if resolved_entry:
            args.entry_node = resolved_entry


def _select_plan_node(plan: dict[str, Any], *, node_id: str) -> dict[str, Any]:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        raise ValueError("node_id must be non-empty")
    for row in _plan_nodes(plan):
        if str(row.get("node_id") or "").strip() == normalized_node_id:
            return row
    raise ValueError(f"node_id not found in cluster inventory: {normalized_node_id!r}")


def _desired_nodes_from_plan(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if plan is None:
        return []
    nodes: list[dict[str, Any]] = []
    for row in _plan_nodes(plan):
        node_id = str(row.get("node_id") or "").strip()
        bind_address = str(row.get("bind_address") or "").strip()
        if not node_id:
            continue
        nodes.append(
            {
                "node_id": node_id,
                "bind_address": bind_address,
                "ssh_target": str(row.get("ssh_target") or "").strip(),
            }
        )
    return nodes


def _desired_state_payload(plan: dict[str, Any] | None) -> dict[str, Any]:
    nodes = _desired_nodes_from_plan(plan)
    source = dict(plan.get("source") or {}) if isinstance(plan, dict) else {}
    return {
        "source": source,
        "node_count": len(nodes),
        "nodes": nodes,
    }


def _observed_nodes_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    raw_nodes = snapshot.get("nodes")
    if not isinstance(raw_nodes, list):
        return []
    nodes: list[dict[str, Any]] = []
    for item in raw_nodes:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or "").strip()
        address = str(item.get("address") or "").strip()
        health = str(item.get("health") or "").strip().lower()
        if not node_id:
            continue
        if not health:
            health = "healthy" if bool(item.get("healthy")) else "unknown"
        nodes.append(
            {
                "node_id": node_id,
                "address": address,
                "health": health,
                "healthy": health == "healthy",
                "incarnation": str(item.get("incarnation") or "").strip(),
                "last_seen_ms": item.get("last_seen_ms"),
                "clock_ms": item.get("clock_ms"),
            }
        )
    return nodes


def _index_observed_nodes(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in _observed_nodes_from_snapshot(snapshot):
        node_id = str(row.get("node_id") or "").strip()
        if not node_id or node_id in indexed:
            continue
        indexed[node_id] = row
    return indexed


def _observed_state_payload(*, entry_node: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    health_summary = snapshot.get("health_summary")
    normalized_health_summary = dict(health_summary) if isinstance(health_summary, dict) else {}
    return {
        "entry_node": entry_node,
        "generated_at": snapshot.get("generated_at"),
        "view_epoch": snapshot.get("view_epoch"),
        "health_summary": normalized_health_summary,
        "node_count": len(_observed_nodes_from_snapshot(snapshot)),
        "nodes": _observed_nodes_from_snapshot(snapshot),
    }


def _compute_cluster_drift(
    *,
    desired_nodes: list[dict[str, Any]],
    observed_nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    desired_by_id: dict[str, dict[str, Any]] = {}
    for row in desired_nodes:
        node_id = str(row.get("node_id") or "").strip()
        if not node_id or node_id in desired_by_id:
            continue
        desired_by_id[node_id] = row

    observed_by_id: dict[str, dict[str, Any]] = {}
    for row in observed_nodes:
        node_id = str(row.get("node_id") or "").strip()
        if not node_id or node_id in observed_by_id:
            continue
        observed_by_id[node_id] = row

    missing = [
        {
            "node_id": node_id,
            "bind_address": str(desired_by_id[node_id].get("bind_address") or "").strip(),
        }
        for node_id in sorted(desired_by_id)
        if node_id not in observed_by_id
    ]
    extra = [
        {
            "node_id": node_id,
            "address": str(observed_by_id[node_id].get("address") or "").strip(),
            "health": str(observed_by_id[node_id].get("health") or "").strip().lower(),
        }
        for node_id in sorted(observed_by_id)
        if node_id not in desired_by_id
    ]
    offline = [
        {
            "node_id": node_id,
            "address": str(row.get("address") or "").strip(),
            "health": str(row.get("health") or "").strip().lower(),
        }
        for node_id, row in sorted(observed_by_id.items())
        if str(row.get("health") or "").strip().lower() != "healthy"
    ]
    offline_desired = [
        row for row in offline if str(row.get("node_id") or "").strip() in desired_by_id
    ]
    return {
        "missing": missing,
        "extra": extra,
        "offline": offline,
        "offline_desired": offline_desired,
        "summary": {
            "missing": len(missing),
            "extra": len(extra),
            "offline": len(offline),
            "offline_desired": len(offline_desired),
        },
    }


def _build_cluster_state_model(
    *,
    plan: dict[str, Any] | None,
    entry_node: str,
    inspections: list[dict[str, Any]],
    caller: Any,
    schema: str,
    preferred_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = preferred_snapshot
    if snapshot is None:
        for row in inspections:
            bind_address = str(row.get("bind_address") or "").strip()
            payload = row.get("payload")
            if entry_node and bind_address != entry_node:
                continue
            if isinstance(payload, dict) and isinstance(payload.get("nodes"), list):
                snapshot = payload
                break
        if snapshot is None and inspections:
            candidate = inspections[0].get("payload")
            if isinstance(candidate, dict) and isinstance(candidate.get("nodes"), list):
                snapshot = candidate
    if snapshot is None:
        if not entry_node:
            snapshot = {
                "schema_version": schema,
                "generated_at": time.time(),
                "view_epoch": 0,
                "health_summary": {"healthy": 0, "degraded": 0, "total": 0},
                "nodes": [],
            }
        else:
            snapshot = _fetch_cluster_view_snapshot(
                caller=caller,
                entry_node=entry_node,
                schema=schema,
            )

    desired_payload = _desired_state_payload(plan)
    observed_payload = _observed_state_payload(entry_node=entry_node, snapshot=snapshot)
    drift_payload = _compute_cluster_drift(
        desired_nodes=list(desired_payload["nodes"]),
        observed_nodes=list(observed_payload["nodes"]),
    )
    return {
        "desired": desired_payload,
        "observed": observed_payload,
        "drift": drift_payload,
    }


def _fetch_cluster_view_snapshot(
    *,
    caller: Any,
    entry_node: str,
    schema: str = "v1",
) -> dict[str, Any]:
    normalized_entry_node = str(entry_node or "").strip()
    if not normalized_entry_node:
        raise ValueError("entry_node is required")
    payload = caller(
        "cluster_view_snapshot",
        schema=schema,
        node_address=normalized_entry_node,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("cluster_view_snapshot must return mapping/object")
    return payload


def _wait_cluster_node_health(
    *,
    caller: Any,
    entry_node: str,
    node_id: str,
    timeout_s: float,
    interval_s: float,
) -> dict[str, Any]:
    normalized_node_id = str(node_id or "").strip()
    deadline = time.time() + max(0.0, float(timeout_s))
    while time.time() <= deadline:
        snapshot = _fetch_cluster_view_snapshot(
            caller=caller,
            entry_node=entry_node,
            schema="v1",
        )
        observed = _index_observed_nodes(snapshot).get(normalized_node_id)
        if observed is not None and str(observed.get("health") or "").strip().lower() == "healthy":
            return snapshot
        time.sleep(max(0.05, float(interval_s)))
    raise TimeoutError(f"node did not become healthy before timeout: {normalized_node_id}")


def _wait_cluster_node_not_healthy(
    *,
    caller: Any,
    entry_node: str,
    node_id: str,
    timeout_s: float,
    interval_s: float,
) -> dict[str, Any]:
    normalized_node_id = str(node_id or "").strip()
    deadline = time.time() + max(0.0, float(timeout_s))
    while time.time() <= deadline:
        snapshot = _fetch_cluster_view_snapshot(
            caller=caller,
            entry_node=entry_node,
            schema="v1",
        )
        observed = _index_observed_nodes(snapshot).get(normalized_node_id)
        if observed is None:
            return snapshot
        if str(observed.get("health") or "").strip().lower() != "healthy":
            return snapshot
        time.sleep(max(0.05, float(interval_s)))
    raise TimeoutError(f"node remained healthy before timeout: {normalized_node_id}")


def _wait_cluster_drift(
    *,
    caller: Any,
    entry_node: str,
    desired_nodes: list[dict[str, Any]],
    timeout_s: float,
    interval_s: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.time() + max(0.0, float(timeout_s))
    last_drift: dict[str, Any] | None = None
    while time.time() <= deadline:
        snapshot = _fetch_cluster_view_snapshot(
            caller=caller,
            entry_node=entry_node,
            schema="v1",
        )
        drift = _compute_cluster_drift(
            desired_nodes=desired_nodes,
            observed_nodes=_observed_nodes_from_snapshot(snapshot),
        )
        last_drift = drift
        summary = drift.get("summary") if isinstance(drift.get("summary"), dict) else {}
        if int(summary.get("missing", 0)) <= 0 and int(summary.get("offline_desired", 0)) <= 0:
            return snapshot, drift
        time.sleep(max(0.05, float(interval_s)))
    raise TimeoutError(
        "reconcile drift did not converge before timeout"
        f" (last={json.dumps(last_drift or {}, ensure_ascii=False, sort_keys=True)})"
    )


def _wait_node_unreachable(
    *,
    caller: Any,
    node_address: str,
    timeout_s: float,
    interval_s: float,
) -> None:
    deadline = time.time() + max(0.0, float(timeout_s))
    while time.time() <= deadline:
        try:
            caller("cluster_view_snapshot", schema="v1", node_address=node_address)
        except Exception:
            return
        time.sleep(max(0.05, float(interval_s)))
    raise TimeoutError(f"node endpoint is still reachable after timeout: {node_address}")


def _is_ssh_target_match(raw_row_target: str, raw_requested_target: str) -> bool:
    row_host = _ssh_target_host(str(raw_row_target or "").strip())
    requested_host = _ssh_target_host(str(raw_requested_target or "").strip())
    return bool(row_host and requested_host and row_host == requested_host)


def _ssh_target_host(raw_target: str) -> str:
    token = str(raw_target or "").strip()
    if not token:
        return ""
    if "@" in token:
        token = token.split("@", 1)[-1]
    return token.strip()


def _cluster_start_remote_node(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any],
    row: dict[str, Any],
    dry_run: bool,
) -> None:
    node_id = str(row.get("node_id") or "").strip()
    bind_address = str(row.get("bind_address") or "").strip()
    if not node_id or not bind_address:
        raise ValueError("cluster start node row is missing node_id/bind_address")
    remote_repo_root = str(getattr(args, "remote_repo_root", "") or "").strip()
    if not remote_repo_root:
        raise ValueError("remote_repo_root must be non-empty")
    remote_inventory_path = str(getattr(args, "remote_inventory_path", "") or "").strip()
    if not remote_inventory_path:
        remote_inventory_path = str(getattr(args, "inventory", "") or "").strip()
    if not remote_inventory_path:
        raise ValueError("remote inventory path is required when using --inventory")

    ssh_user, identity_file = _resolve_node_ssh_auth(args=args, row=row)
    ssh_base = _build_ssh_base_args(args=args, identity_file=identity_file)
    ssh_target = _qualify_ssh_target(str(row.get("ssh_target") or "").strip(), ssh_user)
    start_args = [
        str(getattr(args, "remote_python", "python") or "python"),
        "-m",
        "flownet.node.cli",
        "cluster",
        "start",
        "--node-id",
        node_id,
        "--seed-strategy",
        str(getattr(args, "seed_strategy", "full-mesh") or "full-mesh"),
        "--join-timeout",
        str(float(getattr(args, "join_timeout", 3.0))),
        "--gossip-interval",
        str(float(getattr(args, "gossip_interval", 1.0))),
        "--offline-timeout",
        str(float(getattr(args, "offline_timeout", 8.0))),
        "--http-timeout",
        str(float(getattr(args, "http_timeout", 2.0))),
    ]
    start_args.extend(["--inventory", remote_inventory_path])
    start_cmd = shlex.join(start_args)
    up_script = (
        "set -euo pipefail\n"
        f"PID_FILE={shlex.quote(str(getattr(args, 'remote_work_root', '/tmp/flownet_cluster_cli')) + '/pids/' + node_id + '.pid')}\n"
        f"LOG_FILE={shlex.quote(str(getattr(args, 'remote_work_root', '/tmp/flownet_cluster_cli')) + '/logs/' + node_id + '.log')}\n"
        'mkdir -p "$(dirname "${PID_FILE}")" "$(dirname "${LOG_FILE}")"\n'
        'if [[ -f "${PID_FILE}" ]]; then\n'
        '  old_pid="$(cat "${PID_FILE}" || true)"\n'
        '  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then\n'
        f'    echo "node_already_running:{node_id}:pid=${{old_pid}}"\n'
        "    exit 0\n"
        "  fi\n"
        "fi\n"
        f"cd {shlex.quote(remote_repo_root)}\n"
        "export PYTHONPATH='src:flownet/src:'\"${PYTHONPATH:-}\"\n"
        f'nohup {start_cmd} >"${{LOG_FILE}}" 2>&1 < /dev/null &\n'
        'new_pid="$!"\n'
        'echo "${new_pid}" >"${PID_FILE}"\n'
        f'echo "node_started:{node_id}:pid=${{new_pid}}"\n'
    )
    _ssh_run(
        ssh_base=ssh_base,
        target=ssh_target,
        script=up_script,
        dry_run=dry_run,
    )
    health_script = (
        f"{shlex.quote(str(getattr(args, 'remote_python', 'python') or 'python'))} - {shlex.quote(bind_address)} "
        f"{shlex.quote(str(float(getattr(args, 'health_timeout', 20.0))))} <<'PY'\n"
        "import json\n"
        "import sys\n"
        "import time\n"
        "from urllib import request\n"
        "address = sys.argv[1]\n"
        "timeout_s = float(sys.argv[2])\n"
        "deadline = time.time() + timeout_s\n"
        "while time.time() < deadline:\n"
        "    try:\n"
        "        with request.urlopen(f'http://{address}/healthz', timeout=1.0) as resp:\n"
        "            payload = json.loads(resp.read().decode('utf-8'))\n"
        "        if bool(payload.get('ok')):\n"
        "            raise SystemExit(0)\n"
        "    except Exception:\n"
        "        time.sleep(0.2)\n"
        "raise SystemExit(1)\n"
        "PY\n"
    )
    _ssh_run(
        ssh_base=ssh_base,
        target=ssh_target,
        script=health_script,
        dry_run=dry_run,
    )


def _cluster_stop_remote_node(
    *,
    args: argparse.Namespace,
    row: dict[str, Any],
    mode: str,
    dry_run: bool,
) -> None:
    node_id = str(row.get("node_id") or "").strip()
    if not node_id:
        raise ValueError("cluster stop node row is missing node_id")
    ssh_user, identity_file = _resolve_node_ssh_auth(args=args, row=row)
    ssh_base = _build_ssh_base_args(args=args, identity_file=identity_file)
    ssh_target = _qualify_ssh_target(str(row.get("ssh_target") or "").strip(), ssh_user)
    remote_work_root = str(
        getattr(args, "remote_work_root", "/tmp/flownet_cluster_cli") or ""
    ).strip()
    if not remote_work_root:
        raise ValueError("remote_work_root must be non-empty")

    if mode == "soft":
        down_script = (
            "set -euo pipefail\n"
            f"PID_FILE={shlex.quote(remote_work_root + '/pids/' + node_id + '.pid')}\n"
            'if [[ -f "${PID_FILE}" ]]; then\n'
            '  pid="$(cat "${PID_FILE}" || true)"\n'
            '  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then\n'
            '    kill "${pid}" >/dev/null 2>&1 || true\n'
            "  fi\n"
            "fi\n"
        )
    else:
        down_script = (
            "set -euo pipefail\n"
            f"PID_FILE={shlex.quote(remote_work_root + '/pids/' + node_id + '.pid')}\n"
            'if [[ -f "${PID_FILE}" ]]; then\n'
            '  pid="$(cat "${PID_FILE}" || true)"\n'
            '  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then\n'
            '    kill "${pid}" >/dev/null 2>&1 || true\n'
            "    sleep 0.5\n"
            '    if kill -0 "${pid}" >/dev/null 2>&1; then\n'
            '      kill -9 "${pid}" >/dev/null 2>&1 || true\n'
            "    fi\n"
            "  fi\n"
            '  rm -f "${PID_FILE}"\n'
            "fi\n"
        )
    _ssh_run(
        ssh_base=ssh_base,
        target=ssh_target,
        script=down_script,
        dry_run=dry_run,
    )


def _plan_nodes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = plan.get("nodes")
    if not isinstance(rows, list) or not rows:
        raise ValueError("cluster plan nodes is empty")
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    if not out:
        raise ValueError("cluster plan nodes is empty")
    return out


def _resolve_ssh_identity_file(raw_path: str) -> str:
    normalized = str(raw_path or "").strip()
    if not normalized:
        raise ValueError("ssh_identity_file is required")
    candidate = Path(normalized).expanduser()
    if not candidate.exists():
        raise ValueError(f"ssh_identity_file not found: {candidate}")
    if candidate.is_dir():
        raise ValueError(f"ssh_identity_file must be a file: {candidate}")
    return str(candidate)


def _qualify_ssh_target(target: str, ssh_user: str) -> str:
    normalized_target = str(target or "").strip()
    if not normalized_target:
        raise ValueError("ssh target must be non-empty")
    normalized_user = str(ssh_user or "").strip()
    if normalized_user and "@" not in normalized_target:
        return f"{normalized_user}@{normalized_target}"
    return normalized_target


def _resolve_node_ssh_auth(
    *,
    args: argparse.Namespace,
    row: dict[str, Any],
) -> tuple[str, str]:
    node_id = str(row.get("node_id") or "").strip() or "<unknown>"
    cli_user = str(getattr(args, "ssh_user", "") or "").strip()
    inv_user = str(row.get("ssh_user") or "").strip()
    resolved_user = cli_user or inv_user

    cli_identity = str(getattr(args, "ssh_identity_file", "") or "").strip()
    inv_identity = str(row.get("ssh_identity_file") or "").strip()
    raw_identity = cli_identity or inv_identity
    if not raw_identity:
        raise ValueError(
            "ssh_identity_file is required; pass --ssh-identity-file or set "
            f"inventory ssh.identity_file / nodes[].ssh_identity_file (node_id={node_id})"
        )
    resolved_identity = _resolve_ssh_identity_file(raw_identity)
    return resolved_user, resolved_identity


def _build_ssh_base_args(*, args: argparse.Namespace, identity_file: str) -> list[str]:
    base = [
        "ssh",
        "-i",
        identity_file,
        "-p",
        str(int(args.ssh_port)),
        "-o",
        f"ConnectTimeout={float(args.ssh_connect_timeout)}",
        "-o",
        f"StrictHostKeyChecking={str(args.ssh_strict_host_key_checking)}",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=4",
    ]
    for item in list(getattr(args, "ssh_extra_opt", []) or []):
        token = str(item or "").strip()
        if not token:
            continue
        base.extend(shlex.split(token))
    return base


def _ssh_run(
    *,
    ssh_base: list[str],
    target: str,
    script: str,
    dry_run: bool,
) -> None:
    wrapped = f"bash -lc {shlex.quote(script)}"
    cmd = [*ssh_base, target, wrapped]
    if dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "op": "ssh",
                    "target": target,
                    "cmd": shlex.join(cmd),
                },
                ensure_ascii=False,
            )
        )
        return
    subprocess.run(cmd, check=True)


def _run_inspect_call(
    *,
    caller: Any,
    node_address: str,
    view: str,
    schema: str,
) -> Any:
    if view == "cluster":
        return caller(
            "cluster_view_snapshot",
            schema=schema,
            node_address=node_address,
        )
    if view == "gossip":
        return caller("cluster_gossip_stats", node_address=node_address)
    if view == "contract":
        return caller("cluster_contract_snapshot", node_address=node_address)
    if view == "nodes":
        return caller("list_runtime_nodes", node_address=node_address)
    if view == "actors":
        return caller("list_runtime_actors", node_address=node_address)
    if view == "topics":
        return caller("list_runtime_topics", node_address=node_address)
    raise ValueError(f"unsupported inspect view: {view}")


def _parse_metadata_pairs(items: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in items:
        token = str(item or "").strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"metadata must be k=v, got: {token!r}")
        key, value = token.split("=", 1)
        normalized_key = str(key or "").strip()
        if not normalized_key:
            raise ValueError(f"metadata key must be non-empty, got: {token!r}")
        metadata[normalized_key] = str(value).strip()
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
