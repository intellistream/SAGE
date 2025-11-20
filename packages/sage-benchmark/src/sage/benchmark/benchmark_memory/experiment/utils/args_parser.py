"""命令行参数解析器

处理实验的命令行参数
"""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    """解析命令行参数
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description="Locomo 长轮对话记忆实验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定配置文件和任务ID
  python memory_test_pipeline.py --config config/locomo.yaml --task_id conv-26
  
  # 使用配置文件中的默认任务ID
  python memory_test_pipeline.py --config config/locomo.yaml
        """,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        required=True,
        help="配置文件路径 (必需)",
    )
    parser.add_argument(
        "--task_id",
        "-t",
        type=str,
        default=None,
        help="任务ID，覆盖配置文件中的设置 (可选)",
    )
    return parser.parse_args()
