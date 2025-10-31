"""Helper utilities for diagnosing the local SAGE installation."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import pkgutil
import subprocess
import sys
import traceback
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import parse as parse_version
from rich.console import Console
from rich.table import Table

DEFAULT_DEPENDENCIES: dict[str, str] = {
    "intellistream-sage-kernel": "0.1.5",
    "intellistream-sage-utils": "0.1.3",
    "intellistream-sage-middleware": "0.1.3",
    "intellistream-sage-cli": "0.1.3",
}


@dataclass
class DependencyStatus:
    name: str
    required: str
    installed: str | None
    compatible: bool
    error: str | None = None


def _get_console(console: Console | None) -> Console:
    return console or Console()


def _gather_dependency_status(
    dependencies: dict[str, str],
) -> list[DependencyStatus]:
    statuses: list[DependencyStatus] = []

    for package, minimum in dependencies.items():
        try:
            # 使用 importlib.metadata 替代 pkg_resources
            installed_version = importlib.metadata.version(package)
            compatible = parse_version(installed_version) >= parse_version(minimum)
            statuses.append(
                DependencyStatus(
                    name=package,
                    required=minimum,
                    installed=installed_version,
                    compatible=compatible,
                )
            )
        except importlib.metadata.PackageNotFoundError:
            statuses.append(
                DependencyStatus(
                    name=package,
                    required=minimum,
                    installed=None,
                    compatible=False,
                    error="未安装",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            statuses.append(
                DependencyStatus(
                    name=package,
                    required=minimum,
                    installed=None,
                    compatible=False,
                    error=str(exc),
                )
            )

    return statuses


def _render_status_table(statuses: Iterable[DependencyStatus], console: Console) -> None:
    table = Table(title="SAGE 依赖兼容性", show_lines=True)
    table.add_column("依赖包")
    table.add_column("最低版本", justify="right")
    table.add_column("当前版本", justify="right")
    table.add_column("状态")

    for status in statuses:
        if status.compatible:
            state = "✅ 兼容"
            installed = status.installed or "—"
        else:
            reason = status.error or "版本过低"
            state = f"❌ 不兼容 ({reason})"
            installed = status.installed or "未安装"
        table.add_row(status.name, status.required, installed, state)

    console.print(table)


def check_dependency_versions(
    dependencies: dict[str, str] | None = None,
    *,
    console: Console | None = None,
    verify_import: bool = True,
) -> bool:
    """Check whether required dependencies satisfy minimum versions.

    Parameters
    ----------
    dependencies:
        Mapping of package name to minimum required version. When omitted, the
        default closed-source package requirements are used.
    console:
        Optional ``rich.console.Console`` used for rendering output.
    verify_import:
        When ``True``, attempt to import ``JobManagerClient`` for an extra
        runtime readiness check.

    Returns
    -------
    bool
        ``True`` when all dependencies are compatible; ``False`` otherwise.
    """

    console = _get_console(console)
    dependencies = dependencies or DEFAULT_DEPENDENCIES

    console.rule("依赖兼容性检查")
    statuses = _gather_dependency_status(dependencies)
    _render_status_table(statuses, console)

    incompatible = [status for status in statuses if not status.compatible]
    if incompatible:
        console.print("[yellow]\n需要关注的依赖:\n")
        for status in incompatible:
            console.print(f"  • {status.name} (需要 >= {status.required})")

        package_list = " ".join(status.name for status in incompatible)
        if package_list:
            console.print(f"\n建议升级命令: [bold]pip install --upgrade {package_list}[/bold]")

        if verify_import:
            console.print("\n尝试验证关键模块导入…")
            try:
                from sage.kernel.runtime.jobmanager_client import JobManagerClient  # noqa: F401
            except Exception as exc:  # pragma: no cover - import runtime dependent
                console.print(f"❌ JobManagerClient 导入失败: {exc}")
            else:
                console.print("✅ JobManagerClient 导入成功")

        return False

    console.print("\n✅ 所有依赖版本兼容，系统应该可以正常工作")
    return True


def _resolve_project_root(
    project_root: os.PathLike[str] | str | None = None,
) -> Path:
    if project_root is None:
        return Path.cwd()
    return Path(project_root).expanduser().resolve()


def run_installation_diagnostics(
    project_root: os.PathLike[str] | str | None = None,
    *,
    console: Console | None = None,
) -> None:
    """Render a comprehensive installation diagnostic similar to legacy scripts."""

    console = _get_console(console)
    project_path = _resolve_project_root(project_root)

    console.print("🔍 SAGE 完整安装诊断")
    console.print("=" * 50)

    import_results: dict[str, dict[str, Any]] = {}

    try:
        console.print("📦 基础导入测试...")
        imports_to_test = [
            "sage",
            "sage.common",
            "sage.kernel",
            "sage.libs",
            "sage.middleware",
        ]

        for module in imports_to_test:
            try:
                imported_module = importlib.import_module(module)
                version = getattr(imported_module, "__version__", "Unknown")
                module_path = getattr(
                    imported_module,
                    "__file__",
                    getattr(imported_module, "__path__", "Unknown"),
                )
                import_results[module] = {
                    "status": "success",
                    "version": version,
                    "path": (str(module_path) if module_path != "Unknown" else module_path),
                }
                console.print(f"  ✅ {module} (版本: {version})")
            except ImportError as exc:
                import_results[module] = {"status": "failed", "error": str(exc)}
                console.print(f"  ❌ {module}: {exc}")
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                import_results[module] = {"status": "error", "error": str(exc)}
                console.print(f"  ❌ {module}: {exc}")

        console.print("\n🔗 命名空间包检查...")
        try:
            import sage

            if hasattr(sage, "__path__"):
                console.print(f"  ✅ sage 命名空间路径: {sage.__path__}")
                for _, name, _ in pkgutil.iter_modules(sage.__path__, sage.__name__ + "."):
                    if name.split(".")[-1] in {
                        "common",
                        "kernel",
                        "libs",
                        "middleware",
                        "tools",
                    }:
                        console.print(f"    📦 发现子包: {name}")
            else:
                console.print("  ⚠️  sage 不是命名空间包")
        except Exception as exc:  # pragma: no cover - import runtime dependent
            console.print(f"  ❌ 命名空间检查失败: {exc}")

        console.print("\n🏗️ 包结构检查...")
        packages_dir = project_path / "packages"
        if packages_dir.exists():
            for package_dir in sorted(packages_dir.iterdir()):
                if not package_dir.is_dir() or not package_dir.name.startswith("sage-"):
                    continue

                console.print(f"  📦 {package_dir.name}")
                console.print(
                    "    ✅ pyproject.toml"
                    if (package_dir / "pyproject.toml").exists()
                    else "    ❌ pyproject.toml 缺失"
                )
                console.print(
                    "    ✅ src/ 目录" if (package_dir / "src").exists() else "    ⚠️  src/ 目录缺失"
                )
                console.print(
                    "    ✅ tests/ 目录"
                    if (package_dir / "tests").exists()
                    else "    ⚠️  tests/ 目录缺失"
                )
        else:
            console.print("  ❌ packages 目录不存在")

        console.print("\n🌍 环境变量检查...")
        for var in ["SAGE_HOME", "PYTHONPATH", "PATH"]:
            value = os.environ.get(var)
            if value:
                abbreviated = value[:100] + ("..." if len(value) > 100 else "")
                console.print(f"  ✅ {var}: {abbreviated}")
            else:
                console.print(f"  ⚠️  {var}: 未设置")

        console.print("\n🖥️ CLI 工具检查...")
        cli_commands: Iterable[tuple[str, list[str]]] = [
            ("sage", ["sage", "--help"]),
            ("sage-dev", ["sage", "dev", "--help"]),
        ]
        for label, command in cli_commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    console.print(f"  ✅ {label} 可用")
                else:
                    console.print(f"  ❌ {label} 返回错误码: {result.returncode}")
            except subprocess.TimeoutExpired:
                console.print(f"  ⚠️  {label} 超时")
            except FileNotFoundError:
                console.print(f"  ❌ {label} 未找到")
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"  ❌ {label} 检查失败: {exc}")

        console.print("\n📚 关键依赖检查...")
        key_dependencies = [
            "typer",
            "rich",
            "pydantic",
            "fastapi",
            "pytest",
            "numpy",
            "pandas",
        ]
        for dep in key_dependencies:
            try:
                imported = importlib.import_module(dep)
                version = getattr(imported, "__version__", "Unknown")
                console.print(f"  ✅ {dep} (版本: {version})")
            except ImportError:
                console.print(f"  ⚠️  {dep} 未安装")
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"  ❌ {dep} 检查失败: {exc}")

        console.print("\n📋 诊断总结:")
        total_imports = len(import_results)
        successful_imports = sum(
            1 for result in import_results.values() if result.get("status") == "success"
        )
        console.print(f"  📊 导入成功率: {successful_imports}/{total_imports}")
        if successful_imports == total_imports:
            console.print("  🎉 SAGE 安装完整，所有模块可正常导入")
        elif successful_imports > 0:
            console.print("  ⚠️  SAGE 部分安装，部分模块存在问题")
        else:
            console.print("  ❌ SAGE 安装存在严重问题，无法导入核心模块")

        console.print("\n✅ 完整诊断完成")

    except Exception as exc:  # pragma: no cover - defensive top-level handling
        console.print(f"[red]诊断失败: {exc}[/red]")
        console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")


def collect_packages_status(
    project_root: os.PathLike[str] | str | None = None,
) -> dict[str, Any]:
    """Collect package status information for the provided project root."""

    project_path = _resolve_project_root(project_root)
    packages_dir = project_path / "packages"

    if not packages_dir.exists():
        return {"error": "packages directory not found"}

    packages_status: dict[str, dict[str, Any]] = {}

    for package_dir in sorted(packages_dir.iterdir()):
        if not package_dir.is_dir() or not package_dir.name.startswith("sage-"):
            continue

        package_name = package_dir.name
        module_name = package_name.replace("-", ".")
        status_info: dict[str, Any] = {
            "name": package_name,
            "path": str(package_dir),
            "has_pyproject": (package_dir / "pyproject.toml").exists(),
            "has_setup": (package_dir / "setup.py").exists(),
            "has_tests": (package_dir / "tests").exists(),
            "version": "unknown",
        }

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import importlib, sys; "
                        f"mod = importlib.import_module('{module_name}'); "
                        "print(getattr(mod, '__version__', 'unknown'))"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                status_info["version"] = result.stdout.strip()
                status_info["import_status"] = "success"
            else:
                status_info["import_status"] = "failed"
                status_info["import_error"] = result.stderr.strip()
        except Exception as exc:  # pragma: no cover - defensive
            status_info["import_status"] = "error"
            status_info["import_error"] = str(exc)

        packages_status[package_name] = status_info

    return {"total_packages": len(packages_status), "packages": packages_status}


def print_packages_status_summary(
    project_root: os.PathLike[str] | str | None = None,
    *,
    console: Console | None = None,
) -> None:
    """Render a summary of package installation status."""

    console = _get_console(console)
    data = collect_packages_status(project_root)

    console.print("\n📦 包状态摘要:")

    if "error" in data:
        console.print(f"[red]❌ {data['error']}[/red]")
        return

    total = data["total_packages"]
    packages = data["packages"]

    importable = sum(1 for pkg in packages.values() if pkg.get("import_status") == "success")
    has_tests = sum(1 for pkg in packages.values() if pkg.get("has_tests", False))

    console.print(f"  📊 总包数: {total}")
    console.print(f"  ✅ 可导入: {importable}/{total}")
    console.print(f"  🧪 有测试: {has_tests}/{total}")


def _check_package_dependencies(
    package_name: str,
    console: Console,
    verbose: bool,
) -> None:
    console.print(f"    🔗 检查 {package_name} 依赖...")
    if verbose:
        console.print("    ℹ️  依赖检查功能待完善")


def print_packages_status(
    project_root: os.PathLike[str] | str | None = None,
    *,
    console: Console | None = None,
    verbose: bool = False,
    check_versions: bool = False,
    check_dependencies: bool = False,
) -> None:
    """Display package status details using Rich formatting."""

    console = _get_console(console)
    console.print("📦 SAGE Framework 包状态详情")
    console.print("=" * 50)

    data = collect_packages_status(project_root)
    if "error" in data:
        console.print(f"[red]❌ {data['error']}[/red]")
        return

    for package_name, info in data["packages"].items():
        console.print(f"\n📦 {package_name}")

        console.print(
            "  ✅ pyproject.toml" if info.get("has_pyproject") else "  ❌ pyproject.toml 缺失"
        )
        console.print("  ✅ tests 目录" if info.get("has_tests") else "  ⚠️  tests 目录缺失")

        import_status = info.get("import_status")
        if import_status == "success":
            console.print(f"  ✅ 导入成功 (版本: {info.get('version', 'unknown')})")
        elif import_status == "failed":
            console.print("  ❌ 导入失败")
            if verbose and info.get("import_error"):
                console.print(f"     错误: {info['import_error']}")
        elif import_status == "error":
            console.print("  ❌ 导入检查异常")
            if verbose and info.get("import_error"):
                console.print(f"     错误: {info['import_error']}")
        else:
            console.print("  ⚠️  未检测导入状态")

        if check_versions and verbose:
            console.print(f"  📍 路径: {info.get('path', 'unknown')}")

        if check_dependencies:
            _check_package_dependencies(package_name, console, verbose)


__all__ = [
    "check_dependency_versions",
    "DEFAULT_DEPENDENCIES",
    "DependencyStatus",
    "run_installation_diagnostics",
    "collect_packages_status",
    "print_packages_status",
    "print_packages_status_summary",
]
