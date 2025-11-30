"""Test cases for ``sage cluster`` command group."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _patch(target: str, **kwargs):
    return lambda: patch(target, **kwargs)


def _patch_cluster_config() -> list:
    manager = FakeConfigManager()
    return [
        _patch(
            "sage.tools.cli.commands.cluster.get_config_manager",
            return_value=manager,
        )
    ]


def _patch_time_sleep():
    return _patch("sage.cli.commands.platform.cluster.time.sleep", return_value=None)


def _patch_start_dependencies():
    return [
        _patch("sage.cli.commands.platform.cluster.start_head", return_value=None),
        _patch("sage.cli.commands.platform.cluster.start_workers", return_value=None),
        _patch(
            "sage.cli.commands.platform.cluster.get_config_manager",
            return_value=FakeConfigManager(),
        ),
        _patch_time_sleep(),
    ]


def _patch_stop_dependencies():
    return [
        _patch("sage.cli.commands.platform.cluster.stop_workers", return_value=None),
        _patch("sage.cli.commands.platform.cluster.stop_head", return_value=None),
        _patch_time_sleep(),
    ]


def _patch_status_dependencies():
    manager = FakeConfigManager()
    manager.add_worker_ssh_host("worker-node-1")
    return [
        _patch(
            "sage.cli.commands.platform.cluster.get_config_manager",
            return_value=manager,
        ),
        _patch("sage.cli.commands.platform.cluster.status_head", return_value=None),
        _patch("sage.cli.commands.platform.cluster.status_workers", return_value=None),
    ]


def _patch_deploy_dependencies():
    deployment = SimpleNamespace(deploy_to_all_workers=lambda: (2, 2))
    return [
        _patch(
            "sage.cli.commands.platform.cluster.DeploymentManager",
            return_value=deployment,
        )
    ]


def _patch_scale_dependencies():
    return [
        _patch("sage.cli.commands.platform.cluster.add_worker", return_value=None),
        _patch("sage.cli.commands.platform.cluster.remove_worker", return_value=None),
    ]


def collect_cases() -> list[CLITestCase]:
    patches = _patch_cluster_config()

    return [
        CLITestCase(
            "sage cluster info",
            ["cluster", "info"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage cluster version",
            ["cluster", "version"],
            app=sage_app,
        ),
        CLITestCase(
            "sage cluster start",
            ["cluster", "start"],
            app=sage_app,
            patch_factories=_patch_start_dependencies(),
        ),
        CLITestCase(
            "sage cluster stop",
            ["cluster", "stop"],
            app=sage_app,
            patch_factories=_patch_stop_dependencies(),
        ),
        CLITestCase(
            "sage cluster restart",
            ["cluster", "restart"],
            app=sage_app,
            patch_factories=_patch_start_dependencies() + _patch_stop_dependencies(),
        ),
        CLITestCase(
            "sage cluster status",
            ["cluster", "status"],
            app=sage_app,
            patch_factories=_patch_status_dependencies(),
        ),
        CLITestCase(
            "sage cluster deploy",
            ["cluster", "deploy"],
            app=sage_app,
            patch_factories=_patch_deploy_dependencies(),
        ),
        CLITestCase(
            "sage cluster scale add",
            ["cluster", "scale", "add", "worker:22"],
            app=sage_app,
            patch_factories=_patch_scale_dependencies(),
        ),
        CLITestCase(
            "sage cluster scale remove",
            ["cluster", "scale", "remove", "worker:22"],
            app=sage_app,
            patch_factories=_patch_scale_dependencies(),
        ),
    ]
