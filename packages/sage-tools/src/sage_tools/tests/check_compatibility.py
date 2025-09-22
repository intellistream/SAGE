#!/usr/bin/env python3
"""
SAGE 兼容性检查脚本
验证闭源依赖包的版本是否与当前项目兼容
"""

import subprocess
import sys
import importlib
import pkg_resources
import os

def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 脚本位于项目根目录的scripts/目录下
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent  # 向上1层到项目根目录
    version_file = root_dir / "_version.py"
    
    if version_file.exists():
        version_globals = {}
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                exec(f.read(), version_globals)
            return version_globals.get('__version__', '0.1.4')
        except Exception:
            pass
    
    # 默认值（找不到_version.py时使用）
    return '0.1.4'

def check_dependency_versions():
    """检查依赖包版本并验证兼容性"""
    print("🔍 SAGE 依赖兼容性检查")
    print("=" * 50)
    
    # 获取当前项目版本
    current_version = _load_version()
    print(f"📋 当前项目版本: {current_version}")
    print("")
    
    # 需要检查的闭源包 - 使用动态版本作为基准
    dependencies = {
        "intellistream-sage-kernel": current_version,    # 匹配当前项目版本
        "intellistream-sage-utils": current_version,
        "intellistream-sage-middleware": current_version,
        "intellistream-sage-cli": current_version
    }
    
    all_compatible = True
    upgrade_needed = []
    
    # 检查每个依赖包
    for package, min_version in dependencies.items():
        try:
            # 获取已安装版本
            installed_version = pkg_resources.get_distribution(package).version
            is_compatible = pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(min_version)
            
            if is_compatible:
                print(f"✅ {package} 版本兼容: {installed_version} >= {min_version}")
            else:
                print(f"❌ {package} 版本过低: {installed_version} < {min_version} (需要升级)")
                all_compatible = False
                upgrade_needed.append(package)
        except pkg_resources.DistributionNotFound:
            print(f"❌ {package} 未安装")
            all_compatible = False
            upgrade_needed.append(package)
        except Exception as e:
            print(f"❓ {package} 检查失败: {e}")
            all_compatible = False
    
    # 如果需要升级，提供升级命令
    if not all_compatible:
        print("\n需要升级以下包:")
        for package in upgrade_needed:
            print(f"  - {package}")
        
        print("\n升级命令:")
        packages_str = " ".join(upgrade_needed)
        print(f"  pip install --upgrade {packages_str}")
        
        # 尝试验证模块导入
        print("\n尝试验证关键模块导入:")
        try:
            from sage.kernel import JobManagerClient
            print("✅ JobManagerClient 导入成功")
        except ImportError as e:
            print(f"❌ JobManagerClient 导入失败: {e}")
            print("   这可能会导致应用程序无法正常运行")
    else:
        print("\n✅ 所有依赖版本兼容，系统应该可以正常工作")
    
    return all_compatible

if __name__ == "__main__":
    # 检查当前目录是否是项目根目录
    if not os.path.exists("pyproject.toml"):
        print("⚠️ 请在项目根目录运行此脚本")
        sys.exit(1)
        
    if check_dependency_versions():
        sys.exit(0)
    else:
        sys.exit(1)
