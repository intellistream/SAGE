#!/usr/bin/env python3
"""
SAGE JobManager CLI
集成的作业管理命令行工具
"""

import typer
import json
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import signal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from sage.kernel import JobManagerClient
import yaml
from tabulate import tabulate
from colorama import Fore, Back, Style, init

# 初始化colorama
init(autoreset=True)

app = typer.Typer(name="job", help="SAGE作业管理工具 - 提供作业的暂停、恢复、监控等功能")

class JobManagerCLI:
    """JobManager命令行界面"""
    
    def __init__(self, daemon_host: str = "127.0.0.1", daemon_port: int = 19001):
        self.daemon_host = daemon_host
        self.daemon_port = daemon_port
        self.client: Optional[JobManagerClient] = None
        self.connected = False
        
    def connect(self) -> bool:
        """连接到JobManager"""
        try:
            self.client = JobManagerClient(self.daemon_host, self.daemon_port)
            
            # 健康检查
            health = self.client.health_check()
            if health.get("status") != "success":
                raise Exception(f"Daemon health check failed: {health.get('message')}")
            self.connected = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            self.connected = False
            return False
    
    def ensure_connected(self):
        """确保已连接"""
        if not self.connected:
            if not self.connect():
                raise Exception("Not connected to JobManager")
    
    def _resolve_job_identifier(self, identifier: str) -> Optional[str]:
        """解析作业标识符（可以是作业编号或UUID）"""
        try:
            self.ensure_connected()
            
            # 获取作业列表
            response = self.client.list_jobs()
            if response.get("status") != "success":
                raise Exception(f"Failed to get job list: {response.get('message')}")
            
            jobs = response.get("jobs", [])
            
            # 如果是数字，当作作业编号处理
            if identifier.isdigit():
                job_index = int(identifier) - 1  # 转换为0基索引
                if 0 <= job_index < len(jobs):
                    return jobs[job_index].get('uuid')
                else:
                    print(f"❌ Job number {identifier} is out of range (1-{len(jobs)})")
                    return None
            
            # 如果是UUID（完整或部分）
            # 首先尝试精确匹配
            for job in jobs:
                if job.get('uuid') == identifier:
                    return identifier
            
            # 然后尝试前缀匹配
            matching_jobs = [job for job in jobs if job.get('uuid', '').startswith(identifier)]
            
            if len(matching_jobs) == 1:
                return matching_jobs[0].get('uuid')
            elif len(matching_jobs) > 1:
                print(f"❌ Ambiguous job identifier '{identifier}'. Matches:")
                for i, job in enumerate(matching_jobs, 1):
                    print(f"  {i}. {job.get('uuid')} ({job.get('name', 'unknown')})")
                return None
            else:
                print(f"❌ No job found matching '{identifier}'")
                return None
                
        except Exception as e:
            print(f"❌ Failed to resolve job identifier: {e}")
            return None


# 创建全局CLI实例
cli = JobManagerCLI()

@app.command("list")
def list_jobs(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="按状态过滤作业"),
    format_type: str = typer.Option("table", "--format", "-f", help="输出格式(table/json)"),
    full_uuid: bool = typer.Option(False, "--full-uuid", help="显示完整UUID")
):
    """列出所有作业"""
    try:
        cli.ensure_connected()
        response = cli.client.list_jobs()
        if response.get("status") != "success":
            raise Exception(f"Failed to get job list: {response.get('message')}")
        
        jobs = response.get("jobs", [])
        
        # 状态过滤
        if status:
            jobs = [job for job in jobs if job.get("status") == status]
        
        # 格式化输出
        if format_type == "json":
            print(json.dumps({"jobs": jobs}, indent=2))
        else:
            _format_job_table(jobs, short_uuid=not full_uuid)
            
    except Exception as e:
        print(f"❌ Failed to list jobs: {e}")
        raise typer.Exit(1)

@app.command("show")
def show_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息")
):
    """显示作业详情"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
        
        cli.ensure_connected()
        response = cli.client.get_job_status(job_uuid)
        if response.get("status") != "success":
            raise Exception(f"Failed to get job status: {response.get('message')}")
        
        job_info = response.get("job_status")
        
        if not job_info:
            print(f"❌ Job {job_uuid} not found")
            raise typer.Exit(1)
        
        _format_job_details(job_info, verbose)
        
    except Exception as e:
        print(f"❌ Failed to show job: {e}")
        raise typer.Exit(1)

@app.command("stop")
def stop_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制停止，无需确认")
):
    """停止/暂停作业 (别名: pause)"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
            
        cli.ensure_connected()
        
        # 确认操作
        if not force:
            response = cli.client.get_job_status(job_uuid)
            if response.get("status") == "success" and response.get("job_status"):
                job_info = response.get("job_status")
                job_name = job_info.get('name', 'unknown')
                job_status = job_info.get('status', 'unknown')
                print(f"Job to stop: {job_name} ({job_uuid})")
                print(f"Current status: {job_status}")
            
            if not typer.confirm(f"Are you sure you want to stop this job?"):
                print("ℹ️ Operation cancelled")
                return
        
        # 停止作业
        result = cli.client.pause_job(job_uuid)
        
        if result.get("status") == "stopped":
            print(f"✅ Job {job_uuid[:8]}... stopped successfully")
        else:
            print(f"❌ Failed to stop job: {result.get('message')}")
            raise typer.Exit(1)
            
    except Exception as e:
        print(f"❌ Failed to stop job: {e}")
        raise typer.Exit(1)

# 添加 pause 作为 stop 的别名
app.command("pause", hidden=True)(stop_job)

@app.command("continue")
def continue_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制继续，无需确认")
):
    """继续/恢复作业 (别名: resume)"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
            
        cli.ensure_connected()
        
        # 确认操作
        if not force:
            response = cli.client.get_job_status(job_uuid)
            if response.get("status") == "success" and response.get("job_status"):
                job_info = response.get("job_status")
                job_name = job_info.get('name', 'unknown')
                job_status = job_info.get('status', 'unknown')
                print(f"Job to continue: {job_name} ({job_uuid})")
                print(f"Current status: {job_status}")
            
            if not typer.confirm(f"Are you sure you want to continue this job?"):
                print("ℹ️ Operation cancelled")
                return
        
        # 继续作业
        result = cli.client.continue_job(job_uuid)
        
        if result.get("status") == "running":
            print(f"✅ Job {job_uuid[:8]}... continued successfully")
        else:
            print(f"❌ Failed to continue job: {result.get('message')}")
            raise typer.Exit(1)
            
    except Exception as e:
        print(f"❌ Failed to continue job: {e}")
        raise typer.Exit(1)

# 添加 resume 作为 continue 的别名
app.command("resume", hidden=True)(continue_job)

@app.command("delete")
def delete_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，无需确认")
):
    """删除作业"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
            
        cli.ensure_connected()
        
        # 确认操作
        if not force:
            response = cli.client.get_job_status(job_uuid)
            if response.get("status") == "success" and response.get("job_status"):
                job_info = response.get("job_status")
                job_name = job_info.get('name', 'unknown')
                job_status = job_info.get('status', 'unknown')
                print(f"Job to delete: {job_name} ({job_uuid})")
                print(f"Current status: {job_status}")
            
            if not typer.confirm(f"Are you sure you want to delete this job? This action cannot be undone."):
                print("ℹ️ Operation cancelled")
                return
        
        # 删除作业
        result = cli.client.delete_job(job_uuid, force=force)
        print(f"✅ Job {job_uuid[:8]}... deleted . message:{result.get('message')})")
            
    except Exception as e:
        print(f"❌ Failed to delete job: {e}")
        raise typer.Exit(1)

@app.command("status")
def job_status(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID")
):
    """获取作业状态"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
            
        cli.ensure_connected()
        response = cli.client.get_job_status(job_uuid)
        if response.get("status") != "success":
            raise Exception(f"Failed to get job status: {response.get('message')}")
        
        job_info = response.get("job_status")
        
        if not job_info:
            print(f"❌ Job {job_uuid} not found")
            raise typer.Exit(1)
        
        status = job_info.get("status", "unknown")
        job_name = job_info.get("name", "unknown")
        _print_status_colored(f"Job '{job_name}' ({job_uuid[:8]}...) status: {status}")
        
    except Exception as e:
        print(f"❌ Failed to get job status: {e}")
        raise typer.Exit(1)

@app.command("cleanup")
def cleanup_jobs(
    force: bool = typer.Option(False, "--force", "-f", help="强制清理，无需确认")
):
    """清理所有作业"""
    try:
        cli.ensure_connected()
        
        # 确认操作
        if not force:
            response = cli.client.list_jobs()
            if response.get("status") != "success":
                raise Exception(f"Failed to get job list: {response.get('message')}")
            
            jobs = response.get("jobs", [])
            if not jobs:
                print("ℹ️ No jobs to cleanup")
                return
            
            print(f"Found {len(jobs)} jobs to cleanup:")
            for job in jobs:
                print(f"  - {job.get('name')} ({job.get('uuid')[:8]}...) [{job.get('status')}]")
            
            if not typer.confirm(f"Are you sure you want to cleanup all {len(jobs)} jobs?"):
                print("ℹ️ Operation cancelled")
                return
        
        # 清理所有作业
        result = cli.client.cleanup_all_jobs()
        
        if result.get("status") == "success":
            print(f"✅ {result.get('message')}")
        else:
            print(f"❌ Failed to cleanup jobs: {result.get('message')}")
            raise typer.Exit(1)
            
    except Exception as e:
        print(f"❌ Failed to cleanup jobs: {e}")
        raise typer.Exit(1)

@app.command("health")
def health_check():
    """健康检查"""
    try:
        if not cli.client:
            cli.client = JobManagerClient(cli.daemon_host, cli.daemon_port)
        
        health = cli.client.health_check()
        
        if health.get("status") == "success":
            print("✅ JobManager is healthy")
            
            daemon_status = health.get("daemon_status", {})
            print(f"Daemon: {daemon_status.get('socket_service')}")
            print(f"Actor: {daemon_status.get('actor_name')}@{daemon_status.get('namespace')}")
        else:
            print(f"⚠️ Health check warning: {health.get('message')}")
            raise typer.Exit(1)
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        raise typer.Exit(1)

@app.command("info")
def system_info():
    """显示JobManager系统信息"""
    try:
        cli.ensure_connected()
        
        # 获取系统信息
        response = cli.client.get_server_info()
        if response.get("status") != "success":
            raise Exception(f"Failed to get server info: {response.get('message')}")
        
        info = response.get("server_info", {})
        
        print(f"\n{Fore.CYAN}=== JobManager System Information ==={Style.RESET_ALL}")
        print(f"Session ID: {info.get('session_id')}")
        print(f"Log Directory: {info.get('log_base_dir')}")
        print(f"Total Jobs: {info.get('environments_count', 0)}")
        
        # 统计作业状态
        jobs = info.get('jobs', [])
        status_counts = {}
        for job in jobs:
            status = job.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            print(f"\nJob Status Summary:")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
                
    except Exception as e:
        print(f"❌ Failed to get system info: {e}")
        raise typer.Exit(1)

@app.command("monitor")
def monitor_jobs(
    refresh: int = typer.Option(5, "--refresh", "-r", help="刷新间隔（秒）")
):
    """实时监控所有作业"""
    try:
        cli.ensure_connected()
        
        print(f"ℹ️ Monitoring jobs (refresh every {refresh}s, press Ctrl+C to stop)")
        
        def signal_handler(signum, frame):
            print("\nMonitoring stopped")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            # 清屏
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # 显示标题
            print(f"{Fore.CYAN}=== SAGE JobManager Monitor ==={Style.RESET_ALL}")
            print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # 获取并显示作业列表
            response = cli.client.list_jobs()
            if response.get("status") == "success":
                jobs = response.get("jobs", [])
                _format_job_table(jobs)
            else:
                print(f"❌ Failed to get job list: {response.get('message')}")
            
            # 等待
            time.sleep(refresh)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        raise typer.Exit(1)

@app.command("watch")
def watch_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    refresh: int = typer.Option(2, "--refresh", "-r", help="刷新间隔（秒）")
):
    """监控特定作业"""
    try:
        # 解析作业标识符
        job_uuid = cli._resolve_job_identifier(job_identifier)
        if not job_uuid:
            raise typer.Exit(1)
            
        cli.ensure_connected()
        
        print(f"ℹ️ Watching job {job_uuid[:8]}... (refresh every {refresh}s)")
        
        def signal_handler(signum, frame):
            print("\nWatching stopped")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            # 清屏
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # 显示作业详情
            response = cli.client.get_job_status(job_uuid)
            if response.get("status") == "success":
                job_info = response.get("job_status")
                if job_info:
                    print(f"{Fore.CYAN}=== Watching Job {job_uuid[:8]}... ==={Style.RESET_ALL}")
                    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    _format_job_details(job_info, verbose=True)
                else:
                    print(f"❌ Job {job_uuid} not found")
                    break
            else:
                print(f"❌ Failed to get job status: {response.get('message')}")
                break
            
            time.sleep(refresh)
            
    except KeyboardInterrupt:
        print("\nWatching stopped")
    except Exception as e:
        print(f"❌ Watch failed: {e}")
        raise typer.Exit(1)

# ==================== 辅助函数 ====================

def _format_job_table(jobs: List[Dict[str, Any]], short_uuid: bool = False):
    """格式化作业表格"""
    if not jobs:
        print("ℹ️ No jobs found")
        return
    
    # 根据终端宽度决定是否显示完整UUID
    import shutil
    terminal_width = shutil.get_terminal_size().columns
    
    if short_uuid or terminal_width < 120:
        headers = ['#', 'UUID (Short)', 'Name', 'Status', 'Started', 'Runtime']
    else:
        headers = ['#', 'UUID', 'Name', 'Status', 'Started', 'Runtime']
    
    rows = []
    
    for i, job in enumerate(jobs, 1):
        full_uuid = job.get('uuid', 'unknown')
        
        if short_uuid or terminal_width < 120:
            uuid_display = full_uuid[:8] + '...' if len(full_uuid) > 8 else full_uuid
        else:
            uuid_display = full_uuid
            
        name = job.get('name', 'unknown')
        status = job.get('status', 'unknown')
        start_time = job.get('start_time', 'unknown')
        runtime = job.get('runtime', 'unknown')
        
        # 状态着色
        if status == 'running':
            status = f"{Fore.GREEN}{status}{Style.RESET_ALL}"
        elif status in ['stopped', 'paused']:
            status = f"{Fore.YELLOW}{status}{Style.RESET_ALL}"
        elif status == 'failed':
            status = f"{Fore.RED}{status}{Style.RESET_ALL}"
        
        rows.append([i, uuid_display, name, status, start_time, runtime])
    
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    # 如果使用短UUID，显示提示信息
    if short_uuid or terminal_width < 120:
        print(f"\n{Fore.BLUE}💡 Tip:{Style.RESET_ALL} Use job number (#) or full UUID for commands")
        if jobs:
            print(f"   Example: sage job show 1  or  sage job show {jobs[0].get('uuid', '')}")
        print(f"   Use --full-uuid to see complete UUIDs")

def _format_job_details(job_info: Dict[str, Any], verbose: bool = False):
    """格式化作业详情"""
    print(f"{Fore.CYAN}=== Job Details ==={Style.RESET_ALL}")
    
    uuid = job_info.get('uuid', 'unknown')
    name = job_info.get('name', 'unknown')
    status = job_info.get('status', 'unknown')
    
    print(f"UUID: {uuid}")
    print(f"Name: {name}")
    
    # 状态着色
    if status == 'running':
        status_colored = f"{Fore.GREEN}{status}{Style.RESET_ALL}"
    elif status in ['stopped', 'paused']:
        status_colored = f"{Fore.YELLOW}{status}{Style.RESET_ALL}"
    elif status == 'failed':
        status_colored = f"{Fore.RED}{status}{Style.RESET_ALL}"
    else:
        status_colored = status
    
    print(f"Status: {status_colored}")
    print(f"Start Time: {job_info.get('start_time', 'unknown')}")
    print(f"Runtime: {job_info.get('runtime', 'unknown')}")
    
    if verbose:
        if 'error' in job_info:
            print(f"Error: {job_info['error']}")
        
        # 显示更多详细信息
        print(f"\nEnvironment Details:")
        env_info = job_info.get('environment', {})
        for key, value in env_info.items():
            print(f"  {key}: {value}")

def _print_status_colored(message: str):
    """打印带颜色的状态消息"""
    if 'running' in message:
        print(message.replace('running', f"{Fore.GREEN}running{Style.RESET_ALL}"))
    elif 'stopped' in message or 'paused' in message:
        if 'stopped' in message:
            print(message.replace('stopped', f"{Fore.YELLOW}stopped{Style.RESET_ALL}"))
        if 'paused' in message:
            print(message.replace('paused', f"{Fore.YELLOW}paused{Style.RESET_ALL}"))
    elif 'failed' in message:
        print(message.replace('failed', f"{Fore.RED}failed{Style.RESET_ALL}"))
    else:
        print(message)

if __name__ == "__main__":
    app()
