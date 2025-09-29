"""Helper utilities for diagnosing third-party dependency compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from rich.console import Console
from rich.table import Table

try:  # pragma: no cover - optional dependency in some environments
    import pkg_resources
except ImportError:  # pragma: no cover - tooling should ensure this exists
    pkg_resources = None  # type: ignore[assignment]


DEFAULT_DEPENDENCIES: Dict[str, str] = {
    "intellistream-sage-kernel": "0.1.5",
    "intellistream-sage-utils": "0.1.3",
    "intellistream-sage-middleware": "0.1.3",
    "intellistream-sage-cli": "0.1.3",
}


@dataclass
class DependencyStatus:
    name: str
    required: str
    installed: Optional[str]
    compatible: bool
    error: Optional[str] = None


def _get_console(console: Optional[Console]) -> Console:
    return console or Console()


def _gather_dependency_status(
    dependencies: Dict[str, str],
) -> List[DependencyStatus]:
    statuses: List[DependencyStatus] = []

    if pkg_resources is None:
        for name, required in dependencies.items():
            statuses.append(
                DependencyStatus(
                    name=name,
                    required=required,
                    installed=None,
                    compatible=False,
                    error="pkg_resources 未安装",
                )
            )
        return statuses

    for package, minimum in dependencies.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            compatible = pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(
                minimum
            )
            statuses.append(
                DependencyStatus(
                    name=package,
                    required=minimum,
                    installed=installed_version,
                    compatible=compatible,
                )
            )
        except pkg_resources.DistributionNotFound:
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
    dependencies: Optional[Dict[str, str]] = None,
    *,
    console: Optional[Console] = None,
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
                from sage.kernel.jobmanager.jobmanager_client import (  # type: ignore import
                    JobManagerClient,  # noqa: F401
                )
            except Exception as exc:  # pragma: no cover - import runtime dependent
                console.print(f"❌ JobManagerClient 导入失败: {exc}")
            else:
                console.print("✅ JobManagerClient 导入成功")

        return False

    console.print("\n✅ 所有依赖版本兼容，系统应该可以正常工作")
    return True


__all__ = ["check_dependency_versions", "DEFAULT_DEPENDENCIES", "DependencyStatus"]
