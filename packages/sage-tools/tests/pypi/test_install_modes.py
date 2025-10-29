#!/usr/bin/env python3
"""
测试本地包安装模式的脚本
"""

import os
import sys

import pytest


@pytest.mark.parametrize(
    "mode,description",
    [
        ("minimal", "最小化安装 - 核心功能"),
        ("standard", "标准安装 - 常用功能"),
        ("dev", "开发模式 - 开发工具"),
    ],
)
def test_install_mode(mode, description):
    """测试单个安装模式 - 简化版本，只测试包的可用性"""
    print(f"\n=== 测试 {mode} 模式: {description} ===")

    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))

    # 检查必需的包是否存在
    packages_to_check = [
        "packages/sage-common",
        "packages/sage-kernel",
        "packages/sage-tools",
    ]

    if mode in ["standard", "dev"]:
        packages_to_check.extend(["packages/sage-middleware", "packages/sage-libs"])

    # 检查所有必需的包目录是否存在且有pyproject.toml
    for package in packages_to_check:
        package_path = os.path.join(project_root, package)
        pyproject_path = os.path.join(package_path, "pyproject.toml")

        assert os.path.exists(package_path), f"包目录不存在: {package}"
        assert os.path.exists(pyproject_path), f"pyproject.toml 不存在: {package}"

        print(f"✅ 检查通过: {package}")

    # 检查主包
    main_package_path = os.path.join(project_root, "packages/sage")
    main_pyproject_path = os.path.join(main_package_path, "pyproject.toml")

    assert os.path.exists(main_package_path), "主包目录不存在: packages/sage"
    assert os.path.exists(main_pyproject_path), "主包 pyproject.toml 不存在"

    print("✅ 检查通过: packages/sage")

    # 检查主包的pyproject.toml中是否包含对应的安装模式
    with open(main_pyproject_path, encoding="utf-8") as f:
        content = f.read()
        assert f"{mode} = [" in content, f"{mode} 安装模式未在pyproject.toml中定义"

    print(f"✅ {mode} 安装模式已定义")
    print(f"✅ {mode} 模式配置检查成功")


def main():
    """主测试函数"""
    modes = {
        "minimal": "最小化安装 - 核心功能",
        "standard": "标准安装 - 常用功能",
        "dev": "开发模式 - 开发工具",
    }

    results = {}

    for mode, desc in modes.items():
        try:
            test_install_mode(mode, desc)
            results[mode] = True
        except AssertionError as e:
            print(f"❌ {mode} 模式测试失败: {e}")
            results[mode] = False
        except Exception as e:
            print(f"❌ {mode} 模式测试过程中出现异常: {e}")
            results[mode] = False

    print("\n=== 测试结果汇总 ===")
    for mode, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{mode}: {status}")

    # 如果有失败的测试，退出码为1
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
