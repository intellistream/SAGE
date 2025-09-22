#!/usr/bin/env python3
"""
SAGE Head Manager CLI
Ray Head节点管理相关命令
"""

import typer
import subprocess
import os
import time
from pathlib import Path
from ..config_manager import get_config_manager

app = typer.Typer(name="head", help="Ray Head节点管理")

def get_conda_init_code(conda_env: str = "sage") -> str:
    """获取Conda环境初始化代码"""
    return f'''
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
'''

@app.command("start")
def start_head():
    """启动Ray Head节点"""
    typer.echo("🚀 启动Ray Head节点...")
    
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    remote_config = config_manager.get_remote_config()
    
    head_host = head_config.get('host', 'localhost')
    head_port = head_config.get('head_port', 6379)
    dashboard_port = head_config.get('dashboard_port', 8265)
    dashboard_host = head_config.get('dashboard_host', '0.0.0.0')
    head_temp_dir = head_config.get('temp_dir', '/tmp/ray_head')
    head_log_dir = head_config.get('log_dir', '/tmp/sage_head_logs')
    
    ray_command = head_config.get('ray_command', '/opt/conda/envs/sage/bin/ray')
    conda_env = head_config.get('conda_env', 'sage')
    
    typer.echo(f"📋 配置信息:")
    typer.echo(f"   Head主机: {head_host}")
    typer.echo(f"   Head端口: {head_port}")
    typer.echo(f"   Dashboard: {dashboard_host}:{dashboard_port}")
    typer.echo(f"   临时目录: {head_temp_dir}")
    typer.echo(f"   日志目录: {head_log_dir}")
    
    start_command = f'''
export PYTHONUNBUFFERED=1

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

# 停止现有的ray进程
echo "[INFO] 停止现有Ray进程..." | tee -a "$LOG_DIR/head.log"
{ray_command} stop >> "$LOG_DIR/head.log" 2>&1 || true
sleep 2

# 设置环境变量
export RAY_TMPDIR="$HEAD_TEMP_DIR"
export RAY_DISABLE_IMPORT_WARNING=1

# 启动ray head
echo "[INFO] 启动Ray Head进程..." | tee -a "$LOG_DIR/head.log"
RAY_START_CMD="{ray_command} start --head --port={head_port} --node-ip-address={head_host} --dashboard-host={dashboard_host} --dashboard-port={dashboard_port} --temp-dir=$HEAD_TEMP_DIR --disable-usage-stats"
echo "[INFO] 执行命令: $RAY_START_CMD" | tee -a "$LOG_DIR/head.log"

# 执行启动命令并捕获所有输出
$RAY_START_CMD 2>&1 | tee -a "$LOG_DIR/head.log"
RAY_EXIT_CODE=${{PIPESTATUS[0]}}

echo "[INFO] Ray启动命令退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/head.log"

if [ $RAY_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Ray Head启动成功" | tee -a "$LOG_DIR/head.log"
    sleep 3
    
    RAY_PIDS=$(pgrep -f 'raylet|gcs_server|dashboard' 2>/dev/null || true)
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
fi'''
    
    try:
        result = subprocess.run(
            ['bash', '-c', start_command],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        
        if result.returncode == 0:
            typer.echo("✅ Ray Head节点启动成功")
            typer.echo(f"🌐 Dashboard访问地址: http://{dashboard_host}:{dashboard_port}")
        else:
            typer.echo("❌ Ray Head节点启动失败")
            raise typer.Exit(1)
            
    except subprocess.TimeoutExpired:
        typer.echo("❌ Ray Head启动超时")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Ray Head启动失败: {e}")
        raise typer.Exit(1)

@app.command("stop")
def stop_head():
    """停止Ray Head节点"""
    typer.echo("🛑 停止Ray Head节点...")
    
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    remote_config = config_manager.get_remote_config()
    
    head_temp_dir = head_config.get('temp_dir', '/tmp/ray_head')
    head_log_dir = head_config.get('log_dir', '/tmp/sage_head_logs')
    ray_command = remote_config.get('ray_command', '/opt/conda/envs/sage/bin/ray')
    conda_env = remote_config.get('conda_env', 'sage')
    
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
{ray_command} stop >> "$LOG_DIR/head.log" 2>&1 || true
sleep 2

# 强制停止残留进程
echo "[INFO] 清理残留的Ray进程..." | tee -a "$LOG_DIR/head.log"
for pattern in 'ray.*start' 'raylet' 'gcs_server' 'dashboard' 'log_monitor' 'ray::'; do
    PIDS=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "[INFO] 终止进程: $pattern (PIDs: $PIDS)" | tee -a "$LOG_DIR/head.log"
        echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        echo "$PIDS" | xargs -r kill -KILL 2>/dev/null || true
    fi
done

# 清理临时文件
HEAD_TEMP_DIR='{head_temp_dir}'
if [[ -d "$HEAD_TEMP_DIR" ]]; then
    echo "[INFO] 清理临时目录: $HEAD_TEMP_DIR" | tee -a "$LOG_DIR/head.log"
    rm -rf "$HEAD_TEMP_DIR"/* 2>/dev/null || true
fi

echo "[SUCCESS] Ray Head已停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/head.log"'''
    
    try:
        result = subprocess.run(
            ['bash', '-c', stop_command],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        
        typer.echo("✅ Ray Head节点停止完成")
        
    except subprocess.TimeoutExpired:
        typer.echo("❌ Ray Head停止超时")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Ray Head停止失败: {e}")
        raise typer.Exit(1)

@app.command("status")
def status_head():
    """检查Ray Head节点状态"""
    typer.echo("📊 检查Ray Head节点状态...")
    
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    remote_config = config_manager.get_remote_config()
    
    head_host = head_config.get('host', 'localhost')
    head_port = head_config.get('head_port', 6379)
    dashboard_port = head_config.get('dashboard_port', 8265)
    head_log_dir = head_config.get('log_dir', '/tmp/sage_head_logs')
    ray_command = remote_config.get('ray_command', '/opt/conda/envs/sage/bin/ray')
    conda_env = remote_config.get('conda_env', 'sage')
    
    status_command = f'''set +e
export PYTHONUNBUFFERED=1

echo "==============================================="
echo "Ray Head状态检查: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "==============================================="

# 初始化conda环境
{get_conda_init_code(conda_env)}

# 检查Ray进程
echo "--- Ray Head进程状态 ---"
RAY_PIDS=$(pgrep -f 'raylet|gcs_server|dashboard' 2>/dev/null || true)
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
    netstat -tlnp 2>/dev/null | grep ":{head_port}" || echo "  未监听"
    echo "Dashboard端口 {dashboard_port}:"
    netstat -tlnp 2>/dev/null | grep ":{dashboard_port}" || echo "  未监听"
    
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
            ['bash', '-c', status_command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
        
        if result.returncode == 0:
            typer.echo("✅ Ray Head节点正在运行")
            typer.echo(f"🌐 Dashboard访问地址: http://{head_host}:{dashboard_port}")
        else:
            typer.echo("❌ Ray Head节点未运行")
        
    except subprocess.TimeoutExpired:
        typer.echo("❌ Ray Head状态检查超时")
    except Exception as e:
        typer.echo(f"❌ Ray Head状态检查失败: {e}")

@app.command("restart")
def restart_head():
    """重启Ray Head节点"""
    typer.echo("🔄 重启Ray Head节点...")
    
    # 先停止
    typer.echo("第1步: 停止Head节点")
    stop_head()
    
    # 等待
    typer.echo("⏳ 等待3秒后重新启动...")
    time.sleep(3)
    
    # 再启动
    typer.echo("第2步: 启动Head节点")
    start_head()
    
    typer.echo("✅ Head节点重启完成！")

@app.command("logs")
def show_logs(lines: int = typer.Option(20, "--lines", "-n", help="显示日志行数")):
    """显示Head节点日志"""
    config_manager = get_config_manager()
    head_config = config_manager.get_head_config()
    head_log_dir = head_config.get('log_dir', '/tmp/sage_head_logs')
    log_file = Path(head_log_dir) / "head.log"
    
    if not log_file.exists():
        typer.echo("❌ 日志文件不存在")
        return
    
    try:
        result = subprocess.run(
            ['tail', '-n', str(lines), str(log_file)],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            typer.echo(f"📋 Ray Head日志 (最后{lines}行):")
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
    typer.echo("Version: 1.0.1")
    typer.echo("Author: IntelliStream Team")
    typer.echo("Repository: https://github.com/intellistream/SAGE")

if __name__ == "__main__":
    app()
