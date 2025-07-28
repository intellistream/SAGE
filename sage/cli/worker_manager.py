#!/usr/bin/env python3
"""
SAGE Worker Manager CLI
Ray Worker节点管理相关命令
"""

import typer
import subprocess
import sys
import re
import tempfile
import os
import time
from pathlib import Path
from typing import List, Tuple

app = typer.Typer(name="worker", help="Ray Worker节点管理")

def load_config():
    """加载配置文件（简单解析YAML格式）"""
    config_file = Path.home() / ".sage" / "config.yaml"
    if not config_file.exists():
        typer.echo(f"❌ Config file not found: {config_file}")
        typer.echo("💡 Please run setup.py first to create default config")
        raise typer.Exit(1)
    
    try:
        config = {}
        current_section = None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 匹配section header (如 workers:)
                section_match = re.match(r'^(\w+):\s*$', line)
                if section_match:
                    current_section = section_match.group(1)
                    config[current_section] = {}
                    continue
                
                # 匹配key: value对
                kv_match = re.match(r'^(\w+):\s*(.+)$', line)
                if kv_match and current_section:
                    key, value = kv_match.groups()
                    # 处理数值
                    if value.isdigit():
                        value = int(value)
                    # 处理字符串，去掉引号
                    elif value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    config[current_section][key] = value
                    continue
                
                # 匹配简单赋值 (如 head_node = sage1)
                assign_match = re.match(r'^(\w+)\s*=\s*(.+)$', line)
                if assign_match and current_section:
                    key, value = assign_match.groups()
                    if value.isdigit():
                        value = int(value)
                    config[current_section][key] = value
        
        return config
    except Exception as e:
        typer.echo(f"❌ Failed to load config: {e}")
        raise typer.Exit(1)

def parse_worker_nodes(worker_nodes_str: str) -> List[Tuple[str, int]]:
    """解析worker节点列表"""
    nodes = []
    for node in worker_nodes_str.split(','):
        node = node.strip()
        if ':' in node:
            host, port = node.split(':', 1)
            port = int(port)
        else:
            host = node
            port = 22  # 默认SSH端口
        nodes.append((host, port))
    return nodes

def execute_remote_command(host: str, port: int, command: str, ssh_user: str, ssh_key_path: str, timeout: int = 60) -> bool:
    """在远程主机上执行命令"""
    typer.echo(f"🔗 连接到 {ssh_user}@{host}:{port}")
    
    # 创建临时脚本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_script:
        temp_script.write("#!/bin/bash\n")
        temp_script.write(command)
        temp_script_path = temp_script.name
    
    try:
        ssh_cmd = [
            'ssh',
            '-i', os.path.expanduser(ssh_key_path),
            '-p', str(port),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
            f'{ssh_user}@{host}',
            'bash -s'
        ]
        
        with open(temp_script_path, 'r') as script_file:
            result = subprocess.run(
                ssh_cmd,
                stdin=script_file,
                capture_output=True,
                text=True,
                timeout=timeout
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

def get_conda_init_code(remote_conda_env: str = "sage") -> str:
    """获取Conda环境初始化代码"""
    return f'''
# 多种conda安装路径尝试
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

if [ -z "$CONDA_FOUND" ]; then
    echo "[ERROR] 未找到conda安装，请检查conda是否正确安装"
    exit 1
fi

# 激活sage环境
if ! conda activate {remote_conda_env}; then
    echo "[ERROR] 无法激活conda环境: {remote_conda_env}"
    echo "[INFO] 可用的conda环境:"
    conda env list
    exit 1
fi

echo "[SUCCESS] 已激活conda环境: {remote_conda_env}"
'''

@app.command("start")
def start_workers():
    """启动所有Ray Worker节点"""
    typer.echo("🚀 启动Ray Worker节点...")
    config = load_config()
    
    workers_config = config.get('workers', {})
    head_node = workers_config.get('head_node')
    worker_nodes = workers_config.get('worker_nodes')
    head_port = workers_config.get('head_port', 6379)
    ssh_user = workers_config.get('ssh_user', 'sage')
    ssh_key_path = workers_config.get('ssh_key_path', '~/.ssh/id_rsa')
    worker_temp_dir = workers_config.get('worker_temp_dir', '/tmp/ray_worker')
    worker_log_dir = workers_config.get('worker_log_dir', '/tmp/sage_worker_logs')
    remote_sage_home = workers_config.get('remote_sage_home', '/home/sage')
    remote_python_path = workers_config.get('remote_python_path', '/opt/conda/envs/sage/bin/python')
    remote_ray_command = workers_config.get('remote_ray_command', '/opt/conda/envs/sage/bin/ray')
    
    if not head_node or not worker_nodes:
        typer.echo("❌ 配置错误: head_node 或 worker_nodes 未设置")
        raise typer.Exit(1)
    
    typer.echo(f"📋 配置信息:")
    typer.echo(f"   Head节点: {head_node}:{head_port}")
    typer.echo(f"   Worker节点: {worker_nodes}")
    typer.echo(f"   SSH用户: {ssh_user}")
    
    nodes = parse_worker_nodes(worker_nodes)
    success_count = 0
    total_count = len(nodes)
    
    for i, (host, port) in enumerate(nodes, 1):
        typer.echo(f"\n🔧 启动Worker节点 {i}/{total_count}: {host}:{port}")
        
        start_command = f'''set -e
export PYTHONUNBUFFERED=1

# 当前主机名
CURRENT_HOST='{host}'

# 创建必要目录
LOG_DIR='{worker_log_dir}'
WORKER_TEMP_DIR='{worker_temp_dir}'
mkdir -p "$LOG_DIR" "$WORKER_TEMP_DIR"

# 记录启动时间
echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Ray Worker启动 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "目标头节点: {head_node}:{head_port}" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code()}

# 停止现有的ray进程
echo "[INFO] 停止现有Ray进程..." | tee -a "$LOG_DIR/worker.log"
{remote_ray_command} stop >> "$LOG_DIR/worker.log" 2>&1 || true
sleep 2

# 强制清理残留进程
echo "[INFO] 强制清理所有Ray相关进程..." | tee -a "$LOG_DIR/worker.log"
for proc in raylet core_worker log_monitor; do
    PIDS=$(pgrep -f "$proc" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "[INFO] 发现$proc进程: $PIDS" | tee -a "$LOG_DIR/worker.log"
        echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
    fi
done

# 清理Ray会话目录
echo "[INFO] 清理Ray会话目录..." | tee -a "$LOG_DIR/worker.log"
rm -rf "$WORKER_TEMP_DIR"/* 2>/dev/null || true

sleep 3

# 使用配置文件中指定的节点名称
NODE_IP="$CURRENT_HOST"
echo "[INFO] 使用节点名称: $NODE_IP" | tee -a "$LOG_DIR/worker.log"

# 设置环境变量
export RAY_TMPDIR="$WORKER_TEMP_DIR"
export RAY_DISABLE_IMPORT_WARNING=1

# 测试连通性
echo "[INFO] 测试到头节点的连通性..." | tee -a "$LOG_DIR/worker.log"
if timeout 10 nc -z {head_node} {head_port} 2>/dev/null; then
    echo "[SUCCESS] 可以连接到头节点 {head_node}:{head_port}" | tee -a "$LOG_DIR/worker.log"
else
    echo "[WARNING] 无法验证到头节点的连通性，但继续尝试启动Ray" | tee -a "$LOG_DIR/worker.log"
fi

# 启动ray worker
echo "[INFO] 启动Ray Worker进程..." | tee -a "$LOG_DIR/worker.log"
RAY_START_CMD="{remote_ray_command} start --address={head_node}:{head_port} --node-ip-address=$NODE_IP --temp-dir=$WORKER_TEMP_DIR"
echo "[INFO] 执行命令: $RAY_START_CMD" | tee -a "$LOG_DIR/worker.log"

$RAY_START_CMD >> "$LOG_DIR/worker.log" 2>&1
RAY_EXIT_CODE=$?

if [ $RAY_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Ray Worker启动成功" | tee -a "$LOG_DIR/worker.log"
    sleep 3
    
    RAY_PIDS=$(pgrep -f 'raylet|core_worker' || true)
    if [[ -n "$RAY_PIDS" ]]; then
        echo "[SUCCESS] Ray Worker进程正在运行，PIDs: $RAY_PIDS" | tee -a "$LOG_DIR/worker.log"
        echo "[INFO] 节点已连接到集群: {head_node}:{head_port}" | tee -a "$LOG_DIR/worker.log"
    else
        echo "[WARNING] Ray启动命令成功但未发现运行中的进程" | tee -a "$LOG_DIR/worker.log"
    fi
else
    echo "[ERROR] Ray Worker启动失败，退出码: $RAY_EXIT_CODE" | tee -a "$LOG_DIR/worker.log"
    exit 1
fi'''
        
        if execute_remote_command(host, port, start_command, ssh_user, ssh_key_path, 120):
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
def stop_workers():
    """停止所有Ray Worker节点"""
    typer.echo("🛑 停止Ray Worker节点...")
    config = load_config()
    
    workers_config = config.get('workers', {})
    worker_nodes = workers_config.get('worker_nodes')
    ssh_user = workers_config.get('ssh_user', 'sage')
    ssh_key_path = workers_config.get('ssh_key_path', '~/.ssh/id_rsa')
    worker_temp_dir = workers_config.get('worker_temp_dir', '/tmp/ray_worker')
    worker_log_dir = workers_config.get('worker_log_dir', '/tmp/sage_worker_logs')
    remote_ray_command = workers_config.get('remote_ray_command', '/opt/conda/envs/sage/bin/ray')
    
    if not worker_nodes:
        typer.echo("❌ 配置错误: worker_nodes 未设置")
        raise typer.Exit(1)
    
    nodes = parse_worker_nodes(worker_nodes)
    success_count = 0
    total_count = len(nodes)
    
    for i, (host, port) in enumerate(nodes, 1):
        typer.echo(f"\n🔧 停止Worker节点 {i}/{total_count}: {host}:{port}")
        
        stop_command = f'''set +e
export PYTHONUNBUFFERED=1

LOG_DIR='{worker_log_dir}'
mkdir -p "$LOG_DIR"

echo "===============================================" | tee -a "$LOG_DIR/worker.log"
echo "Ray Worker停止 ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG_DIR/worker.log"
echo "Worker节点: $(hostname)" | tee -a "$LOG_DIR/worker.log"
echo "===============================================" | tee -a "$LOG_DIR/worker.log"

# 初始化conda环境
{get_conda_init_code()}

# 优雅停止
echo "[INFO] 正在优雅停止Ray进程..." | tee -a "$LOG_DIR/worker.log"
{remote_ray_command} stop >> "$LOG_DIR/worker.log" 2>&1 || true
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
        
        if execute_remote_command(host, port, stop_command, ssh_user, ssh_key_path, 60):
            typer.echo(f"✅ Worker节点 {host} 停止成功")
            success_count += 1
        else:
            typer.echo(f"⚠️  Worker节点 {host} 停止完成（可能本来就未运行）")
            success_count += 1  # 停止操作通常允许失败
    
    typer.echo(f"\n📊 停止结果: {success_count}/{total_count} 个节点处理完成")
    typer.echo("✅ 所有Worker节点停止操作完成！")

@app.command("status")
def status_workers():
    """检查所有Ray Worker节点状态"""
    typer.echo("📊 检查Ray Worker节点状态...")
    config = load_config()
    
    workers_config = config.get('workers', {})
    head_node = workers_config.get('head_node')
    worker_nodes = workers_config.get('worker_nodes')
    head_port = workers_config.get('head_port', 6379)
    ssh_user = workers_config.get('ssh_user', 'sage')
    ssh_key_path = workers_config.get('ssh_key_path', '~/.ssh/id_rsa')
    worker_log_dir = workers_config.get('worker_log_dir', '/tmp/sage_worker_logs')
    remote_ray_command = workers_config.get('remote_ray_command', '/opt/conda/envs/sage/bin/ray')
    
    if not worker_nodes:
        typer.echo("❌ 配置错误: worker_nodes 未设置")
        raise typer.Exit(1)
    
    nodes = parse_worker_nodes(worker_nodes)
    running_count = 0
    total_count = len(nodes)
    
    for i, (host, port) in enumerate(nodes, 1):
        typer.echo(f"\n📋 检查Worker节点 {i}/{total_count}: {host}:{port}")
        
        status_command = f'''set +e
export PYTHONUNBUFFERED=1

echo "==============================================="
echo "节点状态检查: $(hostname) ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "==============================================="

# 初始化conda环境
{get_conda_init_code()}

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
    timeout 10 {remote_ray_command} status 2>/dev/null || echo "[警告] 无法获取Ray集群状态"
    exit 0
else
    echo "[已停止] 未发现Ray进程"
    exit 1
fi

echo ""
echo "--- 网络连通性测试 ---"
if timeout 5 nc -z {head_node} {head_port} 2>/dev/null; then
    echo "[正常] 可以连接到头节点 {head_node}:{head_port}"
else
    echo "[异常] 无法连接到头节点 {head_node}:{head_port}"
fi

# 显示最近的日志
LOG_DIR='{worker_log_dir}'
if [[ -f "$LOG_DIR/worker.log" ]]; then
    echo ""
    echo "--- 最近的日志 (最后5行) ---"
    tail -5 "$LOG_DIR/worker.log" 2>/dev/null || echo "无法读取日志文件"
fi

echo "==============================================="'''
        
        if execute_remote_command(host, port, status_command, ssh_user, ssh_key_path, 30):
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
    """重启所有Ray Worker节点"""
    typer.echo("🔄 重启Ray Worker节点...")
    
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
    config = load_config()
    
    workers_config = config.get('workers', {})
    
    typer.echo(f"Head节点: {workers_config.get('head_node', 'N/A')}")
    typer.echo(f"Head端口: {workers_config.get('head_port', 'N/A')}")
    typer.echo(f"Worker节点: {workers_config.get('worker_nodes', 'N/A')}")
    typer.echo(f"SSH用户: {workers_config.get('ssh_user', 'N/A')}")
    typer.echo(f"SSH密钥路径: {workers_config.get('ssh_key_path', 'N/A')}")
    typer.echo(f"临时目录: {workers_config.get('worker_temp_dir', 'N/A')}")
    typer.echo(f"日志目录: {workers_config.get('worker_log_dir', 'N/A')}")
    typer.echo(f"远程SAGE目录: {workers_config.get('remote_sage_home', 'N/A')}")
    typer.echo(f"远程Python路径: {workers_config.get('remote_python_path', 'N/A')}")
    typer.echo(f"远程Ray命令: {workers_config.get('remote_ray_command', 'N/A')}")

if __name__ == "__main__":
    app()
