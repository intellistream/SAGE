#!/usr/bin/env python3
"""Legacy wrapper for environment management utilities.

The full implementation lives inside the :mod:`sage.tools` package. This script
remains to support existing automation that has not yet been updated to the new
CLI commands (``sage config env ...``).
"""

from __future__ import annotations

import sys
from typing import Sequence

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "sage-tools" / "src"))

from sage.tools.cli.commands.env import run_setup_interactive
from sage.tools.utils import env as env_utils


def _print_status(status: dict) -> None:
    print("🔍 环境变量状态")
    print("=" * 40)
    print(f"项目根目录: {status['project_root']}")
    print(f"python-dotenv 可用: {status['dotenv_available']}")
    print(f".env: {status['env_file_exists']} ({status['env_file']})")
    print(f".env.template: {status['env_template_exists']} ({status['env_template']})")
    print("\n🔑 API Keys:")
    for key, info in status["api_keys"].items():
        icon = "✅" if info["set"] else "❌"
        length = info["length"] if info["set"] else 0
        print(f"  {icon} {key} ({length} chars)")


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])

    if args and args[0] == "setup":
        run_setup_interactive()
        return 0

    override = "--override" in args
    path_arg = next((arg for arg in args if not arg.startswith("-")), None)

    try:
        loaded, resolved = env_utils.load_environment_file(
            None if path_arg is None else Path(path_arg), override=override
        )
    except RuntimeError as exc:  # pragma: no cover - legacy wrapper
        print(f"⚠️ {exc}")
        return 1

    if loaded:
        print(f"✅ 已加载 .env: {resolved}")
    else:
        target = resolved or env_utils.find_project_root() / ".env"
        print(f"ℹ️ 未找到 .env 文件: {target}")

    status = env_utils.check_environment_status()
    _print_status(status)

    if not any(info["set"] for info in status["api_keys"].values()):
        print("\n⚠️ 未检测到任何 API Keys! 建议运行: sage config env setup")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main(sys.argv[1:]))
