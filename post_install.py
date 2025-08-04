#!/usr/bin/env python3
"""
SAGE Framework 安装后脚本

这个脚本会在 sage-workspace 包安装完成后自动运行，
安装所有必需的子包。
"""

import os
import sys
import subprocess
from pathlib import Path


def post_install():
    """安装后执行的函数"""
    print("\n" + "="*60)
    print("SAGE Framework Monorepo 安装后处理")
    print("="*60)
    
    # 尝试找到 SAGE 源码目录
    # 方法1: 通过环境变量
    sage_root = os.environ.get('SAGE_ROOT')
    
    # 方法2: 通过当前脚本路径
    if not sage_root:
        script_path = Path(__file__).resolve()
        # 寻找包含 packages 目录的父目录
        for parent in script_path.parents:
            if (parent / "packages").exists() and (parent / "pyproject.toml").exists():
                sage_root = str(parent)
                break
    
    # 方法3: 通过已安装包的路径查找
    if not sage_root:
        try:
            # 尝试导入已安装的包
            import importlib.util
            spec = importlib.util.find_spec("sage_workspace")
            if spec and spec.origin:
                pkg_path = Path(spec.origin).parent
                for parent in pkg_path.parents:
                    if (parent / "packages").exists():
                        sage_root = str(parent)
                        break
        except (ImportError, AttributeError):
            pass
    
    if not sage_root:
        print("❌ 无法找到 SAGE 源码目录")
        print("请手动运行以下命令安装子包:")
        print("  cd <SAGE源码目录>")
        print("  ./install_packages.sh")
        return False
    
    sage_root = Path(sage_root)
    print(f"✓ 找到 SAGE 源码目录: {sage_root}")
    
    # 检查安装脚本是否存在
    install_script = sage_root / "install_packages.sh"
    setup_script = sage_root / "setup.py"
    
    if install_script.exists():
        print("正在运行安装脚本...")
        try:
            result = subprocess.run([
                "bash", str(install_script)
            ], cwd=str(sage_root), check=True, capture_output=True, text=True)
            print("✓ 子包安装成功!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装脚本执行失败: {e}")
            print("请手动运行: ./install_packages.sh")
            return False
    
    elif setup_script.exists():
        print("正在通过 setup.py 安装子包...")
        try:
            result = subprocess.run([
                sys.executable, str(setup_script)
            ], cwd=str(sage_root), check=True, capture_output=True, text=True)
            print("✓ 子包安装成功!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ setup.py 执行失败: {e}")
            return False
    
    else:
        print("❌ 未找到安装脚本")
        print("请手动安装子包")
        return False


if __name__ == "__main__":
    success = post_install()
    if success:
        print("\n🎉 SAGE Framework 安装完成!")
        print("\n您现在可以运行:")
        print("  sage --help")
        print("  python -c \"import sage; print('SAGE 已就绪')\"")
    else:
        print("\n⚠️  需要手动完成子包安装")
        sys.exit(1)
