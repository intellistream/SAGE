#!/usr/bin/env python3
"""
SAGE Issues下载工具 - sage-tools适配版本
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..config import IssuesConfig


class IssuesDownloader:
    """Issues下载器 - sage-tools适配版本"""
    
    def __init__(self, config: Optional[IssuesConfig] = None):
        self.config = config or IssuesConfig()
        self.workspace = self.config.workspace_path
        self.output_path = self.config.output_path
        self.metadata_path = self.config.metadata_path
        
        # 确保目录存在
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "issues").mkdir(parents=True, exist_ok=True)
        (self.workspace / "data").mkdir(parents=True, exist_ok=True)
        
        # GitHub API headers
        self.headers = self.config.get_github_client()
    
    def download_all_issues(self, state: str = "all") -> bool:
        """下载所有Issues
        
        Args:
            state: 'open', 'closed', 'all'
        """
        print(f"🔄 开始下载Issues (状态: {state})...")
        
        try:
            issues = self._fetch_issues_from_github(state)
            if not issues:
                print("❌ 没有获取到任何Issues")
                return False
            
            print(f"✅ 获取到 {len(issues)} 个Issues")
            
            # 保存原始数据
            self._save_raw_data(issues, state)
            
            # 转换为markdown格式
            self._convert_to_markdown(issues, state)
            
            print(f"💾 Issues已保存到: {self.workspace}")
            return True
            
        except Exception as e:
            print(f"❌ 下载Issues失败: {e}")
            return False
    
    def _fetch_issues_from_github(self, state: str = "all") -> List[Dict[str, Any]]:
        """从GitHub API获取Issues"""
        all_issues = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}/issues"
            params = {
                'state': state,
                'per_page': per_page,
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            print(f"  📡 获取第 {page} 页...")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"GitHub API请求失败: {response.status_code} - {response.text}")
            
            issues = response.json()
            if not issues:
                break
                
            # 过滤掉pull requests (GitHub API将PR也当作issue返回)
            issues = [issue for issue in issues if 'pull_request' not in issue]
            all_issues.extend(issues)
            
            print(f"    ✓ 获取 {len(issues)} 个Issues")
            
            # 如果返回的数量少于per_page，说明这是最后一页
            if len(issues) < per_page:
                break
                
            page += 1
        
        return all_issues
    
    def _save_raw_data(self, issues: List[Dict[str, Any]], state: str):
        """保存原始JSON数据"""
        data_dir = self.workspace / "data"
        data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"issues_{state}_{timestamp}.json"
        
        with open(data_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
        
        # 也保存一个最新版本
        latest_filename = f"issues_{state}_latest.json"
        with open(data_dir / latest_filename, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
    
    def _convert_to_markdown(self, issues: List[Dict[str, Any]], state: str):
        """转换Issues为markdown格式"""
        issues_dir = self.workspace / "issues"
        issues_dir.mkdir(exist_ok=True)
        
        for issue in issues:
            # 生成文件名
            issue_number = issue['number']
            issue_state = issue['state']
            safe_title = self._safe_filename(issue['title'])
            filename = f"{issue_state}_{issue_number:04d}_{safe_title}.md"
            
            # 生成markdown内容
            content = self._generate_markdown_content(issue)
            
            # 保存文件
            issue_file = issues_dir / filename
            with open(issue_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"  📝 转换为markdown格式: {len(issues)} 个文件")
    
    def _safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全的字符
        safe = title.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe = safe.replace('<', '_').replace('>', '_').replace('|', '_')
        safe = safe.replace('?', '_').replace('*', '_').replace('"', '_')
        
        # 限制长度
        if len(safe) > 50:
            safe = safe[:50]
        
        return safe
    
    def _generate_markdown_content(self, issue: Dict[str, Any]) -> str:
        """生成Issue的markdown内容"""
        title = issue['title']
        number = issue['number']
        state = issue['state']
        author = issue['user']['login']
        created_at = issue['created_at']
        updated_at = issue['updated_at']
        body = issue.get('body', '') or ''
        
        # 提取标签
        labels = [label['name'] for label in issue.get('labels', [])]
        labels_str = ', '.join(labels) if labels else '无'
        
        # 提取分配者
        assignees = [assignee['login'] for assignee in issue.get('assignees', [])]
        assignees_str = ', '.join(assignees) if assignees else '未分配'
        
        # 生成markdown
        content = f"""# {title}

**Issue编号**: #{number}
**状态**: {state}
**创建者**: {author}
**创建时间**: {created_at}
**更新时间**: {updated_at}

## 标签
{labels_str}

## 分配给
{assignees_str}

## 描述

{body}

---
*此文件由SAGE Issues管理工具自动生成*
"""
        return content
    
    def download_open_issues(self) -> bool:
        """下载开放的Issues"""
        return self.download_all_issues("open")
    
    def download_closed_issues(self) -> bool:
        """下载已关闭的Issues"""
        return self.download_all_issues("closed")
    
    def get_download_status(self) -> Dict[str, Any]:
        """获取下载状态"""
        issues_dir = self.workspace / "issues"
        data_dir = self.workspace / "data"
        
        status = {
            "workspace_path": str(self.workspace),
            "issues_count": 0,
            "last_update": None,
            "available_files": []
        }
        
        if issues_dir.exists():
            status["issues_count"] = len(list(issues_dir.glob("*.md")))
        
        if data_dir.exists():
            data_files = list(data_dir.glob("*.json"))
            status["available_files"] = [f.name for f in data_files]
            
            # 找最新的数据文件
            if data_files:
                latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
                status["last_update"] = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
        
        return status


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="下载GitHub Issues")
    parser.add_argument("--state", choices=["open", "closed", "all"], default="all",
                       help="下载状态 (default: all)")
    parser.add_argument("--status", action="store_true",
                       help="显示下载状态")
    
    args = parser.parse_args()
    
    downloader = IssuesDownloader()
    
    if args.status:
        status = downloader.get_download_status()
        print("📊 下载状态:")
        print(f"  工作目录: {status['workspace_path']}")
        print(f"  Issues数量: {status['issues_count']}")
        print(f"  最后更新: {status['last_update'] or '未知'}")
        if status['available_files']:
            print(f"  可用文件: {', '.join(status['available_files'])}")
    else:
        success = downloader.download_all_issues(args.state)
        if success:
            print("\n🎉 下载完成！")
        else:
            print("\n💥 下载失败！")
            sys.exit(1)


if __name__ == "__main__":
    main()