#!/usr/bin/env python3
"""
SAGE Worker Manager CLI
Worker节点管理相关命令
"""

import os
import subprocess
import tempfile
import time

import typer

from ...management.config_manager import get_config_manager
from ...management.deployment_manager import DeploymentManager

app = typer.Typer(name="worker", help="Worker节点管理")


def execute_remote_command(host: str, port: int, command: str, timeout: int = 60) -> bool:
    """在远程主机上执行命令"""
    config_manager = get_config_manager()
    ssh_config = config_manager.get_ssh_config()
    ssh_user = ssh_config.get("user", "sage")
    ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))

    typer.echo(f"🔗 连接到 {ssh_user}@{host}:{port}")

    # 创建临时脚本文件
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
        typer.echo(f"❌ Remote command timeout ({timeout}s)")
        return False
    except Exception as e:
        typer.echo(f"❌ Remote command failed: {e}")
        return False
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_script_path)
        except OSError:
            pass


def get_conda_init_code(conda_env: str = "sage") -> str:
    """获取Conda环境初始化代码

    支持 base 环境和自定义环境（如 sage）。
    base 环境的路径是 $CONDA_BASE/bin，其他环境是 $CONDA_BASE/envs/{env}/bin。
    """
    return f"""
# 多种conda安装路径尝试
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
        CONDA_FOUND=true
        break
    fi
done

if [ -z "$CONDA_FOUND" ]; then
    echo "[ERROR] 未找到conda安装，请检查conda是否正确安装"
    exit 1
fi

# 激活环境
if ! conda activate {conda_env}; then
    echo "[ERROR] 无法激活conda环境: {conda_env}"
    echo "[INFO] 可用的conda环境:"
    conda env list
    exit 1
fi

echo "[SUCCESS] 已激活conda环境: {conda_env}"

# 设置 RAY_CMD 变量（根据环境类型选择正确路径）
# base 环境: $CONDA_BASE/bin/ray
# 其他环境: $CONDA_BASE/envs/{conda_env}/bin/ray
if [ "{conda_env}" = "base" ]; then
    RAY_CMD="$CONDA_BASE/bin/ray"
else
    RAY_CMD="$CONDA_BASE/envs/{conda_env}/bin/ray"
fi
if [ ! -f "$RAY_CMD" ]; then
    # 如果 conda env 中没有 ray，尝试使用 PATH 中的
    RAY_CMD=$(which ray 2>/dev/null || echo "ray")
fi
echo "[INFO] RAY_CMD: $RAY_CMD"
"""


@app.command("start")
def start_workers():
    """启动所有Worker节点"""
    typer.echo("🚀 启动Worker节点...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何worker节点")
        return  # 没有worker节点不应该视为错误

    head_host = head_config.get("host", "localhost")
    head_port = head_config.get("head_port", 6379)
    worker_bind_host = worker_config.get("bind_host", "localhost")
    worker_temp_dir = worker_config.get("temp_dir", "/tmp/ray_worker")
    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    # 读取 CPU/GPU 资源限制配置（用于容器环境）
    worker_num_cpus = worker_config.get("num_cpus")
    worker_num_gpus = worker_config.get("num_gpus")

    remote_config.get("ray_command") or "ray"
    conda_env = remote_config.get("conda_env", "sage")

    typer.echo("📋 配置信息:")
    typer.echo(f"   Head节点: {head_host}:{head_port}")
    typer.echo(f"   Worker节点: {len(workers)} 个")
    if worker_num_cpus is not None:
        typer.echo(f"   Worker CPUs: {worker_num_cpus}")
    if worker_num_gpus is not None:
        typer.echo(f"   Worker GPUs: {worker_num_gpus}")
    typer.echo(f"   Worker绑定主机: {worker_bind_host}")

    success_count = 0
    import socket

    total_count = len(workers)

    # 构建 CPU/GPU 资源限制参数（用于容器环境）
    resource_args = ""
    if worker_num_cpus is not None:
        resource_args += f" --num-cpus={worker_num_cpus}"
    if worker_num_gpus is not None:
        resource_args += f" --num-gpus={worker_num_gpus}"

    for i, (host, port) in enumerate(workers, 1):
        # Resolve hostname to IP to ensure worker binds to the correct interface
        try:
            node_ip = socket.gethostbyname(host)
        except Exception:
            node_ip = host  # Fallback to hostname if resolution fails

        typer.echo(f"\n🔧 启动Worker节点 {i}/{total_count}: {host}:{port} (IP: {node_ip})")

        start_command = f"""set -e
export PYTHONUNBUFFERED=1

# 当前主机名
CURRENT_HOST='{host}'
# 解析后的IP
RESOLVED_IP='{node_ip}'

# 创建必要目录
LOG_DIR='{worker_log_dir}'
WORKER_TEMP_DIR='{worker_temp_dir}'
mkdir -p "$LOG_DIR" "$WORKER_TEMP_DIR"

# 记录启动时间
echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Ray Worker启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "目标头节点: {head_host}:{head_port}" | tee -a "$LOG_DIR/worker.log"
echo "绑定主机: {worker_bind_host}" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 记录版本信息
echo "[INFO] Python版本: $(python --version 2>&1)" | tee -a "$LOG_DIR/worker.log"
echo "[INFO] Ray版本: $($RAY_CMD --version 2>&1)" | tee -a "$LOG_DIR/worker.log"

# 停止现有的ray进程
echo "[INFO] 停止现有Ray进程..." | tee -a "$LOG_DIR/worker.log"
$RAY_CMD stop >> "$LOG_DIR/worker.log" 2>&1 || true
sleep 2

# 强制清理残留进程
echo "[INFO] 强制清理所有Ray相关进程..." | tee -a "$LOG_DIR/worker.log"
# 使用更精确的匹配模式，并限制为当前用户
pgrep -u $(whoami) -x raylet | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -x gcs_server | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/dashboard/[d]ashboard.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/dashboard/[a]gent.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray.util.client.[s]erver" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/autoscaler/_private/[m]onitor.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/_private/[l]og_monitor.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/core/src/ray/raylet/raylet" | xargs -r kill -9 2>/dev/null || true

# for proc in raylet core_worker log_monitor; do
#     PIDS=$(pgrep -f "$proc" 2>/dev/null || true)
#     if [[ -n "$PIDS" ]]; then
#         echo "[INFO] 发现$proc进程: $PIDS" | tee -a "$LOG_DIR/worker.log"
#         echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
#         sleep 2
#     fi
# done

# 清理Ray会话目录
echo "[INFO] 清理Ray会话目录..." | tee -a "$LOG_DIR/worker.log"
rm -rf "$WORKER_TEMP_DIR"/* 2>/dev/null || true

sleep 3

# 设置节点IP
NODE_IP="{worker_bind_host}"
if [ "{worker_bind_host}" = "localhost" ] || [ "{worker_bind_host}" = "127.0.0.1" ]; then
    NODE_IP="$RESOLVED_IP"
fi
echo "[INFO] 使用节点IP: $NODE_IP" | tee -a "$LOG_DIR/worker.log"

# 设置环境变量
export RAY_TMPDIR="$WORKER_TEMP_DIR"
export RAY_DISABLE_IMPORT_WARNING=1

# 测试连通性
echo "[INFO] 测试到头节点的连通性..." | tee -a "$LOG_DIR/worker.log"
if python -c "import socket; s = socket.socket(); s.settimeout(10); s.connect(('{head_host}', {head_port})); s.close()" 2>/dev/null; then
    echo "[SUCCESS] 可以连接到头节点 {head_host}:{head_port}" | tee -a "$LOG_DIR/worker.log"
else
    echo "[WARNING] 无法验证到头节点的连通性，但继续尝试启动Ray" | tee -a "$LOG_DIR/worker.log"
fi

# 启动ray worker
echo "[INFO] 启动Ray Worker进程..." | tee -a "$LOG_DIR/worker.log"
RAY_START_CMD="$RAY_CMD start --address={head_host}:{head_port} --node-ip-address=$NODE_IP{resource_args}"
echo "[INFO] 执行命令: $RAY_START_CMD" | tee -a "$LOG_DIR/worker.log"

# 执行Ray启动命令并捕获输出和退出码
set +e  # 临时允许命令失败
RAY_OUTPUT=$($RAY_START_CMD 2>&1)
RAY_EXIT_CODE=$?
set -e  # 重新开启严格模式

# 将输出写入日志
echo "$RAY_OUTPUT" | tee -a "$LOG_DIR/worker.log"

# 等待一下让Ray有时间完全启动
sleep 5

# 检查Ray进程是否真正启动成功
RAY_PIDS=$(pgrep -f 'raylet|core_worker' || true)
if [[ -n "$RAY_PIDS" ]]; then
    echo "[SUCCESS] Ray Worker启动成功，进程PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/worker.log"
    echo "[INFO] 节点已连接到集群: {head_host}:{head_port}" | tee -a "$LOG_DIR/worker.log"

    # 验证Ray状态
    if timeout 10 $RAY_CMD status > /dev/null 2>&1; then
        echo "[SUCCESS] Ray集群连接验证成功" | tee -a "$LOG_DIR/worker.log"
    else
        echo "[WARNING] Ray集群连接验证失败，但进程正在运行" | tee -a "$LOG_DIR/worker.log"
    fi
elif [ $RAY_EXIT_CODE -eq 0 ]; then
    echo "[WARNING] Ray启动命令成功但未发现运行中的进程，可能仍在启动中" | tee -a "$LOG_DIR/worker.log"
    sleep 3
    # 再次检查
    RAY_PIDS=$(pgrep -f 'raylet|core_worker' || true)
    if [[ -n "$RAY_PIDS" ]]; then
        echo "[SUCCESS] Ray Worker延迟启动成功，进程PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/worker.log"
    else
        echo "[ERROR] Ray Worker启动失败，未发现进程且退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/worker.log"
        exit 1
    fi
else
    echo "[ERROR] Ray Worker启动失败，退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/worker.log"
    echo "[DEBUG] Ray启动输出: $RAY_OUTPUT" | tee -a "$LOG_DIR/worker.log"
    exit 1
fi"""

        if execute_remote_command(host, port, start_command, 120):
            typer.echo(f"✅ Worker节点 {host} 启动成功")
            success_count += 1
        else:
            typer.echo(f"❌ Worker节点 {host} 启动失败")

    typer.echo(f"\n📊 启动结果: {success_count}/{total_count} 个节点启动成功")
    if success_count == total_count:
        typer.echo("✅ 所有Worker节点启动成功！")
    else:
        typer.echo("⚠️  部分Worker节点启动失败")
        raise typer.Exit(1)


@app.command("stop")
def stop_workers(force: bool = typer.Option(False, "--force", "-f", help="强制停止所有运行时进程")):
    """停止所有Worker节点"""
    typer.echo("🛑 停止Worker节点...")

    config_manager = get_config_manager()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何worker节点")
        raise typer.Exit(1)

    worker_temp_dir = worker_config.get("temp_dir", "/tmp/ray_worker")
    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    remote_config.get("ray_command") or "ray"
    conda_env = remote_config.get("conda_env", "sage")

    success_count = 0
    total_count = len(workers)

    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"\n🔧 停止Worker节点 {i}/{total_count}: {host}:{port}")

        if force:
            # 强制模式：直接杀死所有进程
            stop_command = f'''set +e
export PYTHONUNBUFFERED=1

LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Ray Worker强制停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 强制杀死所有Ray相关进程
echo "[INFO] 强制终止所有Ray进程..." | tee -a "$LOG_DIR/worker.log"
for pattern in 'ray.*start' 'raylet' 'core_worker' 'ray::' 'python.*ray'; do
    PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "[INFO] 强制终止进程: $pattern (PIDs: $PIDS)" | tee -a "$LOG_DIR/worker.log"
        echo "$PIDS" | xargs -r kill -KILL 2>/dev/null || true
    fi
done

# 清理临时文件
WORKER_TEMP_DIR='{worker_temp_dir}'
if [[ -d "$WORKER_TEMP_DIR" ]]; then
    echo "[INFO] 清理临时目录: $WORKER_TEMP_DIR" | tee -a "$LOG_DIR/worker.log"
    rm -rf "$WORKER_TEMP_DIR"/* 2>/dev/null || true
fi

echo "[SUCCESS] Ray Worker强制停止完成 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"'''
        else:
            # 正常模式：优雅停止
            stop_command = f'''set +e
export PYTHONUNBUFFERED=1

LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Ray Worker停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 优雅停止
echo "[INFO] 正在优雅停止Ray进程..." | tee -a "$LOG_DIR/worker.log"
$RAY_CMD stop >> "$LOG_DIR/worker.log" 2>&1 || true
sleep 2

# 强制停止残留进程
echo "[INFO] 清理残留的Ray进程..." | tee -a "$LOG_DIR/worker.log"
for pattern in 'ray.*start' 'raylet' 'core_worker' 'ray::'; do
    PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "[INFO] 终止进程: $pattern (PIDs: $PIDS)" | tee -a "$LOG_DIR/worker.log"
        echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        echo "$PIDS" | xargs -r kill -KILL 2>/dev/null || true
    fi
done

# 清理临时文件
WORKER_TEMP_DIR='{worker_temp_dir}'
if [[ -d "$WORKER_TEMP_DIR" ]]; then
    echo "[INFO] 清理临时目录: $WORKER_TEMP_DIR" | tee -a "$LOG_DIR/worker.log"
    rm -rf "$WORKER_TEMP_DIR"/* 2>/dev/null || true
fi

echo "[SUCCESS] Ray Worker已停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"'''

        if execute_remote_command(host, port, stop_command, 60):
            typer.echo(f"✅ Worker节点 {host} 停止成功")
            success_count += 1
        else:
            typer.echo(f"⚠️  Worker节点 {host} 停止完成（可能本来就未运行）")
            success_count += 1  # 停止操作通常允许失败

    typer.echo(f"\n📊 停止结果: {success_count}/{total_count} 个节点处理完成")
    typer.echo("✅ 所有Worker节点停止操作完成！")


@app.command("status")
def status_workers():
    """检查所有Worker节点状态"""
    typer.echo("📊 检查Worker节点状态...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何worker节点")
        raise typer.Exit(1)

    head_host = head_config.get("host", "localhost")
    head_port = head_config.get("head_port", 6379)
    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    remote_config.get("ray_command") or "ray"
    conda_env = remote_config.get("conda_env", "sage")

    running_count = 0
    total_count = len(workers)

    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"\n📋 检查Worker节点 {i}/{total_count}: {host}:{port}")

        status_command = f'''set +e
export PYTHONUNBUFFERED=1

echo "==============================================="
echo "节点状态检查: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "==============================================="

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 检查Ray进程
echo "--- Ray进程状态 ---"
RAY_PIDS=$(pgrep -f 'raylet|core_worker|ray.*start' 2>/dev/null || true)
if [[ -n "$RAY_PIDS" ]]; then
    echo "[运行中] 发现Ray进程:"
    echo "$RAY_PIDS" | while read pid; do
        if [[ -n "$pid" ]]; then
            ps -p "$pid" -o pid,ppid,pcpu,pmem,etime,cmd --no-headers 2>/dev/null || true
        fi
    done

    echo ""
    echo "--- Ray集群连接状态 ---"
    timeout 10 $RAY_CMD status 2>/dev/null || echo "[警告] 无法获取Ray集群状态"
    exit 0
else
    echo "[已停止] 未发现Ray进程"
    exit 1
fi

echo ""
echo "--- 网络连通性测试 ---"
if timeout 5 nc -z {head_host} {head_port} 2>/dev/null; then
    echo "[正常] 可以连接到头节点 {head_host}:{head_port}"
else
    echo "[异常] 无法连接到头节点 {head_host}:{head_port}"
fi

# 显示最近的日志
LOG_DIR='{worker_log_dir}'
if [[ -f "$LOG_DIR/worker.log" ]]; then
    echo ""
    echo "--- 最近的日志 (最后5行) ---"
    tail -5 "$LOG_DIR/worker.log" 2>/dev/null || echo "无法读取日志文件"
fi

echo "==============================================="'''

        if execute_remote_command(host, port, status_command, 30):
            typer.echo(f"✅ Worker节点 {host} 正在运行")
            running_count += 1
        else:
            typer.echo(f"❌ Worker节点 {host} 未运行或检查失败")

    typer.echo(f"\n📊 状态统计: {running_count}/{total_count} 个Worker节点正在运行")
    if running_count == total_count:
        typer.echo("✅ 所有Worker节点都在正常运行！")
    elif running_count > 0:
        typer.echo("⚠️  部分Worker节点未运行")
    else:
        typer.echo("❌ 没有Worker节点在运行")


@app.command("restart")
def restart_workers():
    """重启所有Worker节点"""
    typer.echo("🔄 重启Worker节点...")

    # 先停止
    typer.echo("第1步: 停止所有Worker节点")
    stop_workers()

    # 等待
    typer.echo("⏳ 等待3秒后重新启动...")
    time.sleep(3)

    # 再启动
    typer.echo("第2步: 启动所有Worker节点")
    start_workers()

    typer.echo("✅ Worker节点重启完成！")


@app.command("config")
def show_config():
    """显示当前Worker配置信息"""
    typer.echo("📋 当前Worker配置信息")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    worker_config = config_manager.get_worker_config()
    ssh_config = config_manager.get_ssh_config()
    remote_config = config_manager.get_remote_config()
    workers = config_manager.get_workers_ssh_hosts()

    typer.echo(f"Head节点: {head_config.get('host', 'N/A')}")
    typer.echo(f"Head端口: {head_config.get('head_port', 'N/A')}")
    typer.echo(f"Dashboard端口: {head_config.get('dashboard_port', 'N/A')}")
    typer.echo(f"Dashboard主机: {head_config.get('dashboard_host', 'N/A')}")
    typer.echo(f"Worker绑定主机: {worker_config.get('bind_host', 'N/A')}")
    typer.echo(f"Worker节点数量: {len(workers)}")
    if workers:
        for i, (host, port) in enumerate(workers, 1):
            typer.echo(f"  Worker {i}: {host}:{port}")
    typer.echo(f"SSH用户: {ssh_config.get('user', 'N/A')}")
    typer.echo(f"SSH密钥路径: {ssh_config.get('key_path', 'N/A')}")
    typer.echo(f"Worker临时目录: {worker_config.get('temp_dir', 'N/A')}")
    typer.echo(f"Worker日志目录: {worker_config.get('log_dir', 'N/A')}")
    typer.echo(f"远程SAGE目录: {remote_config.get('sage_home', 'N/A')}")
    typer.echo(f"远程Python路径: {remote_config.get('python_path', 'N/A')}")
    typer.echo(
        f"远程运行时命令: {remote_config.get('runtime_command', remote_config.get('ray_command', 'N/A'))}"
    )


@app.command("deploy")
def deploy_workers():
    """部署项目到所有Worker节点"""
    typer.echo("🚀 开始部署到Worker节点...")

    deployment_manager = DeploymentManager()
    success_count, total_count = deployment_manager.deploy_to_all_workers()

    if success_count == total_count:
        typer.echo("✅ 所有节点部署成功！")
    else:
        typer.echo("⚠️  部分节点部署失败")
        raise typer.Exit(1)


@app.command("add")
def add_worker(node: str = typer.Argument(..., help="节点地址，格式为 host:port")):
    """动态添加新的Worker节点"""
    typer.echo(f"➕ 添加新Worker节点: {node}")

    # 解析节点地址
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

    # 添加到配置
    if config_manager.add_worker_ssh_host(host, port):
        typer.echo(f"✅ 已添加Worker节点 {host}:{port} 到配置")
    else:
        typer.echo(f"⚠️  Worker节点 {host}:{port} 已存在")

    # 部署到新节点
    typer.echo(f"🚀 开始部署到新节点 {host}:{port}...")
    deployment_manager = DeploymentManager()

    if deployment_manager.deploy_to_worker(host, port):
        typer.echo(f"✅ 新节点 {host}:{port} 部署成功")

        # 启动worker
        typer.echo("🔧 启动新Worker节点...")
        head_config = config_manager.get_head_config()
        worker_config = config_manager.get_worker_config()
        remote_config = config_manager.get_remote_config()

        head_host = head_config.get("host", "localhost")
        head_port = head_config.get("head_port", 6379)
        worker_bind_host = worker_config.get("bind_host", "localhost")
        worker_temp_dir = worker_config.get("temp_dir", "/tmp/ray_worker")
        worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
        worker_num_cpus = worker_config.get("num_cpus")
        worker_num_gpus = worker_config.get("num_gpus")
        remote_config.get("ray_command") or "ray"
        conda_env = remote_config.get("conda_env", "sage")

        # 构建 CPU/GPU 资源限制参数（用于容器环境）
        resource_args = ""
        if worker_num_cpus is not None:
            resource_args += f" --num-cpus={worker_num_cpus}"
        if worker_num_gpus is not None:
            resource_args += f" --num-gpus={worker_num_gpus}"

        # 解析主机名为IP，避免 --node-ip-address 传入不可用的占位值
        import socket

        try:
            resolved_ip = socket.gethostbyname(host)
        except Exception:
            resolved_ip = host

        start_command = f"""set -e
export PYTHONUNBUFFERED=1

CURRENT_HOST='{host}'
RESOLVED_IP='{resolved_ip}'
LOG_DIR='{worker_log_dir}'
WORKER_TEMP_DIR='{worker_temp_dir}'
mkdir -p "$LOG_DIR" "$WORKER_TEMP_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "新Worker节点启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "目标头节点: {head_host}:{head_port}" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 停止现有的ray进程
$RAY_CMD stop >> "$LOG_DIR/worker.log" 2>&1 || true
sleep 2

# 强制清理残留进程与默认Ray会话目录，避免 node_ip_address.json 记录的旧值导致异常
echo "[INFO] 强制清理所有Ray相关进程..." | tee -a "$LOG_DIR/worker.log"
pgrep -u $(whoami) -x raylet | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -x gcs_server | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/dashboard/[d]ashboard.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/dashboard/[a]gent.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray.util.client.[s]erver" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/_private/[l]og_monitor.py" | xargs -r kill -9 2>/dev/null || true
pgrep -u $(whoami) -f "ray/core/src/ray/raylet/raylet" | xargs -r kill -9 2>/dev/null || true

# 清理常见Ray临时目录
echo "[INFO] 清理Ray临时目录 /tmp/ray" | tee -a "$LOG_DIR/worker.log"
rm -rf /tmp/ray/* 2>/dev/null || true

# 设置节点IP
NODE_IP="{worker_bind_host}"
if [ "{worker_bind_host}" = "localhost" ] || [ "{worker_bind_host}" = "127.0.0.1" ]; then
    NODE_IP="$RESOLVED_IP"
fi

export RAY_TMPDIR="$WORKER_TEMP_DIR"
export RAY_DISABLE_IMPORT_WARNING=1

# 启动ray worker
echo "[INFO] 启动Ray Worker进程..." | tee -a "$LOG_DIR/worker.log"

RAY_START_CMD="$RAY_CMD start --address={head_host}:{head_port} --node-ip-address=$NODE_IP --temp-dir=$WORKER_TEMP_DIR{resource_args}"

echo "[INFO] 执行命令: $RAY_START_CMD" | tee -a "$LOG_DIR/worker.log"

# 执行Ray启动命令并捕获输出和退出码
set +e  # 临时允许命令失败
RAY_OUTPUT=$($RAY_START_CMD 2>&1)
RAY_EXIT_CODE=$?
set -e  # 重新开启严格模式

# 将输出写入日志
echo "$RAY_OUTPUT" | tee -a "$LOG_DIR/worker.log"

# 等待一下让Ray有时间启动
sleep 5

# 检查Ray是否启动成功
RAY_PIDS=$(pgrep -f 'raylet|core_worker' || true)
if [[ -n "$RAY_PIDS" ]]; then
    echo "[SUCCESS] 新Worker节点启动成功，PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/worker.log"
elif [ $RAY_EXIT_CODE -eq 0 ]; then
    echo "[WARNING] Ray启动命令成功但未发现运行中的进程，可能仍在启动中" | tee -a "$LOG_DIR/worker.log"
    sleep 3
    # 再次检查
    RAY_PIDS=$(pgrep -f 'raylet|core_worker' || true)
    if [[ -n "$RAY_PIDS" ]]; then
        echo "[SUCCESS] 新Worker节点延迟启动成功，PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/worker.log"
    else
        echo "[ERROR] 新Worker节点启动失败，未发现进程" | tee -a "$LOG_DIR/worker.log"
        echo "[DEBUG] Ray启动输出: $RAY_OUTPUT" | tee -a "$LOG_DIR/worker.log"
        exit 1
    fi
else
    echo "[ERROR] 新Worker节点启动失败，退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/worker.log"
    echo "[DEBUG] Ray启动输出: $RAY_OUTPUT" | tee -a "$LOG_DIR/worker.log"
    exit 1
fi"""

        if execute_remote_command(host, port, start_command, 30):
            typer.echo(f"✅ 新Worker节点 {host}:{port} 启动成功")
        else:
            typer.echo(f"❌ 新Worker节点 {host}:{port} 启动失败")
            raise typer.Exit(1)
    else:
        typer.echo(f"❌ 新节点 {host}:{port} 部署失败")
        raise typer.Exit(1)


@app.command("remove")
def remove_worker(node: str = typer.Argument(..., help="节点地址，格式为 host:port")):
    """移除Worker节点"""
    typer.echo(f"➖ 移除Worker节点: {node}")

    # 解析节点地址
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

    # 先停止该节点上的worker
    typer.echo(f"🛑 停止Worker节点 {host}:{port}...")
    worker_config = config_manager.get_worker_config()
    remote_config = config_manager.get_remote_config()

    worker_temp_dir = worker_config.get("temp_dir", "/tmp/ray_worker")
    worker_log_dir = worker_config.get("log_dir", "/tmp/sage_worker_logs")
    remote_config.get("ray_command") or "ray"
    conda_env = remote_config.get("conda_env", "sage")

    stop_command = f'''set +e
LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "停止Worker节点 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 停止Ray
$RAY_CMD stop >> "$LOG_DIR/worker.log" 2>&1 || true

# 强制清理
for pattern in 'ray.*start' 'raylet' 'core_worker'; do
    PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        echo "$PIDS" | xargs -r kill -KILL 2>/dev/null || true
    fi
done

# 清理临时文件
rm -rf {worker_temp_dir}/* 2>/dev/null || true

echo "Worker节点已停止" | tee -a "$LOG_DIR/worker.log"'''

    if execute_remote_command(host, port, stop_command, 60):
        typer.echo(f"✅ Worker节点 {host}:{port} 已停止")
    else:
        typer.echo(f"⚠️  Worker节点 {host}:{port} 停止可能未完全成功")

    # 从配置中移除
    if config_manager.remove_worker_ssh_host(host, port):
        typer.echo(f"✅ 已从配置中移除Worker节点 {host}:{port}")
    else:
        typer.echo(f"⚠️  Worker节点 {host}:{port} 不在配置中")

    typer.echo(f"✅ Worker节点 {host}:{port} 移除完成")


@app.command("list")
def list_workers():
    """列出所有配置的Worker节点"""
    typer.echo("📋 配置的Worker节点列表")

    config_manager = get_config_manager()
    workers = config_manager.get_workers_ssh_hosts()

    if not workers:
        typer.echo("❌ 未配置任何Worker节点")
        typer.echo("💡 使用 'sage worker add <host> [port]' 添加Worker节点")
        return

    typer.echo(f"📊 共配置了 {len(workers)} 个Worker节点:")
    for i, (host, port) in enumerate(workers, 1):
        typer.echo(f"  {i}. {host}:{port}")

    typer.echo("\n💡 使用 'sage worker status' 检查节点状态")


@app.command("version")
def version_command():
    """Show version information."""
    typer.echo("👥 SAGE Worker Manager")
    typer.echo("Version: 1.0.1")
    typer.echo("Author: IntelliStream Team")
    typer.echo("Repository: https://github.com/intellistream/SAGE")


if __name__ == "__main__":
    app()
