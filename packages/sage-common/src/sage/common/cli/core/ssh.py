#!/usr/bin/env python3
"""
SAGE CLI SSH Manager
====================

SSH连接和远程命令执行功能
"""

import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Union, Any
import tempfile
import os

from .exceptions import ConnectionError, CLIException, ValidationError
from .validation import validate_host, validate_port, validate_path, validate_timeout
from .utils import run_subprocess, format_command_for_display
from .output import OutputFormatter


class SSHConfig:
    """SSH配置类"""
    
    def __init__(self, user: str, key_path: str, connect_timeout: int = 10,
                 strict_host_key_checking: bool = False, 
                 known_hosts_file: Optional[str] = None):
        self.user = user
        self.key_path = validate_path(key_path, must_exist=True, must_be_file=True)
        self.connect_timeout = validate_timeout(connect_timeout)
        self.strict_host_key_checking = strict_host_key_checking
        self.known_hosts_file = known_hosts_file
    
    def to_ssh_args(self) -> List[str]:
        """转换为SSH命令行参数"""
        args = [
            '-i', str(self.key_path),
            '-o', f'ConnectTimeout={self.connect_timeout}',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
        ]
        
        if not self.strict_host_key_checking:
            args.extend([
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null'
            ])
        elif self.known_hosts_file:
            args.extend(['-o', f'UserKnownHostsFile={self.known_hosts_file}'])
        
        return args


class SSHManager:
    """SSH连接管理器"""
    
    def __init__(self, config: SSHConfig):
        self.config = config
        self.formatter = OutputFormatter()
    
    def execute_command(self, host: str, port: int, command: str, 
                       timeout: int = 60, capture_output: bool = True) -> subprocess.CompletedProcess:
        """
        在远程主机上执行命令
        
        Args:
            host: 目标主机
            port: SSH端口
            command: 要执行的命令
            timeout: 超时时间
            capture_output: 是否捕获输出
            
        Returns:
            命令执行结果
            
        Raises:
            ConnectionError: SSH连接失败
            CLIException: 命令执行失败
        """
        host = validate_host(host)
        port = validate_port(port)
        timeout = validate_timeout(timeout)
        
        self.formatter.print_info(f"Executing on {self.config.user}@{host}:{port}: {command}")
        
        ssh_cmd = ['ssh'] + self.config.to_ssh_args() + [
            '-p', str(port),
            f'{self.config.user}@{host}',
            command
        ]
        
        try:
            return run_subprocess(
                ssh_cmd, 
                timeout=timeout, 
                capture_output=capture_output,
                check=False  # 我们手动检查结果
            )
        except CLIException as e:
            if "Connection" in str(e) or "connect" in str(e).lower():
                raise ConnectionError(f"Failed to connect to {host}:{port}: {e}")
            raise
    
    def transfer_file(self, local_path: Union[str, Path], host: str, port: int,
                     remote_path: str, direction: str = "upload") -> bool:
        """
        传输文件
        
        Args:
            local_path: 本地文件路径
            host: 目标主机
            port: SSH端口
            remote_path: 远程文件路径
            direction: 传输方向 ("upload" or "download")
            
        Returns:
            是否成功
            
        Raises:
            ConnectionError: SSH连接失败
            ValidationError: 参数验证失败
        """
        host = validate_host(host)
        port = validate_port(port)
        
        if direction == "upload":
            local_path = validate_path(local_path, must_exist=True)
            self.formatter.print_info(f"Uploading {local_path} to {host}:{remote_path}")
            src, dst = str(local_path), f"{self.config.user}@{host}:{remote_path}"
        elif direction == "download":
            local_path = validate_path(local_path)
            self.formatter.print_info(f"Downloading {host}:{remote_path} to {local_path}")
            src, dst = f"{self.config.user}@{host}:{remote_path}", str(local_path)
        else:
            raise ValidationError(f"Invalid direction: {direction}")
        
        scp_cmd = ['scp'] + self.config.to_ssh_args() + [
            '-P', str(port),
            src, dst
        ]
        
        try:
            result = run_subprocess(scp_cmd, check=False, capture_output=True)
            
            if result.returncode == 0:
                self.formatter.print_success("File transfer completed")
                return True
            else:
                self.formatter.print_error(f"File transfer failed: {result.stderr}")
                return False
                
        except CLIException as e:
            if "Connection" in str(e) or "connect" in str(e).lower():
                raise ConnectionError(f"Failed to connect to {host}:{port} for file transfer: {e}")
            raise
    
    def test_connection(self, host: str, port: int = 22) -> bool:
        """
        测试SSH连接
        
        Args:
            host: 目标主机
            port: SSH端口
            
        Returns:
            连接是否成功
        """
        host = validate_host(host)
        port = validate_port(port)
        
        try:
            result = self.execute_command(host, port, "echo 'Connection test'", timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def ensure_directory(self, host: str, port: int, directory: str) -> bool:
        """
        确保远程目录存在
        
        Args:
            host: 目标主机
            port: SSH端口
            directory: 目录路径
            
        Returns:
            操作是否成功
        """
        command = f"mkdir -p {directory}"
        result = self.execute_command(host, port, command)
        return result.returncode == 0


class RemoteExecutor:
    """远程命令执行器"""
    
    def __init__(self, ssh_manager: SSHManager):
        self.ssh_manager = ssh_manager
        self.formatter = OutputFormatter()
    
    def execute_script(self, host: str, port: int, script_content: str,
                      interpreter: str = "bash", timeout: int = 300) -> subprocess.CompletedProcess:
        """
        在远程主机上执行脚本
        
        Args:
            host: 目标主机
            port: SSH端口
            script_content: 脚本内容
            interpreter: 脚本解释器
            timeout: 超时时间
            
        Returns:
            命令执行结果
        """
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        try:
            # 上传脚本文件
            remote_script = f"/tmp/sage_script_{int(time.time())}.sh"
            success = self.ssh_manager.transfer_file(
                temp_script, host, port, remote_script, "upload"
            )
            
            if not success:
                raise CLIException("Failed to upload script file")
            
            # 执行脚本
            command = f"chmod +x {remote_script} && {interpreter} {remote_script}"
            result = self.ssh_manager.execute_command(host, port, command, timeout)
            
            # 清理远程脚本文件
            cleanup_cmd = f"rm -f {remote_script}"
            self.ssh_manager.execute_command(host, port, cleanup_cmd, timeout=10)
            
            return result
            
        finally:
            # 清理本地临时文件
            os.unlink(temp_script)
    
    def execute_python_script(self, host: str, port: int, script_content: str,
                             python_path: str = "python3", timeout: int = 300) -> subprocess.CompletedProcess:
        """
        在远程主机上执行Python脚本
        
        Args:
            host: 目标主机
            port: SSH端口
            script_content: Python脚本内容
            python_path: Python解释器路径
            timeout: 超时时间
            
        Returns:
            命令执行结果
        """
        return self.execute_script(host, port, script_content, python_path, timeout)
    
    def batch_execute(self, hosts_ports: List[tuple], command: str, 
                     parallel: bool = False, timeout: int = 60) -> Dict[str, subprocess.CompletedProcess]:
        """
        批量执行命令
        
        Args:
            hosts_ports: 主机端口列表 [(host1, port1), (host2, port2), ...]
            command: 要执行的命令
            parallel: 是否并行执行
            timeout: 超时时间
            
        Returns:
            执行结果字典 {host:port -> result}
        """
        results = {}
        
        if parallel:
            import concurrent.futures
            
            def execute_on_host(host_port):
                host, port = host_port
                key = f"{host}:{port}"
                try:
                    result = self.ssh_manager.execute_command(host, port, command, timeout)
                    return key, result
                except Exception as e:
                    # 创建一个错误结果
                    error_result = subprocess.CompletedProcess(
                        args=[command], returncode=1, stdout="", stderr=str(e)
                    )
                    return key, error_result
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_host = {
                    executor.submit(execute_on_host, host_port): host_port 
                    for host_port in hosts_ports
                }
                
                for future in concurrent.futures.as_completed(future_to_host):
                    key, result = future.result()
                    results[key] = result
        else:
            # 串行执行
            for host, port in hosts_ports:
                key = f"{host}:{port}"
                try:
                    result = self.ssh_manager.execute_command(host, port, command, timeout)
                    results[key] = result
                except Exception as e:
                    # 创建一个错误结果
                    error_result = subprocess.CompletedProcess(
                        args=[command], returncode=1, stdout="", stderr=str(e)
                    )
                    results[key] = error_result
        
        return results
    
    def check_service_status(self, host: str, port: int, service_name: str) -> Dict[str, Any]:
        """
        检查远程服务状态
        
        Args:
            host: 目标主机
            port: SSH端口
            service_name: 服务名称
            
        Returns:
            服务状态信息
        """
        # 检查进程是否运行
        ps_cmd = f"ps aux | grep -v grep | grep {service_name}"
        result = self.ssh_manager.execute_command(host, port, ps_cmd, timeout=10)
        
        status_info = {
            "host": host,
            "port": port,
            "service": service_name,
            "running": result.returncode == 0,
            "processes": []
        }
        
        if result.returncode == 0 and result.stdout:
            status_info["processes"] = result.stdout.strip().split('\n')
        
        return status_info
