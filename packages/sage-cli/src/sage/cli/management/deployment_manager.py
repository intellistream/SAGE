#!/usr/bin/env python3
"""
SAGE Deployment Manager
处理项目文件部署到远程节点
"""

import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import typer

from .config_manager import get_config_manager


class DeploymentManager:
    """部署管理器"""

    def __init__(self):
        self.config_manager = get_config_manager()

        # 智能检测项目根目录
        self.project_root = self._find_project_root()
        typer.echo(f"🔍 检测到项目根目录: {self.project_root}")

    def _find_project_root(self) -> Path:
        """智能查找项目根目录"""
        current_file = Path(__file__).resolve()

        # 方法1: 从当前文件位置向上查找（开发环境）
        current_path = current_file.parent
        while current_path != current_path.parent:
            if self._is_sage_project_root(current_path):
                return current_path
            current_path = current_path.parent

        # 方法2: 从当前工作目录向上查找
        current_path = Path.cwd()
        while current_path != current_path.parent:
            if self._is_sage_project_root(current_path):
                return current_path
            current_path = current_path.parent

        # 方法3: 检查环境变量
        sage_home = os.environ.get("SAGE_HOME")
        if sage_home:
            sage_path = Path(sage_home)
            if self._is_sage_project_root(sage_path):
                return sage_path

        # 方法4: 在用户主目录下查找常见的项目目录名
        common_project_names = [
            "SAGE",
            "sage",
            "workspace/SAGE",
            "workspace/sage",
            "projects/SAGE",
            "code/SAGE",
        ]
        home_dir = Path.home()

        for project_name in common_project_names:
            project_path = home_dir / project_name
            if self._is_sage_project_root(project_path):
                return project_path

        # 如果都找不到，使用当前工作目录并给出警告
        typer.echo("⚠️  警告: 无法自动检测SAGE项目根目录，使用当前工作目录")
        typer.echo("💡 提示: 请确保在SAGE项目目录下运行，或设置SAGE_HOME环境变量")
        return Path.cwd()

    def _is_sage_project_root(self, path: Path) -> bool:
        """检查路径是否为SAGE项目根目录"""
        if not path.exists():
            return False

        # 检查必需文件 - 使用现在实际存在的标识文件
        required_files = ["quickstart.sh", "README.md"]
        for file_name in required_files:
            if not (path / file_name).exists():
                return False

        # 检查SAGE特有的目录结构
        required_dirs = ["packages", "tools"]
        for dir_name in required_dirs:
            if not (path / dir_name).exists():
                return False

        # 检查packages目录下是否有sage相关包
        packages_dir = path / "packages"
        sage_packages = [
            "sage",
            "sage-common",
            "sage-kernel",
            "sage-libs",
            "sage-middleware",
            "sage-tools",
        ]
        has_sage_package = any((packages_dir / pkg).exists() for pkg in sage_packages)

        return has_sage_package

    def create_deployment_package(self) -> str:
        typer.echo("📦 创建部署包...")
        typer.echo(f"📂 项目根目录: {self.project_root}")

        # 验证项目根目录是否有效
        if not self.project_root.exists():
            raise FileNotFoundError(f"项目根目录不存在: {self.project_root}")

        # 检查关键文件是否存在
        key_files = ["quickstart.sh", "README.md"]
        for file_name in key_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                typer.echo(f"⚠️  关键文件不存在: {file_path}")
                # 列出实际存在的文件供调试
                typer.echo("📋 实际存在的文件:")
                for item in self.project_root.iterdir():
                    if item.is_file():
                        typer.echo(f"   - {item.name}")

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="sage_deploy_")
        package_path = os.path.join(temp_dir, "sage_deployment.tar.gz")

        try:
            with tarfile.open(package_path, "w:gz") as tar:
                # 只添加必要的目录和文件，避免大文件

                # 1. 添加核心工具目录（quickstart.sh 等）
                tools_dir = self.project_root / "tools"
                if tools_dir.exists():
                    typer.echo("📦 添加 tools 目录...")
                    tar.add(tools_dir, arcname="tools")
                experiment_dir = self.project_root / "experiments"
                if experiment_dir.exists():
                    typer.echo("📦 添加 experiments 目录...")
                    tar.add(experiment_dir, arcname="experiments")
                # 2. 添加包源代码（不包含构建产物）
                packages_dir = self.project_root / "packages"
                if packages_dir.exists():
                    typer.echo("📦 添加 packages 源代码...")

                    # 自定义过滤器，排除构建产物和缓存
                    def package_filter(tarinfo):
                        # 排除构建产物和缓存目录
                        exclude_patterns = [
                            "__pycache__",
                            ".pyc",
                            ".pyo",
                            ".so",
                            "build/",
                            "dist/",
                            "*.egg-info/",
                            ".pytest_cache/",
                            ".tox/",
                            "node_modules",  # 排除任何深度的node_modules目录
                            ".git/",
                            ".vscode/",
                            ".idea/",
                        ]

                        for pattern in exclude_patterns:
                            if pattern in tarinfo.name:
                                return None
                        return tarinfo

                    tar.add(packages_dir, arcname="packages", filter=package_filter)

                # 3. 添加安装脚本（精简版）
                scripts_dir = self.project_root / "scripts"
                if scripts_dir.exists():
                    typer.echo("📦 添加关键脚本...")
                    # 只添加必要的脚本文件
                    essential_scripts = [
                        "requirements/",  # 依赖文件
                        "lib/common_utils.sh",
                        "lib/logging.sh",
                        "lib/config.sh",  # 工具脚本
                    ]

                    for script_item in essential_scripts:
                        script_path = scripts_dir / script_item
                        if script_path.exists():
                            tar.add(script_path, arcname=f"scripts/{script_item}")

                # 4. 添加必需的配置文件
                required_files = [
                    "quickstart.sh",
                    "README.md",
                    "LICENSE",
                    "CONTRIBUTING.md",
                ]
                for filename in required_files:
                    file_path = self.project_root / filename
                    if file_path.exists():
                        tar.add(file_path, arcname=filename)
                        typer.echo(f"✅ 已添加文件: {filename}")
                    else:
                        raise FileNotFoundError(f"必需文件不存在: {file_path}")

                # 5. 添加文档目录（如果存在）
                docs_dir = self.project_root / "docs"
                if docs_dir.exists():
                    typer.echo("📦 添加 docs 目录...")

                    # 过滤文档目录，只添加必要文件
                    def docs_filter(tarinfo):
                        # 排除大的构建产物
                        exclude_patterns = [
                            ".git/",
                            "__pycache__/",
                            ".pyc",
                            ".pyo",
                            "node_modules/",
                            ".vscode/",
                            ".idea/",
                            "build/",
                            "dist/",
                        ]

                        for pattern in exclude_patterns:
                            if pattern in tarinfo.name:
                                return None

                        # 限制单个文件大小（10MB）
                        if tarinfo.isfile() and tarinfo.size > 10 * 1024 * 1024:
                            return None

                        return tarinfo

                    tar.add(docs_dir, arcname="docs", filter=docs_filter)
                else:
                    typer.echo("ℹ️  docs 目录不存在，跳过")

                # 6. 添加可选文件（小文件）
                optional_files = ["README.md", "LICENSE"]
                for filename in optional_files:
                    file_path = self.project_root / filename
                    if file_path.exists() and file_path.stat().st_size < 1024 * 1024:  # 小于1MB
                        tar.add(file_path, arcname=filename)
                        typer.echo(f"✅ 已添加文件: {filename}")
                    else:
                        typer.echo(f"ℹ️  跳过大文件或不存在的文件: {filename}")

            # 检查最终包大小
            package_size = os.path.getsize(package_path)
            size_mb = package_size / (1024 * 1024)
            typer.echo(f"✅ 部署包已创建: {package_path}")
            typer.echo(f"📊 包大小: {size_mb:.1f} MB")

            if size_mb > 100:
                typer.echo(f"⚠️  警告: 包大小较大 ({size_mb:.1f} MB)，传输可能较慢")

            return package_path

        except Exception as e:
            typer.echo(f"❌ 创建部署包失败: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def execute_ssh_command_with_progress(
        self, host: str, port: int, command: str, timeout: int = 60, step_name: str = ""
    ) -> bool:
        """执行SSH命令并显示进度"""
        ssh_config = self.config_manager.get_ssh_config()
        ssh_user = ssh_config.get("user", "sage")
        ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))

        typer.echo(f"🔗 连接到 {ssh_user}@{host}:{port}")
        if step_name:
            typer.echo(f"📋 执行步骤: {step_name}")

        ssh_cmd = [
            "ssh",
            "-i",
            ssh_key_path,
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={ssh_config.get('connect_timeout', 30)}",
            "-o",
            "ServerAliveInterval=10",
            "-o",
            "ServerAliveCountMax=6",
            "-o",
            "TCPKeepAlive=yes",
            "-o",
            "BatchMode=yes",  # 非交互模式
            f"{ssh_user}@{host}",
            command,
        ]

        try:
            import threading
            import time

            # 启动进度显示线程
            progress_active = threading.Event()
            progress_active.set()

            def show_progress():
                dots = 0
                start_time = time.time()
                while progress_active.is_set():
                    elapsed = int(time.time() - start_time)
                    progress_str = "." * (dots % 4)
                    typer.echo(
                        f"\r⏳ 执行中{progress_str:<3} (已用时: {elapsed}s/{timeout}s)",
                        nl=False,
                    )
                    dots += 1
                    time.sleep(1)

            progress_thread = threading.Thread(target=show_progress, daemon=True)
            progress_thread.start()

            # 执行SSH命令
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

            # 停止进度显示
            progress_active.clear()
            typer.echo()  # 换行

            # 显示输出
            if result.stdout:
                typer.echo("📤 远程输出:")
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        typer.echo(f"   {line}")

            if result.stderr:
                typer.echo("⚠️  远程错误:")
                for line in result.stderr.strip().split("\n"):
                    if line.strip():
                        typer.echo(f"   {line}")

            if result.returncode == 0:
                typer.echo(f"✅ {step_name}完成" if step_name else "✅ 命令执行成功")
                return True
            else:
                typer.echo(
                    f"❌ {step_name}失败 (返回码: {result.returncode})"
                    if step_name
                    else f"❌ 命令执行失败 (返回码: {result.returncode})"
                )
                return False

        except subprocess.TimeoutExpired:
            progress_active.clear()
            typer.echo()
            typer.echo(
                f"❌ {step_name}超时 ({timeout}s)" if step_name else f"❌ SSH命令超时 ({timeout}s)"
            )
            return False
        except Exception as e:
            progress_active.clear()
            typer.echo()
            typer.echo(f"❌ {step_name}失败: {e}" if step_name else f"❌ SSH命令失败: {e}")
            return False

    def execute_ssh_command(self, host: str, port: int, command: str, timeout: int = 60) -> bool:
        """执行SSH命令（兼容性方法，使用简单输出）"""
        ssh_config = self.config_manager.get_ssh_config()
        ssh_user = ssh_config.get("user", "sage")
        ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))

        ssh_cmd = [
            "ssh",
            "-i",
            ssh_key_path,
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={ssh_config.get('connect_timeout', 10)}",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=10",
            f"{ssh_user}@{host}",
            command,
        ]

        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            if result.stdout:
                typer.echo(result.stdout)
            if result.stderr:
                typer.echo(result.stderr, err=True)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            typer.echo(f"❌ SSH命令超时 ({timeout}s)")
            return False
        except Exception as e:
            typer.echo(f"❌ SSH命令失败: {e}")
            return False

    def transfer_file(self, local_path: str, host: str, port: int, remote_path: str) -> bool:
        """传输文件到远程主机"""
        ssh_config = self.config_manager.get_ssh_config()
        ssh_user = ssh_config.get("user", "sage")
        ssh_key_path = os.path.expanduser(ssh_config.get("key_path", "~/.ssh/id_rsa"))

        typer.echo(f"📤 传输文件到 {ssh_user}@{host}:{port}:{remote_path}")

        try:
            scp_cmd = [
                "scp",
                "-i",
                ssh_key_path,
                "-P",
                str(port),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                f"ConnectTimeout={ssh_config.get('connect_timeout', 10)}",
                local_path,
                f"{ssh_user}@{host}:{remote_path}",
            ]

            result = subprocess.run(scp_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                typer.echo("✅ 文件传输成功")
                return True
            else:
                typer.echo(f"❌ 文件传输失败: {result.stderr}")
                return False

        except Exception as e:
            typer.echo(f"❌ 文件传输失败: {e}")
            return False

    def deploy_to_worker(self, host: str, port: int) -> bool:
        """部署到单个worker节点"""
        typer.echo(f"\n🚀 部署到Worker节点: {host}:{port}")

        try:
            # 1. 创建部署包
            package_path = self.create_deployment_package()

            # 2. 传输部署包
            remote_package_path = "/tmp/sage_deployment.tar.gz"
            if not self.transfer_file(package_path, host, port, remote_package_path):
                return False

            # 3. 在远程主机上解压和安装
            remote_config = self.config_manager.get_remote_config()
            sage_home = remote_config.get("sage_home", "/home/sage")

            # 构建 quickstart 参数
            quickstart_args = ["--dev", "--yes"]  # 使用开发者安装模式，并跳过确认提示

            # 使用配置中的环境名，如果没有配置则使用 'sage'
            env_name = remote_config.get("conda_env", "sage")
            # quickstart.sh 会通过环境变量获取环境名

            if remote_config.get("force_reinstall"):
                quickstart_args.append("--force")

            # 添加远程部署标志，用于启用非交互模式
            quickstart_env_vars = [
                "SAGE_REMOTE_DEPLOY=true",  # 标识这是远程部署
                "DEBIAN_FRONTEND=noninteractive",
                "CONDA_ALWAYS_YES=true",
                f"SAGE_ENV_NAME={env_name}",
            ]

            quickstart_args_str = " ".join(quickstart_args)
            quickstart_env_str = " ".join(quickstart_env_vars)

            # 分步执行安装，显示详细进度
            typer.echo(f"\n🚀 开始部署SAGE到 {host}:{port}")
            typer.echo("📋 部署计划:")
            typer.echo("   1️⃣ 解压项目文件和环境准备 (预计1-2分钟)")
            typer.echo("   2️⃣ 初始化conda环境 (预计30秒)")
            typer.echo("   3️⃣ 执行SAGE安装 (预计5-10分钟)")
            typer.echo("   4️⃣ 清理临时文件 (预计30秒)")
            typer.echo()

            # 步骤1: 解压和准备 - 简化版本，逐步调试
            typer.echo("1️⃣ 解压项目文件和环境准备...")

            # 先测试最简单的连接
            typer.echo("   - 测试基本SSH连接...")

            # SSH连接诊断
            try:
                typer.echo(f"🔍 开始诊断SSH连接到 {host}:{port}")

                # 测试网络连通性
                typer.echo("⚡ 测试网络连通性...")
                ping_cmd = ["ping", "-c", "1", "-W", "5", host]
                ping_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
                if ping_result.returncode == 0:
                    typer.echo("✅ 网络连通性正常")
                else:
                    typer.echo(f"❌ 网络不通: {ping_result.stderr}")
                    return False

                # 测试SSH端口
                typer.echo(f"🔌 测试SSH端口 {port}...")
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                try:
                    result = sock.connect_ex((host, port))
                    if result == 0:
                        typer.echo(f"✅ SSH端口 {port} 可达")
                    else:
                        typer.echo(f"❌ SSH端口 {port} 不可达")
                        return False
                finally:
                    sock.close()

                typer.echo("🔐 执行SSH命令测试...")

            except Exception as e:
                typer.echo(f"❌ 连接诊断失败: {e}")
                return False

            simple_test = "whoami"  # 更简单的命令，不需要特殊字符

            if not self.execute_ssh_command_with_progress(
                host, port, simple_test, 15, "基本连接测试"
            ):
                typer.echo("❌ SSH基本连接失败，请检查网络和SSH配置")
                return False

            # 备份现有安装
            typer.echo("   - 备份现有安装...")
            backup_cmd = (
                f"set -e\n"
                f"cd {sage_home}\n"
                f"if [ -d 'SAGE' ]; then\n"
                f"    echo '发现现有SAGE目录，进行备份'\n"
                f"    mv SAGE SAGE_backup_$(date +%Y%m%d_%H%M%S)\n"
                f"    echo '备份完成'\n"
                f"else\n"
                f"    echo '无现有SAGE目录'\n"
                f"fi\n"
            )

            if not self.execute_ssh_command_with_progress(host, port, backup_cmd, 30, "备份检查"):
                return False

            # 解压文件
            typer.echo("   - 执行解压...")
            extract_cmd = (
                f"set -e\n"
                f"cd {sage_home}\n"
                f"echo '开始解压到: {sage_home}/SAGE'\n"
                f"mkdir -p SAGE\n"
                f"echo '检查压缩文件是否存在...'\n"
                f"ls -lh {remote_package_path}\n"
                f"echo '开始解压，请稍候...'\n"
                f"tar -xzf {remote_package_path} -C SAGE\n"
                f"echo '解压完成，检查结果...'\n"
                f"cd SAGE\n"
                f"ls -la | head -5\n"
                f"echo '解压步骤完成'\n"
            )

            if not self.execute_ssh_command_with_progress(
                host, port, extract_cmd, 120, "文件解压"
            ):  # 2分钟
                return False

            # 步骤2: 初始化conda环境
            typer.echo("\n2️⃣ 初始化conda环境...")
            conda_init_commands = (
                f"set -e\n"
                f"cd {sage_home}/SAGE\n"
                f"echo '🐍 查找并初始化conda环境...'\n"
                f"CONDA_FOUND=false\n"
                f"for conda_path in \\\n"
                f"    '$HOME/miniconda3/etc/profile.d/conda.sh' \\\n"
                f"    '$HOME/anaconda3/etc/profile.d/conda.sh' \\\n"
                f"    '/opt/conda/etc/profile.d/conda.sh' \\\n"
                f"    '/usr/local/miniconda3/etc/profile.d/conda.sh' \\\n"
                f"    '/usr/local/anaconda3/etc/profile.d/conda.sh'; do\n"
                f'    if [ -f "$conda_path" ]; then\n'
                f'        echo "✅ 找到conda: $conda_path"\n'
                f'        source "$conda_path"\n'
                f"        CONDA_FOUND=true\n"
                f"        break\n"
                f"    fi\n"
                f"done\n"
                f'if [ "$CONDA_FOUND" = "false" ]; then\n'
                f"    echo '⚠️  未找到conda，使用系统python3'\n"
                f"fi\n"
                f"echo '✅ 环境初始化完成'\n"
            )

            if not self.execute_ssh_command_with_progress(
                host, port, conda_init_commands, 30, "conda环境初始化"
            ):
                return False

            # 步骤3: 执行安装（增加超时时间）
            typer.echo("\n3️⃣ 执行SAGE安装...")
            typer.echo(f"📦 安装命令: {quickstart_env_str} ./quickstart.sh {quickstart_args_str}")
            typer.echo("⏰ 注意: 这一步可能需要10-20分钟，请耐心等待...")
            typer.echo("🔍 如果长时间无输出，可能在下载或编译大型包（torch, numpy等）")

            install_command = (
                f"set -e\n"
                f"cd {sage_home}/SAGE\n"
                f"echo '📦 开始执行SAGE安装...'\n"
                f"echo '命令: {quickstart_env_str} ./quickstart.sh {quickstart_args_str}'\n"
                f"echo '⏰ 开始时间: $(date)'\n"
                f"# 创建安装进度监控\n"
                f"mkdir -p .sage/logs\n"
                f"touch .sage/logs/progress.log\n"
                f"# 设置conda环境\n"
                f"for conda_path in \\\n"
                f"    '$HOME/miniconda3/etc/profile.d/conda.sh' \\\n"
                f"    '$HOME/anaconda3/etc/profile.d/conda.sh' \\\n"
                f"    '/opt/conda/etc/profile.d/conda.sh' \\\n"
                f"    '/usr/local/miniconda3/etc/profile.d/conda.sh' \\\n"
                f"    '/usr/local/anaconda3/etc/profile.d/conda.sh'; do\n"
                f'    if [ -f "$conda_path" ]; then\n'
                f'        echo "🐍 使用conda: $conda_path"\n'
                f'        source "$conda_path"\n'
                f"        break\n"
                f"    fi\n"
                f"done\n"
                f"# 设置环境变量并执行quickstart脚本\n"
                f"export {quickstart_env_str.replace(' ', ' export ')}\n"
                f"echo '🚀 开始执行quickstart脚本...'\n"
                f"chmod +x ./quickstart.sh\n"
                f"# 使用tee同时输出到终端和日志文件，添加时间戳\n"
                f"(timeout 1200 ./quickstart.sh {quickstart_args_str} 2>&1 | tee >(while IFS= read -r line; do echo \"[$(date +'%H:%M:%S')] $line\"; done > .sage/logs/progress.log)) &\n"
                f"INSTALL_PID=$!\n"
                f"# 监控安装进程，每30秒报告一次状态\n"
                f"while kill -0 $INSTALL_PID 2>/dev/null; do\n"
                f"    sleep 30\n"
                f"    echo \"[$(date +'%H:%M:%S')] 📊 安装进行中，进程ID: $INSTALL_PID\"\n"
                f"    if [ -f .sage/logs/progress.log ]; then\n"
                f"        tail -3 .sage/logs/progress.log | head -1\n"
                f"    fi\n"
                f"done\n"
                f"wait $INSTALL_PID\n"
                f"INSTALL_RESULT=$?\n"
                f"if [ $INSTALL_RESULT -eq 124 ]; then\n"
                f"    echo '❌ quickstart脚本执行超时（1200秒）'\n"
                f"    exit 1\n"
                f"elif [ $INSTALL_RESULT -ne 0 ]; then\n"
                f"    echo '❌ quickstart脚本执行失败，返回码: $INSTALL_RESULT'\n"
                f"    if [ -f .sage/logs/progress.log ]; then\n"
                f"        echo '📋 最后几行日志:'\n"
                f"        tail -10 .sage/logs/progress.log\n"
                f"    fi\n"
                f"    exit 1\n"
                f"fi\n"
                f"echo '✅ SAGE安装完成 - $(date)'\n"
            )

            # 安装步骤使用更长的超时时间（增加到20分钟）
            if not self.execute_ssh_command_with_progress(
                host, port, install_command, 1200, "SAGE安装"
            ):  # 20分钟
                # 安装失败，尝试获取日志信息
                typer.echo("🔍 获取安装失败的详细信息...")
                log_check_cmd = (
                    f"cd {sage_home}/SAGE\n"
                    f"echo '=== 检查安装日志 ==='\n"
                    f"if [ -f .sage/logs/install.log ]; then\n"
                    f"    echo '📋 最后50行安装日志:'\n"
                    f"    tail -50 .sage/logs/install.log\n"
                    f"else\n"
                    f"    echo '❌ 未找到安装日志文件'\n"
                    f"fi\n"
                    f"echo '\\n=== 检查Python环境 ==='\n"
                    f"python3 --version 2>/dev/null || echo '❌ Python3不可用'\n"
                    f"pip3 --version 2>/dev/null || echo '❌ pip3不可用'\n"
                    f"echo '\\n=== 检查磁盘空间 ==='\n"
                    f"df -h . | head -2\n"
                )

                self.execute_ssh_command_with_progress(host, port, log_check_cmd, 60, "日志检查")
                return False

            # 步骤4: 清理和完成
            typer.echo("\n4️⃣ 清理临时文件...")
            cleanup_commands = (
                f"rm -f {remote_package_path}\n"
                f"echo '=================================='\n"
                f"echo '✅ SAGE部署完成在 $(hostname)'\n"
                f"echo '=================================='\n"
            )

            if not self.execute_ssh_command_with_progress(host, port, cleanup_commands, 30, "清理"):
                return False

            # 4. 传输配置文件
            local_config_path = self.config_manager.config_path
            if local_config_path.exists():
                remote_config_dir = "~/.sage"
                remote_config_path = "~/.sage/config.yaml"

                typer.echo(f"📋 传输配置文件: {local_config_path} -> {host}:{remote_config_path}")

                # 创建配置目录
                if not self.execute_ssh_command(host, port, f"mkdir -p {remote_config_dir}"):
                    typer.echo("⚠️  创建远程配置目录失败，但继续...")

                # 传输配置文件
                if not self.transfer_file(str(local_config_path), host, port, remote_config_path):
                    typer.echo("⚠️  配置文件传输失败，但继续...")
                else:
                    typer.echo("✅ 配置文件传输成功")
            else:
                typer.echo(f"⚠️  本地配置文件不存在: {local_config_path}")

            # 5. 清理本地临时文件
            temp_dir = os.path.dirname(package_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            typer.echo(f"✅ Worker节点 {host} 部署成功")
            return True

        except Exception as e:
            typer.echo(f"❌ Worker节点 {host} 部署失败: {e}")
            return False

    def deploy_to_all_workers(self) -> tuple[int, int]:
        """部署到所有worker节点"""
        typer.echo("🚀 开始部署到所有Worker节点...")

        workers = self.config_manager.get_workers_ssh_hosts()
        if not workers:
            typer.echo("❌ 未配置任何worker节点")
            return 0, 0

        success_count = 0
        total_count = len(workers)

        for i, (host, port) in enumerate(workers, 1):
            typer.echo(f"\n📋 部署进度: {i}/{total_count}")
            if self.deploy_to_worker(host, port):
                success_count += 1

        typer.echo(f"\n📊 部署结果: {success_count}/{total_count} 个节点部署成功")
        return success_count, total_count


if __name__ == "__main__":
    # 测试部署管理器
    deployment_manager = DeploymentManager()
    try:
        success, total = deployment_manager.deploy_to_all_workers()
        if success == total:
            typer.echo("✅ 所有节点部署成功！")
        else:
            typer.echo("⚠️  部分节点部署失败")
    except Exception as e:
        typer.echo(f"❌ 部署失败: {e}")
