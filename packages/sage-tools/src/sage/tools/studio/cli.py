"""
SAGE Studio CLI - Studio Web 界面管理工具
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
import psutil
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

class StudioManager:
    """Studio 管理器"""
    
    def __init__(self):
        self.studio_dir = Path(__file__).parent
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
            
            # 检查进程是否存在
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if 'node' in proc.name().lower() or 'ng' in ' '.join(proc.cmdline()):
                    return pid
            
            # PID 文件存在但进程不存在，清理 PID 文件
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
            if result.returncode != 0:
                console.print("[red]Node.js 未安装[/red]")
                return False
            
            node_version = result.stdout.strip().replace('v', '')
            major_version = int(node_version.split('.')[0])
            if major_version < 16:
                console.print(f"[red]Node.js 版本过低 ({node_version})，需要 >= 16[/red]")
                return False
                
        except FileNotFoundError:
            console.print("[red]Node.js 未安装[/red]")
            return False
        
        # 检查 npm
        try:
            subprocess.run(['npm', '--version'], 
                         capture_output=True, check=True)
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
            console.print("[red]package.json 不存在[/red]")
            return False
        
        console.print("[blue]正在安装 npm 依赖...[/blue]")
        try:
            subprocess.run(['npm', 'install'], 
                         cwd=self.studio_dir, check=True)
            console.print("[green]✅ 依赖安装完成[/green]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]依赖安装失败: {e}[/red]")
            return False
    
    def start(self, port: int = None, host: str = None, dev: bool = False) -> bool:
        """启动 Studio"""
        # 检查是否已运行
        running_pid = self.is_running()
        if running_pid:
            config = self.load_config()
            console.print(f"[yellow]Studio 已经在运行 (PID: {running_pid})[/yellow]")
            console.print(f"[blue]访问地址: http://{config.get('host', self.default_host)}:{config.get('port', self.default_port)}[/blue]")
            return True
        
        # 检查依赖
        if not self.check_dependencies():
            console.print("[red]依赖检查失败[/red]")
            return False
        
        # 检查是否需要安装依赖
        node_modules = self.studio_dir / "node_modules"
        if not node_modules.exists():
            if not self.install_dependencies():
                return False
        
        # 配置参数
        config = self.load_config()
        if port:
            config['port'] = port
        if host:
            config['host'] = host
        config['dev_mode'] = dev
        self.save_config(config)
        
        # 启动命令
        cmd = ['npm', 'start']
        if dev:
            cmd = ['ng', 'serve', '--host', config['host'], '--port', str(config['port'])]
        
        console.print(f"[blue]正在启动 Studio (端口: {config['port']})...[/blue]")
        
        try:
            # 启动进程
            with open(self.log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.studio_dir,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
            
            # 保存 PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # 等待启动
            console.print("[blue]等待服务启动...[/blue]")
            for i in range(30):  # 最多等待30秒
                try:
                    response = requests.get(f"http://{config['host']}:{config['port']}", timeout=1)
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(1)
            else:
                console.print("[yellow]服务可能仍在启动中，请稍后检查[/yellow]")
            
            console.print("[green]✅ Studio 启动成功[/green]")
            console.print(f"[blue]访问地址: http://{config['host']}:{config['port']}[/blue]")
            return True
            
        except Exception as e:
            console.print(f"[red]启动失败: {e}[/red]")
            return False
    
    def stop(self) -> bool:
        """停止 Studio"""
        running_pid = self.is_running()
        if not running_pid:
            console.print("[yellow]Studio 未运行[/yellow]")
            return True
        
        try:
            # 优雅停止
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/PID', str(running_pid)], check=True)
            else:
                os.killpg(os.getpgid(running_pid), signal.SIGTERM)
                
                # 等待进程结束
                for _ in range(10):
                    if not psutil.pid_exists(running_pid):
                        break
                    time.sleep(1)
                
                # 强制停止
                if psutil.pid_exists(running_pid):
                    os.killpg(os.getpgid(running_pid), signal.SIGKILL)
            
            # 清理 PID 文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            console.print("[green]✅ Studio 已停止[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]停止失败: {e}[/red]")
            return False
    
    def status(self):
        """显示状态"""
        running_pid = self.is_running()
        config = self.load_config()
        
        table = Table(title="SAGE Studio 状态")
        table.add_column("项目", style="cyan")
        table.add_column("值", style="green")
        
        if running_pid:
            table.add_row("状态", "🟢 运行中")
            table.add_row("PID", str(running_pid))
            table.add_row("访问地址", f"http://{config.get('host', self.default_host)}:{config.get('port', self.default_port)}")
        else:
            table.add_row("状态", "🔴 未运行")
        
        table.add_row("配置文件", str(self.config_file))
        table.add_row("日志文件", str(self.log_file))
        table.add_row("Studio 目录", str(self.studio_dir))
        
        console.print(table)
    
    def logs(self, follow: bool = False):
        """显示日志"""
        if not self.log_file.exists():
            console.print("[yellow]日志文件不存在[/yellow]")
            return
        
        if follow:
            console.print("[blue]正在跟踪日志 (Ctrl+C 停止)...[/blue]")
            try:
                subprocess.run(['tail', '-f', str(self.log_file)])
            except KeyboardInterrupt:
                console.print("\n[blue]停止跟踪日志[/blue]")
        else:
            with open(self.log_file, 'r') as f:
                content = f.read()
                if content:
                    console.print(Panel(content, title="Studio 日志"))
                else:
                    console.print("[yellow]日志为空[/yellow]")


# CLI 命令
@click.group()
@click.version_option()
def cli():
    """SAGE Studio - Web 界面管理工具"""
    pass

@cli.command()
@click.option('--port', '-p', type=int, help='指定端口')
@click.option('--host', '-h', default='localhost', help='指定主机')
@click.option('--dev', is_flag=True, help='开发模式')
def start(port, host, dev):
    """启动 Studio"""
    manager = StudioManager()
    success = manager.start(port=port, host=host, dev=dev)
    sys.exit(0 if success else 1)

@cli.command()
def stop():
    """停止 Studio"""
    manager = StudioManager()
    success = manager.stop()
    sys.exit(0 if success else 1)

@cli.command()
def restart():
    """重启 Studio"""
    manager = StudioManager()
    manager.stop()
    time.sleep(2)
    success = manager.start()
    sys.exit(0 if success else 1)

@cli.command()
def status():
    """显示状态"""
    manager = StudioManager()
    manager.status()

@cli.command()
@click.option('--follow', '-f', is_flag=True, help='跟踪日志')
def logs(follow):
    """查看日志"""
    manager = StudioManager()
    manager.logs(follow=follow)

@cli.command()
def install():
    """安装依赖"""
    manager = StudioManager()
    if manager.check_dependencies():
        success = manager.install_dependencies()
        sys.exit(0 if success else 1)
    else:
        sys.exit(1)

@cli.command()
def open():
    """在浏览器中打开 Studio"""
    manager = StudioManager()
    running_pid = manager.is_running()
    if not running_pid:
        console.print("[red]Studio 未运行，请先启动[/red]")
        sys.exit(1)
    
    config = manager.load_config()
    url = f"http://{config.get('host', manager.default_host)}:{config.get('port', manager.default_port)}"
    
    try:
        import webbrowser
        webbrowser.open(url)
        console.print(f"[green]已在浏览器中打开: {url}[/green]")
    except Exception as e:
        console.print(f"[red]打开浏览器失败: {e}[/red]")
        console.print(f"[blue]请手动访问: {url}[/blue]")

def main():
    """入口函数"""
    cli()

if __name__ == '__main__':
    main()
