#!/usr/bin/env python3
"""
SAGE Framework 安装验证脚本
用于验证 Monorepo 中所有子包是否正确安装
"""

import sys
import importlib
from pathlib import Path


def check_package_import(package_name, description=""):
    """检查包是否可以正确导入"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {package_name} ({description}) - version: {version}")
        return True
    except ImportError as e:
        print(f"✗ {package_name} ({description}) - 导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠ {package_name} ({description}) - 其他错误: {e}")
        return False


def main():
    """主验证函数"""
    print("=== SAGE Framework 安装验证 ===\n")
    
    # 定义要检查的包
    packages_to_check = [
        ("sage", "SAGE 核心包"),
        ("sage.core", "SAGE 内核"),
        ("sage.middleware", "SAGE 中间件"),
        ("sage.userspace", "SAGE 用户空间"),
        ("sage_dev_toolkit", "开发工具包"),
    ]
    
    success_count = 0
    total_count = len(packages_to_check)
    
    print("检查包导入状态:")
    for package_name, description in packages_to_check:
        if check_package_import(package_name, description):
            success_count += 1
        print()
    
    print(f"=== 验证结果 ===")
    print(f"成功导入: {success_count}/{total_count} 个包")
    
    if success_count == total_count:
        print("🎉 所有包安装成功！SAGE Framework 可以正常使用。")
        print("\n您现在可以运行以下命令来开始使用 SAGE:")
        print("  sage --help                    # 查看 CLI 命令")
        print("  python app/qa_dense_retrieval.py  # 运行示例应用")
        return True
    else:
        print("⚠ 部分包安装不完整，请检查安装过程中的错误信息。")
        print("\n建议运行以下命令重新安装:")
        print("  ./install_packages.sh")
        print("  或者: pip install -e .")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
