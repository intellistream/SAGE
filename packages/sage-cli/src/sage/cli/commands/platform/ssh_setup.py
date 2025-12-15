"""SSH 免密登录自动配置工具"""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer


def check_sshpass_installed() -> bool:
    """检查 sshpass 是否已安装"""
    try:
        subprocess.run(
            ["which", "sshpass"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_sshpass() -> bool:
    """安装 sshpass 工具"""
    typer.echo("[blue]📦 安装 sshpass 工具...[/blue]")

    # 检测包管理器并安装
    if Path("/usr/bin/apt-get").exists():
        try:
            subprocess.run(
                ["sudo", "apt-get", "update"],
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "sshpass"],
                check=True,
                timeout=120,
            )
            typer.echo("[green]✅ sshpass 安装成功[/green]")
            return True
        except subprocess.CalledProcessError:
            typer.echo("[red]❌ sshpass 安装失败（apt-get）[/red]")
            return False
    elif Path("/usr/bin/yum").exists():
        try:
            subprocess.run(
                ["sudo", "yum", "install", "-y", "sshpass"],
                check=True,
                timeout=120,
            )
            typer.echo("[green]✅ sshpass 安装成功[/green]")
            return True
        except subprocess.CalledProcessError:
            typer.echo("[red]❌ sshpass 安装失败（yum）[/red]")
            return False
    else:
        typer.echo("[red]❌ 无法自动安装 sshpass，请手动安装[/red]")
        typer.echo("[yellow]   Ubuntu/Debian: sudo apt-get install sshpass[/yellow]")
        typer.echo("[yellow]   CentOS/RHEL: sudo yum install sshpass[/yellow]")
        return False


def generate_ssh_key(key_path: str) -> bool:
    """生成 SSH 密钥对"""
    if Path(key_path).exists():
        typer.echo(f"[green]✅ SSH 密钥已存在: {key_path}[/green]")
        return True

    typer.echo("[blue]🔑 生成 SSH 密钥对...[/blue]")

    try:
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "rsa",
                "-b",
                "4096",
                "-f",
                key_path,
                "-N",
                "",
                "-C",
                f"sage-cluster-{os.getenv('USER', 'user')}",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        typer.echo(f"[green]✅ SSH 密钥生成成功: {key_path}[/green]")
        return True
    except subprocess.CalledProcessError as e:
        typer.echo(f"[red]❌ SSH 密钥生成失败: {e}[/red]")
        return False


def test_ssh_connection(
    host: str,
    user: str,
    password: str,
    port: int = 22,
) -> bool:
    """测试 SSH 连接（使用密码）"""
    try:
        result = subprocess.run(
            [
                "sshpass",
                "-p",
                password,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ConnectTimeout=5",
                "-p",
                str(port),
                f"{user}@{host}",
                "echo 'Connection OK'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def copy_ssh_key(
    host: str,
    user: str,
    password: str,
    key_path: str,
    port: int = 22,
) -> bool:
    """复制 SSH 公钥到远程主机"""
    pub_key_path = f"{key_path}.pub"

    if not Path(pub_key_path).exists():
        typer.echo(f"[red]❌ 公钥文件不存在: {pub_key_path}[/red]")
        return False

    try:
        result = subprocess.run(
            [
                "sshpass",
                "-p",
                password,
                "ssh-copy-id",
                "-o",
                "StrictHostKeyChecking=no",
                "-i",
                pub_key_path,
                "-p",
                str(port),
                f"{user}@{host}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception as e:
        typer.echo(f"[yellow]复制密钥时出错: {e}[/yellow]")
        return False


def verify_passwordless_login(
    host: str,
    user: str,
    key_path: str,
    port: int = 22,
) -> bool:
    """验证免密登录"""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-i",
                key_path,
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ConnectTimeout=5",
                "-o",
                "BatchMode=yes",
                "-p",
                str(port),
                f"{user}@{host}",
                "echo 'Passwordless login works'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def setup_ssh_for_host(
    host: str,
    user: str,
    password: str,
    key_path: str,
    port: int = 22,
) -> bool:
    """为单个主机配置 SSH 免密登录"""
    typer.echo(f"[blue]🔧 配置 {host}...[/blue]")

    # 1. 测试连接
    typer.echo("  1. 测试 SSH 连接...")
    if not test_ssh_connection(host, user, password, port):
        typer.echo(f"[red]  ❌ 无法连接到 {host}[/red]")
        return False
    typer.echo("[green]  ✅ 连接成功[/green]")

    # 2. 复制公钥
    typer.echo("  2. 复制 SSH 公钥...")
    if not copy_ssh_key(host, user, password, key_path, port):
        typer.echo("[red]  ❌ 公钥复制失败[/red]")
        return False
    typer.echo("[green]  ✅ 公钥复制成功[/green]")

    # 3. 验证免密登录
    typer.echo("  3. 验证免密登录...")
    if not verify_passwordless_login(host, user, key_path, port):
        typer.echo("[red]  ❌ 免密登录验证失败[/red]")
        return False
    typer.echo(f"[green]  ✅ 免密登录配置成功: {user}@{host}[/green]")

    return True


def auto_setup_ssh_keys(
    hosts: list[tuple[str, int]],
    user: str = "sage",
    password: str = "123",
    key_path: Optional[str] = None,
) -> tuple[int, int]:
    """自动配置 SSH 免密登录

    Args:
        hosts: [(host, port), ...] 列表
        user: SSH 用户名
        password: SSH 密码
        key_path: SSH 密钥路径

    Returns:
        (成功数量, 总数量)
    """
    if key_path is None:
        key_path = os.path.expanduser("~/.ssh/id_rsa")

    typer.echo("\n[cyan]═══════════════════════════════════════[/cyan]")
    typer.echo("[cyan]  SSH 免密登录自动配置[/cyan]")
    typer.echo("[cyan]═══════════════════════════════════════[/cyan]\n")

    # 1. 检查并安装 sshpass
    if not check_sshpass_installed():
        typer.echo("[yellow]⚠️  未安装 sshpass[/yellow]")
        if not install_sshpass():
            typer.echo("[red]❌ SSH 配置失败: 无法安装 sshpass[/red]")
            return (0, len(hosts))

    # 2. 生成 SSH 密钥
    if not generate_ssh_key(key_path):
        typer.echo("[red]❌ SSH 配置失败: 无法生成密钥[/red]")
        return (0, len(hosts))

    # 3. 配置每个主机
    typer.echo(f"\n[cyan]配置 {len(hosts)} 个主机...[/cyan]\n")
    success_count = 0

    for host, port in hosts:
        # 先检查是否已经配置了免密登录
        if verify_passwordless_login(host, user, key_path, port):
            typer.echo(f"[green]✅ {host}: 免密登录已配置[/green]\n")
            success_count += 1
            continue

        # 配置免密登录
        if setup_ssh_for_host(host, user, password, key_path, port):
            success_count += 1
        typer.echo("")

    # 4. 总结
    typer.echo("[cyan]═══════════════════════════════════════[/cyan]")
    typer.echo(f"[cyan]配置完成: {success_count}/{len(hosts)} 成功[/cyan]")
    typer.echo("[cyan]═══════════════════════════════════════[/cyan]\n")

    if success_count == len(hosts):
        typer.echo("[green]🎉 所有主机配置成功！[/green]\n")
    elif success_count > 0:
        typer.echo("[yellow]⚠️  部分主机配置失败[/yellow]\n")
    else:
        typer.echo("[red]❌ 所有主机配置失败[/red]\n")

    return (success_count, len(hosts))
