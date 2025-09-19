#!/usr/bin/env python3
"""
测试本地包安装模式的脚本
"""
import os
import subprocess
import sys
import tempfile


def test_install_mode(mode, description):
    """测试单个安装模式 - 简化版本，只测试包的可用性"""
    print(f"\n=== 测试 {mode} 模式: {description} ===")

    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
    
    try:
        # 检查必需的包是否存在
        packages_to_check = ["packages/sage-common", "packages/sage-kernel", "packages/sage-tools"]
        
        if mode in ["standard", "dev"]:
            packages_to_check.extend(["packages/sage-middleware", "packages/sage-libs"])
            
        # 检查所有必需的包目录是否存在且有pyproject.toml
        for package in packages_to_check:
            package_path = os.path.join(project_root, package)
            pyproject_path = os.path.join(package_path, "pyproject.toml")
            
            if not os.path.exists(package_path):
                print(f"❌ 包目录不存在: {package}")
                return False
                
            if not os.path.exists(pyproject_path):
                print(f"❌ pyproject.toml 不存在: {package}")
                return False
                
            print(f"✅ 检查通过: {package}")
        
        # 检查主包
        main_package_path = os.path.join(project_root, "packages/sage")
        main_pyproject_path = os.path.join(main_package_path, "pyproject.toml")
        
        if not os.path.exists(main_package_path):
            print("❌ 主包目录不存在: packages/sage")
            return False
            
        if not os.path.exists(main_pyproject_path):
            print("❌ 主包 pyproject.toml 不存在")
            return False
            
        print("✅ 检查通过: packages/sage")
        
        # 检查主包的pyproject.toml中是否包含对应的安装模式
        with open(main_pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if f'{mode} = [' in content:
                print(f"✅ {mode} 安装模式已定义")
            else:
                print(f"❌ {mode} 安装模式未在pyproject.toml中定义")
                return False
        
        print(f"✅ {mode} 模式配置检查成功")
        return True
        
    except Exception as e:
        print(f"❌ {mode} 模式测试过程中出现异常: {e}")
        return False


def main():
    """主测试函数"""
    modes = {
        "minimal": "最小化安装 - 核心功能",
        "standard": "标准安装 - 常用功能", 
        "dev": "开发模式 - 开发工具",
    }

    results = {}

    for mode, desc in modes.items():
        results[mode] = test_install_mode(mode, desc)

    print("\n=== 测试结果汇总 ===")
    for mode, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{mode}: {status}")


if __name__ == "__main__":
    main()
