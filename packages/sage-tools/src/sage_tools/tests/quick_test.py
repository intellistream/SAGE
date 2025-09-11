# Converted from quick_test.sh
# SAGE Framework 快速测试脚本
# Quick Test Script for SAGE Framework
#
# 快速测试主要包，适用于日常开发验证
# Quick test for main packages, suitable for daily development verification

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 尝试导入 logging
try:
    from sage_tools.utils.logging import log_info, log_success, log_warning, log_error
except ImportError:
    # Fallback
    import logging
    logging.basicConfig(level=logging.INFO)
    log_info = lambda msg: print(f"[INFO] {msg}")
    log_success = lambda msg: print(f"[SUCCESS] {msg}")
    log_warning = lambda msg: print(f"[WARNING] {msg}")
    log_error = lambda msg: print(f"[ERROR] {msg}")

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = (SCRIPT_DIR / "../../").resolve()

# 快速测试配置
QUICK_PACKAGES = ["sage-common", "sage-kernel", "sage-libs", "sage-middleware"]
QUICK_TIMEOUT = 120
QUICK_JOBS = 3


def show_help():
    """显示帮助信息"""
    help_text = f"""SAGE Framework 快速测试工具

用法: {sys.argv[0]} [选项]

选项:
  -v, --verbose       详细输出模式
  -s, --summary       只显示摘要结果
  -h, --help          显示此帮助信息

特性:
  🎯 只测试有测试的主要包 ({' '.join(QUICK_PACKAGES)})
  🚀 自动并行执行 ({QUICK_JOBS} 个worker)
  ⚡ 较短的超时时间 ({QUICK_TIMEOUT} 秒)
  🛡️ 自动继续执行，即使某个包失败
"""
    print(help_text)


def main():
    parser = argparse.ArgumentParser(description="SAGE Framework 快速测试工具")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("-s", "--summary", action="store_true", help="只显示摘要结果")
    parser.add_argument("-h", "--help", action="help", help="显示此帮助信息")
    args = parser.parse_args()

    if args.help:
        show_help()
        return

    # 构建参数
    cmd_args = [
        "--jobs", str(QUICK_JOBS),
        "--timeout", str(QUICK_TIMEOUT),
        "--continue-on-error"
    ]

    if args.verbose:
        cmd_args.append("--verbose")
    if args.summary:
        cmd_args.append("--summary")

    cmd_args.extend(QUICK_PACKAGES)

    # 调用主测试脚本
    log_info("🚀 启动 SAGE Framework 快速测试")
    log_info(f"测试包: {' '.join(QUICK_PACKAGES)}")
    print()

    # 执行 python -m sage_tools.tests.test_all_packages
    try:
        result = subprocess.run(
            [sys.executable, "-m", "sage_tools.tests.test_all_packages"] + cmd_args,
            cwd=str(PROJECT_ROOT),
            check=True,
            text=True,
            capture_output=False
        )
        log_success("快速测试完成")
    except subprocess.CalledProcessError as e:
        log_error(f"快速测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()