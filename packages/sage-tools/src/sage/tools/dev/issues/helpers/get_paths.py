#!/usr/bin/env python3
"""
from sage.common.utils.logging.custom_logger import CustomLogger
获取config.py中的路径配置
用于shell脚本调用
"""

import sys
from pathlib import Path

# 添加父目录到sys.path以导入config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import Config

    def main():
        config = Config()

        if len(sys.argv) < 2:
            self.logger.info("用法: python3 get_paths.py <path_type>")
            self.logger.info("path_type: workspace | output | metadata | project_root")
            sys.exit(1)

        path_type = sys.argv[1].lower()

        if path_type == "workspace":
            self.logger.info(config.workspace_path)
        elif path_type == "output":
            self.logger.info(config.output_path)
        elif path_type == "metadata":
            self.logger.info(config.metadata_path)
        elif path_type == "project_root":
            self.logger.info(config.project_root)
        elif path_type == "issues":
            self.logger.info(config.workspace_path / "issues")
        else:
            self.logger.info(f"未知的路径类型: {path_type}", file=sys.stderr)
            sys.exit(1)

except Exception as e:
    self.logger.info(f"获取路径失败: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
