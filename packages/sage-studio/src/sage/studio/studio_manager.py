"""
SAGE Studio 管理器 - 从 studio/cli.py 提取的业务逻辑
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests
from rich.console import Console
from rich.table import Table

from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

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

        # Use XDG paths via sage-common
        user_paths = get_user_paths()

        # State (PIDs, Logs)
        self.pid_file = user_paths.state_dir / "studio.pid"
        self.backend_pid_file = user_paths.state_dir / "studio_backend.pid"
        self.gateway_pid_file = user_paths.state_dir / "gateway.pid"

        self.log_file = user_paths.logs_dir / "studio.log"
        self.backend_log_file = user_paths.logs_dir / "studio_backend.log"
        self.gateway_log_file = user_paths.logs_dir / "gateway.log"

        # Config
        self.config_file = user_paths.config_dir / "studio.config.json"

        # Cache (Build artifacts)
        self.studio_cache_dir = user_paths.cache_dir / "studio"
        self.node_modules_dir = self.studio_cache_dir / "node_modules"
        self.vite_cache_dir = self.studio_cache_dir / ".vite"
        self.npm_cache_dir = self.studio_cache_dir / "npm"
        self.dist_dir = self.studio_cache_dir / "dist"

        # React + Vite 默认端口是 5173
        self.default_port = SagePorts.STUDIO_FRONTEND
        self.backend_port = SagePorts.STUDIO_BACKEND  # Studio backend API
        # Allow env override for gateway port; fallback logic handled in _start_gateway
        self.gateway_port = int(os.environ.get("SAGE_GATEWAY_PORT", str(SagePorts.GATEWAY_DEFAULT)))
        self.default_host = "0.0.0.0"  # 修改为监听所有网络接口

        # 确保所有目录存在
        self.ensure_sage_directories()

    def ensure_sage_directories(self):
        """确保所有 .sage 相关目录存在"""
        directories = [
            self.studio_cache_dir,
            self.vite_cache_dir,
            self.npm_cache_dir,
            self.dist_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_node_modules_root(self) -> Path | None:
        """Locate the effective node_modules directory."""

        if self.node_modules_dir.exists():
            return self.node_modules_dir

        fallback = self.frontend_dir / "node_modules"
        if fallback.exists():
            return fallback

        return None

    def load_config(self) -> dict:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
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

    def is_running(self) -> int | None:
        """检查 Studio 前端是否运行中

        Returns:
            int: 进程 PID
            -1: 服务在运行但无法确定 PID（外部启动）
            None: 服务未运行
        """
        # 方法1: 检查 PID 文件
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())

                if psutil.pid_exists(pid):
                    return pid
                else:
                    # PID 文件存在但进程不存在，清理文件
                    self.pid_file.unlink()
            except Exception:
                pass

        # 方法2: 通过端口检查（检测外部启动的服务）
        config = self.load_config()
        port = config.get("port", self.default_port)
        try:
            response = requests.get(f"http://localhost:{port}/", timeout=1)
            # Vite dev server 或 preview server 会返回 HTML
            if response.status_code == 200:
                return -1  # 运行中但无 PID 文件
        except Exception:
            pass

        return None

    def is_backend_running(self) -> int | None:
        """检查 Studio 后端API是否运行中

        Returns:
            int: 进程 PID
            -1: 服务在运行但无法确定 PID（外部启动）
            None: 服务未运行
        """
        # 方法1: 检查 PID 文件
        if self.backend_pid_file.exists():
            try:
                with open(self.backend_pid_file) as f:
                    pid = int(f.read().strip())

                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    # 检查是否是Python进程且包含api.py
                    if "python" in proc.name().lower() and "api.py" in " ".join(proc.cmdline()):
                        return pid

                # PID 文件存在但进程不存在，清理文件
                self.backend_pid_file.unlink()
            except Exception:
                pass

        # 方法2: 通过端口健康检查（检测外部启动的服务）
        config = self.load_config()
        backend_port = config.get("backend_port", self.backend_port)
        try:
            response = requests.get(f"http://localhost:{backend_port}/health", timeout=1)
            if response.status_code == 200:
                return -1  # 运行中但无 PID 文件
        except Exception:
            pass

        return None

    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return False  # 可以绑定，说明端口空闲
            except OSError:
                return True  # 无法绑定，说明端口被占用

    def _kill_process_on_port(self, port: int) -> bool:
        """杀死占用指定端口的进程"""
        try:
            for conn in psutil.net_connections(kind="inet"):
                if hasattr(conn, "laddr") and conn.laddr and conn.laddr.port == port:
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            console.print(f"[dim]   杀死进程 {conn.pid} ({proc.name()})[/dim]")
                            proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            return True
        except Exception as e:
            console.print(f"[dim]   无法杀死端口 {port} 上的进程: {e}[/dim]")
            return False

    def is_gateway_running(self) -> int | None:
        """检查 Gateway 是否运行中"""
        # 方法1: 检查 PID 文件
        if self.gateway_pid_file.exists():
            try:
                with open(self.gateway_pid_file) as f:
                    pid = int(f.read().strip())

                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    # 检查是否是 sage-gateway 进程
                    cmdline = " ".join(proc.cmdline())
                    if "sage-gateway" in cmdline or "gateway" in cmdline:
                        return pid

                # PID 文件存在但进程不存在，清理文件
                self.gateway_pid_file.unlink()
            except Exception:
                pass

        # 方法2: 通过端口检查
        try:
            response = requests.get(f"http://localhost:{self.gateway_port}/health", timeout=1)
            if response.status_code == 200:
                # Gateway 在运行但没有 PID 文件，尝试找到进程
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        cmdline = " ".join(proc.cmdline())
                        if "sage-gateway" in cmdline or (
                            "python" in proc.name().lower() and "gateway" in cmdline
                        ):
                            return proc.pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                return -1  # 运行中但找不到 PID
        except Exception:
            pass

        return None

    def start_gateway(self, host: str | None = None, port: int | None = None) -> bool:
        """启动 Gateway 服务"""
        host = host or self.default_host
        port = port or self.gateway_port

        # 检查是否已经运行
        existing_pid = self.is_gateway_running()
        if existing_pid:
            if existing_pid == -1:
                console.print("[green]✅ Gateway 已在运行中（外部启动）[/green]")
            else:
                console.print(f"[green]✅ Gateway 已在运行中 (PID: {existing_pid})[/green]")
            return True

        console.print(f"[blue]🚀 启动 Gateway 服务 ({host}:{port})...[/blue]")

        try:
            # 检查 sage-llm-gateway 命令是否可用
            result = subprocess.run(["which", "sage-llm-gateway"], capture_output=True, text=True)
            if result.returncode != 0:
                console.print(
                    "[yellow]⚠️  sage-llm-gateway 命令未找到，尝试使用 python -m sage.llm.gateway.server[/yellow]"
                )
                cmd = [
                    "python",
                    "-m",
                    "sage.llm.gateway.server",
                    "--host",
                    host,
                    "--port",
                    str(port),
                ]
            else:
                cmd = ["sage-llm-gateway", "--host", host, "--port", str(port)]

            # 启动进程
            log_handle = open(self.gateway_log_file, "w")
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,  # 阻止子进程读取 stdin
                stdout=log_handle,
                stderr=log_handle,
                start_new_session=True,
            )
            # 注意：不关闭 log_handle，让子进程继承并管理它

            # 保存 PID
            with open(self.gateway_pid_file, "w") as f:
                f.write(str(process.pid))

            # 等待服务启动 - 增加到 60 秒，因为 Gateway 需要加载 studio routes
            console.print("[blue]等待 Gateway 服务启动...[/blue]")
            max_wait = 60  # 最多等待 60 秒

            # 创建不使用代理的 session
            session = requests.Session()
            session.trust_env = False

            for i in range(max_wait):
                # 检查进程是否还在运行
                if not psutil.pid_exists(process.pid):
                    console.print("[red]❌ Gateway 进程已退出[/red]")
                    # 输出日志帮助调试
                    if self.gateway_log_file.exists():
                        console.print("[yellow]Gateway 日志（最后 30 行）:[/yellow]")
                        try:
                            with open(self.gateway_log_file) as f:
                                lines = f.readlines()
                                for line in lines[-30:]:
                                    console.print(f"[dim]  {line.rstrip()}[/dim]")
                        except Exception:
                            pass
                    return False

                try:
                    response = session.get(f"http://localhost:{port}/health", timeout=2)
                    if response.status_code == 200:
                        console.print(
                            f"[green]✅ Gateway 服务启动成功 (PID: {process.pid}, 耗时 {i + 1} 秒)[/green]"
                        )
                        console.print(f"[blue]📡 Gateway API: http://{host}:{port}[/blue]")
                        return True
                except Exception:
                    pass

                # 每 10 秒输出一次状态
                if (i + 1) % 10 == 0:
                    console.print(f"[blue]   等待 Gateway 响应... ({i + 1}/{max_wait}秒)[/blue]")

                time.sleep(1)

            # 超时但进程还在，可能只是启动慢
            if psutil.pid_exists(process.pid):
                console.print("[yellow]⚠️  Gateway 启动超时，但进程仍在运行[/yellow]")
                console.print(f"[yellow]   请检查日志: {self.gateway_log_file}[/yellow]")
                # 输出日志最后几行
                if self.gateway_log_file.exists():
                    try:
                        with open(self.gateway_log_file) as f:
                            lines = f.readlines()
                            if lines:
                                console.print("[yellow]   Gateway 日志（最后 10 行）:[/yellow]")
                                for line in lines[-10:]:
                                    console.print(f"[dim]     {line.rstrip()}[/dim]")
                    except Exception:
                        pass
                return True  # 进程还在，认为可能成功

            console.print("[red]❌ Gateway 启动失败[/red]")
            return False

        except Exception as e:
            console.print(f"[red]❌ Gateway 启动失败: {e}[/red]")
            return False

    def stop_gateway(self) -> bool:
        """停止 Gateway 服务"""
        pid = self.is_gateway_running()
        if not pid:
            return False

        if pid == -1:
            console.print("[yellow]⚠️  Gateway 在运行但无法确定 PID，请手动停止[/yellow]")
            return False

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
            console.print(f"[green]✅ Gateway 已停止 (PID: {pid})[/green]")

            # 清理 PID 文件
            if self.gateway_pid_file.exists():
                self.gateway_pid_file.unlink()

            return True
        except psutil.TimeoutExpired:
            proc.kill()
            console.print(f"[yellow]⚠️  Gateway 强制停止 (PID: {pid})[/yellow]")
            if self.gateway_pid_file.exists():
                self.gateway_pid_file.unlink()
            return True
        except Exception as e:
            console.print(f"[red]❌ 停止 Gateway 失败: {e}[/red]")
            return False

    def check_dependencies(self) -> bool:
        """检查依赖"""
        MIN_NODE_VERSION = 20  # Vite 7.x 需要 Node.js 20.19+，推荐 22+

        # 检查 Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                # 解析版本号（例如 v12.22.9 -> 12）
                version_str = node_version.lstrip("v").split(".")[0]
                try:
                    major_version = int(version_str)
                except ValueError:
                    major_version = 0

                if major_version < MIN_NODE_VERSION:
                    console.print(
                        f"[red]Node.js 版本过低: {node_version}（需要 v{MIN_NODE_VERSION}+）[/red]"
                    )
                    console.print("[yellow]💡 请升级 Node.js:[/yellow]")
                    console.print("   conda install -y nodejs=22 -c conda-forge")
                    console.print("   # 或通过 nvm 安装: nvm install 22 && nvm use 22")
                    return False
                console.print(f"[green]Node.js: {node_version}[/green]")
            else:
                console.print("[red]Node.js 未找到[/red]")
                console.print("[yellow]💡 安装方法:[/yellow]")
                console.print("   conda install -y nodejs=20 -c conda-forge")
                console.print("   # 或 apt install nodejs npm")
                return False
        except FileNotFoundError:
            console.print("[red]Node.js 未安装[/red]")
            console.print("[yellow]💡 安装方法:[/yellow]")
            console.print("   conda install -y nodejs=20 -c conda-forge")
            console.print("   # 或 apt install nodejs npm")
            return False

        # 检查 npm
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                console.print(f"[green]npm: {npm_version}[/green]")
            else:
                console.print("[red]npm 未找到[/red]")
                console.print("[yellow]💡 npm 通常随 Node.js 一起安装[/yellow]")
                return False
        except (FileNotFoundError, subprocess.CalledProcessError):
            console.print("[red]npm 未安装[/red]")
            console.print("[yellow]💡 npm 通常随 Node.js 一起安装[/yellow]")
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

    def _ensure_frontend_dependency_integrity(
        self, auto_fix: bool = True, skip_confirm: bool = False
    ) -> bool:
        """Detect and optionally repair broken critical frontend dependencies."""

        modules_root = self._get_node_modules_root()
        if modules_root is None:
            return True  # Nothing to check yet

        critical_packages = [
            {
                "name": "lines-and-columns",
                "version": "1.2.4",
                "required": ["build", "build/index.js"],
                "reason": "PostCSS SourceMap helper (Vite dev server)",
            },
            {
                "name": "typescript",
                "version": "^5.2.2",
                "required": ["bin/tsc"],
                "reason": "TypeScript compiler for build",
            },
            {
                "name": "vite",
                "version": "^5.0.8",
                "required": ["bin/vite.js", "dist/node/cli.js"],
                "reason": "Vite build tool",
            },
        ]

        broken: list[tuple[dict, list[str]]] = []

        for pkg in critical_packages:
            pkg_dir = modules_root / pkg["name"]
            missing: list[str] = []

            if not pkg_dir.exists():
                missing.append("package directory")
            else:
                for rel_path in pkg["required"]:
                    if not (pkg_dir / rel_path).exists():
                        missing.append(rel_path)

            if missing:
                broken.append((pkg, missing))

        if not broken:
            return True

        console.print("[yellow]⚠️  检测到前端依赖缺少关键文件，Vite 可能无法启动[/yellow]")
        for pkg, missing in broken:
            missing_display = ", ".join(missing)
            console.print(
                f"   • {pkg['name']}: 缺少 {missing_display} ({pkg.get('reason', '必需文件')})"
            )

        if not auto_fix:
            console.print(
                "[yellow]自动修复已禁用，请运行 'sage studio install' 或在"
                f" {self.frontend_dir} 执行: npm cache clean --force && "
                "npm install --no-save <package>@<version>[/yellow]"
            )
            return False

        for pkg, _missing in broken:
            if not self._repair_node_package(pkg):
                return False

        return self._ensure_frontend_dependency_integrity(auto_fix=False)

    def _repair_node_package(self, package_meta: dict) -> bool:
        """Attempt to self-heal a corrupted npm package installation."""

        package_name = package_meta["name"]
        version = package_meta.get("version")
        spec = f"{package_name}@{version}" if version else package_name

        modules_root = self._get_node_modules_root()
        if modules_root is None:
            console.print("[red]node_modules 尚未安装，无法修复依赖[/red]")
            return False

        console.print(f"[blue]🧹 修复前端依赖 {spec}...[/blue]")

        targets = {
            modules_root / package_name,
            (self.frontend_dir / "node_modules") / package_name,
        }

        for target in targets:
            if target.exists() or target.is_symlink():
                try:
                    if target.is_symlink() or target.is_file():
                        target.unlink()
                    else:
                        shutil.rmtree(target)
                    console.print(f"   [green]✓[/green] 已清理 {target}")
                except Exception as exc:  # pragma: no cover - best effort cleanup
                    console.print(f"[red]清理 {target} 失败: {exc}[/red]")
                    return False

        env = os.environ.copy()
        env["npm_config_cache"] = str(self.npm_cache_dir)

        def run_npm(args: list[str], label: str) -> bool:
            try:
                subprocess.run(
                    ["npm", *args],
                    cwd=self.frontend_dir,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return True
            except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime failure
                console.print(f"[red]npm {label} 失败 (exit {exc.returncode})[/red]")
                if exc.stdout:
                    console.print(exc.stdout.strip())
                if exc.stderr:
                    console.print(exc.stderr.strip())
                return False

        console.print("   [blue]刷新 npm 缓存...[/blue]")
        if not run_npm(["cache", "clean", "--force"], "cache clean"):
            return False

        console.print("   [blue]重新安装依赖文件...[/blue]")
        install_args = ["install", "--no-save", spec]
        if not run_npm(install_args, f"install {spec}"):
            return False

        # 仅在 .sage/studio/node_modules 已存在时尝试创建符号链接，
        # 避免误删项目目录中的实际依赖目录
        if self.node_modules_dir.exists():
            self.ensure_node_modules_link()
        console.print(f"[green]✅ {spec} 修复完成[/green]")
        return True

    def install_dependencies(
        self,
        command: str = "install",
        extra_args: list[str] | None = None,
    ) -> bool:
        """安装依赖"""
        if not self.frontend_dir.exists():
            console.print(f"[red]前端目录不存在: {self.frontend_dir}[/red]")
            return False

        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            console.print(f"[red]package.json 不存在: {package_json}[/red]")
            return False

        console.print(f"[blue]正在执行 npm {command} ...[/blue]")

        try:
            # 设置 npm 缓存目录
            env = os.environ.copy()
            env["npm_config_cache"] = str(self.npm_cache_dir)

            # 安装依赖到项目目录
            cmd = ["npm", command]
            if extra_args:
                cmd.extend(extra_args)

            subprocess.run(
                cmd,
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

        if not self._ensure_frontend_dependency_integrity(auto_fix=True):
            console.print("[red]❌ 依赖完整性检查失败[/red]")
            return False

        # 检查 TypeScript 编译
        self.check_typescript_compilation()

        # 确保 node_modules 符号链接正确
        self.ensure_node_modules_link()

        console.print("[green]✅ Studio 安装完成[/green]")
        return True

    def run_npm_command(self, npm_args: list[str]) -> bool:
        """在 Studio 前端目录中运行任意 npm 命令。"""
        if not npm_args:
            console.print("[red]请提供要执行的 npm 子命令，例如: install[/red]")
            return False

        if not self.frontend_dir.exists():
            console.print(f"[red]前端目录不存在: {self.frontend_dir}[/red]")
            return False

        if not self.check_dependencies():
            console.print("[red]依赖检查失败，无法执行 npm 命令[/red]")
            return False

        command = npm_args[0]
        extra_args = npm_args[1:]

        if command in {"install", "ci"}:
            return self.install_dependencies(command=command, extra_args=extra_args)

        env = os.environ.copy()
        env["npm_config_cache"] = str(self.npm_cache_dir)

        console.print(f"[blue]运行 npm {' '.join(npm_args)}... 按 Ctrl+C 可中断[/blue]")
        try:
            subprocess.run(
                ["npm", *npm_args],
                cwd=self.frontend_dir,
                env=env,
                check=True,
            )
            console.print("[green]npm 命令执行完成[/green]")
            return True
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]npm 命令失败 (退出码 {exc.returncode})[/red]")
            return False
        except KeyboardInterrupt:
            console.print("[yellow]npm 命令已被用户中断[/yellow]")
            return False

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
        server_script = self.studio_cache_dir / "spa_server.py"

        server_code = f'''#!/usr/bin/env python3
"""
SAGE Studio SPA 服务器
支持 React 单页应用的路由重定向
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
                ["npm", "run", "build", "--", f"--outDir={self.dist_dir}"],
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

    def _print_backend_log_tail(self, lines: int = 20, prefix: str = "") -> None:
        """输出后端日志的最后几行"""
        try:
            if self.backend_log_file.exists():
                with open(self.backend_log_file, encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    tail_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                    if tail_lines:
                        console.print(
                            f"[dim]{prefix}--- 后端日志 (最后 {len(tail_lines)} 行) ---[/dim]"
                        )
                        for line in tail_lines:
                            console.print(f"[dim]{prefix}{line.rstrip()}[/dim]")
                        console.print(f"[dim]{prefix}--- 日志结束 ---[/dim]")
        except Exception as e:
            console.print(f"[dim]{prefix}读取日志失败: {e}[/dim]")

    def _print_backend_log_incremental(self, last_pos: int = 0) -> int:
        """增量输出后端日志（从上次位置开始的新内容）

        Returns:
            当前日志文件位置，用于下次调用
        """
        try:
            if not self.backend_log_file.exists():
                return 0

            with open(self.backend_log_file, encoding="utf-8", errors="replace") as f:
                f.seek(last_pos)
                new_content = f.read()
                current_pos = f.tell()

                if new_content.strip():
                    # 输出新增内容，每行添加前缀
                    for line in new_content.splitlines():
                        if line.strip():
                            console.print(f"[dim]   [后端] {line}[/dim]")

                return current_pos
        except Exception as e:
            console.print(f"[dim]   读取后端日志失败: {e}[/dim]")
            return last_pos

    def start_backend(self, port: int | None = None) -> bool:
        """启动后端API服务"""
        # 检查是否已运行
        running_pid = self.is_backend_running()
        if running_pid:
            if running_pid == -1:
                console.print("[green]✅ 检测到后端API已在运行（外部启动），直接复用[/green]")
            else:
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

        # 检查端口是否被占用（可能是僵尸进程或其他服务）
        if self._is_port_in_use(backend_port):
            console.print(f"[yellow]⚠️  端口 {backend_port} 被占用，尝试释放...[/yellow]")
            self._kill_process_on_port(backend_port)
            # 等待端口释放
            import time

            for _ in range(5):
                time.sleep(1)
                if not self._is_port_in_use(backend_port):
                    console.print(f"[green]✅ 端口 {backend_port} 已释放[/green]")
                    break
            else:
                console.print(f"[red]❌ 无法释放端口 {backend_port}，请手动检查[/red]")
                return False

        console.print(f"[blue]正在启动后端API (端口: {backend_port})...[/blue]")

        try:
            # 启动后端进程
            cmd = [sys.executable, str(api_file)]
            log_handle = open(self.backend_log_file, "w")
            process = subprocess.Popen(
                cmd,
                cwd=self.backend_dir,
                stdin=subprocess.DEVNULL,  # 阻止子进程读取 stdin
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )
            # 注意：不关闭 log_handle，让子进程继承并管理它

            # 保存 PID
            with open(self.backend_pid_file, "w") as f:
                f.write(str(process.pid))

            # 等待后端启动
            console.print("[blue]等待后端API启动...[/blue]")
            startup_success = False

            # 创建一个不使用代理的 session（本地服务不需要代理）
            session = requests.Session()
            session.trust_env = False  # 忽略环境变量中的代理设置

            # CI 环境首次启动可能较慢，增加等待时间
            # 设置较长的超时时间，确保服务有足够时间启动
            max_wait = 120  # 最多等待120秒（2分钟）
            last_log_pos = 0  # 记录上次读取日志的位置

            for i in range(max_wait):
                # 首先检查进程是否还存在
                if not psutil.pid_exists(process.pid):
                    console.print("[red]❌ 后端API进程已退出[/red]")
                    # 输出完整日志帮助调试
                    self._print_backend_log_tail(20, prefix="[后端日志] ")
                    return False

                try:
                    # 使用 localhost 而不是 0.0.0.0，避免代理问题
                    health_url = f"http://localhost:{backend_port}/health"
                    response = session.get(health_url, timeout=2)
                    if response.status_code == 200:
                        startup_success = True
                        console.print(f"[green]✅ 后端API启动成功 (耗时 {i + 1} 秒)[/green]")
                        break
                except requests.RequestException:
                    pass

                # 每 5 秒输出一次等待状态和新增的日志
                if (i + 1) % 5 == 0:
                    console.print(f"[blue]   等待后端响应... ({i + 1}/{max_wait}秒)[/blue]")
                    # 实时输出后端日志的新增内容
                    last_log_pos = self._print_backend_log_incremental(last_log_pos)

                time.sleep(1)

            if not startup_success:
                # 最后再检查一次健康状态
                try:
                    response = session.get(f"http://localhost:{backend_port}/health", timeout=5)
                    if response.status_code == 200:
                        console.print("[green]✅ 后端API启动成功[/green]")
                        return True
                except requests.RequestException:
                    pass

                # 检查端口是否在监听（更可靠的检查方式）
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                port_open = sock.connect_ex(("localhost", backend_port)) == 0
                sock.close()

                if port_open:
                    console.print("[yellow]⚠️ 后端API端口已监听，但健康检查未响应[/yellow]")
                    console.print(
                        f"[yellow]   服务可能仍在初始化，请访问 http://localhost:{backend_port}/health 检查[/yellow]"
                    )
                    return True  # 端口已监听，认为启动成功
                elif psutil.pid_exists(process.pid):
                    console.print("[yellow]⚠️ 后端API进程存在但端口未监听[/yellow]")
                    console.print("[yellow]   进程可能启动失败，请检查日志[/yellow]")
                    # 输出后端日志帮助调试
                    console.print("[yellow]   === 后端日志（最后50行）===[/yellow]")
                    self._print_backend_log_tail(lines=50, prefix="   ")
                    return False  # 进程存在但端口未监听，认为启动失败
                else:
                    console.print("[red]❌ 后端API进程已退出[/red]")
                    # 输出后端日志帮助调试
                    console.print("[red]   === 后端日志（最后50行）===[/red]")
                    self._print_backend_log_tail(lines=50, prefix="   ")
                    return False
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

                # 等待进程结束（增加等待时间和更详细的检查）
                console.print("[blue]等待后端API进程停止...[/blue]")
                max_wait = 15  # 增加到15秒
                for i in range(max_wait):
                    if not psutil.pid_exists(running_pid):
                        console.print(f"[green]后端API进程已停止 (等待 {i}秒)[/green]")
                        break
                    time.sleep(1)
                else:
                    # 超时后强制停止
                    console.print("[yellow]进程未在预期时间内停止，强制终止...[/yellow]")
                    if psutil.pid_exists(running_pid):
                        os.killpg(os.getpgid(running_pid), signal.SIGKILL)
                        time.sleep(1)  # 等待强制终止完成

            # 清理 PID 文件
            if self.backend_pid_file.exists():
                self.backend_pid_file.unlink()

            # 再次确认进程已停止
            time.sleep(0.5)  # 额外等待确保进程完全清理
            if psutil.pid_exists(running_pid):
                console.print("[yellow]⚠️ 后端API进程可能仍在运行[/yellow]")

            console.print("[green]✅ 后端API已停止[/green]")
            return True

        except Exception as e:
            console.print(f"[red]后端API停止失败: {e}[/red]")
            return False

    def _ensure_rag_index(self) -> bool:
        """(已弃用) 确保 RAG 索引就绪

        注意：索引构建逻辑已移交 AgentPlanner 动态决策，不再硬编码。
        此方法保留仅作参考，不再自动调用。
        """
        console.print("[dim]ℹ️  RAG 索引构建已移交 AgentPlanner，跳过硬编码检查[/dim]")
        return True

    def start(
        self,
        port: int | None = None,
        host: str | None = None,
        dev: bool = True,
        backend_port: int | None = None,
        auto_gateway: bool = True,  # 新增：是否自动启动 gateway
        auto_install: bool = True,  # 新增：是否自动安装依赖
        auto_build: bool = True,  # 新增：是否自动构建（生产模式）
        skip_confirm: bool = False,  # 新增：跳过确认（用于 restart）
    ) -> bool:
        """启动 Studio（前端和后端）"""
        # 🆕 步骤0: RAG 索引构建已移交 AgentPlanner 动态决策
        self._ensure_rag_index()

        # 检查并启动 Gateway（如果需要 Chat 模式）
        if auto_gateway:
            gateway_pid = self.is_gateway_running()
            if not gateway_pid:
                console.print("[blue]🔍 检测到 Gateway 未运行，正在启动...[/blue]")
                if not self.start_gateway(host=host):
                    console.print("[yellow]⚠️  Gateway 启动失败，Chat 模式可能无法正常使用[/yellow]")
                    console.print(
                        f"[yellow]   您可以稍后手动启动: sage-gateway --host 0.0.0.0 --port {SagePorts.GATEWAY_DEFAULT}[/yellow]"
                    )
            else:
                console.print(f"[green]✅ Gateway 已在运行中 (PID: {gateway_pid})[/green]")

        # 后端 API 已合并进 Gateway，不再单独启动

        # 🆕 智能端口冲突解决 (Smart Port Conflict Resolution)
        # 解决场景：配置文件中保存了旧端口 (如 5173)，但该端口被其他服务占用 (如 Prod 环境)，
        # 而当前代码的默认端口已更新 (如 5179)。此时应自动切换到新默认端口。
        if port is None:
            config = self.load_config()
            config_port = config.get("port", self.default_port)

            # 如果配置端口 != 默认端口 (说明可能是旧配置)
            if config_port != self.default_port:
                # 检查配置端口是否被占用
                if self._is_port_in_use(config_port):
                    # 检查是否是我们的 PID (如果是我们自己，就不算冲突)
                    pid_exists = False
                    if self.pid_file.exists():
                        try:
                            with open(self.pid_file) as f:
                                pid = int(f.read().strip())
                            if psutil.pid_exists(pid):
                                pid_exists = True
                        except Exception:
                            pass

                    if not pid_exists:
                        # 端口被占用且不是我们的 PID -> 冲突
                        # 检查默认端口是否空闲
                        if not self._is_port_in_use(self.default_port):
                            console.print(
                                f"[yellow]⚠️  检测到配置端口 {config_port} 被占用 (可能是旧配置)，自动切换到默认端口 {self.default_port}[/yellow]"
                            )
                            # 更新配置文件
                            config["port"] = self.default_port
                            self.save_config(config)

        # 检查前端是否已运行
        running_pid = self.is_running()
        if running_pid:
            if running_pid == -1:
                console.print("[yellow]⚠️  检测到 Studio 端口被占用 (孤儿进程)[/yellow]")
                console.print("[dim]   请运行 'sage studio stop' 来清理它[/dim]")
            else:
                console.print(f"[yellow]Studio前端已经在运行中 (PID: {running_pid})[/yellow]")
            return True

        if not self.check_dependencies():
            console.print("[red]依赖检查失败[/red]")
            return False

        # 检查并安装 npm 依赖
        node_modules = self.frontend_dir / "node_modules"
        if not node_modules.exists():
            if auto_install:
                console.print("[blue]📦 检测到未安装前端依赖[/blue]")

                # 交互式确认（除非 skip_confirm=True）
                should_install = skip_confirm  # 如果跳过确认，直接安装

                if not skip_confirm:
                    console.print("[yellow]是否立即安装？这可能需要几分钟时间...[/yellow]")
                    try:
                        from rich.prompt import Confirm

                        should_install = Confirm.ask("[cyan]开始安装依赖?[/cyan]", default=True)
                    except ImportError:
                        # 如果没有 rich.prompt，直接安装
                        should_install = True

                if should_install:
                    console.print("[blue]开始安装依赖...[/blue]")
                    if not self.install_dependencies():
                        console.print("[red]依赖安装失败[/red]")
                        return False
                else:
                    console.print("[yellow]跳过安装，请稍后手动运行: sage studio install[/yellow]")
                    return False
            else:
                console.print("[yellow]未安装依赖，请先运行: sage studio install[/yellow]")
                return False

        if not self._ensure_frontend_dependency_integrity(
            auto_fix=auto_install, skip_confirm=skip_confirm
        ):
            console.print("[red]前端依赖损坏，已停止启动流程[/red]")
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
                if not self.dist_dir.exists() or not list(self.dist_dir.glob("*")):
                    if auto_build:
                        console.print("[blue]🏗️  检测到无构建输出[/blue]")

                        # 交互式确认（除非 skip_confirm=True）
                        should_build = skip_confirm  # 如果跳过确认，直接构建

                        if not skip_confirm:
                            console.print("[yellow]是否立即构建？这可能需要几分钟时间...[/yellow]")
                            try:
                                from rich.prompt import Confirm

                                should_build = Confirm.ask("[cyan]开始构建?[/cyan]", default=True)
                            except ImportError:
                                # 如果没有 rich.prompt，直接构建
                                should_build = True

                        if should_build:
                            console.print("[blue]开始构建...[/blue]")
                            if not self.build():
                                console.print("[red]构建失败，无法启动生产模式[/red]")
                                return False
                        else:
                            console.print(
                                "[yellow]跳过构建，请稍后手动运行: sage studio build[/yellow]"
                            )
                            return False
                    else:
                        console.print("[yellow]未构建，请先运行: sage studio build[/yellow]")
                        return False

                console.print("[blue]启动生产服务器（Vite Preview）...[/blue]")

                # 使用 Vite preview，指定从 .sage/studio/dist 读取构建产物
                cmd = [
                    "npm",
                    "run",
                    "preview",
                    "--",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--outDir",
                    str(self.dist_dir),  # 指定构建输出目录
                ]

            # 准备环境变量
            env = os.environ.copy()
            env["npm_config_cache"] = str(self.npm_cache_dir)
            # 传递 Gateway 端口给 Vite (用于 proxy target)
            env["VITE_GATEWAY_PORT"] = str(self.gateway_port)
            # 传递 PORT 给 Vite (虽然 CLI 参数也会覆盖，但保持一致更好)
            env["PORT"] = str(port)

            # 启动进程 - 使用独立的日志文件句柄
            # 关键修复: 使用 with 语句确保文件句柄正确管理，并设置 stdin=DEVNULL
            # 防止 npm/Vite 进程尝试读取终端输入导致卡顿
            log_handle = open(self.log_file, "w")
            process = subprocess.Popen(
                cmd,
                cwd=self.frontend_dir,
                env=env,  # 传递环境变量
                stdin=subprocess.DEVNULL,  # 关键：阻止子进程读取 stdin
                stdout=log_handle,
                stderr=log_handle,
                start_new_session=True,  # 在新会话中运行,避免信号问题
            )
            # 注意：不关闭 log_handle，让子进程继承并管理它
            # 子进程退出时会自动关闭

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

    def stop(self, stop_gateway: bool = False) -> bool:
        """停止 Studio（前端）

        Args:
            stop_gateway: 是否同时停止 Gateway（默认不停止，因为可能被其他服务使用）
        """
        frontend_pid = self.is_running()

        stopped_services = []

        # 停止前端
        if frontend_pid and frontend_pid != -1:
            try:
                # 发送终止信号
                os.killpg(os.getpgid(frontend_pid), signal.SIGTERM)

                # 等待进程结束
                for _i in range(10):
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
                spa_server_script = self.studio_cache_dir / "spa_server.py"
                if spa_server_script.exists():
                    spa_server_script.unlink()

                stopped_services.append("前端")
            except Exception as e:
                console.print(f"[red]前端停止失败: {e}[/red]")

        # 补充检查：通过端口清理孤儿进程 (Orphaned Process Cleanup)
        # 即使 PID 文件不存在或已处理，端口可能仍被占用 (如 frontend_pid == -1 或僵尸进程)
        config = self.load_config()
        port = config.get("port", self.default_port)
        if self._is_port_in_use(port):
            console.print(f"[yellow]检测到端口 {port} 仍被占用，尝试清理孤儿进程...[/yellow]")
            if self._kill_process_on_port(port):
                stopped_services.append(f"前端(端口{port})")
                # 再次确保 PID 文件被清理
                if self.pid_file.exists():
                    self.pid_file.unlink()

        # 后端已合并到 Gateway，不需要单独停止

        # 可选：停止 Gateway
        if stop_gateway:
            gateway_pid = self.is_gateway_running()
            if gateway_pid and gateway_pid != -1:
                if self.stop_gateway():
                    stopped_services.append("Gateway")

        if stopped_services:
            console.print(f"[green]Studio {' 和 '.join(stopped_services)} 已停止[/green]")
            return True
        else:
            console.print("[yellow]Studio 未运行或停止失败[/yellow]")
            return False

    def clean_frontend_cache(self) -> bool:
        """清理前端构建缓存

        清理以下目录以确保使用最新代码：
        - dist/ (构建产物)
        - .vite/ (Vite 缓存)
        - node_modules/.vite/ (Vite 节点缓存)

        Returns:
            bool: 是否成功清理
        """
        import shutil

        cleaned_dirs = []
        errors = []

        # 定义要清理的目录（相对于 frontend_dir）
        cache_dirs = [
            self.frontend_dir / "dist",
            self.frontend_dir / ".vite",
            self.frontend_dir / "node_modules" / ".vite",
        ]

        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    cleaned_dirs.append(cache_dir.name)
                    console.print(
                        f"[green]  ✓ 清理: {cache_dir.relative_to(self.frontend_dir)}[/green]"
                    )
                except Exception as e:
                    errors.append(f"{cache_dir.name}: {e}")
                    console.print(f"[yellow]  ⚠ 清理失败: {cache_dir.name} - {e}[/yellow]")

        if cleaned_dirs:
            console.print(f"[green]✅ 已清理 {len(cleaned_dirs)} 个缓存目录[/green]")
            return True
        elif errors:
            console.print("[red]❌ 清理过程中出现错误[/red]")
            return False
        else:
            console.print("[blue]ℹ️  未发现需要清理的缓存[/blue]")
            return False

    def clean(self) -> bool:
        """清理 Studio 缓存和临时文件（兼容旧命令）

        这是 clean_frontend_cache 的别名，用于命令行接口。
        """
        return self.clean_frontend_cache()

    def status(self):
        """显示状态"""
        frontend_pid = self.is_running()
        gateway_pid = self.is_gateway_running()
        config = self.load_config()

        # 创建前端状态表格
        frontend_table = Table(title="SAGE Studio 前端状态")
        frontend_table.add_column("属性", style="cyan", width=12)
        frontend_table.add_column("值", style="white")

        if frontend_pid:
            if frontend_pid == -1:
                frontend_table.add_row("状态", "[yellow]运行中（PID未知）[/yellow]")
            else:
                try:
                    process = psutil.Process(frontend_pid)
                    frontend_table.add_row("状态", "[green]运行中[/green]")
                    frontend_table.add_row("PID", str(frontend_pid))
                    frontend_table.add_row(
                        "启动时间",
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(process.create_time())),
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

        # 创建 Gateway 状态表格（后端 API 已合并到 Gateway）
        gateway_table = Table(title="SAGE Gateway 状态")
        gateway_table.add_column("属性", style="cyan", width=12)
        gateway_table.add_column("值", style="white")

        if gateway_pid:
            if gateway_pid == -1:
                gateway_table.add_row("状态", "[yellow]运行中（PID未知）[/yellow]")
            else:
                gateway_table.add_row("状态", "[green]运行中[/green]")
                gateway_table.add_row("PID", str(gateway_pid))
            gateway_table.add_row("端口", str(self.gateway_port))
            gateway_table.add_row("API", f"http://localhost:{self.gateway_port}/v1")
        else:
            gateway_table.add_row("状态", "[red]未运行[/red]")
            gateway_table.add_row("端口", str(self.gateway_port))
            gateway_table.add_row(
                "启动命令", f"sage-gateway --host 0.0.0.0 --port {SagePorts.GATEWAY_DEFAULT}"
            )

        gateway_table.add_row("PID文件", str(self.gateway_pid_file))
        gateway_table.add_row("日志文件", str(self.gateway_log_file))

        console.print(gateway_table)

        # 检查端口是否可访问（不使用代理）
        if frontend_pid:
            try:
                session = requests.Session()
                session.trust_env = False  # 忽略环境代理
                url = f"http://localhost:{config.get('port', self.default_port)}"
                response = session.get(url, timeout=5)
                if response.status_code == 200:
                    console.print(f"[green]✅ 前端服务可访问: {url}[/green]")
                else:
                    console.print(f"[yellow]⚠️ 前端服务响应异常: {response.status_code}[/yellow]")
            except requests.RequestException as e:
                console.print(f"[red]❌ 前端服务不可访问: {e}[/red]")

        # 检查 Gateway 是否可访问（后端 API 通过 Gateway 提供）
        if gateway_pid:
            try:
                session = requests.Session()
                session.trust_env = False  # 忽略环境代理
                gateway_url = f"http://localhost:{self.gateway_port}/health"
                response = session.get(gateway_url, timeout=5)
                if response.status_code == 200:
                    console.print(f"[green]✅ Gateway可访问: {gateway_url}[/green]")
                    console.print(
                        "[dim]   (后端 API 已合并到 Gateway: /api/chat, /api/config 等)[/dim]"
                    )
                else:
                    console.print(f"[yellow]⚠️ Gateway响应异常: {response.status_code}[/yellow]")
            except requests.RequestException as e:
                console.print(f"[red]❌ Gateway不可访问: {e}[/red]")

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
            console.print(f"[blue]跟踪{service_name}日志 (按 Ctrl+C 退出): {log_file}[/blue]")
            try:
                subprocess.run(["tail", "-f", str(log_file)])
            except KeyboardInterrupt:
                console.print(f"\n[blue]停止跟踪{service_name}日志[/blue]")
        else:
            console.print(f"[blue]显示{service_name}日志: {log_file}[/blue]")
            try:
                with open(log_file) as f:
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
