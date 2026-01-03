#!/usr/bin/env python3
"""
SAGE Cluster Manager CLI
统一的Ray集群管理工具
"""

import os

import typer

from ...management.config_manager import get_config_manager
from ...management.deployment_manager import DeploymentManager
from .head import app as head_app
from .worker import app as worker_app

app = typer.Typer(name="cluster", help="🏗️ Ray集群统一管理")

# 添加子命令
app.add_typer(head_app, name="head", help="🏠 Head节点管理")
app.add_typer(worker_app, name="worker", help="👥 Worker节点管理")


@app.command("start")
def start_cluster(
    skip_ssh_check: bool = typer.Option(False, "--skip-ssh-check", help="跳过SSH免密登录检查"),
    ssh_password: str = typer.Option(
        None, "--ssh-password", "-p", help="SSH密码（用于自动配置免密登录）"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="强制重启：如果Ray已运行，先停止再启动"
    ),
):
    """启动整个Ray集群（Head + 所有Workers）"""
    config_manager = get_config_manager()
    workers = config_manager.get_workers_ssh_hosts()
    ssh_config = config_manager.get_ssh_config()

    # 0. SSH免密登录检查（仅当有worker节点时）
    if workers and not skip_ssh_check:
        typer.echo("🔐 第0步: 检查SSH免密登录...")

        from .ssh_setup import auto_setup_ssh_keys, verify_passwordless_login

        user = ssh_config.get("user", "sage")
        key_path = ssh_config.get("key_path", "~/.ssh/id_rsa")
        key_path = os.path.expanduser(key_path)

        # 检查每个worker的SSH连接
        failed_hosts = []
        for host, port in workers:
            if not verify_passwordless_login(host, user, key_path, port):
                failed_hosts.append((host, port))

        if failed_hosts:
            typer.echo(f"[yellow]⚠️  发现 {len(failed_hosts)} 个节点未配置免密登录:[/yellow]")
            for host, port in failed_hosts:
                typer.echo(f"   - {host}:{port}")

            # 如果提供了密码，自动配置
            if ssh_password:
                typer.echo("\n[cyan]🔧 使用提供的密码自动配置SSH免密登录...[/cyan]")
                success, total = auto_setup_ssh_keys(
                    hosts=failed_hosts,
                    user=user,
                    password=ssh_password,
                    key_path=key_path,
                )
                if success < total:
                    typer.echo(f"[red]❌ SSH配置失败: {total - success} 个节点无法配置[/red]")
                    typer.echo(
                        "[yellow]提示: 使用 --skip-ssh-check 跳过检查，或手动配置SSH[/yellow]"
                    )
                    raise typer.Exit(1)
            else:
                # 交互式询问是否配置
                typer.echo("\n[cyan]是否现在配置SSH免密登录？[/cyan]")
                try:
                    password = typer.prompt(f"请输入SSH密码（用户: {user}）", hide_input=True)
                    success, total = auto_setup_ssh_keys(
                        hosts=failed_hosts,
                        user=user,
                        password=password,
                        key_path=key_path,
                    )
                    if success < total:
                        typer.echo(f"[red]❌ SSH配置失败: {total - success} 个节点无法配置[/red]")
                        raise typer.Exit(1)
                except typer.Abort:
                    typer.echo(
                        "[yellow]\n⚠️  跳过SSH配置。使用 --skip-ssh-check 避免此检查[/yellow]"
                    )
                    raise typer.Exit(1)
        else:
            typer.echo("[green]✅ 所有节点SSH免密登录正常[/green]")

    typer.echo("🚀 启动Ray集群...")

    # 1. 启动Head节点
    typer.echo("第1步: 启动Head节点")
    try:
        from .head import start_head

        start_head(force=force)
    except typer.Exit as e:
        # typer.Exit(0) 表示 Ray Head 已在运行，视为成功
        if e.exit_code != 0:
            typer.echo(f"❌ Head节点启动失败 (exit code: {e.exit_code})")
            raise typer.Exit(1)
        # exit_code == 0 表示已在运行，继续执行
    except Exception as e:
        typer.echo(f"❌ Head节点启动失败: {e}")
        raise typer.Exit(1)

    # 等待Head节点完全启动
    typer.echo("⏳ 等待Head节点完全启动...")
    import time

    time.sleep(5)

    # 2. 启动所有Worker节点
    typer.echo("第2步: 启动所有Worker节点")
    try:
        from .worker import start_workers

        if not workers:
            typer.echo("💡 未配置worker节点，跳过worker启动")
        else:
            start_workers()
            typer.echo("✅ Worker节点启动完成")
    except typer.Exit as e:
        if e.exit_code != 0:
            typer.echo(f"❌ Worker节点启动失败 (exit code: {e.exit_code})")
            typer.echo("💡 Head节点已启动，可尝试手动启动Worker节点")
            raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Worker节点启动失败: {e}")
        typer.echo("💡 Head节点已启动，可尝试手动启动Worker节点")
        raise typer.Exit(1)

    typer.echo("✅ Ray集群启动完成!")


@app.command("stop")
def stop_cluster():
    """停止整个Ray集群（所有Workers + Head）"""
    typer.echo("�� 停止Ray集群...")

    # 1. 先停止所有Worker节点
    typer.echo("第1步: 停止所有Worker节点")
    try:
        from .worker import stop_workers

        stop_workers()
    except Exception as e:
        typer.echo(f"⚠️  Worker节点停止遇到问题: {e}")
        # 继续执行，因为停止操作允许部分失败

    # 等待Worker节点完全停止
    typer.echo("⏳ 等待Worker节点完全停止...")
    import time

    time.sleep(3)

    # 2. 停止Head节点
    typer.echo("第2步: 停止Head节点")
    try:
        from .head import stop_head

        stop_head()
    except Exception as e:
        typer.echo(f"⚠️  Head节点停止遇到问题: {e}")

    typer.echo("✅ Ray集群停止完成!")


@app.command("restart")
def restart_cluster():
    """重启整个Ray集群"""
    typer.echo("🔄 重启Ray集群...")

    # 先停止
    typer.echo("第1阶段: 停止集群")
    stop_cluster()

    # 等待
    typer.echo("⏳ 等待5秒后重新启动...")
    import time

    time.sleep(5)

    # 再启动
    typer.echo("第2阶段: 启动集群")
    start_cluster()

    typer.echo("✅ Ray集群重启完成!")


@app.command("status")
def status_cluster():
    """检查整个Ray集群状态"""
    typer.echo("📊 检查Ray集群状态...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    workers = config_manager.get_workers_ssh_hosts()

    head_host = head_config.get("host", "localhost")
    dashboard_port = head_config.get("dashboard_port", 8265)

    # 1. 检查Head节点
    typer.echo("\n�� Head节点状态:")
    try:
        from .head import status_head

        status_head()
        head_running = True
    except Exception:
        head_running = False

    # 2. 检查Worker节点
    typer.echo(f"\n👥 Worker节点状态 ({len(workers)} 个节点):")
    try:
        from .worker import status_workers

        status_workers()
    except Exception:
        pass

    # 3. 显示集群访问信息
    if head_running:
        typer.echo("\n🌐 集群访问信息:")
        typer.echo(f"   Dashboard: http://{head_host}:{dashboard_port}")
        typer.echo(f"   Ray集群地址: {head_host}:{head_config.get('head_port', 6379)}")


@app.command("deploy")
def deploy_cluster():
    """部署SAGE到所有Worker节点"""
    typer.echo("🚀 部署SAGE到集群...")

    deployment_manager = DeploymentManager()
    success_count, total_count = deployment_manager.deploy_to_all_workers()

    if success_count == total_count:
        typer.echo("✅ 集群部署成功!")
    else:
        typer.echo(f"⚠️  部分节点部署失败 ({success_count}/{total_count})")
        raise typer.Exit(1)


@app.command("scale")
def scale_cluster(
    action: str = typer.Argument(..., help="操作: add 或 remove"),
    node: str = typer.Argument(..., help="节点地址，格式为 host:port"),
):
    """动态扩缩容集群（添加或移除Worker节点）"""
    if action not in ["add", "remove"]:
        typer.echo("❌ 操作必须是 'add' 或 'remove'")
        raise typer.Exit(1)

    if action == "add":
        typer.echo(f"➕ 扩容集群: 添加节点 {node}")
        try:
            from .worker import add_worker

            add_worker(node)
        except Exception as e:
            typer.echo(f"❌ 添加节点失败: {e}")
            raise typer.Exit(1)
    else:
        typer.echo(f"➖ 缩容集群: 移除节点 {node}")
        try:
            from .worker import remove_worker

            remove_worker(node)
        except Exception as e:
            typer.echo(f"❌ 移除节点失败: {e}")
            raise typer.Exit(1)


@app.command("info")
def cluster_info():
    """显示集群配置信息"""
    typer.echo("📋 Ray集群配置信息")
    typer.echo("=" * 50)

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    worker_config = config_manager.get_worker_config()
    ssh_config = config_manager.get_ssh_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    typer.echo("🏠 Head节点配置:")
    typer.echo(f"   主机: {head_config.get('host', 'N/A')}")
    typer.echo(f"   端口: {head_config.get('head_port', 'N/A')}")
    typer.echo(
        f"   Dashboard: {head_config.get('dashboard_host', 'N/A')}:{head_config.get('dashboard_port', 'N/A')}"
    )
    typer.echo(f"   临时目录: {head_config.get('temp_dir', 'N/A')}")
    typer.echo(f"   日志目录: {head_config.get('log_dir', 'N/A')}")

    typer.echo(f"\n👥 Worker节点配置 ({len(workers)} 个节点):")
    typer.echo(f"   绑定主机: {worker_config.get('bind_host', 'N/A')}")
    typer.echo(f"   临时目录: {worker_config.get('temp_dir', 'N/A')}")
    typer.echo(f"   日志目录: {worker_config.get('log_dir', 'N/A')}")

    if workers:
        typer.echo("   节点列表:")
        for i, (host, port) in enumerate(workers, 1):
            typer.echo(f"     {i}. {host}:{port}")

    typer.echo("\n🔗 SSH配置:")
    typer.echo(f"   用户: {ssh_config.get('user', 'N/A')}")
    typer.echo(f"   密钥路径: {ssh_config.get('key_path', 'N/A')}")
    typer.echo(f"   连接超时: {ssh_config.get('connect_timeout', 'N/A')}s")

    typer.echo("\n🛠️ 远程环境:")
    typer.echo(f"   SAGE目录: {remote_config.get('sage_home', 'N/A')}")
    typer.echo(f"   Python路径: {remote_config.get('python_path', 'N/A')}")
    typer.echo(f"   Ray命令: {remote_config.get('ray_command', 'N/A')}")
    typer.echo(f"   Conda环境: {remote_config.get('conda_env', 'N/A')}")


@app.command("version")
def version_command():
    """Show version information."""
    typer.echo("🏗️ SAGE Cluster Manager")
    typer.echo("Version: 1.0.1")
    typer.echo("Author: IntelliStream Team")
    typer.echo("Repository: https://github.com/intellistream/SAGE")


if __name__ == "__main__":
    app()
