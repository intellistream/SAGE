#!/usr/bin/env python3
"""
SAGE Head Manager CLI
Head节点（Flownet 主节点）管理命令

使用 sageFlownet 作为分布式运行时。
Head 节点是集群中的第一个节点，Worker 节点通过 --seed 参数加入。
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import typer

from ...management.config_manager import get_config_manager

app = typer.Typer(name="head", help="Head节点（Flownet 主节点）管理")


def get_conda_init_code(conda_env: str = "sage") -> str:
    """获取 Conda 环境初始化代码"""
    return f"""
# 检查是否已经在目标环境中
if [[ "$CONDA_DEFAULT_ENV" == "{conda_env}" ]]; then
    echo "[INFO] 已在conda环境: {conda_env}"
else
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
        if conda activate {conda_env} 2>/dev/null; then
            echo "[SUCCESS] 已激活conda环境: {conda_env}"
        else
            echo "[WARNING] 无法激活conda环境: {conda_env}，继续使用当前环境"
        fi
    fi
fi
"""


def _find_flownet_cmd() -> str:
    """找到 flownet CLI 可执行文件路径"""
    candidate = os.path.join(os.path.dirname(sys.executable), "flownet")
    if os.path.exists(candidate):
        return candidate
    return "flownet"


def _run_local(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """在本地执行 shell 命令，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def check_flownet_running() -> bool:
    """检查 Flownet 节点是否已在本地运行"""
    flownet_cmd = _find_flownet_cmd()
    rc, out, _ = _run_local(f"{flownet_cmd} node status --no-probe 2>/dev/null", timeout=10)
    return rc == 0 and "running" in out.lower()


@app.command("start")
def start_head(
    force: bool = typer.Option(
        False, "--force", "-f", help="强制重启：如果 Flownet 节点已运行，先停止再启动"
    ),
    foreground: bool = typer.Option(False, "--foreground", help="在前台运行（默认后台守护进程）"),
):
    """启动 Head 节点（Flownet 主节点）"""
    typer.echo("🚀 启动 Head 节点（Flownet 运行时）...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()

    head_host = head_config.get("host", "127.0.0.1")
    flownet_port = head_config.get("flownet_port", head_config.get("head_port", 8787))
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    conda_env = head_config.get("conda_env", "sage")
    num_cpus = head_config.get("num_cpus")
    num_gpus = head_config.get("num_gpus")
    threads = head_config.get("threads", 4)

    Path(head_log_dir).mkdir(parents=True, exist_ok=True)
    log_file = f"{head_log_dir}/head.log"

    flownet_cmd = _find_flownet_cmd()

    typer.echo("📋 配置信息:")
    typer.echo(f"   Head 主机: {head_host}")
    typer.echo(f"   Flownet 端口: {flownet_port}")
    typer.echo(f"   日志目录: {head_log_dir}")
    typer.echo(f"   线程数: {threads}")
    if num_cpus is not None:
        typer.echo(f"   CPU 核心数: {num_cpus}")
    if num_gpus is not None:
        typer.echo(f"   GPU 数量: {num_gpus}")

    if check_flownet_running():
        if force:
            typer.echo("⚠️  检测到 Flownet 节点已在运行，正在强制停止...")
            rc_stop, out_stop, _ = _run_local(
                f"{flownet_cmd} node stop --force --timeout=10", timeout=30
            )
            if out_stop:
                typer.echo(out_stop.strip())
            if rc_stop != 0:
                typer.echo("❌ 无法停止现有 Flownet 节点，请手动执行: sage cluster head stop")
                raise typer.Exit(1)
            typer.echo("✅ 现有节点已停止")
            time.sleep(2)
        else:
            typer.echo("⚠️  Head 节点已在运行")
            typer.echo("💡 如需重启，请使用: sage cluster head start --force")
            raise typer.Exit(0)

    resource_flags = ""
    if num_cpus is not None:
        resource_flags += f" --resource=cpu={num_cpus}"
    if num_gpus is not None:
        resource_flags += f" --resource=gpu={num_gpus}"

    foreground_flag = "--foreground" if foreground else ""
    conda_init = get_conda_init_code(conda_env)

    start_script = f"""set +e
export PYTHONUNBUFFERED=1
{conda_init}

LOG_DIR='{head_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/head.log"
echo "Flownet Head 节点启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"
echo "主机: $(hostname)  绑定: {head_host}:{flownet_port}" | tee -a "$LOG_DIR/head.log"
echo "===============================================" | tee -a "$LOG_DIR/head.log"

echo "[INFO] Python: $(python --version 2>&1)" | tee -a "$LOG_DIR/head.log"
FLOWNET_VER=$(python -c 'import sage.flownet; print(sage.flownet.__version__)' 2>/dev/null || echo '不可用')
echo "[INFO] sageFlownet: $FLOWNET_VER" | tee -a "$LOG_DIR/head.log"

echo "[INFO] 启动 Flownet Head 节点..." | tee -a "$LOG_DIR/head.log"
{flownet_cmd} node start \\
    --node-id=head \\
    --bind={head_host}:{flownet_port} \\
    --threads={threads} \\
    --log-file="{log_file}"{resource_flags} {foreground_flag} 2>&1 | tee -a "$LOG_DIR/head.log"

EXIT_CODE=${{PIPESTATUS[0]}}
echo "[INFO] 启动命令退出码: $EXIT_CODE" | tee -a "$LOG_DIR/head.log"

if [ $EXIT_CODE -eq 0 ]; then
    sleep 2
    {flownet_cmd} node status 2>/dev/null | tee -a "$LOG_DIR/head.log" || true
    echo "[SUCCESS] Flownet Head 节点启动成功，监听: {head_host}:{flownet_port}" | tee -a "$LOG_DIR/head.log"
else
    echo "[ERROR] Flownet Head 节点启动失败，退出码: $EXIT_CODE" | tee -a "$LOG_DIR/head.log"
    exit 1
fi"""

    try:
        result = subprocess.run(
            ["bash", "-c", start_script], capture_output=True, text=True, timeout=120
        )
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        if result.returncode == 0:
            typer.echo("✅ Head 节点启动成功")
            typer.echo(f"   绑定地址: {head_host}:{flownet_port}")
            typer.echo("💡 Worker 节点通过以下命令加入: sage cluster worker start")
        else:
            typer.echo("❌ Head 节点启动失败")
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head 节点启动超时")
        typer.echo("💡 可能的原因:")
        typer.echo(f"   1. 端口被占用 - 检查: ss -tlnp | grep {flownet_port}")
        typer.echo('   2. sageFlownet 未安装 - 检查: python -c "import sage.flownet"')
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Head 节点启动失败: {e}")
        raise typer.Exit(1)


@app.command("stop")
def stop_head(
    force: bool = typer.Option(False, "--force", "-f", help="强制终止（优雅停止超时后 kill）"),
    timeout: float = typer.Option(8.0, "--timeout", help="优雅停止等待时间（秒）"),
):
    """停止 Head 节点"""
    typer.echo("🛑 停止 Head 节点（Flownet 运行时）...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    conda_env = head_config.get("conda_env", "sage")

    Path(head_log_dir).mkdir(parents=True, exist_ok=True)
    flownet_cmd = _find_flownet_cmd()
    force_flag = "--force" if force else ""
    conda_init = get_conda_init_code(conda_env)

    stop_script = f"""set +e
export PYTHONUNBUFFERED=1
{conda_init}

LOG_DIR='{head_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/head.log"
echo "Flownet Head 节点停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"
echo "===============================================" | tee -a "$LOG_DIR/head.log"

{flownet_cmd} node stop --timeout={timeout} {force_flag} 2>&1 | tee -a "$LOG_DIR/head.log"
EXIT_CODE=${{PIPESTATUS[0]}}

if [ $EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Flownet Head 节点已停止" | tee -a "$LOG_DIR/head.log"
else
    echo "[WARNING] 停止命令退出码: $EXIT_CODE（节点可能已停止）" | tee -a "$LOG_DIR/head.log"
fi"""

    try:
        result = subprocess.run(
            ["bash", "-c", stop_script], capture_output=True, text=True, timeout=60
        )
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        typer.echo("✅ Head 节点停止完成")

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head 节点停止超时")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Head 节点停止失败: {e}")
        raise typer.Exit(1)


@app.command("status")
def status_head(
    json_output: bool = typer.Option(False, "--json", help="以 JSON 格式输出"),
):
    """检查 Head 节点状态"""
    typer.echo("🔍 检查 Head 节点状态...")

    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_host = head_config.get("host", "127.0.0.1")
    flownet_port = head_config.get("flownet_port", head_config.get("head_port", 8787))
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    conda_env = head_config.get("conda_env", "sage")

    flownet_cmd = _find_flownet_cmd()
    json_flag = "--json" if json_output else ""
    conda_init = get_conda_init_code(conda_env)

    status_script = f"""set +e
export PYTHONUNBUFFERED=1
{conda_init}

echo "==============================================="
echo "Flownet Head 节点状态: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "绑定地址: {head_host}:{flownet_port}"
echo "==============================================="

{flownet_cmd} node status {json_flag} 2>&1
EXIT_CODE=${{PIPESTATUS[0]}}

echo ""
echo "--- 端口监听状态 ---"
echo "Flownet 端口 {flownet_port}:"
ss -tlnp 2>/dev/null | grep ":{flownet_port}" || echo "  未监听"

LOG_DIR='{head_log_dir}'
if [[ -f "$LOG_DIR/head.log" ]]; then
    echo ""
    echo "--- 最近日志（最后 5 行）---"
    tail -5 "$LOG_DIR/head.log" 2>/dev/null || true
fi

echo "==============================================="
exit $EXIT_CODE"""

    try:
        result = subprocess.run(
            ["bash", "-c", status_script], capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        if result.returncode == 0:
            typer.echo("✅ Head 节点正在运行")
            typer.echo(f"   节点地址: head@{head_host}:{flownet_port}")
            typer.echo(f"💡 Worker 节点通过以下 seed 加入: --seed=head@{head_host}:{flownet_port}")
        else:
            typer.echo("❌ Head 节点未运行")
            typer.echo("💡 启动命令: sage cluster head start")

    except subprocess.TimeoutExpired:
        typer.echo("❌ Head 节点状态检查超时")
    except Exception as e:
        typer.echo(f"❌ Head 节点状态检查失败: {e}")


@app.command("restart")
def restart_head():
    """重启 Head 节点"""
    typer.echo("🔄 重启 Head 节点...")
    typer.echo("第 1 步: 停止 Head 节点")
    stop_head(force=True, timeout=10.0)
    typer.echo("⏳ 等待 3 秒后重新启动...")
    time.sleep(3)
    typer.echo("第 2 步: 启动 Head 节点")
    start_head(force=False, foreground=False)
    typer.echo("✅ Head 节点重启完成")


@app.command("logs")
def show_logs(
    lines: int = typer.Option(20, "--lines", "-n", help="显示日志行数"),
    follow: bool = typer.Option(False, "--follow", "-f", help="持续跟踪日志输出"),
):
    """显示 Head 节点日志"""
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_log_dir = head_config.get("log_dir", "/tmp/sage_head_logs")
    log_file = Path(head_log_dir) / "head.log"

    flownet_cmd = _find_flownet_cmd()

    if follow:
        typer.echo("📋 跟踪 Head 节点日志 (Ctrl-C 停止):")
        try:
            subprocess.run([flownet_cmd, "node", "logs", "--follow"], timeout=None)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            pass
        except FileNotFoundError:
            if log_file.exists():
                subprocess.run(["tail", "-f", str(log_file)])
        return

    # 优先用 flownet node logs
    rc, out, _ = _run_local(f"{flownet_cmd} node logs --tail={lines} 2>/dev/null", timeout=10)
    if rc == 0 and out.strip():
        typer.echo(f"📋 Head 节点日志（最后 {lines} 行）:")
        typer.echo("=" * 50)
        typer.echo(out)
        return

    if not log_file.exists():
        typer.echo("❌ 日志文件不存在")
        return

    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_file)], capture_output=True, text=True
        )
        if result.stdout:
            typer.echo(f"📋 Head 节点日志（最后 {lines} 行）:")
            typer.echo("=" * 50)
            typer.echo(result.stdout)
        else:
            typer.echo("📋 日志文件为空")
    except Exception as e:
        typer.echo(f"❌ 读取日志失败: {e}")


@app.command("version")
def version_command():
    """显示版本信息"""
    typer.echo("🏠 SAGE Head Manager (Flownet Runtime)")
    typer.echo("Version: 2.0.0")
    typer.echo("Runtime: sageFlownet")
    typer.echo("Repository: https://github.com/intellistream/SAGE")

    rc, out, _ = _run_local(
        'python -c "import sage.flownet; print(sage.flownet.__version__)" 2>/dev/null',
        timeout=5,
    )
    if rc == 0 and out.strip():
        typer.echo(f"sageFlownet: {out.strip()}")


if __name__ == "__main__":
    app()
