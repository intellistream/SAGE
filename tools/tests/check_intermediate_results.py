#!/usr/bin/env python3
"""
中间结果放置检查命令行工具

用法: python3 check_intermediate_results.py [项目根目录]
如果不指定项目根目录，则使用当前工作目录。
"""

import sys
from pathlib import Path

# 添加 sage-tools 到 Python 路径
script_path = Path(__file__).parent
tools_src = script_path.parent.parent / "packages" / "sage-tools" / "src"
if tools_src.exists():
    sys.path.insert(0, str(tools_src))

from sage.tools.dev.utils.intermediate_results_checker import \
    print_intermediate_results_check


def main():
    """主函数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    # 确保路径是绝对路径
    project_root = str(Path(project_root).resolve())

    # 执行检查
    passed = print_intermediate_results_check(project_root)

    # 返回适当的退出码
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
