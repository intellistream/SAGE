"""
Example Runner Module

This module provides tools for executing Python example files
and collecting execution results.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from .models import ExampleInfo, ExampleTestResult
from .utils import find_examples_directory, find_project_root


class ExampleRunner:
    """示例执行器"""

    def __init__(self, timeout: int | None = None):
        """初始化 ExampleRunner

        Args:
            timeout: 默认超时时间（秒），None表示使用策略决定

        Raises:
            RuntimeError: 如果找不到项目根目录（开发环境不可用）
        """
        # 优先级：传入参数 > 环境变量 > 默认值（让策略决定）
        if timeout is not None:
            self.timeout = timeout
        else:
            # 如果没有传入timeout，检查环境变量，否则使用默认值让策略决定
            env_timeout = os.environ.get("SAGE_EXAMPLE_TIMEOUT")
            if env_timeout:
                self.timeout = int(env_timeout)
            else:
                # 不设置默认超时，让_get_test_timeout方法从策略中获取
                self.timeout = None

        # 使用新的环境检测工具
        project_root = find_project_root()
        examples_dir = find_examples_directory()

        if project_root is None or examples_dir is None:
            raise RuntimeError(
                "Cannot find SAGE project root directory. "
                "This tool requires a development environment. "
                "Please see the Examples Testing README for setup instructions."
            )

        self.project_root = project_root
        self.examples_root = examples_dir

    def run_example(self, example_info: ExampleInfo) -> ExampleTestResult:
        """运行单个示例

        Args:
            example_info: 示例文件信息

        Returns:
            ExampleTestResult 对象
        """
        start_time = time.time()

        # 检查依赖
        if not self._check_dependencies(example_info.dependencies):
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="skipped",
                execution_time=0,
                output="",
                error="Missing dependencies",
                dependencies_met=False,
            )

        # 检查是否需要用户输入
        if self._requires_user_input(example_info.file_path):
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="skipped",
                execution_time=0,
                output="",
                error="Requires user input",
                requires_user_input=True,
            )

        # 准备环境
        env = self._prepare_environment(example_info)

        # 确定超时时间
        test_timeout = self._get_test_timeout(example_info)

        try:
            # 执行示例
            result = subprocess.run(
                [sys.executable, example_info.file_path],
                capture_output=True,
                text=True,
                timeout=test_timeout,
                cwd=str(self.project_root),
                env=env,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                status = "passed"
                error = None
            else:
                status = "failed"
                error = result.stderr

            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status=status,
                execution_time=execution_time,
                output=result.stdout,
                error=error,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            # 在超时情况下，尝试获取可能的输出
            error_msg = f"Execution timed out after {test_timeout}s"
            if os.environ.get("CI") == "true":
                error_msg += (
                    f"\nFile: {example_info.file_path}"
                    f"\nCategory: {example_info.category}"
                    f"\nEstimated runtime: {example_info.estimated_runtime}"
                )
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="timeout",
                execution_time=execution_time,
                output="",  # 超时情况下没有输出
                error=error_msg,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="failed",
                execution_time=execution_time,
                output="",
                error=str(e),
            )

    def _get_test_timeout(self, example_info: ExampleInfo) -> int:
        """从测试标记中确定超时时间"""
        # 检查是否有自定义超时标记
        for tag in example_info.test_tags:
            if tag.startswith("timeout="):
                try:
                    return int(tag.split("=")[1])
                except (ValueError, IndexError):
                    pass

        # 从类别策略中获取超时
        category = self._get_category_from_tags(example_info.test_tags) or example_info.category

        # 导入策略类
        try:
            from .strategies import ExampleTestStrategies

            strategies = ExampleTestStrategies.get_strategies()
            if category in strategies:
                return strategies[category].timeout
        except ImportError:
            pass

        # 如果策略不可用，使用默认超时
        if self.timeout is not None:
            return self.timeout

        # 最后的默认值
        return 60

    def _get_category_from_tags(self, test_tags: list[str]) -> str | None:
        """从测试标记中提取类别"""
        for tag in test_tags:
            if tag.startswith("category="):
                try:
                    return tag.split("=")[1]
                except IndexError:
                    pass
        return None

    def _check_dependencies(self, dependencies: list[str]) -> bool:
        """检查依赖是否满足"""
        # 包名到导入名的映射
        import_name_map = {
            "pyyaml": "yaml",
            "python-dotenv": "dotenv",
            "kafka-python": "kafka",
            "opencv-python": "cv2",
        }

        for dep in dependencies:
            import_name = import_name_map.get(dep, dep)
            try:
                subprocess.run(
                    [sys.executable, "-c", f"import {import_name}"],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return False
        return True

    def _requires_user_input(self, file_path: str) -> bool:
        """检查是否需要用户输入"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 检查文件是否在测试模式下有特殊处理
            has_test_mode_check = any(
                pattern in content
                for pattern in [
                    'os.getenv("SAGE_TEST_MODE")',
                    'os.getenv("SAGE_EXAMPLES_MODE")',
                    "SAGE_TEST_MODE",
                    "SAGE_EXAMPLES_MODE",
                ]
            )

            # 如果有测试模式检查，即使有 input() 也不算需要用户输入
            if has_test_mode_check:
                return False

            input_indicators = ["input(", "raw_input(", "getpass."]
            return any(indicator in content for indicator in input_indicators)
        except Exception:
            return False

    def _prepare_environment(self, example_info: ExampleInfo) -> dict[str, str]:
        """准备执行环境"""
        env = os.environ.copy()

        # 设置 Python 路径 - 使用动态路径而不是硬编码
        python_path = env.get("PYTHONPATH", "")
        sage_paths_all = [
            str(self.project_root),  # Add project root for examples imports
            str(self.project_root / "packages" / "sage" / "src"),
            str(self.project_root / "packages" / "sage-common" / "src"),
            str(self.project_root / "packages" / "sage-kernel" / "src"),
            str(self.project_root / "packages" / "sage-libs" / "src"),
            str(self.project_root / "packages" / "sage-middleware" / "src"),
            str(self.project_root / "packages" / "sage-tools" / "src"),
        ]

        # 对依赖已编译扩展的示例（如 sage_flow），避免通过源码空目录覆盖已安装的二进制模块
        is_sage_flow_example = "sage_flow" in example_info.file_path or any(
            imp.startswith("sage.middleware.components.sage_flow") for imp in example_info.imports
        )
        if is_sage_flow_example and env.get("SAGE_EXAMPLES_USE_INSTALLED_MIDDLEWARE", "1") != "0":
            # 去掉 middleware/src，让 Python 优先使用 site-packages 中已安装的模块
            mw_src = str(self.project_root / "packages" / "sage-middleware" / "src")
            sage_paths = [p for p in sage_paths_all if p != mw_src]
        else:
            sage_paths = sage_paths_all

        if python_path:
            env["PYTHONPATH"] = ":".join(sage_paths + [python_path])
        else:
            env["PYTHONPATH"] = ":".join(sage_paths)

        # 设置示例特定的环境变量
        env["SAGE_EXAMPLES_MODE"] = "test"
        env["SAGE_TEST_MODE"] = "true"  # 标记为测试模式，用于示例中的条件判断
        env["SAGE_LOG_LEVEL"] = "WARNING"  # 减少日志输出

        # 检查是否需要使用真实API (通过环境变量传递)
        if os.environ.get("SAGE_USE_REAL_API") == "true":
            env["SAGE_USE_REAL_API"] = "true"

        return env
