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
            project_root = None
            while True:
                candidate = current / ".github_token"
                if candidate.exists():
                    found = candidate
                    break
                # 记录项目根目录（包含.git的目录）
                if (current / ".git").exists():
                    project_root = current
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
        
        # 没有找到token，给出详细的创建指导
        self._prompt_create_token_file(project_root)
        return None
    
    def _prompt_create_token_file(self, project_root: Optional[Path]):
        """提示用户创建GitHub Token文件"""
        print("\n" + "="*60)
        print("❌ 未找到GitHub Token！")
        print("="*60)
        print("\n为了使用GitHub API，您需要创建一个包含GitHub Personal Access Token的文件。")
        print("\n📋 请按以下步骤操作：")
        print("\n1. 访问GitHub生成Personal Access Token:")
        print("   https://github.com/settings/tokens")
        print("\n2. 创建新的token，需要以下权限:")
        print("   - repo (完整仓库访问权限)")
        print("   - read:org (读取组织信息)")
        print("\n3. 复制生成的token")
        
        # 确定推荐的token文件位置
        if project_root:
            recommended_path = project_root / ".github_token"
        else:
            recommended_path = Path.cwd() / ".github_token"
        
        print(f"\n4. 创建token文件:")
        print(f"   文件路径: {recommended_path}")
        print(f"   命令: echo 'your_token_here' > {recommended_path}")
        
        print("\n5. 确保文件权限安全:")
        print(f"   chmod 600 {recommended_path}")
        
        print("\n⚠️ 注意: 请妥善保管您的token，不要将其提交到版本控制系统！")
        print("="*60)
        
        # 询问用户是否要立即创建文件
        try:
            response = input("\n是否要现在创建token文件？(y/N): ").strip().lower()
            if response in ['y', 'yes']:
                token = input("请输入您的GitHub Token: ").strip()
                if token:
                    try:
                        with open(recommended_path, 'w', encoding='utf-8') as f:
                            f.write(token)
                        os.chmod(recommended_path, 0o600)
                        print(f"✅ Token文件已创建: {recommended_path}")
                        print("请重新运行程序以使用新的token。")
                    except Exception as e:
                        print(f"❌ 创建token文件失败: {e}")
                else:
                    print("❌ 未输入token，跳过创建。")
        except KeyboardInterrupt:
            print("\n\n操作已取消。")
        except EOFError:
            pass


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
