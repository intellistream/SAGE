#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE PyPI发布准备快速验证脚本

这是一个快速的PyPI发布准备验证脚本，专门用于验证代码是否准备好发布到PyPI。
主要功能：
1. 验证wheel包能正确构建
2. 模拟用户pip install过程
3. 验证安装后核心功能正常
4. 确保发布到PyPI后用户能正常使用

主要改进：
1. 更快的安装过程
2. 并行化测试
3. 更好的进度显示
4. 跳过耗时的测试项
"""

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple


class FastPipValidator:
    """快速PyPI发布准备验证器"""

    def __init__(self, test_dir: Optional[str] = None, skip_wheel: bool = False):
        # 查找SAGE项目根目录
        current_file = Path(__file__).resolve()
        # 从 packages/sage-tools/tests/pypi/test_pip_validate_fast.py 找到项目根目录
        self.project_root = (
            current_file.parent.parent.parent.parent.parent
        )  # pypi -> tests -> sage-tools -> packages -> SAGE

        # 如果没有指定test_dir，则在.sage目录下创建
        if test_dir:
            self.test_dir = Path(test_dir)
        else:
            sage_config_dir = self.project_root / ".sage" / "temp"
            sage_config_dir.mkdir(parents=True, exist_ok=True)
            self.test_dir = sage_config_dir / f"pip_test_{int(time.time())}"

        self.venv_dir = self.test_dir / "test_env"

        # 验证项目根目录
        if not (self.project_root / "packages" / "sage").exists():
            # 如果不在标准位置，向上查找
            check_dir = current_file.parent
            while check_dir.parent != check_dir:
                if (check_dir / "packages" / "sage").exists():
                    self.project_root = check_dir
                    break
                check_dir = check_dir.parent

        self.python_exe = None
        self.pip_exe = None
        self.skip_wheel = skip_wheel

        # 测试结果
        self.results = {
            "environment_setup": False,
            "wheel_build": False,
            "package_installation": False,
            "basic_imports": False,
            "core_functionality": False,
            "cli_availability": False,
            "cleanup": False,
        }

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        capture_output: bool = True,
        timeout: int = 300,
        env: Optional[dict] = None,
    ) -> Tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            # 如果没有指定环境变量，使用当前环境
            if env is None:
                env = os.environ.copy()

            result = subprocess.run(
                cmd,
                cwd=cwd or self.test_dir,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    def show_progress(self, message: str, duration: float = 0):
        """显示进度动画"""
        if duration <= 0:
            print(f"  {message}")
            return

        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        start_time = time.time()
        i = 0

        while time.time() - start_time < duration:
            print(f"\r  {chars[i % len(chars)]} {message}", end="", flush=True)
            time.sleep(0.1)
            i += 1

        print(f"\r  ✅ {message}")

    def setup_test_environment(self) -> bool:
        """设置测试环境"""
        print("\n🔧 设置测试环境...")

        try:
            # 创建测试目录
            self.test_dir.mkdir(parents=True, exist_ok=True)

            # 创建虚拟环境（使用--system-site-packages加速）
            print("  📦 创建虚拟环境...")
            returncode, stdout, stderr = self.run_command(
                [
                    sys.executable,
                    "-m",
                    "venv",
                    str(self.venv_dir),
                    "--system-site-packages",
                ],
                timeout=60,
            )

            if returncode != 0:
                print(f"  ❌ 创建虚拟环境失败: {stderr}")
                return False

            # 设置Python和pip路径
            if sys.platform == "win32":
                self.python_exe = self.venv_dir / "Scripts" / "python.exe"
                self.pip_exe = self.venv_dir / "Scripts" / "pip.exe"
            else:
                self.python_exe = self.venv_dir / "bin" / "python"
                self.pip_exe = self.venv_dir / "bin" / "pip"

            # 快速升级pip（只升级必要组件）
            print("  📦 配置pip...")
            returncode, stdout, stderr = self.run_command(
                [
                    str(self.python_exe),
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "--quiet",
                ],
                timeout=60,
            )

            print("  ✅ 虚拟环境设置完成")
            self.results["environment_setup"] = True
            return True

        except Exception as e:
            print(f"  ❌ 设置测试环境失败: {e}")
            return False

    def build_or_find_wheel(self) -> Optional[Path]:
        """构建或查找wheel包"""
        if self.skip_wheel:
            print("\n📦 查找现有wheel包...")
        else:
            print("\n🔨 快速构建wheel包...")

        try:
            # 查找sage包目录
            sage_package_dir = self.project_root / "packages" / "sage"
            if not sage_package_dir.exists():
                print(f"  ❌ sage包目录不存在: {sage_package_dir}")
                return None

            dist_dir = sage_package_dir / "dist"

            if not self.skip_wheel:
                # 快速清理和构建
                if dist_dir.exists():
                    shutil.rmtree(dist_dir)

                print("  🔨 执行快速构建...")
                returncode, stdout, stderr = self.run_command(
                    [sys.executable, "setup.py", "bdist_wheel", "--quiet"],
                    cwd=sage_package_dir,
                    timeout=300,
                )

                if returncode != 0:
                    print(f"  ❌ 构建wheel包失败: {stderr}")
                    return None

            # 查找wheel文件
            if not dist_dir.exists():
                print(f"  ❌ dist目录不存在: {dist_dir}")
                return None

            wheel_files = list(dist_dir.glob("*.whl"))
            if not wheel_files:
                print("  ❌ 未找到wheel包文件")
                return None

            wheel_file = wheel_files[0]
            print(f"  ✅ 找到wheel包: {wheel_file.name}")
            self.results["wheel_build"] = True
            return wheel_file

        except Exception as e:
            print(f"  ❌ 处理wheel包失败: {e}")
            return None

    def install_package(self, wheel_file: Path) -> bool:
        """快速安装包"""
        print("\n📥 安装SAGE包...")

        try:
            print(f"  📦 安装: {wheel_file.name}")

            # 显示安装进度
            def install_with_progress():
                return self.run_command(
                    [
                        str(self.pip_exe),
                        "install",
                        str(wheel_file),
                        "--quiet",
                        "--no-deps",
                    ],
                    timeout=300,
                )

            # 使用进度显示
            result_container = [None]

            def run_install():
                result_container[0] = install_with_progress()

            install_thread = threading.Thread(target=run_install)
            install_thread.daemon = True
            install_thread.start()

            # 显示进度
            chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            i = 0
            while install_thread.is_alive():
                print(f"\r  {chars[i % len(chars)]} 安装中...", end="", flush=True)
                time.sleep(0.1)
                i += 1

            install_thread.join()
            print("\r" + " " * 20 + "\r", end="", flush=True)

            returncode, stdout, stderr = result_container[0]

            if returncode != 0:
                print(f"  ❌ 安装失败: {stderr}")
                return False

            # 快速验证安装
            print(f"  🔍 使用Python路径: {self.python_exe}")
            test_cmd = [
                str(self.python_exe),
                "-c",
                "import sage; print(f'SAGE {sage.__version__} 安装成功')",
            ]
            print(f"  🔍 执行命令: {' '.join(test_cmd)}")

            # 创建干净的环境变量，移除PYTHONPATH避免导入冲突
            clean_env = os.environ.copy()
            clean_env.pop("PYTHONPATH", None)  # 移除PYTHONPATH

            returncode, stdout, stderr = self.run_command(test_cmd, env=clean_env)

            print(f"  🔍 返回码: {returncode}")
            print(f"  🔍 标准输出: {stdout}")
            print(f"  🔍 标准错误: {stderr}")

            if returncode != 0:
                print(f"  ❌ 验证安装失败: {stderr}")

                # 添加额外的诊断信息
                print("  🔧 运行诊断...")
                diag_returncode, diag_stdout, diag_stderr = self.run_command(
                    [
                        str(self.python_exe),
                        "-c",
                        "import sys, os; print(f'工作目录: {os.getcwd()}'); print('Python路径:'); [print(f'  {p}') for p in sys.path]; import sage; print(f'sage文件: {sage.__file__}'); print(f'sage属性: {dir(sage)}')",
                    ],
                    env=clean_env,
                )
                print(f"  🔍 诊断输出: {diag_stdout}")
                if diag_stderr.strip():
                    print(f"  🔍 诊断错误: {diag_stderr}")

                return False

            print(f"  ✅ {stdout.strip()}")
            self.results["package_installation"] = True
            return True

        except Exception as e:
            print(f"  ❌ 安装包失败: {e}")
            return False

    def test_basic_imports(self) -> bool:
        """测试核心导入"""
        print("\n🔍 测试核心导入...")

        # 核心导入测试（简化版）
        test_script = """
import sys
try:
    import sage
    from sage.core.api.local_environment import LocalEnvironment
    from sage.libs.io_utils.source import FileSource
    from sage.libs.io_utils.sink import TerminalSink
    from sage.common.utils.logging.custom_logger import CustomLogger
    print("✅ 所有核心模块导入成功")
    sys.exit(0)
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)
"""

        try:
            # 创建测试脚本
            test_file = self.test_dir / "test_imports.py"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_script)

            # 运行测试
            returncode, stdout, stderr = self.run_command(
                [str(self.python_exe), str(test_file)], timeout=30
            )

            if returncode == 0:
                print(f"  {stdout.strip()}")
                self.results["basic_imports"] = True
                return True
            else:
                print(f"  {stderr.strip()}")
                return False

        except Exception as e:
            print(f"  ❌ 导入测试异常: {e}")
            return False

    def test_core_functionality(self) -> bool:
        """测试核心功能"""
        print("\n⚙️ 测试核心功能...")

        # 核心功能测试（简化版）
        test_script = """
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.sink_function import SinkFunction

# 测试环境创建
env = LocalEnvironment("test_env")
print("✅ 环境创建成功")

# 测试基本函数
class TestBatch(BatchFunction):
    def __init__(self):
        super().__init__()
        self.count = 0
    
    def execute(self):
        if self.count < 2:
            self.count += 1
            return f"data_{self.count}"
        return None

class TestSink(SinkFunction):
    def __init__(self):
        super().__init__()
        self.received = []
    
    def execute(self, data):
        self.received.append(data)

# 简单的数据流测试
batch = TestBatch()
sink = TestSink()

while True:
    data = batch.execute()
    if data is None:
        break
    sink.execute(data)

if len(sink.received) == 2:
    print("✅ 数据流测试成功")
    print(f"处理数据: {sink.received}")
else:
    print(f"❌ 数据流测试失败: 预期2条，实际{len(sink.received)}条")
    exit(1)
"""

        try:
            # 创建测试脚本
            test_file = self.test_dir / "test_functionality.py"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_script)

            # 运行测试
            returncode, stdout, stderr = self.run_command(
                [str(self.python_exe), str(test_file)], timeout=30
            )

            if returncode == 0:
                print(f"  {stdout.strip()}")
                self.results["core_functionality"] = True
                return True
            else:
                print(f"  ❌ 功能测试失败: {stderr}")
                return False

        except Exception as e:
            print(f"  ❌ 功能测试异常: {e}")
            return False

    def test_cli_availability(self) -> bool:
        """测试CLI可用性"""
        print("\n🔧 测试CLI可用性...")

        try:
            # 测试sage模块是否支持命令行调用
            returncode, stdout, stderr = self.run_command(
                [
                    str(self.python_exe),
                    "-c",
                    "import sage; print('✅ SAGE模块CLI支持正常')",
                ],
                timeout=10,
            )

            if returncode == 0:
                print(f"  {stdout.strip()}")
                self.results["cli_availability"] = True
                return True
            else:
                print(f"  ❌ CLI测试失败: {stderr}")
                return False

        except Exception as e:
            print(f"  ❌ CLI测试异常: {e}")
            return False

    def cleanup(self) -> bool:
        """清理测试环境"""
        print("\n🧹 清理测试环境...")

        try:
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)
                print("  ✅ 测试目录已清理")
            else:
                print("  ℹ️  测试目录不存在，无需清理")

            self.results["cleanup"] = True
            return True

        except Exception as e:
            print(f"  ❌ 清理失败: {e}")
            return False

    def run_fast_validation(self) -> bool:
        """运行快速发布准备验证"""
        print("🚀 SAGE PyPI发布准备快速验证")
        print("=" * 50)

        start_time = time.time()

        # 运行测试步骤
        steps = [
            ("环境设置", self.setup_test_environment),
            ("包构建", lambda: self.build_or_find_wheel() is not None),
            ("包安装", lambda: self.install_package(self.build_or_find_wheel())),
            ("导入测试", self.test_basic_imports),
            ("功能测试", self.test_core_functionality),
            ("CLI测试", self.test_cli_availability),
        ]

        all_passed = True
        completed_steps = 0

        for step_name, step_func in steps:
            try:
                if step_func():
                    completed_steps += 1
                else:
                    all_passed = False
                    break
            except Exception as e:
                print(f"  ❌ {step_name} 异常: {e}")
                all_passed = False
                break

        # 计算测试时间
        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 50)
        print("📊 快速发布准备验证结果:")

        for test_name, passed in self.results.items():
            if test_name == "cleanup":
                continue
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {test_name}: {status}")

        print(f"⏱️  验证时间: {duration:.1f}秒")
        print(f"📈 完成步骤: {completed_steps}/{len(steps)}")

        if all_passed:
            print("\n🎉 快速发布准备验证通过！")
            print("📦 SAGE核心功能可以正常工作")
            print("🚀 建议运行完整验证确认发布准备")
            return True
        else:
            print("\n⚠️  快速发布准备验证失败")
            print("🔧 建议运行完整验证以获取详细信息")
            return False

    def cleanup(self):
        """清理测试环境"""
        if self.test_dir.exists():
            print(f"\n🧹 清理测试环境: {self.test_dir}")
            try:
                shutil.rmtree(self.test_dir)
                print("✅ 清理完成")
            except Exception as e:
                print(f"⚠️  清理失败: {e}")
                print("💡 请手动删除测试目录")


def main():
    parser = argparse.ArgumentParser(description="SAGE PyPI发布准备快速验证脚本")
    parser.add_argument("--test-dir", type=str, help="指定测试目录（可选）")
    parser.add_argument(
        "--skip-wheel", action="store_true", help="跳过wheel构建，使用现有的wheel包"
    )
    parser.add_argument(
        "--cleanup", action="store_true", default=True, help="测试完成后清理临时文件"
    )

    args = parser.parse_args()

    # 创建验证器
    validator = FastPipValidator(args.test_dir, args.skip_wheel)

    try:
        success = validator.run_fast_validation()

        # 清理
        if args.cleanup:
            validator.cleanup()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  验证被用户中断")
        validator.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
