"""
SAGE Issues管理工具 - 辅助脚本模块

这个模块包含各种辅助功能:
- download_issues: 下载GitHub Issues (简化版)
- download_issues_v2: 下载GitHub Issues (高级版)
- get_team_members: 获取团队成员信息
- create_issue: 创建新Issue
- sync_issues: 同步Issues到GitHub
- ai_analyzer: AI分析功能
- github_helper: GitHub API辅助工具
- execute_fix_plan: 执行修复计划
- 其他辅助工具
"""

from .download_issues import IssuesDownloader

# 如果需要使用其他helper，可以尝试导入
try:
    from . import (ai_analyzer, create_issue, execute_fix_plan,
                   get_team_members, github_helper, sync_issues)

    __all__ = [
        "IssuesDownloader",
        "get_team_members",
        "create_issue",
        "sync_issues",
        "ai_analyzer",
        "github_helper",
        "execute_fix_plan",
    ]
except ImportError:
    # 如果导入失败，只导出基础的下载器
    __all__ = ["IssuesDownloader"]
