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

def check_dependency_versions():
    """检查依赖包版本并验证兼容性"""
    print("🔍 SAGE 依赖兼容性检查")
    print("=" * 50)
    
    # 需要检查的闭源包
    dependencies = {
        "intellistream-sage-kernel": "0.1.5",    # 最低需要此版本才有 JobManagerClient
        "intellistream-sage-utils": "0.1.3",
        "intellistream-sage-middleware": "0.1.3",
        "intellistream-sage-cli": "0.1.3"
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
