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
        self.frontend_dir = self.studio_dir / "frontend"
        
        # 统一的 .sage 目录管理
        self.sage_dir = Path.home() / ".sage"
        self.studio_sage_dir = self.sage_dir / "studio"
        
        self.pid_file = self.sage_dir / "studio.pid"
        self.log_file = self.sage_dir / "studio.log"
        self.config_file = self.sage_dir / "studio.config.json"
        
        # 缓存和构建目录
        self.node_modules_dir = self.studio_sage_dir / "node_modules"
        self.angular_cache_dir = self.studio_sage_dir / ".angular" / "cache"
        self.npm_cache_dir = self.studio_sage_dir / "cache" / "npm"
        self.dist_dir = self.studio_sage_dir / "dist"
        
        self.default_port = 4200
        self.default_host = "localhost"

        # 确保所有目录存在
        self.ensure_sage_directories()

    def ensure_sage_directories(self):
        """确保所有 .sage 相关目录存在"""
        directories = [
            self.sage_dir,
            self.studio_sage_dir,
            self.angular_cache_dir,
            self.npm_cache_dir,
            self.dist_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> dict:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"port": self.default_port, "host": self.default_host, "dev_mode": False}

    def save_config(self, config: dict):
        """保存配置"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[red]保存配置失败: {e}[/red]")

    def is_running(self) -> Optional[int]:
        """检查 Studio 是否运行中"""
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, "r") as f:
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
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True
            )
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
            result = subprocess.run(
                ["npm", "--version"], capture_output=True, text=True
            )
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

    def clean_scattered_files(self) -> bool:
        """清理散乱的临时文件和缓存"""
        console.print("[blue]清理散乱的临时文件...[/blue]")
        
        # 清理项目目录中的临时文件
        cleanup_patterns = [
            self.studio_dir / ".angular",
            self.studio_dir / "dist", 
            self.frontend_dir / ".angular",
            self.frontend_dir / "dist",
        ]
        
        cleaned = False
        for pattern in cleanup_patterns:
            if pattern.exists():
                import shutil
                if pattern.is_dir():
                    shutil.rmtree(pattern)
                    console.print(f"[green]✓ 已清理: {pattern}[/green]")
                    cleaned = True
                elif pattern.is_file():
                    pattern.unlink()
                    console.print(f"[green]✓ 已清理: {pattern}[/green]")
                    cleaned = True
        
        if not cleaned:
            console.print("[green]✓ 无需清理散乱文件[/green]")
        
        return True

    def ensure_node_modules_link(self) -> bool:
        """确保 node_modules 符号链接正确设置"""
        project_modules = self.frontend_dir / "node_modules"
        
        # 如果项目目录中有实际的 node_modules，删除它
        if project_modules.exists() and not project_modules.is_symlink():
            console.print("[blue]清理项目目录中的 node_modules...[/blue]")
            import shutil
            shutil.rmtree(project_modules)
        
        # 如果已经是符号链接，检查是否指向正确位置
        if project_modules.is_symlink():
            if project_modules.resolve() == self.node_modules_dir:
                console.print("[green]✓ node_modules 符号链接已正确设置[/green]")
                return True
            else:
                console.print("[blue]更新 node_modules 符号链接...[/blue]")
                project_modules.unlink()
        
        # 创建符号链接
        if self.node_modules_dir.exists():
            project_modules.symlink_to(self.node_modules_dir)
            console.print("[green]✓ 已创建 node_modules 符号链接[/green]")
            return True
        else:
            console.print("[yellow]警告: 目标 node_modules 不存在[/yellow]")
            return False

    def ensure_angular_dependencies(self) -> bool:
        """确保所有必要的 Angular 依赖都已安装"""
        required_packages = [
            "@angular/cdk",
            "@angular/animations", 
            "@angular/common",
            "@angular/core",
            "@angular/forms",
            "@angular/platform-browser",
            "@angular/platform-browser-dynamic",
            "@angular/router"
        ]
        
        console.print("[blue]检查 Angular 依赖...[/blue]")
        
        # 检查 package.json 中是否已有这些依赖
        package_json = self.frontend_dir / "package.json"
        try:
            import json
            with open(package_json, 'r') as f:
                package_data = json.load(f)
            
            dependencies = package_data.get('dependencies', {})
            missing_packages = []
            
            for package in required_packages:
                if package not in dependencies:
                    missing_packages.append(package)
            
            if missing_packages:
                console.print(f"[yellow]检测到缺失的依赖: {', '.join(missing_packages)}[/yellow]")
                console.print("[blue]正在安装缺失的依赖...[/blue]")
                
                # 安装缺失的包
                env = os.environ.copy()
                cache_dir = Path.home() / ".sage" / "studio" / "cache" / "npm"
                env["npm_config_cache"] = str(cache_dir)
                
                for package in missing_packages:
                    result = subprocess.run(
                        ["npm", "install", package, "--save"],
                        cwd=self.frontend_dir,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if result.returncode != 0:
                        console.print(f"[red]安装 {package} 失败[/red]")
                        return False
                    console.print(f"[green]✓ {package} 安装成功[/green]")
            else:
                console.print("[green]✓ 所有 Angular 依赖已就绪[/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]检查依赖时出错: {e}[/red]")
            return False
        """安装依赖"""
        if not self.frontend_dir.exists():
            console.print(f"[red]前端目录不存在: {self.frontend_dir}[/red]")
            return False

        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            console.print(f"[red]package.json 不存在: {package_json}[/red]")
            return False

        console.print("[blue]正在安装 npm 依赖...[/blue]")

        try:
            # 设置 npm 缓存目录
            env = os.environ.copy()
            env["npm_config_cache"] = str(self.npm_cache_dir)

            # 安装依赖到项目目录
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.frontend_dir,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            # 处理 node_modules 的位置
            project_modules = self.frontend_dir / "node_modules"

            if project_modules.exists():
                console.print("[blue]移动 node_modules 到 .sage 目录...[/blue]")

                # 如果目标目录已存在，先删除
                if self.node_modules_dir.exists():
                    import shutil
                    shutil.rmtree(self.node_modules_dir)

                # 移动 node_modules
                project_modules.rename(self.node_modules_dir)
                console.print("[green]node_modules 已移动到 .sage/studio/[/green]")

            # 无论如何都要创建符号链接（如果不存在的话）
            if not project_modules.exists():
                if self.node_modules_dir.exists():
                    project_modules.symlink_to(self.node_modules_dir)
                    console.print("[green]已创建 node_modules 符号链接[/green]")
                else:
                    console.print("[yellow]警告: 目标 node_modules 不存在，无法创建符号链接[/yellow]")

            console.print("[green]依赖安装成功[/green]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]依赖安装失败: {e}[/red]")
            if e.stdout:
                console.print(f"stdout: {e.stdout}")
            if e.stderr:
                console.print(f"stderr: {e.stderr}")
            return False

    def install_dependencies(self) -> bool:
        """安装依赖"""
        if not self.frontend_dir.exists():
            console.print(f"[red]前端目录不存在: {self.frontend_dir}[/red]")
            return False

        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            console.print(f"[red]package.json 不存在: {package_json}[/red]")
            return False

        console.print("[blue]正在安装 npm 依赖...[/blue]")

        try:
            # 设置 npm 缓存目录
            env = os.environ.copy()
            env["npm_config_cache"] = str(self.npm_cache_dir)

            # 安装依赖到项目目录
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.frontend_dir,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            # 处理 node_modules 的位置
            project_modules = self.frontend_dir / "node_modules"

            if project_modules.exists():
                console.print("[blue]移动 node_modules 到 .sage 目录...[/blue]")

                # 如果目标目录已存在，先删除
                if self.node_modules_dir.exists():
                    import shutil
                    shutil.rmtree(self.node_modules_dir)

                # 移动 node_modules
                project_modules.rename(self.node_modules_dir)
                console.print("[green]node_modules 已移动到 .sage/studio/[/green]")

            # 无论如何都要创建符号链接（如果不存在的话）
            if not project_modules.exists():
                if self.node_modules_dir.exists():
                    project_modules.symlink_to(self.node_modules_dir)
                    console.print("[green]已创建 node_modules 符号链接[/green]")
                else:
                    console.print("[yellow]警告: 目标 node_modules 不存在，无法创建符号链接[/yellow]")

            console.print("[green]依赖安装成功[/green]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]依赖安装失败: {e}[/red]")
            if e.stdout:
                console.print(f"stdout: {e.stdout}")
            if e.stderr:
                console.print(f"stderr: {e.stderr}")
            return False

    def install(self) -> bool:
        """安装 Studio 依赖"""
        console.print("[blue]📦 安装 SAGE Studio 依赖...[/blue]")

        # 清理散乱的临时文件
        self.clean_scattered_files()

        # 检查基础依赖
        if not self.check_dependencies():
            console.print("[red]❌ 依赖检查失败[/red]")
            return False

        # 确保 Angular 依赖完整
        if not self.ensure_angular_dependencies():
            console.print("[red]❌ Angular 依赖检查失败[/red]")
            return False

        # 安装所有依赖
        if not self.install_dependencies():
            console.print("[red]❌ 依赖安装失败[/red]")
            return False

        # 检查 TypeScript 编译
        self.check_typescript_compilation()

        # 确保 node_modules 符号链接正确
        self.ensure_node_modules_link()

        # 设置配置
        if not self.setup_studio_config():
            console.print("[red]❌ 配置设置失败[/red]")
            return False

        console.print("[green]✅ Studio 安装完成[/green]")
        return True

    def setup_studio_config(self) -> bool:
        """设置 Studio 配置"""
        console.print("[blue]配置 Studio 输出路径...[/blue]")

        try:
            # 运行配置脚本
            setup_script = self.studio_dir / "tools" / "setup_config.py"
            if setup_script.exists():
                result = subprocess.run(
                    [sys.executable, str(setup_script)],
                    cwd=self.studio_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    console.print("[green]Studio 配置成功[/green]")
                    return True
                else:
                    console.print(f"[red]Studio 配置失败: {result.stderr}[/red]")
                    return False
            else:
                console.print("[yellow]配置脚本不存在，跳过配置[/yellow]")
                return True
        except Exception as e:
            console.print(f"[red]配置失败: {e}[/red]")
            return False

    def check_typescript_compilation(self) -> bool:
        """检查 TypeScript 编译是否正常"""
        console.print("[blue]检查 TypeScript 编译...[/blue]")
        
        try:
            # 运行 TypeScript 编译检查
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                console.print("[green]✓ TypeScript 编译检查通过[/green]")
                return True
            else:
                console.print("[yellow]⚠️ TypeScript 编译警告/错误:[/yellow]")
                if result.stdout:
                    console.print(result.stdout)
                if result.stderr:
                    console.print(result.stderr)
                # 编译错误不阻止安装，只是警告
                return True
                
        except Exception as e:
            console.print(f"[yellow]TypeScript 检查跳过: {e}[/yellow]")
            return True

    def build(self) -> bool:
        """构建 Studio"""
        if not self.frontend_dir.exists():
            console.print(f"[red]前端目录不存在: {self.frontend_dir}[/red]")
            return False

        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            console.print(f"[red]package.json 不存在: {package_json}[/red]")
            return False

        console.print("[blue]正在构建 Studio...[/blue]")

        try:
            # 设置构建环境变量
            env = os.environ.copy()
            env["npm_config_cache"] = str(self.npm_cache_dir)

            # 运行构建命令，使用 .sage 目录作为输出
            result = subprocess.run(
                ["npm", "run", "build", "--", f"--output-path={self.dist_dir}"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                env=env,
            )

            if result.returncode == 0:
                console.print("[green]Studio 构建成功[/green]")
                
                # 检查构建输出
                if self.dist_dir.exists():
                    console.print(f"[blue]构建输出位置: {self.dist_dir}[/blue]")
                else:
                    console.print(f"[yellow]警告: 构建输出目录不存在: {self.dist_dir}[/yellow]")
                
                return True
            else:
                console.print(f"[red]Studio 构建失败[/red]")
                if result.stdout:
                    console.print("构建输出:")
                    console.print(result.stdout)
                if result.stderr:
                    console.print("错误信息:")
                    console.print(result.stderr)
                return False
                
        except Exception as e:
            console.print(f"[red]构建过程出错: {e}[/red]")
            return False

    def start(self, port: int = None, host: str = None, dev: bool = False) -> bool:
        """启动 Studio"""
        if self.is_running():
            console.print("[yellow]Studio 已经在运行中[/yellow]")
            return False

        if not self.check_dependencies():
            console.print("[red]依赖检查失败[/red]")
            return False

        # 设置 Studio 配置
        if not self.setup_studio_config():
            console.print("[red]Studio 配置失败[/red]")
            return False

        # 检查并安装 npm 依赖
        node_modules = self.frontend_dir / "node_modules"
        if not node_modules.exists():
            console.print("[blue]检测到未安装依赖，开始安装...[/blue]")
            if not self.install_dependencies():
                console.print("[red]依赖安装失败[/red]")
                return False

        # 使用提供的参数或配置文件中的默认值
        config = self.load_config()
        port = port or config.get("port", self.default_port)
        host = host or config.get("host", self.default_host)

        # 保存新配置
        config.update({"port": port, "host": host, "dev_mode": dev})
        self.save_config(config)

        console.print(f"[blue]启动 Studio 在 {host}:{port}[/blue]")

        try:
            # 根据模式选择启动命令
            if dev:
                # 开发模式：使用 ng serve
                console.print("[blue]启动开发模式...[/blue]")
                cmd = [
                    "npx", "ng", "serve",
                    "--host", host,
                    "--port", str(port),
                    "--disable-host-check",
                    "--configuration=development"
                ]
            else:
                # 生产模式：确保有构建输出，然后启动静态服务器
                if not self.dist_dir.exists():
                    console.print("[blue]检测到无构建输出，开始构建...[/blue]")
                    if not self.build():
                        console.print("[red]构建失败，无法启动生产模式[/red]")
                        return False

                console.print("[blue]启动生产服务器...[/blue]")
                cmd = [
                    "npx", "--yes", "http-server",
                    str(self.dist_dir),
                    "-p", str(port),
                    "-a", host,
                    "-c-1",  # 禁用缓存
                    "--cors"  # 启用 CORS
                ]

            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=self.frontend_dir,
                stdout=open(self.log_file, "w"),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )

            # 保存 PID
            with open(self.pid_file, "w") as f:
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
                table.add_row(
                    "启动时间",
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(process.create_time())
                    ),
                )
                table.add_row("CPU %", f"{process.cpu_percent():.1f}%")
                table.add_row(
                    "内存", f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
                )
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
                    console.print(
                        f"[yellow]⚠️ 服务响应异常: {response.status_code}[/yellow]"
                    )
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
                subprocess.run(["tail", "-f", str(self.log_file)])
            except KeyboardInterrupt:
                console.print("\n[blue]停止跟踪日志[/blue]")
        else:
            console.print(f"[blue]显示日志: {self.log_file}[/blue]")
            try:
                with open(self.log_file, "r") as f:
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
