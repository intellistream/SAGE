#!/usr/bin/env python3
"""
SAGE JobManager Controller
命令行工具，用于管理和监控 JobManager 作业
"""

import argparse
import json
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import signal

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from sage.jobmanager.jobmanager_client import JobManagerClient
    from sage_utils.actor_wrapper import ActorWrapper
    import yaml
    from tabulate import tabulate
    from colorama import Fore, Back, Style, init
    import click
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install pyyaml tabulate colorama click")
    sys.exit(1)

# 初始化colorama
init(autoreset=True)

class ControllerError(Exception):
    """Controller基础异常"""
    pass

class ConnectionError(ControllerError):
    """连接异常"""
    pass

class JobNotFoundError(ControllerError):
    """作业未找到异常"""
    pass

class JobManagerController:
    """JobManager控制器"""
    
    def __init__(self, daemon_host: str = "127.0.0.1", daemon_port: int = 19001):
        self.daemon_host = daemon_host
        self.daemon_port = daemon_port
        self.client: Optional[JobManagerClient] = None
        self.jobmanager: Optional[ActorWrapper] = None
        self.connected = False
        
        # 加载配置
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path.home() / ".sage" / "config.yaml"
        default_config = {
            "daemon": {
                "host": "127.0.0.1",
                "port": 19001
            },
            "output": {
                "format": "table",
                "colors": True
            },
            "monitor": {
                "refresh_interval": 5
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = yaml.safe_load(f) or {}
                    # 合并配置
                    default_config.update(user_config)
            except Exception as e:
                self._print_warning(f"Failed to load config: {e}")
        
        return default_config
    
    def connect(self) -> bool:
        """连接到JobManager"""
        try:
            self._print_info(f"Connecting to JobManager daemon at {self.daemon_host}:{self.daemon_port}...")
            
            self.client = JobManagerClient(self.daemon_host, self.daemon_port)
            
            # 健康检查
            health = self.client.health_check()
            if health.get("status") != "success":
                raise ConnectionError(f"Daemon health check failed: {health.get('message')}")
            
            # 获取JobManager句柄
            self.jobmanager = self.client.get_actor_handle()
            self.connected = True
            
            self._print_success("Connected to JobManager successfully")
            return True
            
        except Exception as e:
            self._print_error(f"Failed to connect: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.client = None
        self.jobmanager = None
    
    def ensure_connected(self):
        """确保已连接"""
        if not self.connected:
            if not self.connect():
                raise ConnectionError("Not connected to JobManager")
    
    def _resolve_job_identifier(self, identifier: str) -> Optional[str]:
        """解析作业标识符（可以是作业编号或UUID）"""
        try:
            self.ensure_connected()
            
            # 获取作业列表
            jobs = self.jobmanager.list_jobs()
            
            # 如果是数字，当作作业编号处理
            if identifier.isdigit():
                job_index = int(identifier) - 1  # 转换为0基索引
                if 0 <= job_index < len(jobs):
                    return jobs[job_index].get('uuid')
                else:
                    self._print_error(f"Job number {identifier} is out of range (1-{len(jobs)})")
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
                self._print_error(f"Ambiguous job identifier '{identifier}'. Matches:")
                for i, job in enumerate(matching_jobs, 1):
                    print(f"  {i}. {job.get('uuid')} ({job.get('name', 'unknown')})")
                return None
            else:
                self._print_error(f"No job found matching '{identifier}'")
                return None
                
        except Exception as e:
            self._print_error(f"Failed to resolve job identifier: {e}")
            return None
    
    # ==================== 命令实现 ====================
    
    def cmd_list(self, status_filter: Optional[str] = None, format_type: str = "table", full_uuid: bool = False) -> bool:
        """列出所有作业"""
        try:
            self.ensure_connected()
            
            # 获取作业列表
            jobs = self.jobmanager.list_jobs()
            
            # 状态过滤
            if status_filter:
                jobs = [job for job in jobs if job.get("status") == status_filter]
            
            # 格式化输出
            if format_type == "json":
                print(json.dumps({"jobs": jobs}, indent=2))
            else:
                self._format_job_table(jobs, short_uuid=not full_uuid)
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to list jobs: {e}")
            return False
    
    def cmd_show(self, job_identifier: str, verbose: bool = False) -> bool:
        """显示作业详情"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
            
            self.ensure_connected()
            
            # 获取作业状态
            job_info = self.jobmanager.get_job_status(job_uuid)
            
            if not job_info:
                raise JobNotFoundError(f"Job {job_uuid} not found")
            
            self._format_job_details(job_info, verbose)
            return True
            
        except JobNotFoundError as e:
            self._print_error(str(e))
            return False
        except Exception as e:
            self._print_error(f"Failed to show job: {e}")
            return False
    
    def cmd_stop(self, job_identifier: str, force: bool = False) -> bool:
        """停止作业"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
                
            self.ensure_connected()
            
            # 确认操作
            if not force:
                # 显示作业信息用于确认
                job_info = self.jobmanager.get_job_status(job_uuid)
                if job_info:
                    job_name = job_info.get('name', 'unknown')
                    print(f"Job to stop: {job_name} ({job_uuid})")
                
                if not click.confirm(f"Are you sure you want to stop this job?"):
                    self._print_info("Operation cancelled")
                    return True
            
            # 停止作业
            result = self.jobmanager.pause_job(job_uuid)
            
            if result.get("status") == "stopped":
                self._print_success(f"Job {job_uuid[:8]}... stopped successfully")
            else:
                self._print_error(f"Failed to stop job: {result.get('message')}")
                return False
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to stop job: {e}")
            return False
    
    def cmd_status(self, job_identifier: str) -> bool:
        """获取作业状态"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
                
            self.ensure_connected()
            
            job_info = self.jobmanager.get_job_status(job_uuid)
            
            if not job_info:
                raise JobNotFoundError(f"Job {job_uuid} not found")
            
            status = job_info.get("status", "unknown")
            job_name = job_info.get("name", "unknown")
            self._print_status_colored(f"Job '{job_name}' ({job_uuid[:8]}...) status: {status}")
            
            return True
            
        except JobNotFoundError as e:
            self._print_error(str(e))
            return False
        except Exception as e:
            self._print_error(f"Failed to get job status: {e}")
            return False
    
    def cmd_info(self) -> bool:
        """显示JobManager系统信息"""
        try:
            self.ensure_connected()
            
            # 获取系统信息
            info = self.jobmanager.get_server_info()
            
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
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to get system info: {e}")
            return False
    
    def cmd_health(self) -> bool:
        """健康检查"""
        try:
            if not self.client:
                self.client = JobManagerClient(self.daemon_host, self.daemon_port)
            
            health = self.client.health_check()
            
            if health.get("status") == "success":
                self._print_success("JobManager is healthy")
                
                daemon_status = health.get("daemon_status", {})
                print(f"Daemon: {daemon_status.get('socket_service')}")
                print(f"Actor: {daemon_status.get('actor_name')}@{daemon_status.get('namespace')}")
                
                return True
            else:
                self._print_warning(f"Health check warning: {health.get('message')}")
                return False
                
        except Exception as e:
            self._print_error(f"Health check failed: {e}")
            return False
    
    def cmd_continue(self, job_identifier: str, force: bool = False) -> bool:
        """继续作业"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
                
            self.ensure_connected()
            
            # 确认操作
            if not force:
                job_info = self.jobmanager.get_job_status(job_uuid)
                if job_info:
                    job_name = job_info.get('name', 'unknown')
                    print(f"Job to continue: {job_name} ({job_uuid})")
                
                if not click.confirm(f"Are you sure you want to continue this job?"):
                    self._print_info("Operation cancelled")
                    return True
            
            # 重启作业
            result = self.jobmanager.continue_job(job_uuid)
            
            if result.get("status") == "running":
                self._print_success(f"Job {job_uuid[:8]}... continued successfully")
            else:
                self._print_error(f"Failed to continue job: {result.get('message')}")
                return False
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to continue job: {e}")
            return False

    def cmd_delete(self, job_identifier: str, force: bool = False) -> bool:
        """删除作业"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
                
            self.ensure_connected()
            
            # 确认操作
            if not force:
                job_info = self.jobmanager.get_job_status(job_uuid)
                if job_info:
                    job_name = job_info.get('name', 'unknown')
                    job_status = job_info.get('status', 'unknown')
                    print(f"Job to delete: {job_name} ({job_uuid})")
                    print(f"Current status: {job_status}")
                
                if not click.confirm(f"Are you sure you want to delete this job? This action cannot be undone."):
                    self._print_info("Operation cancelled")
                    return True
            
            # 删除作业
            result = self.jobmanager.delete_job(job_uuid, force=force)
            
            if result.get("status") == "deleted":
                self._print_success(f"Job {job_uuid[:8]}... deleted successfully")
            else:
                self._print_error(f"Failed to delete job: {result.get('message')}")
                return False
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to delete job: {e}")
            return False


    def cmd_cleanup(self, force: bool = False) -> bool:
        """清理所有作业"""
        try:
            self.ensure_connected()
            
            # 确认操作
            if not force:
                jobs = self.jobmanager.list_jobs()
                if not jobs:
                    self._print_info("No jobs to cleanup")
                    return True
                
                print(f"Found {len(jobs)} jobs to cleanup:")
                for job in jobs:
                    print(f"  - {job.get('name')} ({job.get('uuid')[:8]}...) [{job.get('status')}]")
                
                if not click.confirm(f"Are you sure you want to cleanup all {len(jobs)} jobs?"):
                    self._print_info("Operation cancelled")
                    return True
            
            # 清理所有作业
            result = self.jobmanager.cleanup_all_jobs()
            
            if result.get("status") == "success":
                self._print_success(result.get("message"))
            else:
                self._print_error(f"Failed to cleanup jobs: {result.get('message')}")
                return False
            
            return True
            
        except Exception as e:
            self._print_error(f"Failed to cleanup jobs: {e}")
            return False

    def cmd_monitor(self, refresh_interval: int = 5) -> bool:
        """实时监控所有作业"""
        try:
            self.ensure_connected()
            
            self._print_info(f"Monitoring jobs (refresh every {refresh_interval}s, press Ctrl+C to stop)")
            
            # 设置信号处理
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
                jobs = self.jobmanager.list_jobs()
                self._format_job_table(jobs)
                
                # 等待
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            return True
        except Exception as e:
            self._print_error(f"Monitor failed: {e}")
            return False
    
    def cmd_watch(self, job_identifier: str, refresh_interval: int = 2) -> bool:
        """监控特定作业"""
        try:
            # 解析作业标识符
            job_uuid = self._resolve_job_identifier(job_identifier)
            if not job_uuid:
                return False
                
            self.ensure_connected()
            
            self._print_info(f"Watching job {job_uuid[:8]}... (refresh every {refresh_interval}s)")
            
            def signal_handler(signum, frame):
                print("\nWatching stopped")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            
            while True:
                # 清屏
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # 显示作业详情
                job_info = self.jobmanager.get_job_status(job_uuid)
                
                if not job_info:
                    self._print_error(f"Job {job_uuid} not found")
                    return False
                
                print(f"{Fore.CYAN}=== Watching Job {job_uuid[:8]}... ==={Style.RESET_ALL}")
                print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                self._format_job_details(job_info, verbose=True)
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\nWatching stopped")
            return True
        except Exception as e:
            self._print_error(f"Watch failed: {e}")
            return False
    
    # ==================== 交互式Shell ====================
    
    def cmd_shell(self) -> bool:
        """进入交互式shell"""
        try:
            self.ensure_connected()
            
            print(f"{Fore.GREEN}SAGE JobManager Interactive Shell{Style.RESET_ALL}")
            print("Type 'help' for available commands, 'exit' to quit")
            
            while True:
                try:
                    cmd_input = input(f"{Fore.BLUE}sage-jm> {Style.RESET_ALL}").strip()
                    
                    if not cmd_input:
                        continue
                    
                    if cmd_input in ['exit', 'quit']:
                        break
                    
                    if cmd_input == 'help':
                        self._show_shell_help()
                        continue
                    
                    # 解析命令
                    parts = cmd_input.split()
                    cmd = parts[0]
                    args = parts[1:]
                    
                    # 执行命令
                    if cmd == 'list':
                        status_filter = None
                        full_uuid = False
                        if '--status' in args:
                            idx = args.index('--status')
                            if idx + 1 < len(args):
                                status_filter = args[idx + 1]
                        if '--full-uuid' in args:
                            full_uuid = True
                        self.cmd_list(status_filter, format_type="table", full_uuid=full_uuid)
                        
                    elif cmd == 'show':
                        if args:
                            verbose = '--verbose' in args or '-v' in args
                            job_identifier = args[0]
                            self.cmd_show(job_identifier, verbose)
                        else:
                            self._print_error("Usage: show <job_number_or_uuid> [--verbose]")
                            
                    elif cmd == 'stop':
                        if args:
                            self.cmd_stop(args[0])
                        else:
                            self._print_error("Usage: stop <job_number_or_uuid>")
                            
                    elif cmd == 'status':
                        if args:
                            self.cmd_status(args[0])
                        else:
                            self._print_error("Usage: status <job_number_or_uuid>")
                            
                    elif cmd == 'info':
                        self.cmd_info()
                        
                    elif cmd == 'health':
                        self.cmd_health()
                        
                    else:
                        self._print_error(f"Unknown command: {cmd}")
                        
                except KeyboardInterrupt:
                    print()
                    continue
                except EOFError:
                    break
            
            print("Goodbye!")
            return True
            
        except Exception as e:
            self._print_error(f"Shell failed: {e}")
            return False
    
    def _show_shell_help(self):
        """显示shell帮助"""
        help_text = """
Available Commands:
  list [--status STATUS] [--full-uuid]    List all jobs
  show <job_number_or_uuid> [--verbose]   Show job details  
  stop <job_number_or_uuid>               Stop a job
  status <job_number_or_uuid>             Get job status
  info                                    Show system information
  health                                  Health check
  help                                    Show this help
  exit/quit                               Exit shell

Job Identifiers:
  You can use either job numbers (1, 2, 3...) or UUIDs
  Examples: show 1, show abc123, stop 2, status def456
"""
        print(help_text)
    
    # ==================== 输出格式化 ====================
    
    def _format_job_table(self, jobs: List[Dict[str, Any]], short_uuid: bool = False):
        """格式化作业表格"""
        if not jobs:
            self._print_info("No jobs found")
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
            elif status == 'stopped':
                status = f"{Fore.YELLOW}{status}{Style.RESET_ALL}"
            elif status == 'failed':
                status = f"{Fore.RED}{status}{Style.RESET_ALL}"
            
            rows.append([i, uuid_display, name, status, start_time, runtime])
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        
        # 如果使用短UUID，显示提示信息
        if short_uuid or terminal_width < 120:
            print(f"\n{Fore.BLUE}💡 Tip:{Style.RESET_ALL} Use job number (#) or full UUID for commands")
            print(f"   Example: sage-jm show 1  or  sage-jm show {jobs[0].get('uuid', '')}")
            print(f"   Use --full-uuid to see complete UUIDs")
    
    def _format_job_details(self, job_info: Dict[str, Any], verbose: bool = False):
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
        elif status == 'stopped':
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
    
    def _print_success(self, message: str):
        """打印成功消息"""
        print(f"{Fore.GREEN}✓{Style.RESET_ALL} {message}")
    
    def _print_error(self, message: str):
        """打印错误消息"""
        print(f"{Fore.RED}✗{Style.RESET_ALL} {message}")
    
    def _print_warning(self, message: str):
        """打印警告消息"""
        print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} {message}")
    
    def _print_info(self, message: str):
        """打印信息消息"""
        print(f"{Fore.BLUE}ℹ{Style.RESET_ALL} {message}")
    
    def _print_status_colored(self, message: str):
        """打印带颜色的状态消息"""
        if 'running' in message:
            print(message.replace('running', f"{Fore.GREEN}running{Style.RESET_ALL}"))
        elif 'stopped' in message:
            print(message.replace('stopped', f"{Fore.YELLOW}stopped{Style.RESET_ALL}"))
        elif 'failed' in message:
            print(message.replace('failed', f"{Fore.RED}failed{Style.RESET_ALL}"))
        else:
            print(message)

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='sage-jm',
        description='SAGE JobManager Controller'
    )
    
    # 全局参数
    parser.add_argument('--host', default='127.0.0.1', help='Daemon host')
    parser.add_argument('--port', type=int, default=19001, help='Daemon port')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='List all jobs')
    list_parser.add_argument('--status', choices=['running', 'stopped', 'failed'], help='Filter by status')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    list_parser.add_argument('--full-uuid', action='store_true', help='Show full UUIDs instead of short versions')
    
    # show 命令
    show_parser = subparsers.add_parser('show', help='Show job details')
    show_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    show_parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose details')
    
    # stop 命令
    stop_parser = subparsers.add_parser('stop', help='Stop a job')
    stop_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    stop_parser.add_argument('--force', '-f', action='store_true', help='Force stop without confirmation')
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='Get job status')
    status_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    
    # info 命令
    subparsers.add_parser('info', help='Show system information')
    
    # health 命令
    subparsers.add_parser('health', help='Health check')
    
    # monitor 命令
    monitor_parser = subparsers.add_parser('monitor', help='Monitor all jobs')
    monitor_parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')
    
    # watch 命令
    watch_parser = subparsers.add_parser('watch', help='Watch specific job')
    watch_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    watch_parser.add_argument('--refresh', type=int, default=2, help='Refresh interval in seconds')

    # continue 命令
    continue_parser = subparsers.add_parser('continue', help='continue a job')
    continue_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    continue_parser.add_argument('--force', '-f', action='store_true', help='Force continue without confirmation')
    
    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='Delete a job')
    delete_parser.add_argument('job_identifier', help='Job number (1,2,3...) or UUID')
    delete_parser.add_argument('--force', '-f', action='store_true', help='Force delete without confirmation')
    
    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup all jobs')
    cleanup_parser.add_argument('--force', '-f', action='store_true', help='Force cleanup without confirmation')

    # shell 命令
    subparsers.add_parser('shell', help='Enter interactive shell')
    
    return parser

def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 禁用颜色输出
    if args.no_color:
        import colorama
        colorama.deinit()
    
    # 创建控制器
    controller = JobManagerController(args.host, args.port)
    
    # 执行命令
    if not args.command:
        parser.print_help()
        return
    
    success = True
    
    try:
        if args.command == 'list':
            success = controller.cmd_list(args.status, args.format, args.full_uuid)
        elif args.command == 'show':
            success = controller.cmd_show(args.job_identifier, args.verbose)
        elif args.command == 'stop':
            success = controller.cmd_stop(args.job_identifier, args.force)
        elif args.command == 'continue':
            success = controller.cmd_continue(args.job_identifier, args.force)
        elif args.command == 'delete':
            success = controller.cmd_delete(args.job_identifier, args.force)
        elif args.command == 'status':
            success = controller.cmd_status(args.job_identifier)
        elif args.command == 'info':
            success = controller.cmd_info()
        elif args.command == 'health':
            success = controller.cmd_health()
        elif args.command == 'monitor':
            success = controller.cmd_monitor(args.refresh)
        elif args.command == 'watch':
            success = controller.cmd_watch(args.job_identifier, args.refresh)
        elif args.command == 'shell':
            success = controller.cmd_shell()
        elif args.command == 'cleanup':
            success = controller.cmd_cleanup(args.force)
        else:
            print(f"Unknown command: {args.command}")
            success = False
            
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        success = True
    except Exception as e:
        print(f"Unexpected error: {e}")
        success = False
    finally:
        controller.disconnect()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()