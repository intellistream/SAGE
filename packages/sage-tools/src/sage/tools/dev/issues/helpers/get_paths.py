#!/usr/bin/env python3
"""
获取config.py中的路径配置
用于shell脚本调用
"""

import sys
from pathlib import Path

# 动态导入config模块
try:
    # 尝试相对导入（当作为模块运行时）
    from ..config import IssuesConfig
except ImportError:
    # 如果相对导入失败，使用绝对导入
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import IssuesConfig

    def main():
        config = IssuesConfig()

        if len(sys.argv) < 2:
            print("用法: python3 get_paths.py <path_type>")
            print("path_type: workspace | output | metadata | project_root")
            sys.exit(1)

        path_type = sys.argv[1].lower()

        if path_type == "workspace":
            print(config.workspace_path)
        elif path_type == "output":
            print(config.output_path)
        elif path_type == "metadata":
            print(config.metadata_path)
        elif path_type == "project_root":
            print(config.project_root)
        elif path_type == "issues":
            print(config.workspace_path / "issues")
        else:
            print(f"未知的路径类型: {path_type}", file=sys.stderr)
            sys.exit(1)

except Exception as e:
    print(f"获取路径失败: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
