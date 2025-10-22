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
from rich.table import Table

console = Console()


class StudioManager:
    """Studio 管理器"""

    def __init__(self):
        # studio_manager.py 在 packages/sage-studio/src/sage/studio/
        # frontend 现在在 packages/sage-studio/src/sage/studio/frontend/
        # __file__ -> studio_manager.py
        # .parent -> studio/
        self.studio_package_dir = Path(__file__).parent
        self.frontend_dir = self.studio_package_dir / "frontend"
        self.backend_dir = Path(__file__).parent / "config" / "backend"

        # 统一的 .sage 目录管理
        self.sage_dir = Path.home() / ".sage"
        self.studio_sage_dir = self.sage_dir / "studio"

        self.pid_file = self.sage_dir / "studio.pid"
        self.backend_pid_file = self.sage_dir / "studio_backend.pid"
        self.log_file = self.sage_dir / "studio.log"
        self.backend_log_file = self.sage_dir / "studio_backend.log"
        self.config_file = self.sage_dir / "studio.config.json"

        # 缓存和构建目录（React + Vite）
        self.node_modules_dir = self.studio_sage_dir / "node_modules"
        self.vite_cache_dir = self.studio_sage_dir / ".vite"  # Vite 缓存
        self.npm_cache_dir = self.studio_sage_dir / "cache" / "npm"
        self.dist_dir = self.studio_sage_dir / "dist"

        # React + Vite 默认端口是 5173
        self.default_port = 5173
        self.backend_port = 8080
        self.default_host = "localhost"

        # 确保所有目录存在
        self.ensure_sage_directories()

    def ensure_sage_directories(self):
        """确保所有 .sage 相关目录存在"""
        directories = [
            self.sage_dir,
            self.studio_sage_dir,
            self.vite_cache_dir,  # Vite 缓存目录
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
        return {
            "port": self.default_port,
            "backend_port": self.backend_port,
            "host": self.default_host,
            "dev_mode": False,
        }

    def save_config(self, config: dict):
        """保存配置"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[red]保存配置失败: {e}[/red]")

    def is_running(self) -> Optional[int]:
        """检查 Studio 前端是否运行中"""
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

    def is_backend_running(self) -> Optional[int]:
        """检查 Studio 后端API是否运行中"""
        if not self.backend_pid_file.exists():
            return None

        try:
            with open(self.backend_pid_file, "r") as f:
                pid = int(f.read().strip())

            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                # 检查是否是Python进程且包含api.py
                if "python" in proc.name().lower() and "api.py" in " ".join(
                    proc.cmdline()
                ):
                    return pid

            # PID 文件存在但进程不存在，清理文件
            self.backend_pid_file.unlink()
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

        # 清理项目目录中的临时文件（React + Vite）
        cleanup_patterns = [
            self.studio_package_dir / ".vite",
            self.studio_package_dir / "dist",
            self.frontend_dir / ".vite",
            self.frontend_dir / "dist",
            self.frontend_dir / "node_modules/.vite",  # Vite 缓存
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
                    console.print(
                        "[yellow]警告: 目标 node_modules 不存在，无法创建符号链接[/yellow]"
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

    def install(self) -> bool:
        """安装 Studio 依赖（React + Vite）"""
        console.print("[blue]📦 安装 SAGE Studio 依赖...[/blue]")

        # 清理散乱的临时文件
        self.clean_scattered_files()

        # 检查基础依赖
        if not self.check_dependencies():
            console.print("[red]❌ 依赖检查失败[/red]")
            return False

        # 安装所有依赖
        if not self.install_dependencies():
            console.print("[red]❌ 依赖安装失败[/red]")
            return False

        # 检查 TypeScript 编译
        self.check_typescript_compilation()

        # 确保 node_modules 符号链接正确
        self.ensure_node_modules_link()

        console.print("[green]✅ Studio 安装完成[/green]")
        return True

    def setup_vite_config(self) -> bool:
        """设置 Vite 配置（如果需要）"""
        console.print("[blue]检查 Vite 配置...[/blue]")

        try:
            vite_config_path = self.frontend_dir / "vite.config.ts"

            if not vite_config_path.exists():
                console.print("[yellow]vite.config.ts 不存在，使用默认配置[/yellow]")
                return True

            console.print("[green]✓ Vite 配置已就绪[/green]")
            return True

        except Exception as e:
            console.print(f"[red]配置检查失败: {e}[/red]")
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

    def create_spa_server_script(self, port: int, host: str) -> Path:
        """创建用于 SPA 的自定义服务器脚本"""
        server_script = self.studio_sage_dir / "spa_server.py"

        server_code = f'''#!/usr/bin/env python3
"""
SAGE Studio SPA 服务器
支持 Angular 单页应用的路由重定向
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    """支持 SPA 路由的 HTTP 处理器"""

    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """处理 GET 请求，支持 SPA 路由回退"""
        # 获取请求的文件路径
        file_path = Path(self.directory) / self.path.lstrip('/')

        # 如果是文件且存在，直接返回
        if file_path.is_file():
            super().do_GET()
            return

        # 如果是目录且包含 index.html，返回 index.html
        if file_path.is_dir():
            index_file = file_path / "index.html"
            if index_file.exists():
                self.path = str(index_file.relative_to(Path(self.directory)))
                super().do_GET()
                return

        # 对于 SPA 路由（不存在的路径），返回根目录的 index.html
        root_index = Path(self.directory) / "index.html"
        if root_index.exists():
            self.path = "/index.html"
            super().do_GET()
        else:
            # 如果连 index.html 都不存在，返回 404
            self.send_error(404, "File not found")

    def end_headers(self):
        """添加 CORS 头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    PORT = {port}
    HOST = "{host}"
    DIRECTORY = "{str(self.dist_dir)}"

    print(f"启动 SAGE Studio SPA 服务器...")
    print(f"地址: http://{{HOST}}:{{PORT}}")
    print(f"目录: {{DIRECTORY}}")
    print("按 Ctrl+C 停止服务器")

    # 更改工作目录
    os.chdir(DIRECTORY)

    # 创建处理器，传入目录参数
    handler = lambda *args, **kwargs: SPAHandler(*args, directory=DIRECTORY, **kwargs)

    try:
        with socketserver.TCPServer((HOST, PORT), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\n服务器已停止")
    except Exception as e:
        print(f"服务器错误: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        # 写入服务器脚本
        with open(server_script, "w") as f:
            f.write(server_code)

        # 设置执行权限
        server_script.chmod(0o755)

        console.print(f"[blue]已创建自定义 SPA 服务器: {server_script}[/blue]")
        return server_script

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
                    console.print(
                        f"[yellow]警告: 构建输出目录不存在: {self.dist_dir}[/yellow]"
                    )

                return True
            else:
                console.print("[red]Studio 构建失败[/red]")
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

    def start_backend(self, port: int = None) -> bool:
        """启动后端API服务"""
        # 检查是否已运行
        running_pid = self.is_backend_running()
        if running_pid:
            console.print(f"[yellow]后端API已经在运行 (PID: {running_pid})[/yellow]")
            return True

        # 检查后端文件是否存在
        api_file = self.backend_dir / "api.py"
        if not api_file.exists():
            console.print(f"[red]后端API文件不存在: {api_file}[/red]")
            return False

        # 配置参数
        config = self.load_config()
        backend_port = port or config.get("backend_port", self.backend_port)

        # 更新配置
        config["backend_port"] = backend_port
        self.save_config(config)

        console.print(f"[blue]正在启动后端API (端口: {backend_port})...[/blue]")

        try:
            # 启动后端进程
            cmd = [sys.executable, str(api_file)]
            with open(self.backend_log_file, "w") as log:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.backend_dir,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )

            # 保存 PID
            with open(self.backend_pid_file, "w") as f:
                f.write(str(process.pid))

            # 等待后端启动
            console.print("[blue]等待后端API启动...[/blue]")
            for i in range(15):  # 最多等待15秒
                try:
                    response = requests.get(
                        f"http://{config['host']}:{backend_port}/health", timeout=1
                    )
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(1)
            else:
                console.print("[yellow]后端API可能仍在启动中，请稍后检查[/yellow]")

            console.print("[green]✅ 后端API启动成功[/green]")
            return True

        except Exception as e:
            console.print(f"[red]后端API启动失败: {e}[/red]")
            return False

    def stop_backend(self) -> bool:
        """停止后端API服务"""
        running_pid = self.is_backend_running()
        if not running_pid:
            console.print("[yellow]后端API未运行[/yellow]")
            return True

        try:
            # 优雅停止
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(running_pid)], check=True)
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
            if self.backend_pid_file.exists():
                self.backend_pid_file.unlink()

            console.print("[green]✅ 后端API已停止[/green]")
            return True

        except Exception as e:
            console.print(f"[red]后端API停止失败: {e}[/red]")
            return False

    def start(self, port: int = None, host: str = None, dev: bool = False) -> bool:
        """启动 Studio（前端和后端）"""
        # 首先启动后端API
        if not self.start_backend():
            console.print("[red]后端API启动失败，无法启动Studio[/red]")
            return False

        # 检查前端是否已运行
        if self.is_running():
            console.print("[yellow]Studio前端已经在运行中[/yellow]")
            return True

        if not self.check_dependencies():
            console.print("[red]依赖检查失败[/red]")
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

        console.print(f"[blue]启动 Studio前端 在 {host}:{port}[/blue]")

        try:
            # 根据模式选择启动命令
            if dev:
                # 开发模式：使用 Vite dev server
                console.print("[blue]启动开发模式（Vite）...[/blue]")
                cmd = [
                    "npm",
                    "run",
                    "dev",
                    "--",
                    "--host",
                    host,
                    "--port",
                    str(port),
                ]
            else:
                # 生产模式：使用 Vite preview 或 serve
                # 首先确保有构建输出
                if not self.dist_dir.exists():
                    console.print("[blue]检测到无构建输出，开始构建...[/blue]")
                    if not self.build():
                        console.print("[red]构建失败，无法启动生产模式[/red]")
                        # 如果前端启动失败，也停止后端
                        self.stop_backend()
                        return False

                console.print("[blue]启动生产服务器（Vite Preview）...[/blue]")
                
                # 使用 Vite preview
                cmd = [
                    "npm",
                    "run",
                    "preview",
                    "--",
                    "--host",
                    host,
                    "--port",
                    str(port),
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
        """停止 Studio（前端和后端）"""
        frontend_pid = self.is_running()
        backend_running = self.is_backend_running()

        stopped_services = []

        # 停止前端
        if frontend_pid:
            try:
                # 发送终止信号
                os.killpg(os.getpgid(frontend_pid), signal.SIGTERM)

                # 等待进程结束
                for i in range(10):
                    if not psutil.pid_exists(frontend_pid):
                        break
                    time.sleep(1)

                # 如果进程仍然存在，强制杀死
                if psutil.pid_exists(frontend_pid):
                    os.killpg(os.getpgid(frontend_pid), signal.SIGKILL)

                # 清理 PID 文件
                if self.pid_file.exists():
                    self.pid_file.unlink()

                # 清理临时服务器脚本
                spa_server_script = self.studio_sage_dir / "spa_server.py"
                if spa_server_script.exists():
                    spa_server_script.unlink()

                stopped_services.append("前端")
            except Exception as e:
                console.print(f"[red]前端停止失败: {e}[/red]")

        # 停止后端
        if backend_running:
            if self.stop_backend():
                stopped_services.append("后端API")

        if stopped_services:
            console.print(
                f"[green]Studio {' 和 '.join(stopped_services)} 已停止[/green]"
            )
            return True
        else:
            console.print("[yellow]Studio 未运行[/yellow]")
            return False

    def status(self):
        """显示状态"""
        frontend_pid = self.is_running()
        backend_running = self.is_backend_running()
        config = self.load_config()

        # 创建前端状态表格
        frontend_table = Table(title="SAGE Studio 前端状态")
        frontend_table.add_column("属性", style="cyan", width=12)
        frontend_table.add_column("值", style="white")

        if frontend_pid:
            try:
                process = psutil.Process(frontend_pid)
                frontend_table.add_row("状态", "[green]运行中[/green]")
                frontend_table.add_row("PID", str(frontend_pid))
                frontend_table.add_row(
                    "启动时间",
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(process.create_time())
                    ),
                )
                frontend_table.add_row("CPU %", f"{process.cpu_percent():.1f}%")
                frontend_table.add_row(
                    "内存", f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
                )
            except psutil.NoSuchProcess:
                frontend_table.add_row("状态", "[red]进程不存在[/red]")
        else:
            frontend_table.add_row("状态", "[red]未运行[/red]")

        frontend_table.add_row("端口", str(config.get("port", self.default_port)))
        frontend_table.add_row("主机", config.get("host", self.default_host))
        frontend_table.add_row("开发模式", "是" if config.get("dev_mode") else "否")
        frontend_table.add_row("配置文件", str(self.config_file))
        frontend_table.add_row("日志文件", str(self.log_file))

        console.print(frontend_table)

        # 创建后端状态表格
        backend_table = Table(title="SAGE Studio 后端API状态")
        backend_table.add_column("属性", style="cyan", width=12)
        backend_table.add_column("值", style="white")

        if backend_running:
            backend_table.add_row("状态", "[green]运行中[/green]")
            backend_table.add_row("端口", str(self.backend_port))
            backend_table.add_row("PID文件", str(self.backend_pid_file))
            backend_table.add_row("日志文件", str(self.backend_log_file))
        else:
            backend_table.add_row("状态", "[red]未运行[/red]")
            backend_table.add_row("端口", str(self.backend_port))

        console.print(backend_table)

        # 检查端口是否可访问
        if frontend_pid:
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

    def logs(self, follow: bool = False, backend: bool = False):
        """显示日志"""
        # 选择要查看的日志文件
        if backend:
            log_file = self.backend_log_file
            service_name = "后端API"
        else:
            log_file = self.log_file
            service_name = "前端"

        if not log_file.exists():
            console.print(f"[yellow]{service_name}日志文件不存在[/yellow]")
            return

        if follow:
            console.print(
                f"[blue]跟踪{service_name}日志 (按 Ctrl+C 退出): {log_file}[/blue]"
            )
            try:
                subprocess.run(["tail", "-f", str(log_file)])
            except KeyboardInterrupt:
                console.print(f"\n[blue]停止跟踪{service_name}日志[/blue]")
        else:
            console.print(f"[blue]显示{service_name}日志: {log_file}[/blue]")
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    # 显示最后50行
                    for line in lines[-50:]:
                        print(line.rstrip())
            except Exception as e:
                console.print(f"[red]读取{service_name}日志失败: {e}[/red]")

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
