"""Typer command group for managing SAGE licenses."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from sage.tools.license import (
    LicenseClient,
    LicenseConfig,
    LicenseValidator,
    LicenseVendor,
)

console = Console()
app = typer.Typer(name="license", help="🛡️ 许可证管理 - 客户与厂商工具")
vendor_app = typer.Typer(name="vendor", help="🏭 厂商工具 - 生成与管理许可证")
app.add_typer(vendor_app, name="vendor")


@app.command()
def status():
    """显示当前许可证状态。"""

    client = LicenseClient(console=console)
    client.show_status()


@app.command()
def install(
    license_key: str = typer.Argument(..., help="要安装的许可证密钥", metavar="LICENSE-KEY"),
):
    """安装商业许可证。"""

    client = LicenseClient(console=console)
    success = client.install_license(license_key)
    if not success:
        raise typer.Exit(1)


@app.command()
def remove():
    """移除已安装的许可证。"""

    client = LicenseClient(console=console)
    success = client.remove_license()
    if not success:
        raise typer.Exit(1)


@app.command()
def features():
    """列出当前许可证可用的功能。"""

    validator = LicenseValidator()
    status = validator.check_license_status()

    table = Table(title="许可证功能")
    table.add_column("功能")
    table.add_column("可用?", justify="center")

    features = (
        status.get("features", [])
        if status.get("has_license")
        else list(LicenseConfig.OPEN_SOURCE_FEATURES)
    )
    for feature in features:
        table.add_row(feature, "✅")

    console.print(table)


@vendor_app.command()
def generate(
    customer: str = typer.Argument(..., help="客户名称"),
    days: int = typer.Option(365, "--days", "-d", help="许可证有效天数"),
    license_type: str = typer.Option(
        "COMM", "--type", "-t", help="许可证类型（默认 COMM）"
    ),
):
    """生成新的商业许可证。"""

    vendor = LicenseVendor(console=console)
    license_key = vendor.generate_license_key(customer, days=days, license_type=license_type)
    vendor.save_generated_license(license_key, customer, days)

    console.print("🎉 许可证生成成功!")
    console.print(f"客户: {customer}")
    console.print(f"有效期: {days} 天")
    console.print(f"许可证: [bold]{license_key}[/bold]")
    console.print("\n💡 客户可使用以下命令安装:")
    console.print(f"   sage license install {license_key}")


@vendor_app.command("list")
def vendor_list():
    """列出已生成的许可证。"""

    vendor = LicenseVendor(console=console)
    records = vendor.list_generated_licenses()
    vendor.print_license_records(records)


@vendor_app.command()
def revoke(
    license_key: str = typer.Argument(..., help="要吊销的许可证密钥", metavar="LICENSE-KEY"),
):
    """吊销指定的许可证。"""

    vendor = LicenseVendor(console=console)
    success = vendor.revoke_license(license_key)
    if success:
        console.print(f"✅ 已吊销许可证 {license_key}")
    else:
        console.print(f"❌ 未找到许可证 {license_key}")
        raise typer.Exit(1)


__all__ = ["app"]
