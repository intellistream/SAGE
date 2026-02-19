#!/usr/bin/env python3
"""
SAGE Head Manager CLI
Head节点管理相关命令
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import typer

from ...management.config_manager import get_config_manager

app = typer.Typer(name="head", help="Head节点管理")


def get_conda_init_code(conda_env: str = "sage") -> str:
    """获取Conda环境初始化代码"""
    return f"""
# 检查是否已经在目标环境中
if [[ "$CONDA_DEFAULT_ENV" == "{conda_env}" ]]; then
    echo "[INFO] 已在conda环境: {conda_env}"
else
    # 多种conda安装路径尝试
    CONDA_FOUND=false
    for conda_path in \\
        "$HOME/miniconda3/etc/profile.d/conda.sh" \\
        "$HOME/anaconda3/etc/profile.d/conda.sh" \\
        "/opt/conda/etc/profile.d/conda.sh" \\
        "/usr/local/miniconda3/etc/profile.d/conda.sh" \\
        "/usr/local/anaconda3/etc/profile.d/conda.sh"; do
        if [ -f "$conda_path" ]; then
            source "$conda_path"
            echo "[INFO] 找到conda: $conda_path"
            CONDA_FOUND=true
            break
        fi
    done

    if [ "$CONDA_FOUND" = "false" ]; then
        echo "[WARNING] 未找到conda安装，跳过conda环境激活"
    else
        # 激活sage环境
        if conda activate {conda_env} 2>/dev/null; then
            echo "[SUCCESS] 已激活conda环境: {conda_env}"
        else
            echo "[WARNING] 无法激活conda环境: {conda_env}，继续使用当前环境"
        fi
    fi
fi
"""


def check_ray_running(head_port: int) -> tuple[bool, list[int]]:
    """检查运行时Head是否已经在运行

    返回: (是否运行, 进程ID列表)

    使用 ps + grep 检查进程，避免匹配到自身
    """
    pids = []

    # 使用 grep 技巧避免匹配自身: [g]cs_server 不会匹配包含 "gcs_server" 字符串的 grep 命令
    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                """
ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep -E '[g]cs_server.*--gcs_server_port|[r]aylet.*--raylet_socket_name' | awk '{print $1}'
""",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                pid_str = line.strip()
                if pid_str.isdigit():
                    pids.append(int(pid_str))
    except Exception:
        pass

    # 备选：检查端口是否被占用
    if not pids:
        try:
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"ss -tlnp 2>/dev/null | grep ':{head_port}' | grep -oP 'pid=\\K[0-9]+'",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for pid_str in result.stdout.strip().split("\n"):
                    if pid_str.strip().isdigit():
                        pids.append(int(pid_str.strip()))
        except Exception:
            pass

    return len(pids) > 0, pids


def force_cleanup_ray_processes(head_log_dir: str, ray_command: str, verbose: bool = True) -> bool:
    """强制清理所有运行时相关进程

    返回: 是否成功清理
    """
    # 首先使用 ray stop 命令
    try:
        result = subprocess.run(
            ["bash", "-c", f"{ray_command} stop 2>&1"], capture_output=True, text=True, timeout=30
        )
        if verbose and result.stdout:
            typer.echo(result.stdout.strip())
    except Exception:
        pass

    time.sleep(2)

    # 然后使用 ps + grep 找到并清理残留进程
    cleanup_command = f"""
set +e
LOG_DIR='{head_log_dir}'
mkdir -p "$LOG_DIR"

echo "[INFO] 清理Ray残留进程..." | tee -a "$LOG_DIR/head.log"

# 使用 grep 技巧避免匹配自身: [g]cs_server 不会匹配 grep 命令本身
GCS_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[g]cs_server.*--gcs_server_port' | awk '{{print $1}}')
RAYLET_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[r]aylet.*--raylet_socket_name' | awk '{{print $1}}')

if [[ -n "$GCS_PIDS" ]]; then
    echo "[INFO] 终止 gcs_server 进程: $GCS_PIDS" | tee -a "$LOG_DIR/head.log"
    echo "$GCS_PIDS" | xargs -r kill -TERM 2>/dev/null || true
fi

if [[ -n "$RAYLET_PIDS" ]]; then
    echo "[INFO] 终止 raylet 进程: $RAYLET_PIDS" | tee -a "$LOG_DIR/head.log"
    echo "$RAYLET_PIDS" | xargs -r kill -TERM 2>/dev/null || true
fi

sleep 2

# 强制终止
GCS_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[g]cs_server.*--gcs_server_port' | awk '{{print $1}}')
RAYLET_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[r]aylet.*--raylet_socket_name' | awk '{{print $1}}')

if [[ -n "$GCS_PIDS" ]] || [[ -n "$RAYLET_PIDS" ]]; then
    echo "[WARNING] 强制终止残留进程..." | tee -a "$LOG_DIR/head.log"
    echo "$GCS_PIDS $RAYLET_PIDS" | xargs -r kill -9 2>/dev/null || true
    sleep 1
fi

# 验证
REMAINING=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep -E '[g]cs_server.*--gcs_server_port|[r]aylet.*--raylet_socket_name' | awk '{{print $1}}')
if [[ -z "$REMAINING" ]]; then
    echo "[SUCCESS] Ray进程清理完成" | tee -a "$LOG_DIR/head.log"
    exit 0
else
    echo "[WARNING] 仍有残留进程: $REMAINING" | tee -a "$LOG_DIR/head.log"
    exit 1
fi
"""

    try:
        result = subprocess.run(
            ["bash", "-c", cleanup_command], capture_output=True, text=True, timeout=30
        )
        if verbose and result.stdout:
            typer.echo(result.stdout)
        return result.returncode == 0
    except Exception as e:
        if verbose:
            typer.echo(f"[WARNING] 清理过程出错: {e}")
        return False


@app.command("start")
def start_head(
    force: bool = typer.Option(
        False, "--force", "-f", help="强制重启：如果运行时已在运行，先停止再启动"
    ),
):
    """启动Head节点"""
    typer.echo("🚀 启动Head节点...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    config_manager.get_remote_config()

    head_host = head_config.get("host", "localhost")
    head_port = head_config.get("head_port", 6379)
    dashboard_port = head_config.get("dashboard_port", 8265)
    ray_client_server_port = head_config.get("ray_client_server_port", 10001)
    dashboard_host = head_config.get("dashboard_host", "0.0.0.0")
    head_temp_dir = head_config.get("temp_dir", "/tmp/ray_head")
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")

    # 容器资源配置 (覆盖自动检测)
    num_cpus = head_config.get("num_cpus")  # None 表示自动检测
    num_gpus = head_config.get("num_gpus")  # None 表示自动检测

    # 优先使用配置中的ray命令，否则尝试使用当前环境的ray
    ray_command = head_config.get("ray_command")
    if not ray_command:
        ray_command = os.path.join(os.path.dirname(sys.executable), "ray")
        if not os.path.exists(ray_command):
            ray_command = "ray"  # Fallback to PATH

    conda_env = head_config.get("conda_env", "sage")

    typer.echo("📋 配置信息:")
    typer.echo(f"   Head主机: {head_host}")
    typer.echo(f"   Head端口: {head_port}")
    typer.echo(f"   Dashboard: {dashboard_host}:{dashboard_port}")
    typer.echo(f"   临时目录: {head_temp_dir}")
    typer.echo(f"   日志目录: {head_log_dir}")
    if num_cpus is not None:
        typer.echo(f"   CPU核心数: {num_cpus} (显式配置)")
    if num_gpus is not None:
        typer.echo(f"   GPU数量: {num_gpus} (显式配置)")

    # 检查是否已有Ray实例在运行
    is_running, pids = check_ray_running(head_port)
    if is_running:
        if force:
            typer.echo(f"⚠️  检测到运行时已在运行 (PIDs: {pids})，正在强制停止...")
            if not force_cleanup_ray_processes(head_log_dir, ray_command):
                typer.echo("❌ 无法清理现有运行时进程，请手动执行: sage cluster head stop")
                raise typer.Exit(1)
            typer.echo("✅ 现有运行时进程已清理")
            time.sleep(2)
        else:
            typer.echo(f"⚠️  Head节点已在运行 (PIDs: {pids})")
            typer.echo("💡 如需重启，请使用: sage cluster head start --force")
            typer.echo("   或先停止: sage cluster head stop")
            typer.echo(f"🌐 Dashboard可能已可访问: http://{dashboard_host}:{dashboard_port}")
            raise typer.Exit(0)

    # 使用 ray stop 先清理，再启动
    start_command = f"""
export PYTHONUNBUFFERED=1

# 确保不因命令失败而退出
set +e

# 创建必要目录
LOG_DIR='{head_log_dir}'
HEAD_TEMP_DIR='{head_temp_dir}'
mkdir -p "$LOG_DIR" "$HEAD_TEMP_DIR"

# 记录启动时间
echo "===============================================" | tee -a "$LOG_DIR/head.log"
echo "Ray Head启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"
echo "Head节点: $(hostname)" | tee -a "$LOG_DIR/head.log"
echo "监听地址: {head_host}:{head_port}" | tee -a "$LOG_DIR/head.log"
echo "Dashboard: {dashboard_host}:{dashboard_port}" | tee -a "$LOG_DIR/head.log"
echo "===============================================" | tee -a "$LOG_DIR/head.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 使用 ray stop 清理（最安全的方式）
echo "[INFO] 使用 ray stop 清理现有进程..." | tee -a "$LOG_DIR/head.log"
{ray_command} stop >> "$LOG_DIR/head.log" 2>&1 || true
sleep 2

# 清理临时目录
rm -rf "$HEAD_TEMP_DIR"/* 2>/dev/null || true
rm -f dump.rdb 2>/dev/null || true

# 设置环境变量
export RAY_TMPDIR="$HEAD_TEMP_DIR"
export RAY_DISABLE_IMPORT_WARNING=1

# 构建 Ray 启动命令
# 基础命令
RAY_START_CMD="{ray_command} start --head --port={head_port} --ray-client-server-port={ray_client_server_port} --node-ip-address={head_host} --dashboard-host={dashboard_host} --dashboard-port={dashboard_port} --temp-dir=$HEAD_TEMP_DIR --disable-usage-stats"

# 添加 CPU/GPU 资源限制 (用于容器环境)
{f'RAY_START_CMD="$RAY_START_CMD --num-cpus={num_cpus}"' if num_cpus is not None else "# num_cpus: 自动检测"}
{f'RAY_START_CMD="$RAY_START_CMD --num-gpus={num_gpus}"' if num_gpus is not None else "# num_gpus: 自动检测"}

# 启动ray head
echo "[INFO] 启动Ray Head进程..." | tee -a "$LOG_DIR/head.log"
echo "[INFO] 执行命令: $RAY_START_CMD" | tee -a "$LOG_DIR/head.log"

# 执行启动命令并捕获所有输出
$RAY_START_CMD 2>&1 | tee -a "$LOG_DIR/head.log"
RAY_EXIT_CODE=${{PIPESTATUS[0]}}

echo "[INFO] Ray启动命令退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/head.log"

if [ $RAY_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Ray Head启动成功" | tee -a "$LOG_DIR/head.log"
    sleep 3

    # 使用 grep 技巧避免匹配自身
    RAY_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep -E '[g]cs_server.*--gcs_server_port|[r]aylet.*--raylet_socket_name' | awk '{{print $1}}' | tr '\\n' ' ')
    if [[ -n "$RAY_PIDS" ]]; then
        echo "[SUCCESS] Ray Head进程正在运行，PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/head.log"
        echo "[INFO] Ray集群已启动，监听端口: {head_port}" | tee -a "$LOG_DIR/head.log"
        echo "[INFO] Dashboard可访问: http://{head_host}:{dashboard_port}" | tee -a "$LOG_DIR/head.log"
    else
        echo "[WARNING] Ray启动命令成功但未发现运行中的进程" | tee -a "$LOG_DIR/head.log"
    fi
else
    echo "[ERROR] Ray Head启动失败，退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/head.log"
    exit 1
fi"""

    try:
        result = subprocess.run(
            ["bash", "-c", start_command], capture_output=True, text=True, timeout=120
        )

        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        if result.returncode == 0:
            typer.echo("✅ Head节点启动成功")
            typer.echo(f"🌐 Dashboard访问地址: http://{dashboard_host}:{dashboard_port}")
        else:
            typer.echo("❌ Head节点启动失败")
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head节点启动超时")
        typer.echo("💡 可能的原因：")
        typer.echo(f"   1. 端口被占用 - 检查: ss -tlnp | grep {head_port}")
        typer.echo("   2. 残留进程 - 尝试: sage cluster head stop")
        typer.echo("   3. 资源不足 - 检查系统资源")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Head节点启动失败: {e}")
        raise typer.Exit(1)


@app.command("stop")
def stop_head():
    """停止Head节点"""
    typer.echo("🛑 停止Head节点...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    config_manager.get_remote_config()

    head_temp_dir = head_config.get("temp_dir", "/tmp/ray_head")
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    conda_env = head_config.get("conda_env", "sage")

    # 优先使用配置中的ray命令，否则尝试使用当前环境的ray
    ray_command = head_config.get("ray_command")
    if not ray_command:
        ray_command = os.path.join(os.path.dirname(sys.executable), "ray")
        if not os.path.exists(ray_command):
            ray_command = "ray"  # Fallback to PATH

    stop_command = f'''set +e
export PYTHONUNBUFFERED=1

LOG_DIR='{head_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/head.log"
echo "Ray Head停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"
echo "Head节点: $(hostname)" | tee -a "$LOG_DIR/head.log"
echo "===============================================" | tee -a "$LOG_DIR/head.log"

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 优雅停止
echo "[INFO] 正在优雅停止Ray进程..." | tee -a "$LOG_DIR/head.log"
{ray_command} stop 2>&1 | tee -a "$LOG_DIR/head.log" || true
sleep 2

# 使用 grep 技巧清理残留进程
echo "[INFO] 清理残留的Ray进程..." | tee -a "$LOG_DIR/head.log"
GCS_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[g]cs_server.*--gcs_server_port' | awk '{{print $1}}')
RAYLET_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep '[r]aylet.*--raylet_socket_name' | awk '{{print $1}}')

if [[ -n "$GCS_PIDS" ]]; then
    echo "[INFO] 终止 gcs_server: $GCS_PIDS" | tee -a "$LOG_DIR/head.log"
    echo "$GCS_PIDS" | xargs -r kill -TERM 2>/dev/null || true
    sleep 1
    echo "$GCS_PIDS" | xargs -r kill -9 2>/dev/null || true
fi

if [[ -n "$RAYLET_PIDS" ]]; then
    echo "[INFO] 终止 raylet: $RAYLET_PIDS" | tee -a "$LOG_DIR/head.log"
    echo "$RAYLET_PIDS" | xargs -r kill -TERM 2>/dev/null || true
    sleep 1
    echo "$RAYLET_PIDS" | xargs -r kill -9 2>/dev/null || true
fi

# 清理临时文件
HEAD_TEMP_DIR='{head_temp_dir}'
if [[ -d "$HEAD_TEMP_DIR" ]]; then
    echo "[INFO] 清理临时目录: $HEAD_TEMP_DIR" | tee -a "$LOG_DIR/head.log"
    rm -rf "$HEAD_TEMP_DIR"/* 2>/dev/null || true
fi

echo "[SUCCESS] Ray Head已停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"'''

    try:
        result = subprocess.run(
            ["bash", "-c", stop_command], capture_output=True, text=True, timeout=60
        )

        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        typer.echo("✅ Head节点停止完成")

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head节点停止超时")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Head节点停止失败: {e}")
        raise typer.Exit(1)


@app.command("status")
def status_head():
    """检查Head节点状态"""
    typer.echo("�� 检查Head节点状态...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    config_manager.get_remote_config()

    head_host = head_config.get("host", "localhost")
    head_port = head_config.get("head_port", 6379)
    dashboard_port = head_config.get("dashboard_port", 8265)
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    conda_env = head_config.get("conda_env", "sage")

    # 优先使用配置中的ray命令，否则尝试使用当前环境的ray
    ray_command = head_config.get("ray_command")
    if not ray_command:
        ray_command = os.path.join(os.path.dirname(sys.executable), "ray")
        if not os.path.exists(ray_command):
            ray_command = "ray"  # Fallback to PATH

    status_command = f'''set +e
export PYTHONUNBUFFERED=1

echo "==============================================="
echo "Ray Head状态检查: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "==============================================="

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 使用 grep 技巧检查Ray进程
echo "--- Ray Head进程状态 ---"
RAY_PIDS=$(ps -u $(whoami) -o pid,cmd --no-headers 2>/dev/null | grep -E '[g]cs_server.*--gcs_server_port|[r]aylet.*--raylet_socket_name' | awk '{{print $1}}')
if [[ -n "$RAY_PIDS" ]]; then
    echo "[运行中] 发现Ray Head进程:"
    echo "$RAY_PIDS" | while read pid; do
        if [[ -n "$pid" ]]; then
            ps -p "$pid" -o pid,ppid,pcpu,pmem,etime,cmd --no-headers 2>/dev/null || true
        fi
    done

    echo ""
    echo "--- Ray集群状态 ---"
    timeout 10 {ray_command} status 2>/dev/null || echo "[警告] 无法获取Ray集群状态"

    echo ""
    echo "--- 端口监听状态 ---"
    echo "Head端口 {head_port}:"
    ss -tlnp 2>/dev/null | grep ":{head_port}" || netstat -tlnp 2>/dev/null | grep ":{head_port}" || echo "  未监听"
    echo "Dashboard端口 {dashboard_port}:"
    ss -tlnp 2>/dev/null | grep ":{dashboard_port}" || netstat -tlnp 2>/dev/null | grep ":{dashboard_port}" || echo "  未监听"

    exit 0
else
    echo "[已停止] 未发现Ray Head进程"
    exit 1
fi

# 显示最近的日志
LOG_DIR='{head_log_dir}'
if [[ -f "$LOG_DIR/head.log" ]]; then
    echo ""
    echo "--- 最近的日志 (最后5行) ---"
    tail -5 "$LOG_DIR/head.log" 2>/dev/null || echo "无法读取日志文件"
fi

echo "==============================================="'''

    try:
        result = subprocess.run(
            ["bash", "-c", status_command], capture_output=True, text=True, timeout=30
        )

        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        if result.returncode == 0:
            typer.echo("✅ Head节点正在运行")
            typer.echo(f"🌐 Dashboard访问地址: http://{head_host}:{dashboard_port}")
        else:
            typer.echo("❌ Head节点未运行")

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head节点状态检查超时")
    except Exception as e:
        typer.echo(f"❌ Head节点状态检查失败: {e}")


@app.command("restart")
def restart_head():
    """重启Head节点"""
    typer.echo("🔄 重启Head节点...")

    # 先停止
    typer.echo("第1步: 停止Head节点")
    stop_head()

    # 等待
    typer.echo("⏳ 等待3秒后重新启动...")
    time.sleep(3)

    # 再启动
    typer.echo("第2步: 启动Head节点")
    start_head(force=False)

    typer.echo("✅ Head节点重启完成.")


@app.command("logs")
def show_logs(lines: int = typer.Option(20, "--lines", "-n", help="显示日志行数")):
    """显示Head节点日志"""
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    log_file = Path(head_log_dir) / "head.log"

    if not log_file.exists():
        typer.echo("❌ 日志文件不存在")
        return

    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_file)], capture_output=True, text=True
        )

        if result.stdout:
            typer.echo(f"📋 Head节点日志 (最后{lines}行):")
            typer.echo("=" * 50)
            typer.echo(result.stdout)
        else:
            typer.echo("📋 日志文件为空")

    except Exception as e:
        typer.echo(f"❌ 读取日志失败: {e}")


@app.command("version")
def version_command():
    """Show version information."""
    typer.echo("🏠 SAGE Head Manager")
    typer.echo("Version: 1.0.5")
    typer.echo("Author: IntelliStream Team")
    typer.echo("Repository: https://github.com/intellistream/SAGE")


if __name__ == "__main__":
    app()
