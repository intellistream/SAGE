#!/usr/bin/env python3
"""
SAGE Worker Manager CLI
Worker 节点（Flownet）管理相关命令
"""

import os
import subprocess
import tempfile
import time

import typer

from ...management.config_manager import get_config_manager
from ...management.deployment_manager import DeploymentManager
from .runtime_checker import check_runtime_version_parity

app = typer.Typer(name="worker", help="Worker 节点（Flownet）管理")


def execute_remote_command(host: str, port: int, command: str, timeout: int = 60) -> bool:
    """在远程主机上执行命令"""
    config_manager = get_config_manager()
    ssh_config = config_manager.get_ssh_config()
    ssh_user = ssh_config.get("user", "sage")
    ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))

    typer.echo(f"🔗 连接到 {ssh_user}@{host}:{port}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as temp_script:
        temp_script.write("#!/bin/bash\n")
        temp_script.write(command)
        temp_script_path = temp_script.name

    try:
        ssh_cmd = [
            "ssh",
            "-i",
            ssh_key_path,
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={ssh_config.get('connect_timeout', 10)}",
            "-o",
            "ServerAliveInterval=60",
            "-o",
            "ServerAliveCountMax=3",
            f"{ssh_user}@{host}",
            "bash -s",
        ]

        with open(temp_script_path) as script_file:
            result = subprocess.run(
                ssh_cmd,
                stdin=script_file,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        typer.echo(f"❌ 远程命令超时 ({timeout}s)")
        return False
    except Exception as e:
        typer.echo(f"❌ 远程命令失败: {e}")
        return False
    finally:
        try:
            os.unlink(temp_script_path)
        except OSError:
            pass


def get_conda_init_code(conda_env: str = "sage") -> str:
    """获取 Conda 环境初始化代码"""
    return f"""
CONDA_BASE=""
for conda_path in \\
    "$HOME/miniconda3" \\
    "$HOME/anaconda3" \\
    "/opt/conda" \\
    "/usr/local/miniconda3" \\
    "/usr/local/anaconda3"; do
    if [ -f "$conda_path/etc/profile.d/conda.sh" ]; then
        source "$conda_path/etc/profile.d/conda.sh"
        CONDA_BASE="$conda_path"
        echo "[INFO] 找到conda: $conda_path"
        break
    fi
done

if [ -z "$CONDA_BASE" ]; then
    echo "[ERROR] 未找到conda安装"
    exit 1
fi

conda activate {conda_env} || {{
    echo "[ERROR] 无法激活conda环境: {conda_env}"
    conda env list
    exit 1
}}

echo "[SUCCESS] 已激活conda环境: {conda_env}"

command -v flownet >/dev/null 2>&1 || {{
    echo "[ERROR] flownet 命令不可用，请先安装 sageFlownet"
    exit 1
}}
"""


def _get_seed_endpoint() -> tuple[str, int]:
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_host = head_config.get("host", "localhost")
    flownet_port = head_config.get("flownet_port", head_config.get("head_port", 8787))
    return head_host, flownet_port


def _get_resource_flags(worker_config: dict) -> str:
    flags = ""
    num_cpus = worker_config.get("num_cpus")
    num_gpus = worker_config.get("num_gpus")
    if num_cpus is not None:
        flags += f" --resource=cpu={num_cpus}"
    if num_gpus is not None:
        flags += f" --resource=gpu={num_gpus}"
    return flags


def _build_remote_start_command(
    head_host: str,
    flownet_port: int,
    worker_log_dir: str,
    conda_env: str,
    worker_config: dict,
) -> str:
    threads = worker_config.get("threads", 4)
    resource_flags = _get_resource_flags(worker_config)

    return f"""set -e
export PYTHONUNBUFFERED=1

LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Flownet Worker 启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker 节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "Seed: head@{head_host}:{flownet_port}" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

{get_conda_init_code(conda_env)}

# 启动前清理
flownet node stop --force --timeout=6 >> "$LOG_DIR/worker.log" 2>&1 || true
sleep 1

NODE_ID="worker-$(hostname)"
echo "[INFO] Node ID: $NODE_ID" | tee -a "$LOG_DIR/worker.log"

flownet node join \\
  --node-id="$NODE_ID" \\
  --seed=head@{head_host}:{flownet_port} \\
  --threads={threads}{resource_flags} \\
  --log-file="$LOG_DIR/worker.log" 2>&1 | tee -a "$LOG_DIR/worker.log"

EXIT_CODE=${{PIPESTATUS[0]}}
if [ $EXIT_CODE -ne 0 ]; then
  echo "[ERROR] Flownet Worker 启动失败，退出码: $EXIT_CODE" | tee -a "$LOG_DIR/worker.log"
  exit $EXIT_CODE
fi

echo "[SUCCESS] Flownet Worker 启动成功" | tee -a "$LOG_DIR/worker.log"
flownet node status --no-probe 2>/dev/null | tee -a "$LOG_DIR/worker.log" || true
"""


def _build_remote_stop_command(worker_log_dir: str, conda_env: str, force: bool) -> str:
    force_flag = "--force" if force else ""
    return f"""set +e
export PYTHONUNBUFFERED=1

LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Flownet Worker 停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker 节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

{get_conda_init_code(conda_env)}

flownet node stop --timeout=8 {force_flag} 2>&1 | tee -a "$LOG_DIR/worker.log"
echo "[INFO] 停止命令执行完成" | tee -a "$LOG_DIR/worker.log"
"""


def _build_remote_status_command(worker_log_dir: str, conda_env: str) -> str:
    return f"""set +e
export PYTHONUNBUFFERED=1

echo "==============================================="
echo "Flownet Worker 状态检查: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "==============================================="

{get_conda_init_code(conda_env)}

flownet node status --json
EXIT_CODE=$?

LOG_DIR='{worker_log_dir}'
if [[ -f "$LOG_DIR/worker.log" ]]; then
    echo ""
    echo "--- 最近日志 (最后5行) ---"
    tail -5 "$LOG_DIR/worker.log" 2>/dev/null || true
fi

exit $EXIT_CODE
"""


def _start_single_worker(host: str, port: int) -> bool:
    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    head_host, flownet_port = _get_seed_endpoint()

    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    conda_env = remote_config.get("conda_env", "sage")

    command = _build_remote_start_command(
        head_host=head_host,
        flownet_port=flownet_port,
        worker_log_dir=worker_log_dir,
        conda_env=conda_env,
        worker_config=worker_config,
    )
    return execute_remote_command(host, port, command, 120)


@app.command("start")
def start_workers():
    """启动所有 Worker 节点"""
    typer.echo("🚀 启动 Worker 节点（Flownet）...")

    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    ssh_config = config_manager.get_ssh_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何 worker 节点")
        return

    head_host, flownet_port = _get_seed_endpoint()
    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    conda_env = remote_config.get("conda_env", "sage")

    typer.echo("📋 配置信息:")
    typer.echo(f"   Seed 节点: head@{head_host}:{flownet_port}")
    typer.echo(f"   Worker 节点: {len(workers)} 个")
    typer.echo(f"   Worker 日志目录: {worker_log_dir}")

    # 运行时版本一致性检查
    ssh_user = ssh_config.get("user", "sage")
    ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))
    check_runtime_version_parity(
        workers=workers,
        user=ssh_user,
        ssh_key_path=ssh_key_path,
        conda_env=conda_env,
        silent=False,
    )

    success_count = 0
    total_count = len(workers)

    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"\n🔧 启动 Worker 节点 {i}/{total_count}: {host}:{port}")
        if _start_single_worker(host, port):
            typer.echo(f"✅ Worker 节点 {host} 启动成功")
            success_count += 1
        else:
            typer.echo(f"❌ Worker 节点 {host} 启动失败")

    typer.echo(f"\n📊 启动结果: {success_count}/{total_count} 个节点启动成功")
    if success_count != total_count:
        raise typer.Exit(1)


@app.command("stop")
def stop_workers(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止 worker 运行时"),
):
    """停止所有 Worker 节点"""
    typer.echo("🛑 停止 Worker 节点（Flownet）...")

    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何 worker 节点")
        raise typer.Exit(1)

    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    conda_env = remote_config.get("conda_env", "sage")

    success_count = 0
    total_count = len(workers)

    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"\n🔧 停止 Worker 节点 {i}/{total_count}: {host}:{port}")
        stop_command = _build_remote_stop_command(
            worker_log_dir=worker_log_dir,
            conda_env=conda_env,
            force=force,
        )
        if execute_remote_command(host, port, stop_command, 60):
            typer.echo(f"✅ Worker 节点 {host} 停止完成")
            success_count += 1
        else:
            typer.echo(f"⚠️ Worker 节点 {host} 停止命令失败（可能已停止）")

    typer.echo(f"\n📊 停止结果: {success_count}/{total_count} 个节点处理成功")


@app.command("status")
def status_workers():
    """检查所有 Worker 节点状态"""
    typer.echo("📊 检查 Worker 节点状态（Flownet）...")

    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    ssh_config = config_manager.get_ssh_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何 worker 节点")
        raise typer.Exit(1)

    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    conda_env = remote_config.get("conda_env", "sage")

    # 运行时版本一致性检查
    ssh_user = ssh_config.get("user", "sage")
    ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))
    check_runtime_version_parity(
        workers=workers,
        user=ssh_user,
        ssh_key_path=ssh_key_path,
        conda_env=conda_env,
        silent=False,
    )

    running_count = 0
    total_count = len(workers)

    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"\n📋 检查 Worker 节点 {i}/{total_count}: {host}:{port}")
        status_command = _build_remote_status_command(worker_log_dir, conda_env)
        if execute_remote_command(host, port, status_command, 30):
            typer.echo(f"✅ Worker 节点 {host} 正在运行")
            running_count += 1
        else:
            typer.echo(f"❌ Worker 节点 {host} 未运行或检查失败")

    typer.echo(f"\n📊 状态统计: {running_count}/{total_count} 个 Worker 节点正在运行")


@app.command("restart")
def restart_workers():
    """重启所有 Worker 节点"""
    typer.echo("🔄 重启 Worker 节点...")
    typer.echo("第 1 步: 停止所有 Worker 节点")
    stop_workers(force=True)
    typer.echo("⏳ 等待 3 秒后重新启动...")
    time.sleep(3)
    typer.echo("第 2 步: 启动所有 Worker 节点")
    start_workers()
    typer.echo("✅ Worker 节点重启完成")


@app.command("config")
def show_config():
    """显示当前 Worker 配置信息"""
    typer.echo("📋 当前 Worker 配置信息")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    worker_config = config_manager.get_worker_config()
    ssh_config = config_manager.get_ssh_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    typer.echo(f"Head 主机: {head_config.get('host', 'N/A')}")
    typer.echo(
        f"Flownet 端口: {head_config.get('flownet_port', head_config.get('head_port', 'N/A'))}"
    )
    typer.echo(f"Worker 节点数量: {len(workers)}")
    if workers:
        for i, (host, port) in enumerate(workers, 1):
            typer.echo(f"  Worker {i}: {host}:{port}")
    typer.echo(f"SSH 用户: {ssh_config.get('user', 'N/A')}")
    typer.echo(f"SSH 密钥路径: {ssh_config.get('key_path', 'N/A')}")
    typer.echo(f"Worker 日志目录: {worker_config.get('log_dir', 'N/A')}")
    typer.echo(f"远程 SAGE 目录: {remote_config.get('sage_home', 'N/A')}")
    typer.echo(f"远程 Python 路径: {remote_config.get('python_path', 'N/A')}")
    typer.echo(f"远程 Conda 环境: {remote_config.get('conda_env', 'N/A')}")
    typer.echo(f"远程运行时命令: {remote_config.get('runtime_command', 'flownet')}")


@app.command("deploy")
def deploy_workers():
    """部署项目到所有 Worker 节点"""
    typer.echo("🚀 开始部署到 Worker 节点...")

    deployment_manager = DeploymentManager()
    success_count, total_count = deployment_manager.deploy_to_all_workers()

    if success_count == total_count:
        typer.echo("✅ 所有节点部署成功")
    else:
        typer.echo("⚠️ 部分节点部署失败")
        raise typer.Exit(1)


@app.command("add")
def add_worker(node: str = typer.Argument(..., help="节点地址，格式 host:port")):
    """动态添加新的 Worker 节点"""
    typer.echo(f"➕ 添加新 Worker 节点: {node}")

    if ":" in node:
        host, port_str = node.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            typer.echo("❌ 端口号必须是数字")
            raise typer.Exit(1)
    else:
        host = node
        port = 22

    config_manager = get_config_manager()
    if config_manager.add_worker_ssh_host(host, port):
        typer.echo(f"✅ 已添加 Worker 节点 {host}:{port} 到配置")
    else:
        typer.echo(f"⚠️ Worker 节点 {host}:{port} 已存在")

    typer.echo(f"🚀 开始部署到新节点 {host}:{port}...")
    deployment_manager = DeploymentManager()
    if not deployment_manager.deploy_to_worker(host, port):
        typer.echo(f"❌ 新节点 {host}:{port} 部署失败")
        raise typer.Exit(1)

    typer.echo(f"✅ 新节点 {host}:{port} 部署成功")
    typer.echo("🔧 启动新 Worker 节点...")
    if _start_single_worker(host, port):
        typer.echo(f"✅ 新 Worker 节点 {host}:{port} 启动成功")
    else:
        typer.echo(f"❌ 新 Worker 节点 {host}:{port} 启动失败")
        raise typer.Exit(1)


@app.command("remove")
def remove_worker(node: str = typer.Argument(..., help="节点地址，格式 host:port")):
    """移除 Worker 节点"""
    typer.echo(f"➖ 移除 Worker 节点: {node}")

    if ":" in node:
        host, port_str = node.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            typer.echo("❌ 端口号必须是数字")
            raise typer.Exit(1)
    else:
        host = node
        port = 22

    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()

    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    conda_env = remote_config.get("conda_env", "sage")

    typer.echo(f"🛑 停止 Worker 节点 {host}:{port}...")
    stop_command = _build_remote_stop_command(worker_log_dir, conda_env, force=True)
    if execute_remote_command(host, port, stop_command, 60):
        typer.echo(f"✅ Worker 节点 {host}:{port} 已停止")
    else:
        typer.echo(f"⚠️ Worker 节点 {host}:{port} 停止可能未完全成功")

    if config_manager.remove_worker_ssh_host(host, port):
        typer.echo(f"✅ 已从配置中移除 Worker 节点 {host}:{port}")
    else:
        typer.echo(f"⚠️ Worker 节点 {host}:{port} 不在配置中")

    typer.echo(f"✅ Worker 节点 {host}:{port} 移除完成")


@app.command("list")
def list_workers():
    """列出所有配置的 Worker 节点"""
    typer.echo("📋 配置的 Worker 节点列表")

    config_manager = get_config_manager()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何 Worker 节点")
        typer.echo("💡 使用 'sage cluster worker add <host:port>' 添加 Worker 节点")
        return

    typer.echo(f"📊 共配置了 {len(workers)} 个 Worker 节点:")
    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"  {i}. {host}:{port}")

    typer.echo("\n💡 使用 'sage cluster worker status' 检查节点状态")


@app.command("version")
def version_command():
    """显示版本信息"""
    typer.echo("👥 SAGE Worker Manager (Flownet Runtime)")
    typer.echo("Version: 2.0.0")
    typer.echo("Runtime: sageFlownet")
    typer.echo("Repository: https://github.com/intellistream/SAGE")


if __name__ == "__main__":
    app()
