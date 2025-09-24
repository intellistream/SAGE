#!/usr/bin/env python3
"""
SAGE Middleware Package Setup with C Extensions
自动编译C++扩展的安装脚本
"""

import os
import subprocess
import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install


class BuildCExtensions(build_ext):
    """自定义C扩展编译命令"""

    def run(self):
        """编译C扩展"""
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            print("⏭️ 跳过C扩展编译（SAGE_SKIP_C_EXTENSIONS=1）")
        else:
            # 在所有模式下尝试构建需要的扩展，失败不阻断安装
            self.build_sage_db()
            self.build_sage_flow()
        super().run()

    def build_sage_db(self):
        """编译sage_db C扩展"""
        sage_db_dir = Path(__file__).parent / "src/sage/middleware/components/sage_db"

        if not sage_db_dir.exists():
            print("⚠️  sage_db目录不存在，跳过编译")
            return

        build_script = sage_db_dir / "build.sh"
        if not build_script.exists():
            print("⚠️  build.sh不存在，跳过C扩展编译")
            return

        print("🔧 编译sage_db C扩展...")
        try:
            # 切换到sage_db目录并运行build.sh
            result = subprocess.run(
                ["bash", "build.sh", "--install-deps"],
                cwd=sage_db_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ sage_db C扩展编译成功")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_db C扩展编译失败: {e}")
            print(f"错误输出: {e.stderr}")
            # C扩展编译失败不应该阻止安装
            print("⚠️  继续安装Python部分（C扩展将不可用）")
        except Exception as e:
            print(f"❌ 编译过程出错: {e}")
            print("⚠️  继续安装Python部分（C扩展将不可用）")

    def build_sage_flow(self):
        """编译 sage_flow 组件（可能包含C/C++/Python扩展）"""
        sage_flow_dir = (
            Path(__file__).parent / "src/sage/middleware/components/sage_flow"
        )

        if not sage_flow_dir.exists():
            print("⚠️  sage_flow 目录不存在，跳过构建")
            return

        # 如果是子模块但未初始化，目录可能为空
        try:
            if not any(sage_flow_dir.iterdir()):
                print("ℹ️ 检测到 sage_flow 目录为空，可能是未初始化的子模块，跳过构建")
                return
        except Exception:
            # 目录不可读，直接跳过
            return

        build_script = sage_flow_dir / "build.sh"
        if not build_script.exists():
            print("ℹ️ 未找到 sage_flow/build.sh，可能不需要本地构建，跳过")
            return

        print("🔧 编译 sage_flow 组件...")
        try:
            result = subprocess.run(
                ["bash", "build.sh", "--install-deps"],
                cwd=sage_flow_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ sage_flow 构建成功")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_flow 构建失败: {e}")
            print(f"错误输出: {e.stderr}")
            print("⚠️  继续安装Python部分（sage_flow 相关示例可能不可用）")
        except Exception as e:
            print(f"❌ 构建过程出错: {e}")
            print("⚠️  继续安装Python部分（sage_flow 相关示例可能不可用）")


class CustomInstall(install):
    """自定义安装命令"""

    def run(self):
        # 在生产安装模式下编译C扩展
        print("🔧 生产安装模式：编译C扩展...")
        self.run_command("build_ext")
        # 然后安装
        super().run()


class CustomDevelop(develop):
    """自定义开发安装命令"""

    def run(self):
        # 开发模式下默认也尝试构建C扩展（与生产一致），可通过环境变量关闭
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            print("⏭️ 开发模式：跳过C扩展编译（SAGE_SKIP_C_EXTENSIONS=1）")
        else:
            print("🔧 开发模式：编译C扩展（可通过 SAGE_SKIP_C_EXTENSIONS=1 跳过）")
            self.run_command("build_ext")
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_ext": BuildCExtensions,
            "install": CustomInstall,
            "develop": CustomDevelop,
        }
    )
