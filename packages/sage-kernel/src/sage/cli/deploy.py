#!/usr/bin/env python3
"""
SAGE Deploy CLI
系统部署与管理相关命令
"""

import typer
import subprocess
import sys
import re
from pathlib import Path

app = typer.Typer(name="deploy", help="SAGE系统部署与管理")

def load_config():
    """加载配置文件（简单解析YAML格式）"""
    config_file = Path.home() / ".sage" / "config.yaml"
    if not config_file.exists():
        typer.echo(f"❌ Config file not found: {config_file}")
        typer.echo("💡 Please run 'sage init' to create default config")
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

@app.command("start")
def start_system(
    ray_only: bool = typer.Option(False, "--ray-only", help="仅启动Ray集群"),
    daemon_only: bool = typer.Option(False, "--daemon-only", help="仅启动JobManager守护进程"),
    with_workers: bool = typer.Option(False, "--with-workers", help="同时启动Worker节点")
):
    """启动SAGE系统（Ray集群 + JobManager）"""
    config = load_config()
    
    if not ray_only and not daemon_only:
        typer.echo("🚀 Starting SAGE system (Ray + JobManager)...")
    
    # 启动Ray集群
    if not daemon_only:
        try:
            typer.echo("🚀 Starting Ray cluster...")
            workers_config = config.get('workers', {})
            head_port = workers_config.get('head_port', 6379)
            
            # 启动Ray head节点，使用配置中的端口
            ray_cmd = [
                "ray", "start", "--head",
                f"--port={head_port}",
                "--dashboard-port=8265"
            ]
            
            typer.echo(f"� Running: {' '.join(ray_cmd)}")
            result = subprocess.run(ray_cmd, check=True, capture_output=True, text=True)
            typer.echo("✅ Ray cluster started successfully")
            
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start Ray cluster: {e}")
            typer.echo(f"❌ Error output: {e.stderr}")
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ Unexpected error starting Ray: {e}")
            raise typer.Exit(1)
    
    # 启动JobManager
    if not ray_only:
        try:
            typer.echo("🚀 Starting JobManager...")
            
            # 使用sage jobmanager start命令
            sage_cmd = [sys.executable, "-m", "sage.cli.jobmanager_controller", "start"]
            
            typer.echo(f"💻 Running: {' '.join(sage_cmd)}")
            result = subprocess.run(sage_cmd, check=True)
            typer.echo("✅ JobManager started successfully")
            
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start JobManager: {e}")
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ Unexpected error starting JobManager: {e}")
            raise typer.Exit(1)
    
    if not ray_only and not daemon_only:
        typer.echo("✅ SAGE system started successfully!")
    elif ray_only:
        typer.echo("✅ Ray cluster started successfully!")
    elif daemon_only:
        typer.echo("✅ JobManager started successfully!")
    
    # 启动Worker节点（如果请求）
    if with_workers and not daemon_only:
        try:
            typer.echo("🚀 Starting Worker nodes...")
            worker_cmd = [sys.executable, "-m", "sage.cli.worker_manager", "start"]
            typer.echo(f"💻 Running: {' '.join(worker_cmd)}")
            result = subprocess.run(worker_cmd, check=True)
            typer.echo("✅ Worker nodes started successfully")
        except subprocess.CalledProcessError as e:
            typer.echo(f"⚠️  Failed to start Worker nodes: {e}")
            # 不退出，因为head节点已经启动成功
        except Exception as e:
            typer.echo(f"⚠️  Unexpected error starting Worker nodes: {e}")
            # 不退出，因为head节点已经启动成功

@app.command("stop")
def stop_system(
    with_workers: bool = typer.Option(False, "--with-workers", help="同时停止Worker节点")
):
    """停止SAGE系统（Ray集群 + JobManager）"""
    typer.echo("🛑 Stopping SAGE system...")
    
    # 停止Worker节点（如果请求）
    if with_workers:
        try:
            typer.echo("🛑 Stopping Worker nodes...")
            worker_cmd = [sys.executable, "-m", "sage.cli.worker_manager", "stop"]
            typer.echo(f"💻 Running: {' '.join(worker_cmd)}")
            result = subprocess.run(worker_cmd, check=True)
            typer.echo("✅ Worker nodes stopped successfully")
        except subprocess.CalledProcessError as e:
            typer.echo(f"⚠️  Failed to stop Worker nodes: {e}")
            # 继续执行，不退出
        except Exception as e:
            typer.echo(f"⚠️  Unexpected error stopping Worker nodes: {e}")
            # 继续执行，不退出
    
    # 停止JobManager
    try:
        typer.echo("🛑 Stopping JobManager...")
        sage_cmd = [sys.executable, "-m", "sage.cli.jobmanager_controller", "stop"]
        typer.echo(f"💻 Running: {' '.join(sage_cmd)}")
        result = subprocess.run(sage_cmd, check=True)
        typer.echo("✅ JobManager stopped successfully")
    except subprocess.CalledProcessError as e:
        typer.echo(f"⚠️  Failed to stop JobManager: {e}")
        # 继续执行，不退出
    except Exception as e:
        typer.echo(f"⚠️  Unexpected error stopping JobManager: {e}")
        # 继续执行，不退出
    
    # 停止Ray集群
    try:
        typer.echo("🛑 Stopping Ray cluster...")
        ray_cmd = ["ray", "stop"]
        typer.echo(f"💻 Running: {' '.join(ray_cmd)}")
        result = subprocess.run(ray_cmd, check=True, capture_output=True, text=True)
        typer.echo("✅ Ray cluster stopped successfully")
    except subprocess.CalledProcessError as e:
        typer.echo(f"⚠️  Failed to stop Ray cluster: {e}")
        typer.echo(f"⚠️  Error output: {e.stderr}")
        # 继续执行，不退出
    except Exception as e:
        typer.echo(f"⚠️  Unexpected error stopping Ray: {e}")
        # 继续执行，不退出
    
    typer.echo("✅ SAGE system stop completed!")

@app.command("restart")
def restart_system():
    """重启SAGE系统"""
    typer.echo("🔄 Restarting SAGE system...")
    stop_system()
    typer.echo("⏳ Waiting 3 seconds before restart...")
    import time
    time.sleep(3)
    start_system()

@app.command("status")
def system_status():
    """显示系统状态"""
    typer.echo("📊 Checking SAGE system status...")
    
    # 检查Ray状态
    try:
        ray_result = subprocess.run(["ray", "status"], capture_output=True, text=True)
        if ray_result.returncode == 0:
            typer.echo("✅ Ray cluster is running")
            typer.echo("Ray Status:")
            typer.echo(ray_result.stdout)
        else:
            typer.echo("❌ Ray cluster is not running")
    except FileNotFoundError:
        typer.echo("❌ Ray command not found")
    except Exception as e:
        typer.echo(f"❌ Error checking Ray status: {e}")
    
    # 检查JobManager状态
    try:
        jm_cmd = [sys.executable, "-m", "sage.cli.jobmanager_controller", "status"]
        jm_result = subprocess.run(jm_cmd, capture_output=True, text=True)
        if jm_result.returncode == 0:
            typer.echo("✅ JobManager is running")
        else:
            typer.echo("❌ JobManager is not running")
    except Exception as e:
        typer.echo(f"❌ Error checking JobManager status: {e}")

if __name__ == "__main__":
    app()