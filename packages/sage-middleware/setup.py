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
        # 检查是否在开发者模式下，如果是则跳过C扩展编译
        if self.is_develop_mode():
            print(
                "🔧 开发者模式：跳过C扩展编译（使用 sage extensions install 手动安装）"
            )
        else:
            self.build_sage_db()
        super().run()

    def is_develop_mode(self):
        """检查是否在开发者模式下"""
        # 检查环境变量
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            return True

        # 检查命令行参数（通过父命令判断）
        import sys

        for arg in sys.argv:
            if arg in ["develop", "editable", "-e", "--editable"]:
                return True

        return False

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
        # 在开发者模式下跳过C扩展编译
        print("🔧 开发者模式：跳过C扩展编译（使用 sage extensions install 手动安装）")
        # 直接运行开发安装，不调用build_ext
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_ext": BuildCExtensions,
            "install": CustomInstall,
            "develop": CustomDevelop,
        }
    )
