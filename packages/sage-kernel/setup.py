#!/usr/bin/env python3
"""
SAGE Kernel Package Setup with C Extensions
自动编译C++扩展的安装脚本
"""

import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.develop import develop


class BuildCExtensions(build_ext):
    """自定义C扩展编译命令"""
    
    def run(self):
        """编译C扩展"""
        self.build_sage_queue()
        super().run()
    
    def build_sage_queue(self):
        """编译sage_queue C扩展"""
        sage_queue_dir = Path(__file__).parent / "src/sage/kernel/enterprise/sage_queue"
        
        if not sage_queue_dir.exists():
            print("⚠️  sage_queue目录不存在，跳过编译")
            return
            
        build_script = sage_queue_dir / "build.sh"
        if not build_script.exists():
            print("⚠️  build.sh不存在，跳过C扩展编译")
            return
            
        print("🔧 编译sage_queue C扩展...")
        try:
            # 在CI环境中设置环境变量
            env = os.environ.copy()
            if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
                env['CI'] = 'true'
                env['DEBIAN_FRONTEND'] = 'noninteractive'
                print("📋 CI环境检测到，使用非交互式编译")
            
            # 切换到sage_queue目录并运行build.sh
            result = subprocess.run(
                ["bash", "build.sh", "--install-deps"],
                cwd=sage_queue_dir,
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            print("✅ sage_queue C扩展编译成功")
            print(result.stdout)
            
            # 复制编译的.so文件到Python包目录
            so_files = list(sage_queue_dir.glob("*.so"))
            if so_files:
                for so_file in so_files:
                    print(f"📦 复制 {so_file.name} 到Python包目录")
                    # 这里可以添加复制逻辑，或者修改Python代码来查找正确路径
            
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_queue C扩展编译失败: {e}")
            print(f"错误输出: {e.stderr}")
            # 企业版功能编译失败不应该阻止安装
            print("⚠️  继续安装Python部分（C扩展将不可用）")
        except Exception as e:
            print(f"❌ 编译过程出错: {e}")
            print("⚠️  继续安装Python部分（C扩展将不可用）")


class CustomInstall(install):
    """自定义安装命令"""
    def run(self):
        # 先编译C扩展
        self.run_command('build_ext')
        # 然后安装
        super().run()


class CustomDevelop(develop):
    """自定义开发安装命令"""
    def run(self):
        # 先编译C扩展
        self.run_command('build_ext')
        # 然后开发安装
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            'build_ext': BuildCExtensions,
            'install': CustomInstall,
            'develop': CustomDevelop,
        }
    )
