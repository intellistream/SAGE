"""
SAGE Studio 管理器 - 从 studio/cli.py 提取的业务逻辑
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import psutil
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

class StudioManager:
    """Studio 管理器"""
    
    def __init__(self):
        self.studio_dir = Path(__file__).parent.parent.parent / "studio"
        self.pid_file = Path.home() / ".sage" / "studio.pid"
        self.log_file = Path.home() / ".sage" / "studio.log"
        self.config_file = Path.home() / ".sage" / "studio.config.json"
        self.default_port = 4200
        self.default_host = "localhost"
        
        # 确保配置目录存在
        self.pid_file.parent.mkdir(exist_ok=True)
    
    def load_config(self) -> dict:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "port": self.default_port,
            "host": self.default_host,
            "dev_mode": False
        }
    
    def save_config(self, config: dict):
        """保存配置"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[red]保存配置失败: {e}[/red]")
    
    def is_running(self) -> Optional[int]:
        """检查 Studio 是否运行中"""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            if psutil.pid_exists(pid):
                return pid
            else:
                # PID 文件存在但进程不存在，清理文件
                self.pid_file.unlink()
                return None
        except Exception:
            return None
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        # 检查 Node.js
        try:
            result = subprocess.run(['node', '--version'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                console.print(f"[green]Node.js: {node_version}[/green]")
            else:
                console.print("[red]Node.js 未找到[/red]")
                return False
        except FileNotFoundError:
            console.print("[red]Node.js 未安装[/red]")
            return False
        
        # 检查 npm
        try:
            result = subprocess.run(['npm', '--version'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                console.print(f"[green]npm: {npm_version}[/green]")
            else:
                console.print("[red]npm 未找到[/red]")
                return False
        except (FileNotFoundError, subprocess.CalledProcessError):
            console.print("[red]npm 未安装[/red]")
            return False
        
        return True
    
    def install_dependencies(self) -> bool:
        """安装依赖"""
        if not self.studio_dir.exists():
            console.print(f"[red]Studio 目录不存在: {self.studio_dir}[/red]")
            return False
        
        package_json = self.studio_dir / "package.json"
        if not package_json.exists():
            console.print(f"[red]package.json 不存在: {package_json}[/red]")
            return False
        
        console.print("[blue]正在安装 npm 依赖...[/blue]")
        
        try:
            result = subprocess.run(
                ['npm', 'install'],
                cwd=self.studio_dir,
                check=True,
                capture_output=True,
                text=True
            )
            console.print("[green]依赖安装成功[/green]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]依赖安装失败: {e}[/red]")
            if e.stdout:
                console.print(f"stdout: {e.stdout}")
            if e.stderr:
                console.print(f"stderr: {e.stderr}")
            return False
    
    def start(self, port: int = None, host: str = None, dev: bool = False) -> bool:
        """启动 Studio"""
        if self.is_running():
            console.print("[yellow]Studio 已经在运行中[/yellow]")
            return False
        
        if not self.check_dependencies():
            console.print("[red]依赖检查失败[/red]")
            return False
        
        # 使用提供的参数或配置文件中的默认值
        config = self.load_config()
        port = port or config.get("port", self.default_port)
        host = host or config.get("host", self.default_host)
        
        # 保存新配置
        config.update({
            "port": port,
            "host": host,
            "dev_mode": dev
        })
        self.save_config(config)
        
        console.print(f"[blue]启动 Studio 在 {host}:{port}[/blue]")
        
        try:
            # 根据模式选择启动命令
            if dev:
                cmd = ['npm', 'run', 'start']
            else:
                cmd = ['npm', 'run', 'build']
            
            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=self.studio_dir,
                stdout=open(self.log_file, 'w'),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            # 保存 PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            console.print(f"[green]Studio 启动成功 (PID: {process.pid})[/green]")
            console.print(f"[blue]访问地址: http://{host}:{port}[/blue]")
            console.print(f"[dim]日志文件: {self.log_file}[/dim]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]启动失败: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """停止 Studio"""
        pid = self.is_running()
        if not pid:
            console.print("[yellow]Studio 未运行[/yellow]")
            return False
        
        try:
            # 发送终止信号
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            
            # 等待进程结束
            for i in range(10):
                if not psutil.pid_exists(pid):
                    break
                time.sleep(1)
            
            # 如果进程仍然存在，强制杀死
            if psutil.pid_exists(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            
            # 清理 PID 文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            console.print("[green]Studio 已停止[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]停止失败: {e}[/red]")
            return False
    
    def status(self):
        """显示状态"""
        pid = self.is_running()
        config = self.load_config()
        
        # 创建状态表格
        table = Table(title="SAGE Studio 状态")
        table.add_column("属性", style="cyan", width=12)
        table.add_column("值", style="white")
        
        if pid:
            try:
                process = psutil.Process(pid)
                table.add_row("状态", "[green]运行中[/green]")
                table.add_row("PID", str(pid))
                table.add_row("启动时间", time.strftime('%Y-%m-%d %H:%M:%S', 
                                                time.localtime(process.create_time())))
                table.add_row("CPU %", f"{process.cpu_percent():.1f}%")
                table.add_row("内存", f"{process.memory_info().rss / 1024 / 1024:.1f} MB")
            except psutil.NoSuchProcess:
                table.add_row("状态", "[red]进程不存在[/red]")
        else:
            table.add_row("状态", "[red]未运行[/red]")
        
        table.add_row("端口", str(config.get("port", self.default_port)))
        table.add_row("主机", config.get("host", self.default_host))
        table.add_row("开发模式", "是" if config.get("dev_mode") else "否")
        table.add_row("配置文件", str(self.config_file))
        table.add_row("日志文件", str(self.log_file))
        
        console.print(table)
        
        # 检查端口是否可访问
        if pid:
            try:
                url = f"http://{config.get('host', self.default_host)}:{config.get('port', self.default_port)}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    console.print(f"[green]✅ 服务可访问: {url}[/green]")
                else:
                    console.print(f"[yellow]⚠️ 服务响应异常: {response.status_code}[/yellow]")
            except requests.RequestException:
                console.print("[red]❌ 服务不可访问[/red]")
    
    def logs(self, follow: bool = False):
        """显示日志"""
        if not self.log_file.exists():
            console.print("[yellow]日志文件不存在[/yellow]")
            return
        
        if follow:
            console.print(f"[blue]跟踪日志 (按 Ctrl+C 退出): {self.log_file}[/blue]")
            try:
                subprocess.run(['tail', '-f', str(self.log_file)])
            except KeyboardInterrupt:
                console.print("\n[blue]停止跟踪日志[/blue]")
        else:
            console.print(f"[blue]显示日志: {self.log_file}[/blue]")
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    # 显示最后50行
                    for line in lines[-50:]:
                        print(line.rstrip())
            except Exception as e:
                console.print(f"[red]读取日志失败: {e}[/red]")
    
    def open_browser(self):
        """在浏览器中打开 Studio"""
        config = self.load_config()
        url = f"http://{config.get('host', self.default_host)}:{config.get('port', self.default_port)}"
        
        try:
            import webbrowser
            webbrowser.open(url)
            console.print(f"[green]已在浏览器中打开: {url}[/green]")
        except Exception as e:
            console.print(f"[red]打开浏览器失败: {e}[/red]")
            console.print(f"[blue]请手动访问: {url}[/blue]")
