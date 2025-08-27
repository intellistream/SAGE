#!/usr/bin/env python3
"""
SAGE Issues管理工具 - 配置管理
统一的配置管理和GitHub API客户端
"""

import os
import sys
import requests
from pathlib import Path
from typing import Optional

class Config:
    """配置管理类"""
    
    # GitHub仓库配置
    GITHUB_OWNER = "intellistream"
    GITHUB_REPO = "SAGE"
    
    # 工作目录配置
    WORKSPACE_DIR = "issues_workspace"
    OUTPUT_DIR = "output"
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.workspace_path = self.base_dir / self.WORKSPACE_DIR
        self.output_path = self.base_dir / self.OUTPUT_DIR
        
        # 确保目录存在
        self.workspace_path.mkdir(exist_ok=True)
        self.output_path.mkdir(exist_ok=True)
        
        # GitHub Token
        self.github_token = self._load_github_token()
    
    def _load_github_token(self) -> Optional[str]:
        """加载GitHub Token"""
        # 优先从环境变量读取
        token = os.getenv('GITHUB_TOKEN')
        if token:
            print("✅ 从环境变量加载GitHub Token")
            return token
        
        # 尝试从项目根目录的 .github_token 文件读取（基于此脚本的位置，而不是硬编码）
        # 优先选择：项目根目录 -> 当前工作目录 -> 用户主目录
        # 向上遍历查找 .github_token（从此文件所在目录开始），以兼容项目根目录放置token的情况
        try:
            current = Path(__file__).resolve()
            found = None
            while True:
                candidate = current / ".github_token"
                if candidate.exists():
                    found = candidate
                    break
                if current.parent == current:
                    break
                current = current.parent
        except Exception:
            found = None

        # 还可以检查当前工作目录和用户主目录
        if not found:
            cwd_candidate = Path.cwd() / ".github_token"
            if cwd_candidate.exists():
                found = cwd_candidate

        if not found:
            home_candidate = Path.home() / ".github_token"
            if home_candidate.exists():
                found = home_candidate

        if found:
            try:
                with open(found, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                if token:
                    print(f"✅ 从文件加载GitHub Token: {found}")
                    return token
            except Exception as e:
                print(f"⚠️ 读取token文件失败: {e}")
        
        print("⚠️ 未找到GitHub Token，使用匿名访问（有限制）")
        return None


class GitHubClient:
    """统一的GitHub API客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SAGE-Issues-Manager/1.0"
        })
        
        if config.github_token:
            self.session.headers["Authorization"] = f"token {config.github_token}"
    
    def get_issues(self, state="all", per_page=100) -> list:
        """获取Issues列表"""
        url = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}/issues"
        
        issues = []
        page = 1
        
        while True:
            params = {
                "state": state,
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc"
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                page_issues = response.json()
                if not page_issues:
                    break
                
                # 过滤掉Pull Requests（GitHub API中Issues包含PR）
                page_issues = [issue for issue in page_issues if "pull_request" not in issue]
                issues.extend(page_issues)
                
                print(f"📥 已获取第{page}页，共{len(page_issues)}个Issues")
                page += 1
                
            except requests.RequestException as e:
                print(f"❌ 请求失败: {e}")
                break
        
        return issues
    
    def update_issue(self, issue_number: int, **kwargs):
        """更新Issue"""
        url = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}/issues/{issue_number}"
        
        try:
            response = self.session.patch(url, json=kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 更新Issue #{issue_number} 失败: {e}")
            return None
    
    def create_issue(self, title: str, body: str = "", labels: list = None, assignees: list = None):
        """创建新Issue"""
        url = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}/issues"
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 创建Issue失败: {e}")
            return None


# 全局配置实例
config = Config()
github_client = GitHubClient(config)
