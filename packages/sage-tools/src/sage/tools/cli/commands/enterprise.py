"""CLI entry points for managing SAGE enterprise features."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from sage.tools.enterprise import EnterpriseManager, check_enterprise_features

console = Console()
app = typer.Typer(name="enterprise", help="🏢 企业版功能管理")


def _render_license_table(license_info: dict) -> None:
    table = Table(title="许可状态", show_header=False)
    table.add_row("类型", license_info.get("type", "unknown"))
    table.add_row(
        "商业许可",
        "✅ 已启用" if license_info.get("commercial_enabled") else "❌ 未启用",
    )
    table.add_row("来源", license_info.get("source", "unknown"))
    table.add_row("特性", ", ".join(license_info.get("features", [])) or "无")
    if license_info.get("expires_at"):
        table.add_row("到期时间", str(license_info["expires_at"]))
    console.print(table)


def _render_components_table(installation: dict) -> None:
    table = Table(title="组件可用性")
    table.add_column("组件")
    table.add_column("状态")
    table.add_column("备注", overflow="fold")

    status_to_icon = {
        "available": "✅ 可用",
        "not_available": "❌ 未安装",
        "error": "⚠️ 异常",
    }

    for component in installation.get("components", []):
        status = component.get("status", "unknown")
        icon = status_to_icon.get(status, status)
        table.add_row(
            component.get("component", "—"),
            icon,
            component.get("error", "") or "",
        )

    summary = (
        f"{installation.get('available_components', 0)}/"
        f"{installation.get('total_components', 0)}"
    )
    console.print(table)
    console.print(f"组件可用性: [bold]{summary}[/bold]")


@app.command()
def check():
    """检查许可状态和企业组件可用性。"""

    data = check_enterprise_features()
    console.rule("SAGE Enterprise 状态")
    _render_license_table(data["license"])
    _render_components_table(data["installation"])

    summary = data.get("summary", {})
    console.print(
        f"企业功能启用: " f"{'✅ 是' if summary.get('enterprise_enabled') else '❌ 否'}"
    )


@app.command()
def install(
    license_key: Optional[str] = typer.Option(
        None, "--license-key", "-k", help="在安装前写入许可证密钥"
    )
):
    """安装企业版依赖包。"""

    manager = EnterpriseManager()
    console.rule("安装企业组件")
    result = manager.install_enterprise_features(license_key)

    for message in result.get("logs", []):
        console.print(f"• {message}")

    table = Table(title="安装结果")
    table.add_column("依赖包")
    table.add_column("状态")
    table.add_column("错误", overflow="fold")
    for item in result.get("results", []):
        status = item.get("status", "unknown")
        symbol = {
            "success": "✅ 成功",
            "failed": "❌ 失败",
            "error": "⚠️ 异常",
        }.get(status, status)
        table.add_row(item.get("package", "—"), symbol, item.get("error", ""))
    console.print(table)

    summary = (
        f"{result.get('installed_packages', 0)}/" f"{result.get('total_packages', 0)}"
    )
    console.print(
        f"安装状态: [bold]{result.get('status', 'unknown')}[/bold] ({summary})"
    )

    if result.get("status") != "success":
        raise typer.Exit(1)


@app.command()
def validate():
    """验证企业组件导入是否正常。"""

    manager = EnterpriseManager()
    console.rule("验证企业组件")
    installation = manager.validate_enterprise_installation()
    _render_components_table(installation)

    if installation.get("available_components", 0) != installation.get(
        "total_components", 0
    ):
        raise typer.Exit(1)


@app.command()
def commands(
    mode: str = typer.Option(
        "enterprise",
        "--mode",
        "-m",
        help="显示不同模式的安装命令",
        case_sensitive=False,
    )
):
    """显示常用的企业版安装命令。"""

    manager = EnterpriseManager()
    console.rule("安装命令")
    console.print(manager.get_installation_command(mode.lower()))


__all__ = ["app"]
