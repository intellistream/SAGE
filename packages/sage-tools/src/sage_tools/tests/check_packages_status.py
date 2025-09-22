# Converted from .sh for Python packaging
# SAGE Framework 包状态检查脚本
# Package Status Check Script for SAGE Framework
# 检查所有包的当前状态，包括版本、依赖等信息
# Check current status of all packages including version, dependencies, etc.

import os
import sys
import subprocess
import tomllib
from pathlib import Path
from glob import glob

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PACKAGES_DIR = PROJECT_ROOT / "packages"

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_colored(color, msg):
    print(f"{color}{msg}{NC}")

def has_sage_dev():
    """检查 sage-dev 是否可用"""
    try:
        subprocess.run(['sage-dev', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_package(package):
    """检查单个包"""
    print_colored(BOLD, f"📦 {package}")
    package_path = PACKAGES_DIR / package
    
    if (package_path / "pyproject.toml").exists():
        print_colored(GREEN, "  ✅ pyproject.toml 存在")
        
        try:
            with open(package_path / "pyproject.toml", 'rb') as f:
                data = tomllib.load(f)
            project = data.get('project', {})
            print_colored(BLUE, f"  名称: {project.get('name', 'N/A')}")
            print_colored(BLUE, f"  版本: {project.get('version', 'N/A')}")
            print_colored(BLUE, f"  描述: {project.get('description', 'N/A')}")
            dependencies = project.get('dependencies', [])
            print_colored(BLUE, f"  依赖: {len(dependencies)} 个")
        except Exception as e:
            print_colored(BLUE, f"  解析失败: {e}")
    else:
        print_colored(YELLOW, "  ⚠️ pyproject.toml 不存在")
    
    # 检查源码目录
    src_dir = package_path / "src"
    if src_dir.exists():
        py_files = len(list(src_dir.rglob("*.py")))
        print_colored(CYAN, f"  📁 源码文件: {py_files} 个 Python 文件")
    else:
        print_colored(YELLOW, "  ⚠️ src/ 目录不存在")
    
    # 检查测试目录
    tests_dir = package_path / "tests"
    if tests_dir.exists():
        test_files = len(list(tests_dir.rglob("*.py")))
        print_colored(CYAN, f"  🧪 测试文件: {test_files} 个")
    
    # 使用 sage-dev info（如果可用）
    if has_sage_dev():
        print_colored(CYAN, "  🔍 详细信息:")
        try:
            result = subprocess.run(['sage-dev', 'info', str(package_path)], capture_output=True, text=True, check=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if '构建文件' in line or 'Python文件' in line:
                    print(f"    {line}")
        except subprocess.CalledProcessError:
            print_colored(YELLOW, "    获取详细信息失败")
    
    print()

def main():
    print_colored(BOLD, "📋 SAGE Framework 包状态检查")
    print_colored(BOLD, "=====================================")
    
    basic_mode = not has_sage_dev()
    if basic_mode:
        print_colored(YELLOW, "⚠️ sage-dev 命令未找到，将使用基础检查")
    
    packages = [d.name for d in PACKAGES_DIR.glob("sage-*") if d.is_dir()]
    
    print(f"发现 {len(packages)} 个包:\n")
    
    for package in packages:
        check_package(package)
    
    print_colored(BOLD, "===== 摘要 =====")
    print(f"总包数: {len(packages)}")
    
    # 检查是否有构建文件
    built_packages = 0
    for package in packages:
        package_path = PACKAGES_DIR / package
        dist_dir = package_path / "dist"
        if dist_dir.exists() and any(dist_dir.iterdir()):
            built_packages += 1
    
    print(f"已构建: {built_packages}")
    print(f"未构建: {len(packages) - built_packages}")
    
    if basic_mode:
        print()
        print_colored(YELLOW, "💡 提示: 安装 sage-dev-toolkit 可获取更详细信息")
        print("   pip install -e packages/sage-dev-toolkit")
    
    print()
    print_colored(GREEN, "✅ 检查完成")

if __name__ == "__main__":
    main()