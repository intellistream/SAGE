#!/usr/bin/env python3
"""
SAGE Issues管理工具 - 配置管理 (适配sage-tools版本)
统一的配置管理和GitHub API客户端
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests


class IssuesConfig:
    """Issues管理配置类"""

    # GitHub仓库配置
    GITHUB_OWNER = "intellistream"
    GITHUB_REPO = "SAGE"

    # 专业领域匹配规则
    EXPERTISE_RULES = {
        "sage-kernel": {
            "CubeLander": [
                "ray",
                "distributed",
                "actor",
                "performance",
                "c++",
                "optimization",
            ],
            "ShuhaoZhangTony": [
                "engine",
                "compiler",
                "architecture",
                "system",
                "design",
            ],
            "Yang-YJY": ["memory", "serialization", "state", "storage", "keyed"],
            "peilin9990": ["streaming", "execution", "runtime", "task"],
            "iliujunn": ["optimization", "scalability", "efficiency", "performance"],
        },
        "sage-middleware": {
            "KimmoZAG": ["rag", "retrieval", "dataset", "data", "management"],
            "zslchase": ["embedding", "vector", "similarity", "search", "index"],
            "hongrugao": ["knowledge graph", "kg", "graph", "memory", "collection"],
            "LaughKing": ["context", "compression", "optimization", "buffer"],
            "ZeroJustMe": ["inference", "vllm", "model", "serving", "gpu"],
            "wrp-wrp": ["document", "parsing", "storage", "reranker"],
        },
        "sage-apps": {
            "leixy2004": ["ui", "frontend", "interface", "demo", "application"],
            "MingqiWang-coder": ["example", "tutorial", "integration", "app"],
            "Pygone": ["documentation", "guide", "manual", "docs"],
            "LIXINYI33": ["dataset", "management", "integration", "data"],
            "Kwan-Yiu": ["literature", "research", "analysis", "paper"],
            "cybber695": ["code completion", "suggestion", "dag", "operator"],
            "kms12425-ctrl": ["testing", "validation", "quality"],
            "Li-changwu": ["deployment", "devops", "infrastructure"],
            "Jerry01020": ["mobile", "android", "ios"],
            "huanghaonan1231": ["web", "javascript", "nodejs"],
        },
        "intellistream": {
            "ShuhaoZhangTony": [
                "architecture",
                "system",
                "design",
                "management",
                "coordination",
                "project",
                "strategy",
                "leadership",
            ]
        },
    }

    def __init__(self, project_root: Optional[Path] = None):
        # 如果没有提供project_root，尝试找到SAGE项目根目录
        if project_root is None:
            self.project_root = self._find_project_root()
        else:
            self.project_root = Path(project_root)

        # 工作目录配置 - 统一放在.sage/issues下
        from sage.common.config.output_paths import get_sage_paths

        sage_paths = get_sage_paths(self.project_root)

        self.workspace_path = sage_paths.issues_dir / "workspace"
        self.output_path = sage_paths.issues_dir / "output"
        self.metadata_path = sage_paths.issues_dir / "metadata"

        # 确保目录存在
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

        # 加载用户设置
        self._load_user_settings()

        # 确保默认metadata文件存在
        self._ensure_default_metadata_files()

        # GitHub Token
        self.github_token = self._load_github_token()

        # 仓库名称（兼容性属性）
        self.repository_name = self.GITHUB_REPO

    def _find_project_root(self) -> Path:
        """找到SAGE项目根目录"""
        current = Path(__file__).resolve()

        # 从当前文件向上查找，直到找到包含特定标记文件的目录
        while current.parent != current:
            # 优先检查.git目录（开发环境的项目根目录标记）
            if (current / ".git").exists():
                return current
            current = current.parent

        # 如果没找到.git目录（可能是已安装的包），尝试其他策略
        # 检查是否在site-packages中，如果是，使用当前工作目录
        if "site-packages" in str(current) or "dist-packages" in str(current):
            # 对于已安装的包，使用当前工作目录作为项目根目录
            return Path.cwd()

        # 最后回退到当前工作目录
        return Path.cwd()

    def _load_user_settings(self):
        """加载用户设置"""
        settings_file = self.metadata_path / "settings.json"
        default_settings = {
            "sync_update_history": True,  # 默认同步更新记录到GitHub
            "auto_backup": True,
            "verbose_output": False,
        }

        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                # 合并默认设置和用户设置
                default_settings.update(user_settings)
            except Exception as e:
                print(f"⚠️ 加载用户设置失败，使用默认设置: {e}")

        # 设置属性
        for key, value in default_settings.items():
            setattr(self, key, value)

    def _ensure_default_metadata_files(self):
        """确保默认的metadata文件存在"""

        # ai_analysis_summary.json
        ai_analysis_file = self.metadata_path / "ai_analysis_summary.json"
        if not ai_analysis_file.exists():
            default_ai_analysis = {
                "last_update": None,
                "ai_summaries": {},
                "auto_labeled_issues": [],
                "priority_assessments": {},
                "duplicate_analyses": {},
            }
            with open(ai_analysis_file, "w", encoding="utf-8") as f:
                json.dump(default_ai_analysis, f, indent=2, ensure_ascii=False)

        # update_history.json
        update_history_file = self.metadata_path / "update_history.json"
        if not update_history_file.exists():
            default_history = {"updates": [], "last_sync": None}
            with open(update_history_file, "w", encoding="utf-8") as f:
                json.dump(default_history, f, indent=2, ensure_ascii=False)

        # assignments.json
        assignments_file = self.metadata_path / "assignments.json"
        if not assignments_file.exists():
            default_assignments = {
                "auto_assignments": {},
                "manual_assignments": {},
                "assignment_rules": {},
            }
            with open(assignments_file, "w", encoding="utf-8") as f:
                json.dump(default_assignments, f, indent=2, ensure_ascii=False)

    def _load_github_token(self) -> Optional[str]:
        """加载GitHub Token"""

        # 1. 从环境变量加载
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # 2. 从配置文件加载 (项目根目录)
        token_file = self.project_root / ".github_token"
        if token_file.exists():
            try:
                with open(token_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass

        # 3. 从用户主目录加载
        home_token_file = Path.home() / ".github_token"
        if home_token_file.exists():
            try:
                with open(home_token_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass

        return None

    def get_github_client(self):
        """获取GitHub API客户端"""
        if not self.github_token:
            raise ValueError(
                "GitHub Token未配置，请设置GITHUB_TOKEN环境变量或创建.github_token文件"
            )

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        return headers

    def test_github_connection(self) -> bool:
        """测试GitHub连接"""
        if not self.github_token:
            return False

        try:
            headers = self.get_github_client()
            response = requests.get(
                f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}",
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_repo_info(self) -> dict:
        """获取仓库信息"""
        headers = self.get_github_client()
        response = requests.get(
            f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


# 兼容性别名
Config = IssuesConfig
