"""
SAGE 项目状态检查器

提供全面的项目状态检查功能，包括：
- 包依赖状态
- 安装状态
- 配置状态
- 服务状态
- 开发环境状态
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()


class ProjectStatusChecker:
    """SAGE 项目状态检查器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.packages_dir = self.project_root / "packages"
        # 缓存已安装的包列表，避免重复调用
        self._installed_packages_cache: dict[str, str] | None = None

    def check_all(self, verbose: bool = False, quick: bool = False) -> dict[str, Any]:
        """执行全面的状态检查

        Args:
            verbose: 详细输出
            quick: 快速模式，跳过耗时检查（如依赖和服务检查）
        """
        status_data = {
            "timestamp": self._get_timestamp(),
            "project_root": str(self.project_root),
            "checks": {},
        }

        # 根据模式决定检查项
        if quick:
            checks = [
                ("environment", "环境检查", self._check_environment),
                ("packages", "包状态检查", self._check_packages),
                ("configuration", "配置检查", self._check_configuration),
            ]
        else:
            checks = [
                ("environment", "环境检查", self._check_environment),
                ("packages", "包状态检查", self._check_packages),
                ("dependencies", "依赖检查", self._check_dependencies),
                ("services", "服务状态检查", self._check_services),
                ("configuration", "配置检查", self._check_configuration),
            ]

        for check_name, check_desc, check_func in checks:
            console.print(f"🔍 {check_desc}...")
            try:
                result = check_func()
                status_data["checks"][check_name] = {
                    "status": "success",
                    "data": result,
                }
                if verbose:
                    self._display_check_result(check_desc, result)
            except Exception as e:
                error_msg = str(e)
                status_data["checks"][check_name] = {
                    "status": "error",
                    "error": error_msg,
                }
                console.print(f"❌ {check_desc}失败: {error_msg}")

        return status_data

    def _check_environment(self) -> dict[str, Any]:
        """检查开发环境"""
        env_info = {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd(),
            "sage_home": os.environ.get("SAGE_HOME", "Not set"),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "None"),
            "virtual_env": os.environ.get("VIRTUAL_ENV", "None"),
        }

        # 检查关键环境变量
        env_vars = ["PATH", "PYTHONPATH", "SAGE_HOME"]
        env_info["environment_variables"] = {}  # type: ignore[assignment]
        for var in env_vars:
            env_info["environment_variables"][var] = os.environ.get(var, "Not set")  # type: ignore[index]

        return env_info

    def _check_packages(self) -> dict[str, Any]:
        """检查SAGE包状态"""
        packages_info = {
            "packages_dir_exists": self.packages_dir.exists(),
            "packages": {},
            "summary": {
                "total": 0,
                "installed": 0,
                "importable": 0,
                "has_pyproject": 0,
                "has_tests": 0,
            },
        }

        if not self.packages_dir.exists():
            return packages_info

        # 预加载已安装包列表（只调用一次）
        self._installed_packages_cache = self._get_installed_packages()

        # 扫描packages目录
        for package_dir in self.packages_dir.iterdir():
            if package_dir.is_dir() and package_dir.name.startswith("sage-"):
                package_name = package_dir.name
                package_info = self._check_single_package(package_dir)
                packages_info["packages"][package_name] = package_info

                # 更新统计
                packages_info["summary"]["total"] += 1
                if package_info["installed"]:
                    packages_info["summary"]["installed"] += 1
                if package_info["importable"]:
                    packages_info["summary"]["importable"] += 1
                if package_info["has_pyproject"]:
                    packages_info["summary"]["has_pyproject"] += 1
                if package_info["has_tests"]:
                    packages_info["summary"]["has_tests"] += 1

        return packages_info

    def _check_single_package(self, package_dir: Path) -> dict[str, Any]:
        """检查单个包的状态"""
        info = {
            "path": str(package_dir),
            "has_pyproject": (package_dir / "pyproject.toml").exists(),
            "has_setup_py": (package_dir / "setup.py").exists(),
            "has_src": (package_dir / "src").exists(),
            "has_tests": (package_dir / "tests").exists(),
            "installed": False,
            "importable": False,
        }

        # 检查是否已安装
        try:
            # 读取pyproject.toml获取包名
            pyproject_path = package_dir / "pyproject.toml"
            if pyproject_path.exists():
                package_name = self._get_package_name_from_pyproject(pyproject_path)
                if package_name:
                    # 使用缓存的已安装包列表（避免重复调用）
                    installed_packages = (
                        self._installed_packages_cache
                        if self._installed_packages_cache is not None
                        else self._get_installed_packages()
                    )
                    if package_name in installed_packages:
                        info["installed"] = True
                        info["version"] = installed_packages[package_name]

                    # 检查是否可导入 (尝试导入主模块)
                    try:
                        # 对于isage-*包，尝试导入sage.*模块
                        if package_name.startswith("isage-"):
                            module_name = "sage." + package_name.replace("isage-", "")
                            if package_name == "isage":
                                module_name = "sage"
                        else:
                            module_name = package_name.replace("-", ".")

                        spec = importlib.util.find_spec(module_name)
                        if spec is not None:
                            info["importable"] = True
                            info["import_path"] = spec.origin if spec.origin else "Built-in"
                            info["module_name"] = module_name
                    except ImportError:
                        pass
        except Exception as e:
            info["error"] = str(e)

        return info

    def _check_dependencies(self) -> dict[str, Any]:
        """检查依赖状态"""
        deps_info = {"critical_packages": {}, "import_tests": {}}

        # 检查关键依赖包
        critical_deps = [
            "typer",
            "rich",
            "click",
            "pydantic",
            "pathlib",
            "tomli",  # TOML解析库
            "numpy",
            "pandas",  # 数据处理库（可选）
        ]

        for dep in critical_deps:
            try:
                spec = importlib.util.find_spec(dep)
                if spec is not None:
                    deps_info["critical_packages"][dep] = {
                        "available": True,
                        "path": spec.origin if spec.origin else "Built-in",
                    }
                    # 尝试实际导入
                    try:
                        __import__(dep)
                        deps_info["import_tests"][dep] = "success"
                    except Exception as e:
                        deps_info["import_tests"][dep] = f"import_error: {e}"
                else:
                    deps_info["critical_packages"][dep] = {"available": False}
                    deps_info["import_tests"][dep] = "not_found"
            except Exception as e:
                deps_info["critical_packages"][dep] = {"error": str(e)}
                deps_info["import_tests"][dep] = f"check_error: {e}"

        return deps_info

    def _check_services(self) -> dict[str, Any]:
        """检查相关服务状态"""
        services_info = {
            "flownet": self._check_flownet_status(),
            "jobmanager": self._check_jobmanager_status(),
        }

        return services_info

    def _check_flownet_status(self) -> dict[str, Any]:
        """检查 sageFlownet 运行时状态"""
        try:
            spec = importlib.util.find_spec("sage.flownet")
            if spec is None:
                return {"available": False, "error": "sage.flownet 包未安装"}

            # 使用公开 API 检查运行时单例是否已初始化
            from sage.flownet.runtime.runtime import try_get_runtime

            runtime = try_get_runtime()
            running = runtime is not None
            return {
                "available": True,
                "running": running,
                "output": "Flownet 运行时已初始化" if running else "Flownet 包可用，运行时未启动",
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _check_jobmanager_status(self) -> dict[str, Any]:
        """检查JobManager状态"""
        try:
            # 尝试导入jobmanager模块
            spec = importlib.util.find_spec("sage.dev.cli.commands.jobmanager")
            if spec is None:
                return {"available": False, "error": "JobManager module not found"}

            # 这里可以添加更具体的JobManager状态检查逻辑
            return {"available": True, "status": "module_available"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _check_configuration(self) -> dict[str, Any]:
        """检查配置状态"""
        config_info = {"config_files": {}, "sage_home_status": {}}

        # 检查主要配置文件
        config_files = ["pyproject.toml", "README.md", "_version.py", "quickstart.sh"]

        for config_file in config_files:
            file_path = self.project_root / config_file
            config_info["config_files"][config_file] = {
                "exists": file_path.exists(),
                "path": str(file_path),
                "size": file_path.stat().st_size if file_path.exists() else 0,
            }

        # 检查SAGE_HOME
        sage_home = os.environ.get("SAGE_HOME")
        if sage_home:
            sage_home_path = Path(sage_home)
            config_info["sage_home_status"] = {
                "path": sage_home,
                "exists": sage_home_path.exists(),
                "is_dir": sage_home_path.is_dir() if sage_home_path.exists() else False,
                "logs_dir_exists": (
                    (sage_home_path / "logs").exists() if sage_home_path.exists() else False
                ),
            }
        else:
            config_info["sage_home_status"] = {"configured": False}

        return config_info

    def _display_check_result(self, check_name: str, result: dict[str, Any]):
        """显示检查结果"""
        panel = Panel(
            self._format_result_for_display(result),
            title=f"✅ {check_name}",
            border_style="green",
        )
        console.print(panel)

    def _format_result_for_display(self, result: dict[str, Any]) -> str:
        """格式化结果用于显示"""
        if isinstance(result, dict):
            lines = []

            # 特殊处理包信息
            if "packages" in result and "summary" in result:
                summary = result["summary"]
                lines.append(f"📦 包总数: {summary['total']}")
                lines.append(f"✅ 已安装: {summary['installed']}")
                lines.append(f"📥 可导入: {summary['importable']}")
                lines.append(f"⚙️ 有配置: {summary['has_pyproject']}")
                lines.append(f"🧪 有测试: {summary['has_tests']}")
                return "\n".join(lines)

            # 特殊处理依赖信息
            if "critical_packages" in result and "import_tests" in result:
                critical = result["critical_packages"]
                imports = result["import_tests"]
                available = sum(1 for pkg in critical.values() if pkg.get("available", False))
                successful_imports = sum(1 for test in imports.values() if test == "success")
                lines.append(f"📚 关键依赖: {available}/{len(critical)} 可用")
                lines.append(f"📥 导入测试: {successful_imports}/{len(imports)} 成功")

                # 显示失败的导入
                failed_imports = [name for name, test in imports.items() if test != "success"]
                if failed_imports:
                    lines.append(f"❌ 导入失败: {', '.join(failed_imports[:3])}")
                return "\n".join(lines)

            # 特殊处理服务信息
            if "flownet" in result:
                flownet = result["flownet"]
                if flownet.get("available", False):
                    status = "✅ 运行中" if flownet.get("running") else "⏸ 未启动"
                else:
                    status = "❌ 未安装"
                lines.append(f"⚡ Flownet 运行时: {status}")
                lines.append(
                    f"🔧 JobManager: {'✅ 可用' if result['jobmanager'].get('available') else '❌ 不可用'}"
                )
                return "\n".join(lines)

            # 特殊处理环境信息
            if "python_version" in result:
                lines.append(f"🐍 Python: {result['python_version'].split()[0]}")
                lines.append(f"🏠 工作目录: {result['working_directory']}")
                lines.append(f"🌍 Conda环境: {result.get('conda_env', 'None')}")
                sage_home = result.get("sage_home", "Not set")
                lines.append(
                    f"🏠 SAGE_HOME: {'✅ 已设置' if sage_home != 'Not set' else '❌ 未设置'}"
                )
                return "\n".join(lines)

            # 特殊处理配置信息
            if "config_files" in result:
                config_files = result["config_files"]
                existing_files = [name for name, info in config_files.items() if info.get("exists")]
                lines.append(f"📄 配置文件: {len(existing_files)}/{len(config_files)} 存在")
                sage_home_status = result.get("sage_home_status", {})
                if sage_home_status.get("configured", True):
                    lines.append(
                        f"🏠 SAGE_HOME: {'✅ 配置正确' if sage_home_status.get('exists') else '❌ 路径不存在'}"
                    )
                else:
                    lines.append("🏠 SAGE_HOME: ❌ 未配置")
                return "\n".join(lines)

            # 默认格式化
            for key, value in result.items():
                if isinstance(value, dict):
                    lines.append(f"{key}: {len(value)} 项")
                elif isinstance(value, list):
                    lines.append(f"{key}: {len(value)} 项")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines[:8])  # 限制显示行数
        return str(result)

    def _get_installed_packages(self) -> dict[str, str]:
        """获取已安装的包列表和版本"""
        # 优先使用 importlib.metadata (Python 3.8+)，避免使用已弃用的 pkg_resources
        try:
            import importlib.metadata as metadata

            installed = {}
            for dist in metadata.distributions():
                try:
                    if dist.metadata and "Name" in dist.metadata:
                        installed[dist.metadata["Name"]] = dist.version
                except Exception:
                    # 跳过损坏的包
                    continue
            return installed
        except ImportError:
            # Python < 3.8 回退方案：使用 pkg_resources（带警告抑制）
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                    import pkg_resources

                installed = {}
                for dist in pkg_resources.working_set:
                    installed[dist.project_name] = dist.version
                return installed
            except ImportError:
                pass

        # 最终回退方案：使用pip list
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                import json

                packages = json.loads(result.stdout)
                return {pkg["name"]: pkg["version"] for pkg in packages}
        except Exception:
            pass
        return {}

    def _get_package_name_from_pyproject(self, pyproject_path: Path) -> str | None:
        """从pyproject.toml中获取包名"""
        try:
            # 尝试使用不同的TOML库
            try:
                import tomllib  # Python 3.11+

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                try:
                    import tomli

                    with open(pyproject_path, "rb") as f:
                        data = tomli.load(f)
                except ImportError:
                    # 回退到手动解析
                    with open(pyproject_path) as f:
                        content = f.read()
                        # 简单解析name字段
                        import re

                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        return match.group(1) if match else None

            return data.get("project", {}).get("name")
        except Exception:
            return None

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def generate_status_summary(self, status_data: dict[str, Any]) -> str:
        """生成状态摘要"""
        total_checks = len(status_data["checks"])
        successful_checks = sum(
            1 for check in status_data["checks"].values() if check["status"] == "success"
        )

        summary_lines = [
            "📊 SAGE 项目状态报告",
            f"⏰ 检查时间: {status_data['timestamp']}",
            f"📁 项目路径: {status_data['project_root']}",
            f"✅ 检查项目: {successful_checks}/{total_checks}",
        ]

        if successful_checks == total_checks:
            summary_lines.append("🎉 所有检查项目都通过了!")
        else:
            failed_checks = total_checks - successful_checks
            summary_lines.append(f"⚠️  有 {failed_checks} 个检查项目失败")

        return "\n".join(summary_lines)
