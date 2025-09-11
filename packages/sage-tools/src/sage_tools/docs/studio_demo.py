# Converted from studio_demo.sh
# SAGE Studio 快速启动演示脚本
# 展示如何使用新的 SAGE CLI 命令启动和管理 Studio

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """运行命令"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=False)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"命令失败: {e}")
        return ""

def main():
    print("🎨 SAGE Studio 快速启动演示")
    print("================================")
    print()

    print("📋 1. 显示 Studio 信息")
    run_command("python -m sage.common.cli.main studio info")
    print()

    print("📋 2. 检查当前状态")
    run_command("python -m sage.common.cli.main studio status")
    print()

    print("📋 3. 安装依赖 (如果需要)")
    print("如需安装依赖，运行: sage studio install")
    print()

    print("📋 4. 启动服务")
    print("运行以下命令启动 Studio：")
    print("  sage studio start")
    print()

    print("📋 5. 访问 Studio")
    print("服务启动后，访问: http://localhost:4200")
    print()

    print("📋 6. 管理命令")
    print("可用的管理命令：")
    print("  sage studio status    # 检查状态")
    print("  sage studio logs      # 查看日志")
    print("  sage studio restart   # 重启服务")
    print("  sage studio stop      # 停止服务")
    print("  sage studio open      # 在浏览器中打开")
    print()

    print("🎯 完成! 现在你可以使用 'sage studio start' 启动 Studio 了！")

if __name__ == "__main__":
    main()