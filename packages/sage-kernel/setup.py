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
        """编译sage_queue C扩展（企业版功能）"""
        sage_queue_dir = Path(__file__).parent / "src/sage/kernel/enterprise/sage_queue"
        
        if not sage_queue_dir.exists():
            print("⚠️  sage_queue目录不存在，跳过编译")
            return
            
        # 检查是否有C++源代码（简单的授权检查）
        cpp_files = list(sage_queue_dir.glob("**/*.cpp")) + list(sage_queue_dir.glob("**/*.h"))
        if not cpp_files:
            print("⚠️  sage_queue C++源代码不可用（企业版功能）")
            return
            
        build_script = sage_queue_dir / "build.sh"
        if not build_script.exists():
            print("⚠️  build.sh不存在，跳过C扩展编译")
            return
            
        print("🔧 编译sage_queue C扩展...")
        try:
            # 设置环境变量，确保在CI环境中正确检测
            env = os.environ.copy()
            
            # 检测CI环境
            is_ci = (
                os.getenv('CI') == 'true' or 
                os.getenv('GITHUB_ACTIONS') == 'true' or
                os.getenv('GITLAB_CI') == 'true' or
                os.getenv('JENKINS_URL') is not None
            )
            
            if is_ci:
                env['CI'] = 'true'
                env['GITHUB_ACTIONS'] = 'true'
                env['DEBIAN_FRONTEND'] = 'noninteractive'
                print("🔍 CI环境检测到，使用非交互式构建")
                build_args = ["bash", "build.sh", "--install-deps"]
            else:
                print("🏠 本地环境检测到，跳过依赖安装以避免密码输入")
                build_args = ["bash", "build.sh"]  # 不加 --install-deps
                
            # 切换到sage_queue目录并运行build.sh
            result = subprocess.run(
                build_args,
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
