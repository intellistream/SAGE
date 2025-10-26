#!/usr/bin/env python3
"""
SAGE Middleware Package Setup with Fallback Strategy
改进的安装脚本，支持优雅降级
"""

import os
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install


class RobustBuildExtensions(build_ext):
    """健壮的C扩展编译命令，支持优雅降级"""

    def run(self):
        """编译C扩展，失败时提供清晰的提示"""
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            print("⏭️ 跳过C扩展编译（SAGE_SKIP_C_EXTENSIONS=1）")
            return

        success_count = 0
        total_extensions = 2

        print("🔧 开始编译 SAGE C++ 扩展...")
        print("ℹ️  如果编译失败，SAGE 核心功能仍然可用，但某些高性能特性将不可用")

        # 检查构建依赖
        if not self._check_build_dependencies():
            print("⚠️  缺少构建依赖，跳过C扩展编译")
            print("💡 安装提示：sudo apt-get install build-essential cmake 或 brew install cmake")
            self._create_stub_modules()
            return

        # 尝试编译 sage_db
        if self.build_sage_db():
            success_count += 1

        # 尝试编译 sage_flow
        if self.build_sage_flow():
            success_count += 1

        # 报告结果
        if success_count == total_extensions:
            print(f"✅ 所有 C++ 扩展编译成功 ({success_count}/{total_extensions})")
        elif success_count > 0:
            print(f"⚠️  部分 C++ 扩展编译成功 ({success_count}/{total_extensions})")
        else:
            print("❌ C++ 扩展编译失败，使用纯Python实现")
            self._create_stub_modules()

        super().run()

    def _check_build_dependencies(self):
        """检查构建依赖是否可用"""
        try:
            # 检查基本构建工具
            subprocess.run(["cmake", "--version"], capture_output=True, check=True)
            subprocess.run(["make", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _create_stub_modules(self):
        """创建存根模块，避免导入错误"""
        print("🔧 创建C扩展存根模块...")

        # sage_db存根
        sage_db_python = Path(__file__).parent / "src/sage/middleware/components/sage_db/python"
        sage_db_python.mkdir(parents=True, exist_ok=True)

        if not (sage_db_python / "_sage_db.py").exists():
            stub_content = '''"""
SAGE DB 存根模块
当C++扩展不可用时提供基本功能
"""

class SageDbStub:
    """SAGE DB存根类"""
    def __init__(self):
        raise ImportError(
            "SAGE DB C++扩展不可用。请安装构建依赖：\\n"
            "Ubuntu/Debian: sudo apt-get install build-essential cmake\\n"
            "macOS: brew install cmake\\n"
            "然后重新安装：pip install --force-reinstall isage-middleware"
        )

# 兼容性导出
SageDb = SageDbStub
'''
            (sage_db_python / "_sage_db.py").write_text(stub_content)

        # sage_flow存根
        sage_flow_python = Path(__file__).parent / "src/sage/middleware/components/sage_flow/python"
        sage_flow_python.mkdir(parents=True, exist_ok=True)

        if not (sage_flow_python / "_sage_flow.py").exists():
            stub_content = '''"""
SAGE Flow 存根模块
当C++扩展不可用时提供基本功能
"""

class SageFlowStub:
    """SAGE Flow存根类"""
    def __init__(self):
        raise ImportError(
            "SAGE Flow C++扩展不可用。请安装构建依赖：\\n"
            "Ubuntu/Debian: sudo apt-get install build-essential cmake\\n"
            "macOS: brew install cmake\\n"
            "然后重新安装：pip install --force-reinstall isage-middleware"
        )

# 兼容性导出
SageFlow = SageFlowStub
'''
            (sage_flow_python / "_sage_flow.py").write_text(stub_content)

    def build_sage_db(self):
        """编译sage_db C扩展"""
        sage_db_dir = Path(__file__).parent / "src/sage/middleware/components/sage_db"

        if not sage_db_dir.exists():
            print("⚠️  sage_db目录不存在，跳过编译")
            return False

        build_script = sage_db_dir / "build.sh"
        if not build_script.exists():
            print("⚠️  sage_db/build.sh不存在，跳过编译")
            return False

        print("🔧 编译 sage_db C扩展...")
        try:
            subprocess.run(
                ["bash", "build.sh", "--install-deps"],
                cwd=sage_db_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            print("✅ sage_db C扩展编译成功")
            return True
        except subprocess.TimeoutExpired:
            print("❌ sage_db 编译超时")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_db 编译失败: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"错误详情: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ sage_db 编译异常: {e}")
            return False

    def build_sage_flow(self):
        """编译 sage_flow 组件"""
        sage_flow_dir = Path(__file__).parent / "src/sage/middleware/components/sage_flow"

        if not sage_flow_dir.exists():
            print("⚠️  sage_flow 目录不存在，跳过构建")
            return False

        # 检查目录是否为空（未初始化的子模块）
        try:
            if not any(sage_flow_dir.iterdir()):
                print("ℹ️ sage_flow 目录为空，可能是未初始化的子模块，跳过构建")
                return False
        except Exception:
            return False

        build_script = sage_flow_dir / "build.sh"
        if not build_script.exists():
            print("ℹ️ 未找到 sage_flow/build.sh，跳过构建")
            return False

        print("🔧 编译 sage_flow 组件...")
        try:
            subprocess.run(
                ["bash", "build.sh", "--install-deps"],
                cwd=sage_flow_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            print("✅ sage_flow 构建成功")
            return True
        except subprocess.TimeoutExpired:
            print("❌ sage_flow 编译超时")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_flow 构建失败: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"错误详情: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ sage_flow 构建异常: {e}")
            return False


class CustomInstall(install):
    """自定义安装命令"""

    def run(self):
        print("🚀 开始安装 SAGE Middleware...")
        self.run_command("build_ext")
        super().run()
        print("✅ SAGE Middleware 安装完成")


class CustomDevelop(develop):
    """自定义开发安装命令"""

    def run(self):
        print("🚀 开始开发模式安装 SAGE Middleware...")
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") != "1":
            self.run_command("build_ext")
        super().run()
        print("✅ SAGE Middleware 开发环境就绪")


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_ext": RobustBuildExtensions,
            "install": CustomInstall,
            "develop": CustomDevelop,
        }
    )
