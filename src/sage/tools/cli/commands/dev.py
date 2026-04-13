#!/usr/bin/env python3
"""In-tree ``sage-dev`` CLI entrypoint.

This replaces the external ``isage-dev-tools`` dependency for the core
developer workflow commands used by SAGE itself.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from sage._version import __version__


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    return int(proc.returncode)


def _run_shell(script: Path, args: Sequence[str] | None = None) -> int:
    cmd = ["bash", str(script)]
    if args:
        cmd.extend(args)
    return _run(cmd, cwd=_repo_root())


def _add_quality_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("quality", help="Run code quality tasks")
    quality_sub = parser.add_subparsers(dest="quality_command")

    check = quality_sub.add_parser("check", help="Run quality checks")
    check.add_argument("--all-files", action="store_true", help="Accepted for compatibility")
    check.add_argument(
        "--readme", action="store_true", help="Run doc quality check as part of quality command"
    )

    fix = quality_sub.add_parser("fix", help="Run quality auto-fixes")
    fix.add_argument("--all-files", action="store_true", help="Accepted for compatibility")
    fix.add_argument(
        "--readme", action="store_true", help="Run doc quality check as part of quality command"
    )

    parser.add_argument("--check-only", action="store_true", help="Legacy alias for quality check")
    parser.add_argument("--all-files", action="store_true", help="Accepted for compatibility")
    parser.add_argument(
        "--readme", action="store_true", help="Run doc quality check as part of quality command"
    )


def _add_project_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("project", help="Project-level commands")
    project_sub = parser.add_subparsers(dest="project_command")

    test = project_sub.add_parser("test", help="Run test suite")
    test.add_argument("--coverage", action="store_true")
    test.add_argument("--test-type", choices=["all", "unit", "integration"], default="all")
    test.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Extra args passed to pytest")

    clean = project_sub.add_parser("clean", help="Clean caches and build artifacts")
    clean.add_argument("--target", choices=["all", "cache"], default="all")
    clean.add_argument("--dry-run", action="store_true")


def _add_maintain_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("maintain", help="Maintenance commands")
    maintain_sub = parser.add_subparsers(dest="maintain_command")

    hooks = maintain_sub.add_parser("hooks", help="Git hooks management")
    hooks_sub = hooks.add_subparsers(dest="hooks_command")

    install = hooks_sub.add_parser("install", help="Install git hooks")
    install.add_argument("--profile", default="lightweight")
    install.add_argument("--mode", default="auto")

    hooks_sub.add_parser("status", help="Show git hooks status")
    maintain_sub.add_parser("doctor", help="Run maintenance doctor checks")


def _add_docs_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("docs", help="Documentation commands")
    docs_sub = parser.add_subparsers(dest="docs_command")
    docs_sub.add_parser("build", help="Run docs quality check")
    docs_sub.add_parser("serve", help="Print docs serve guidance")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sage-dev", description="SAGE in-tree developer CLI")
    sub = parser.add_subparsers(dest="command")

    parser.add_argument("--version", action="store_true", help="Show version")

    _add_quality_parser(sub)
    _add_project_parser(sub)
    _add_maintain_parser(sub)
    _add_docs_parser(sub)

    # Compatibility aliases used in docs and Makefile.
    sub.add_parser("test", help="Alias for project test")
    sub.add_parser("status", help="Show basic developer environment status")

    return parser


def _quality_action(args: argparse.Namespace) -> int:
    repo = _repo_root()

    quality_cmd = args.quality_command
    if quality_cmd is None:
        quality_cmd = "check" if args.check_only else "fix"

    if shutil.which("ruff") is None:
        print("[sage-dev] ruff not found in PATH")
        return 1

    base = ["ruff", "check", "--config", "tools/ruff.toml", "src", "tools"]
    if quality_cmd == "fix":
        rc = _run(base[:2] + ["--fix", *base[2:]], cwd=repo)
        if rc != 0:
            return rc
        rc = _run(["ruff", "format", "--config", "tools/ruff.toml", "src", "tools"], cwd=repo)
    else:
        rc = _run(base, cwd=repo)
        if rc != 0:
            return rc
        rc = _run(
            ["ruff", "format", "--check", "--config", "tools/ruff.toml", "src", "tools"], cwd=repo
        )

    if rc != 0:
        return rc

    if args.readme:
        return _run_shell(repo / "tools/maintenance/check_docs.sh")
    return 0


def _project_test_action(args: argparse.Namespace) -> int:
    repo = _repo_root()
    # Ensure .sage directory exists
    sage_dir = repo / ".sage"
    sage_dir.mkdir(exist_ok=True)
    cmd = ["pytest", "src/tests"]
    if args.coverage:
        # Set COVERAGE_FILE env to .sage/.coverage
        import os

        os.environ["COVERAGE_FILE"] = str(sage_dir / ".coverage")
        cmd.extend(["--cov=src/sage", "--cov-report=term-missing"])
    if args.test_type == "unit":
        cmd.extend(["-m", "not integration"])
    elif args.test_type == "integration":
        cmd.extend(["-m", "integration"])
    if args.pytest_args:
        extra = list(args.pytest_args)
        if extra and extra[0] == "--":
            extra = extra[1:]
        cmd.extend(extra)
    return _run(cmd, cwd=repo)


def _project_clean_action(args: argparse.Namespace) -> int:
    repo = _repo_root()
    if args.dry_run:
        print("[sage-dev] dry-run enabled; would run cleanup helper")
        return 0

    if args.target == "cache":
        return _run(["bash", "tools/install/fixes/build_cache_cleaner.sh", "clean"], cwd=repo)
    return _run_shell(repo / "tools/maintenance/helpers/quick_cleanup.sh")


def _hooks_status() -> int:
    repo = _repo_root()
    hooks = ["pre-commit", "pre-push", "post-checkout"]
    missing = 0
    for name in hooks:
        hook_path = repo / ".git" / "hooks" / name
        exists = hook_path.exists() and hook_path.is_file()
        print(f"{name}: {'installed' if exists else 'missing'}")
        if not exists:
            missing += 1
    return 0 if missing == 0 else 1


def _maintain_action(args: argparse.Namespace) -> int:
    repo = _repo_root()

    if args.maintain_command == "doctor":
        return _run_shell(repo / "tools/maintenance/sage-maintenance.sh", ["doctor"])

    if args.maintain_command != "hooks":
        return 1

    if args.hooks_command == "install":
        return _run_shell(repo / "tools/maintenance/setup_hooks.sh", ["--all", "--force"])
    if args.hooks_command == "status":
        return _hooks_status()
    return 1


def _docs_action(args: argparse.Namespace) -> int:
    repo = _repo_root()
    if args.docs_command == "build":
        return _run_shell(repo / "tools/maintenance/check_docs.sh")
    if args.docs_command == "serve":
        print(
            "SAGE meta repo has no built-in docs server. Use sage-docs repository for mkdocs serve."
        )
        return 0
    return 1


def _status_action() -> int:
    print(f"sage-dev in-tree CLI ready (SAGE {__version__})")
    return 0


def _dispatch(args: argparse.Namespace) -> int:
    if args.version:
        print(f"sage-dev (in-tree) {__version__}")
        return 0

    if args.command == "quality":
        return _quality_action(args)
    if args.command == "project":
        if args.project_command == "test":
            return _project_test_action(args)
        if args.project_command == "clean":
            return _project_clean_action(args)
        return 1
    if args.command == "maintain":
        return _maintain_action(args)
    if args.command == "docs":
        return _docs_action(args)
    if args.command == "test":
        return _run(["pytest", "src/tests"], cwd=_repo_root())
    if args.command == "status":
        return _status_action()

    return _status_action()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return _dispatch(args)


def run_with_suggestions(argv: Sequence[str] | None = None) -> int:
    """Compatibility entrypoint name expected by legacy wrappers."""
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
