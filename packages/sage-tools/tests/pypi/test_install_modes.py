#!/usr/bin/env python3
"""
测试PyPI安装模式的脚本
"""
import os
import subprocess
import sys
import tempfile


def test_install_mode(mode, description):
    """测试单个安装模式"""
    print(f"\n=== 测试 {mode} 模式: {description} ===")

    # 使用临时环境
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_dir = os.path.join(temp_dir, "test_env")

        # 创建虚拟环境
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

        # 安装包
        pip_cmd = [
            os.path.join(venv_dir, "bin", "pip"),
            "install",
            "-e",
            f"packages/sage[{mode}]",
        ]
        result = subprocess.run(pip_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {mode} 模式安装成功")
        else:
            print(f"❌ {mode} 模式安装失败")
            print(f"错误: {result.stderr}")

        return result.returncode == 0


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
