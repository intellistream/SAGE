#!/usr/bin/env python3
"""
SAGE Issues下载工具
根据issues_manager.sh的调用需求重新设计
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import re

# 导入配置
from config import config, github_client

class IssuesDownloader:
    """Issues下载器"""
    
    def __init__(self):
        self.config = config
        self.github = github_client
        self.workspace = self.config.workspace_path
        
        # 创建输出目录结构
        self.issues_dir = self.workspace / "issues"
        self.metadata_dir = self.workspace / "metadata"

        for d in (self.issues_dir, self.metadata_dir):
            d.mkdir(parents=True, exist_ok=True)
        
        # 加载project映射信息
        self.project_mapping = self.load_project_mapping()
        # 添加issue到project的映射缓存
        self.issue_project_cache = {}
    
    def load_project_mapping(self):
        """加载project映射信息"""
        try:
            boards_file = self.config.metadata_path / "boards_metadata.json"
            if boards_file.exists():
                with open(boards_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        12: 'sage-kernel',
                        13: 'sage-middleware', 
                        14: 'sage-apps'
                    }
            return {}
        except Exception as e:
            print(f"⚠️ 加载project映射失败: {e}")
            return {}
    
    def bulk_get_project_info(self, issue_numbers: list):
        """批量获取多个issues的project归属信息，提高性能"""
        if not issue_numbers:
            return
            
        print(f"📊 批量获取 {len(issue_numbers)} 个issues的项目信息...")
        
        try:
            # 使用organization查询来找到包含这些issues的projects
            query = """
            {
              organization(login: "intellistream") {
                projectsV2(first: 20) {
                  nodes {
                    number
                    title
                    items(first: 100) {
                      nodes {
                        content {
                          ... on Issue {
                            number
                            repository {
                              name
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            
            response = self.github.session.post(
                "https://api.github.com/graphql",
                json={"query": query},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"GraphQL API错误: {response.status_code}")
                return
                
            data = response.json()
            
            if 'errors' in data:
                print(f"GraphQL查询错误: {data['errors']}")
                return
                
            if not data.get('data', {}).get('organization', {}).get('projectsV2', {}).get('nodes'):
                print("未找到projects数据")
                return
            
            # 构建issue到project的映射
            found_count = 0
            for project in data['data']['organization']['projectsV2']['nodes']:
                if not project.get('items', {}).get('nodes'):
                    continue
                    
                project_num = project['number']
                project_title = project['title']
                team_name = self.project_mapping.get(project_num, f"unknown-{project_num}")
                
                for item in project['items']['nodes']:
                    content = item.get('content')
                    if not content:
                        continue
                        
                    issue_number = content.get('number')
                    if (issue_number in issue_numbers and
                        content.get('repository', {}).get('name') == 'SAGE'):
                        
                        if issue_number not in self.issue_project_cache:
                            self.issue_project_cache[issue_number] = []
                        
                        self.issue_project_cache[issue_number].append({
                            'number': project_num,
                            'title': project_title,
                            'team': team_name
                        })
                        found_count += 1
            
            print(f"✅ 成功获取 {found_count} 个issues的项目信息")
                        
        except Exception as e:
            print(f"⚠️ 批量获取项目信息失败: {e}")
            import traceback
            traceback.print_exc()
    
    def get_issue_project_info(self, issue_number: int):
        """获取issue的project归属信息（优先从缓存获取）"""
        # 首先检查缓存
        if issue_number in self.issue_project_cache:
            return self.issue_project_cache[issue_number]
        
        # 如果缓存中没有，返回空列表（避免单独的API请求）
        return []
    
    def sanitize_filename(self, text: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法的文件名字符
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'\s+', '_', text)
        return text[:50]  # 限制长度
    
    def format_issue_content(self, issue: dict, project_info: list = None) -> str:
        """格式化Issue内容为Markdown"""
        
        # 格式化project信息
        project_section = ""
        if project_info:
            project_section = "\n## Project归属\n"
            for proj in project_info:
                project_section += f"- **{proj['team']}** (Project #{proj['number']}: {proj['title']})\n"
        else:
            project_section = "\n## Project归属\n未归属到任何Project\n"
        
        content = f"""# {issue['title']}

**Issue #**: {issue['number']}
**状态**: {issue['state']}
**创建时间**: {issue['created_at']}
**更新时间**: {issue['updated_at']}
**创建者**: {issue['user']['login']}
{project_section}
## 标签
{', '.join([label['name'] for label in issue.get('labels', [])])}

## 分配给
{issue.get('assignee', {}).get('login', '未分配') if issue.get('assignee') else '未分配'}

## 描述

{issue.get('body', '无描述')}

---
**GitHub链接**: {issue['html_url']}
**下载时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return content
    
    def save_issue(self, issue: dict):
        """保存单个Issue到文件"""
        # 获取project信息
        project_info = self.get_issue_project_info(issue['number'])
        
        # 生成文件名
        safe_title = self.sanitize_filename(issue['title'])
        filename = f"{issue['state']}_{issue['number']}_{safe_title}.md"
        filepath = self.issues_dir / filename

        # 保存内容
        content = self.format_issue_content(issue, project_info)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存简化的元数据
        try:
            self.save_issue_metadata(issue, project_info)
        except Exception:
            pass

        return filepath

    def get_issue_comments(self, issue_number: int):
        """通过 GitHubClient 的 session 获取 issue 评论（简化实现）"""
        try:
            base = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}"
            url = f"{base}/issues/{issue_number}/comments"
            resp = self.github.session.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️ 获取 Issue #{issue_number} 评论失败: {e}")
            return []

    def save_issue_metadata(self, issue: dict, project_info: list = None):
        """保存简化元数据到 metadata 目录"""
        data = {
            'number': issue.get('number'),
            'title': issue.get('title'),
            'state': issue.get('state'),
            'labels': [l.get('name') for l in issue.get('labels', [])],
            'assignees': [a.get('login') for a in issue.get('assignees', [])] if issue.get('assignees') else (
                [issue.get('assignee', {}).get('login')] if issue.get('assignee') else []),
            'created_at': issue.get('created_at'),
            'updated_at': issue.get('updated_at'),
            'html_url': issue.get('html_url'),
            'user': issue.get('user', {}).get('login'),
            'projects': project_info or []
        }
        fname = f"issue_{data['number']}_metadata.json"
        with open(self.metadata_dir / fname, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def download_issues(self, state="all") -> bool:
        """下载Issues
        
        Args:
            state: Issues状态 ("open", "closed", "all")
        
        Returns:
            bool: 下载是否成功
        """
        print(f"🚀 开始下载 {state} 状态的Issues...")
        
        try:
            # 获取Issues
            issues = self.github.get_issues(state=state)
            
            if not issues:
                print("📭 没有找到符合条件的Issues")
                return True
            
            print(f"📥 共找到 {len(issues)} 个Issues，开始下载...")
            
            # 批量获取所有issues的项目信息（优化性能）
            issue_numbers = [issue['number'] for issue in issues]
            self.bulk_get_project_info(issue_numbers)
            
            # 保存Issues
            saved_count = 0
            for issue in issues:
                try:
                    filepath = self.save_issue(issue)
                    saved_count += 1
                    if saved_count % 10 == 0:
                        print(f"✅ 已保存 {saved_count}/{len(issues)} 个Issues")
                except Exception as e:
                    print(f"❌ 保存Issue #{issue['number']} 失败: {e}")
            
            # 生成下载报告
            self.generate_download_report(issues, saved_count, state)
            
            print(f"🎉 下载完成！成功保存 {saved_count}/{len(issues)} 个Issues")
            print(f"📁 保存位置: {self.issues_dir}")
            
            return True
            
        except Exception as e:
            print(f"💥 下载失败: {e}")
            return False
    
    def generate_download_report(self, issues: list, saved_count: int, state: str):
        """生成下载报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.config.output_path / f"download_report_{state}_{timestamp}.md"
        
        # 统计信息
        total_issues = len(issues)
        open_count = len([i for i in issues if i['state'] == 'open'])
        closed_count = len([i for i in issues if i['state'] == 'closed'])
        
        # 标签统计
        label_stats = {}
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label['name']
                label_stats[label_name] = label_stats.get(label_name, 0) + 1
        
        # 生成报告内容
        report_content = f"""# Issues下载报告

**下载时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**请求状态**: {state}
**下载结果**: {saved_count}/{total_issues} 成功

## 统计信息

- 开放Issues: {open_count}
- 已关闭Issues: {closed_count}
- 总计: {total_issues}

## 标签分布

"""
        
        # 添加标签统计
        for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {label}: {count}\n"
        
        report_content += f"""
## 存储位置

Issues保存在: `{self.issues_dir}`
所有标签信息都包含在每个Issue的markdown文件中

## 文件命名规则

格式: `{{状态}}_{{编号}}_{{标题}}.md`
例如: `open_123_Fix_bug_in_parser.md`
"""
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 下载报告已保存: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="下载GitHub Issues")
    parser.add_argument("--state", 
                       choices=["open", "closed", "all"], 
                       default="all",
                       help="要下载的Issues状态 (default: all)")
    parser.add_argument("--verbose", "-v", 
                       action="store_true",
                       help="显示详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"🔧 配置信息:")
        print(f"   仓库: {config.GITHUB_OWNER}/{config.GITHUB_REPO}")
        print(f"   工作目录: {config.workspace_path}")
        print(f"   Token状态: {'✅' if config.github_token else '❌'}")
        print()
    
    # 执行下载
    downloader = IssuesDownloader()
    success = downloader.download_issues(state=args.state)
    
    if success:
        print("\n🎉 下载完成！")
        sys.exit(0)
    else:
        print("\n💥 下载失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
