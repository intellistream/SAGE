#!/usr/bin/env python3
"""
SAGE Deploy CLI
系统部署与管理相关命令
"""

import typer
import subprocess
import sys
from pathlib import Path

app = typer.Typer(name="deploy", help="SAGE系统部署与管理")

@app.command("start")
def start_system(
    ray_only: bool = typer.Option(False, "--ray-only", help="仅启动Ray集群"),
    daemon_only: bool = typer.Option(False, "--daemon-only", help="仅启动JobManager守护进程")
):
    """启动SAGE系统（可选仅启动Ray或Daemon）"""
    script_path = "deployment/sage_deployment.sh"
    
    try:
        if ray_only:
            print("🚀 Starting Ray cluster...")
            subprocess.run(["bash", script_path, "start-ray"], check=True)
        elif daemon_only:
            print("🚀 Starting JobManager daemon...")
            subprocess.run(["bash", script_path, "start-daemon"], check=True)
        else:
            print("🚀 Starting SAGE system (Ray + Daemon)...")
            subprocess.run(["bash", script_path, "start"], check=True)
        print("✅ System started successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to start system, please check environment")
        raise typer.Exit(1)
    except FileNotFoundError:
        print(f"❌ Deployment script not found: {script_path}")
        raise typer.Exit(1)

@app.command("stop")
def stop_system():
    """停止SAGE系统"""
    print("🛑 Stopping SAGE system...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "stop"], check=True)
        print("✅ System stopped successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to stop system")
        raise typer.Exit(1)
    except FileNotFoundError:
        print("❌ Deployment script not found")
        raise typer.Exit(1)

@app.command("restart")
def restart_system():
    """重启SAGE系统"""
    print("🔄 Restarting SAGE system...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "restart"], check=True)
        print("✅ System restarted successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to restart system")
        raise typer.Exit(1)
    except FileNotFoundError:
        print("❌ Deployment script not found")
        raise typer.Exit(1)

@app.command("status")
def system_status():
    """显示系统状态"""
    print("📊 Checking SAGE system status...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "status"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Failed to get system status")
        raise typer.Exit(1)
    except FileNotFoundError:
        print("❌ Deployment script not found")
        raise typer.Exit(1)

@app.command("health")
def health_check():
    """健康检查"""
    print("🔍 Performing health check...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "health"], check=True)
        print("✅ Health check completed")
    except subprocess.CalledProcessError:
        print("❌ Health check failed")
        raise typer.Exit(1)
    except FileNotFoundError:
        print("❌ Deployment script not found")
        raise typer.Exit(1)

@app.command("monitor")
def monitor_system(
    refresh: int = typer.Option(5, "--refresh", "-r", help="刷新间隔（秒）")
):
    """实时监控系统"""
    print(f"📈 Real-time monitoring SAGE system, refresh every {refresh}s...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "monitor", str(refresh)], check=True)
    except subprocess.CalledProcessError:
        print("❌ Monitoring failed")
        raise typer.Exit(1)
    except FileNotFoundError:
        print("❌ Deployment script not found")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

if __name__ == "__main__":
    app()
