"""Test cases for ``sage config`` command group."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _patch_config_manager(factory: Callable[[], FakeConfigManager]):
    def _factory():
        manager = factory()
        return patch(
            "sage.tools.cli.config_manager.get_config_manager", return_value=manager
        )

    return _factory


def collect_cases() -> list[CLITestCase]:
    def make_show_manager() -> FakeConfigManager:
        manager = FakeConfigManager()
        manager.save_config(manager.load_config())
        return manager

    init_manager = FakeConfigManager()
    init_called = {"value": False}

    def custom_init():
        init_called["value"] = True
        init_manager.save_config(init_manager.load_config())

    init_manager.init_config = custom_init  # type: ignore[assignment]

    def check_init(result):
        assert init_called["value"], "Config init should have been invoked"

    def make_env_status(
        *,
        env_exists: bool,
        template_exists: bool,
    ) -> dict:
        return {
            "dotenv_available": True,
            "project_root": Path("/project"),
            "env_file_exists": env_exists,
            "env_template_exists": template_exists,
            "env_file": Path("/project/.env"),
            "env_template": Path("/project/.env.template"),
            "api_keys": {
                "OPENAI_API_KEY": {"set": False, "length": 0},
                "HF_TOKEN": {"set": False, "length": 0},
            },
        }

    def patch_env_status(*statuses: dict):
        values = list(statuses)

        def _side_effect():
            if values:
                return values.pop(0)
            return statuses[-1]

        return patch(
            "sage.tools.cli.commands.env.env_utils.check_environment_status",
            side_effect=_side_effect,
        )

    return [
        CLITestCase(
            "sage config show",
            ["config", "show"],
            app=sage_app,
            patch_factories=[_patch_config_manager(make_show_manager)],
        ),
        CLITestCase(
            "sage config init --force",
            ["config", "init", "--force"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.config_manager.get_config_manager",
                    return_value=init_manager,
                )
            ],
            check=check_init,
        ),
        CLITestCase(
            "sage config env load success",
            ["config", "env", "load"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.env.env_utils.load_environment_file",
                    return_value=(True, Path("/tmp/.env")),
                )
            ],
        ),
        CLITestCase(
            "sage config env load missing",
            ["config", "env", "load"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.env.env_utils.load_environment_file",
                    return_value=(False, Path("/tmp/.env")),
                )
            ],
            expected_exit_code=1,
        ),
        CLITestCase(
            "sage config env check",
            ["config", "env", "check"],
            app=sage_app,
            patch_factories=[lambda: patch_env_status(make_env_status(env_exists=True, template_exists=True))],
        ),
        CLITestCase(
            "sage config env setup",
            ["config", "env", "setup", "--no-open"],
            app=sage_app,
            patch_factories=[
                lambda: patch_env_status(
                    make_env_status(env_exists=False, template_exists=False),
                    make_env_status(env_exists=False, template_exists=False),
                ),
                lambda: patch("sage.tools.cli.commands.env.typer.confirm", return_value=False),
            ],
        ),
    ]
