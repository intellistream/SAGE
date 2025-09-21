"""
SAGE Issues管理工具 - sage-tools集成版本

这个模块提供了完整的GitHub Issues管理功能，包括：
- 下载和同步Issues
- AI智能分析和整理
- 统计和报告生成
- 团队协作管理
- 项目管理和自动分配

Usage:
    from sage.tools.dev.issues import IssuesManager

    manager = IssuesManager()
    manager.show_statistics()
"""

from .config import IssuesConfig
from .manager import IssuesManager

# 如果在CLI环境中，也导出CLI应用
try:
    from .cli import app as cli_app

    __all__ = ["IssuesManager", "IssuesConfig", "cli_app"]
except ImportError:
    __all__ = ["IssuesManager", "IssuesConfig"]
