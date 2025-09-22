#!/usr/bin/env python3
"""
SAGE CLI Refactoring Example
============================

展示如何使用sage.cli.core模块重构现有命令
"""

import typer
from typing import Optional

# 导入核心模块
from sage.common.cli.core import (
    BaseCommand, JobManagerCommand, RemoteCommand,
    cli_command, require_connection, CLIException,
    OutputFormatter, print_status,
    SSHManager, SSHConfig,
    validate_host, validate_port, ValidationError
)

app = typer.Typer(name="example", help="重构示例命令")


# 示例1: 使用BaseCommand重构简单命令
class DoctorCommand(BaseCommand):
    """系统诊断命令"""
    
    def execute(self):
        """执行系统诊断"""
        self.print_section_header("🔍 SAGE System Diagnosis")
        
        # 检查Python版本
        import sys
        self.formatter.print_info(f"Python Version: {sys.version.split()[0]}")
        
        # 检查SAGE安装
        try:
            import sage
            self.formatter.print_success(f"SAGE Installation: v{getattr(sage, '__version__', 'unknown')}")
        except ImportError:
            self.formatter.print_error("SAGE not installed")
        
        # 检查扩展
        extensions = ["sage_ext", "sage_ext.sage_queue", "sage_ext.sage_db"]
        for ext in extensions:
            try:
                __import__(ext)
                self.formatter.print_success(f"Extension {ext}: Available")
            except ImportError:
                self.formatter.print_warning(f"Extension {ext}: Not available")
        
        # 检查Ray
        try:
            import ray
            self.formatter.print_success(f"Ray: v{ray.__version__}")
        except ImportError:
            self.formatter.print_error("Ray not installed")


@app.command("doctor")
@cli_command(require_config=False)
def doctor():
    """系统诊断"""
    cmd = DoctorCommand()
    cmd.execute()


# 示例2: 使用JobManagerCommand重构作业管理命令
class JobListCommand(JobManagerCommand):
    """作业列表命令"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_connection()
    
    def execute(self, status: Optional[str] = None, format_type: str = "table", 
               full_uuid: bool = False):
        """执行作业列表查询"""
        try:
            response = self.client.list_jobs()
            if response.get("status") != "success":
                raise CLIException(f"Failed to get job list: {response.get('message')}")
            
            jobs = response.get("jobs", [])
            
            # 状态过滤
            if status:
                jobs = [job for job in jobs if job.get("status") == status]
            
            # 格式化输出
            if format_type == "json":
                import json
                print(json.dumps({"jobs": jobs}, indent=2))
            else:
                # 处理UUID显示长度
                if not full_uuid:
                    for job in jobs:
                        if 'uuid' in job and len(job['uuid']) > 8:
                            job['uuid_short'] = job['uuid'][:8] + "..."
                
                headers = ['ID', 'Name', 'Status', 'Created', 'UUID' if full_uuid else 'UUID Short']
                self.formatter.print_data(jobs, headers)
                
        except Exception as e:
            self.handle_exception(e)


@app.command("list-jobs")
@cli_command()
def list_jobs(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    format_type: str = typer.Option("table", "--format", "-f", help="Output format"),
    full_uuid: bool = typer.Option(False, "--full-uuid", help="Show full UUID")
):
    """列出所有作业"""
    cmd = JobListCommand()
    cmd.execute(status, format_type, full_uuid)


# 示例3: 使用RemoteCommand重构集群管理命令
class ClusterStatusCommand(RemoteCommand):
    """集群状态检查命令"""
    
    def execute(self):
        """执行集群状态检查"""
        self.print_section_header("📊 Ray Cluster Status")
        
        # 检查Head节点状态
        head_config = self.get_config_section('head')
        head_host = head_config.get('host', 'localhost')
        dashboard_port = head_config.get('dashboard_port', 8265)
        
        self.formatter.print_info(f"Checking Head node: {head_host}")
        
        # 检查Worker节点状态
        worker_hosts = self.get_worker_hosts()
        
        if not worker_hosts:
            self.formatter.print_warning("No worker nodes configured")
            return
        
        self.formatter.print_info(f"Checking {len(worker_hosts)} worker nodes...")
        
        # 使用SSH检查worker状态
        if not self.ssh_manager:
            self._setup_ssh()
        
        for host, port in worker_hosts:
            try:
                # 测试连接
                if self.ssh_manager.test_connection(host, port):
                    self.formatter.print_success(f"Worker {host}:{port}: Connected")
                    
                    # 检查Ray进程
                    result = self.ssh_manager.execute_command(
                        host, port, "ps aux | grep -v grep | grep ray", timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        self.formatter.print_success(f"Worker {host}:{port}: Ray process running")
                    else:
                        self.formatter.print_warning(f"Worker {host}:{port}: Ray process not found")
                else:
                    self.formatter.print_error(f"Worker {host}:{port}: Connection failed")
                    
            except Exception as e:
                self.formatter.print_error(f"Worker {host}:{port}: Error - {e}")
        
        # 显示集群访问信息
        self.formatter.print_info(f"Dashboard: http://{head_host}:{dashboard_port}")


@app.command("cluster-status")
@cli_command()
def cluster_status():
    """检查集群状态"""
    cmd = ClusterStatusCommand()
    cmd.execute()


# 示例4: 使用装饰器的简单命令重构
@app.command("config-show")
@cli_command(name="show_config", help_text="显示当前配置", require_config=True)
def show_config(
    section: Optional[str] = typer.Option(None, "--section", "-s", help="显示指定配置节")
):
    """显示配置信息"""
    formatter = OutputFormatter()
    
    try:
        from sage.common.cli.core.config import load_and_validate_config
        from pathlib import Path
        
        config_path = Path.home() / ".sage" / "config.yaml"
        config = load_and_validate_config(config_path)
        
        formatter.print_section("📋 SAGE Configuration")
        formatter.print_info(f"Configuration file: {config_path}")
        
        if section:
            if section in config:
                formatter.print_data({section: config[section]})
            else:
                formatter.print_error(f"Configuration section '{section}' not found")
        else:
            formatter.print_data(config)
            
    except Exception as e:
        formatter.print_error(f"Failed to load configuration: {e}")
        raise typer.Exit(1)


# 示例5: 验证功能的使用
@app.command("validate-host")
@cli_command(require_config=False)
def validate_host_command(
    host: str = typer.Argument(..., help="要验证的主机地址"),
    port: int = typer.Option(22, "--port", "-p", help="端口号")
):
    """验证主机地址和端口"""
    formatter = OutputFormatter()
    
    try:
        # 使用核心验证功能
        validated_host = validate_host(host)
        validated_port = validate_port(port)
        
        formatter.print_success(f"Host validation successful: {validated_host}:{validated_port}")
        
        # 测试端口可用性
        from sage.common.cli.core.utils import is_port_available
        if is_port_available(validated_host, validated_port):
            formatter.print_info("Port is available (not in use)")
        else:
            formatter.print_warning("Port appears to be in use")
            
    except ValidationError as e:
        formatter.print_error(f"Validation failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
