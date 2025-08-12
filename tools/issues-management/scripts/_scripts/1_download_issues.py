#!/usr/bin/env python3
"""
GitHub Issues 下载和整理工具
用于批量下载SAGE仓库的issues并整理到指定文件夹
"""

import os
import sys
import json
import requests
import time
from datetime import datetime
from pathlib import Path
import re


class GitHubIssuesDownloader:
    def __init__(self, repo_owner, repo_name, output_dir="issues_workspace", token=None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.output_dir = Path(output_dir)
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        # 设置认证头
        if self.token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })
        else:
            print("⚠️  未提供GitHub token，可能会受到API速率限制")
            
    def create_output_structure(self):
        """创建输出目录结构"""
        directories = [
            self.output_dir,
            self.output_dir / "issues",  # 只保留一个主目录
            self.output_dir / "by_label",
            self.output_dir / "metadata"
        ]
        
        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        print(f"✅ 创建输出目录结构: {self.output_dir}")
        
    def get_all_issues(self):
        """获取所有issues（包括pull requests）"""
        all_issues = []
        page = 1
        per_page = 100
        
        print("📥 开始下载issues...")
        
        while True:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
            params = {
                'page': page,
                'per_page': per_page,
                'state': 'all',  # 获取所有状态的issues
                'sort': 'created',
                'direction': 'desc'
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                issues = response.json()
                if not issues:
                    break
                    
                all_issues.extend(issues)
                print(f"📄 已下载第 {page} 页，共 {len(issues)} 个issues")
                
                # GitHub API 速率限制处理
                if 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers['X-RateLimit-Remaining'])
                    if remaining < 10:
                        reset_time = int(response.headers['X-RateLimit-Reset'])
                        wait_time = reset_time - int(time.time()) + 10
                        print(f"⏳ API限制即将到达，等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                
                page += 1
                time.sleep(0.1)  # 避免过快请求
                
            except requests.RequestException as e:
                print(f"❌ 下载第 {page} 页时出错: {e}")
                break
                
        print(f"✅ 总共下载了 {len(all_issues)} 个issues")
        return all_issues
        
    def sanitize_filename(self, filename):
        """清理文件名，移除不安全字符"""
        # 移除或替换不安全的字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        # 限制长度
        if len(filename) > 100:
            filename = filename[:97] + "..."
        return filename
        
    def get_issue_comments(self, issue_number):
        """获取issue的评论"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"⚠️  获取issue #{issue_number} 评论失败: {e}")
            return []
            
    def save_issue_as_markdown(self, issue, comments=None):
        """将issue保存为Markdown格式 - 统一格式"""
        issue_number = issue['number']
        title = self.sanitize_filename(issue['title'])
        
        # 统一保存到issues目录，用状态作为前缀
        status_prefix = "open" if issue['state'] == 'open' else "closed"
        filename = f"{status_prefix}_{issue_number}_{title}.md"
        filepath = self.output_dir / "issues" / filename
        
        # 生成Markdown内容
        content = f"""# {issue['title']}

**Issue #**: {issue['number']}  
**状态**: {issue['state']}  
**创建时间**: {issue['created_at']}  
**更新时间**: {issue['updated_at']}  
**作者**: {issue['user']['login']}  
**链接**: {issue['html_url']}  

"""
        
        # 添加标签
        if issue['labels']:
            content += "**标签**: "
            labels = [f"`{label['name']}`" for label in issue['labels']]
            content += ", ".join(labels) + "\n\n"
            
        # 添加里程碑
        if issue['milestone']:
            content += f"**里程碑**: {issue['milestone']['title']}\n\n"
            
        # 添加分配者
        if issue['assignees']:
            assignees = [assignee['login'] for assignee in issue['assignees']]
            content += f"**分配给**: {', '.join(assignees)}\n\n"
            
        content += "---\n\n"
        
        # 添加issue正文
        if issue['body']:
            content += "## 描述\n\n"
            content += issue['body'] + "\n\n"
            
        # 添加评论（如果有）
        if comments:
            content += "---\n\n## 评论\n\n"
            for i, comment in enumerate(comments, 1):
                content += f"### 评论 {i} - {comment['user']['login']} ({comment['created_at']})\n\n"
                content += comment['body'] + "\n\n"
                
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return filepath
        
    def save_issue_metadata(self, issue):
        """保存issue的简化元数据"""
        issue_data = {
            'number': issue['number'],
            'title': issue['title'],
            'state': issue['state'],
            'labels': [label['name'] for label in issue['labels']],
            'milestone': issue['milestone']['title'] if issue['milestone'] else None,
            'assignees': [assignee['login'] for assignee in issue['assignees']],
            'created_at': issue['created_at'],
            'updated_at': issue['updated_at'],
            'html_url': issue['html_url'],
            'user': issue['user']['login']
        }
        
        filename = f"issue_{issue['number']}_metadata.json"
        filepath = self.output_dir / "metadata" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2, ensure_ascii=False)
            
        return filepath
        
    def organize_by_labels(self, issues):
        """按标签整理issues - 只创建链接文件"""
        label_dir = self.output_dir / "by_label"
        
        for issue in issues:
            if not issue['labels']:
                continue
                
            for label in issue['labels']:
                label_name = self.sanitize_filename(label['name'])
                label_path = label_dir / label_name
                label_path.mkdir(exist_ok=True)
                
                # 创建简短的引用文件
                status_prefix = "open" if issue['state'] == 'open' else "closed"
                ref_file = label_path / f"{status_prefix}_{issue['number']}.txt"
                with open(ref_file, 'w', encoding='utf-8') as f:
                    f.write(f"Issue #{issue['number']}: {issue['title']}\n")
                    f.write(f"状态: {issue['state']}\n")
                    f.write(f"文件: ../issues/{status_prefix}_{issue['number']}_{self.sanitize_filename(issue['title'])}.md\n")
                    f.write(f"链接: {issue['html_url']}\n")
                    
    def generate_summary(self, issues):
        """生成总结报告"""
        summary_file = self.output_dir / "issues_summary.md"
        
        # 统计信息
        total_issues = len(issues)
        open_issues = len([i for i in issues if i['state'] == 'open'])
        closed_issues = total_issues - open_issues
        
        # 按标签统计
        label_stats = {}
        for issue in issues:
            for label in issue['labels']:
                label_name = label['name']
                label_stats[label_name] = label_stats.get(label_name, 0) + 1
                
        # 生成报告
        content = f"""# SAGE Issues 总结报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**仓库**: {self.repo_owner}/{self.repo_name}  

## 基本统计

- **总Issues数**: {total_issues}
- **开放Issues**: {open_issues}
- **已关闭Issues**: {closed_issues}

## 按标签分布

"""
        
        for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True):
            content += f"- **{label}**: {count} issues\n"
            
        content += f"""

## 文件组织结构

```
{self.output_dir}/
├── issues/                 # 所有issues (Markdown格式)
├── by_label/              # 按标签分类 (引用文件)
├── metadata/              # 简化的JSON元数据
└── issues_summary.md      # 本报告
```

## 最近的Issues

"""
        
        # 显示最近的10个issues
        recent_issues = sorted(issues, key=lambda x: x['created_at'], reverse=True)[:10]
        for issue in recent_issues:
            content += f"- [#{issue['number']}]({issue['html_url']}) {issue['title']} ({issue['state']})\n"
            
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ 总结报告已保存: {summary_file}")
        
    def download_and_organize(self, include_comments=False):
        """主函数：下载并整理所有issues"""
        print(f"🚀 开始下载 {self.repo_owner}/{self.repo_name} 的issues...")
        
        # 创建目录结构
        self.create_output_structure()
        
        # 下载所有issues
        issues = self.get_all_issues()
        
        if not issues:
            print("❌ 没有找到任何issues")
            return
            
        # 过滤掉pull requests（如果不需要的话）
        actual_issues = [issue for issue in issues if not issue.get('pull_request')]
        print(f"📋 过滤后的真实issues数量: {len(actual_issues)}")
        
        # 保存每个issue
        print("💾 保存issues...")
        for i, issue in enumerate(actual_issues, 1):
            print(f"处理 {i}/{len(actual_issues)}: #{issue['number']} {issue['title'][:50]}...")
            
            # 获取评论（如果需要）
            comments = None
            if include_comments and issue['comments'] > 0:
                comments = self.get_issue_comments(issue['number'])
                time.sleep(0.1)  # 避免API限制
                
            # 只保存Markdown格式和简化的元数据
            self.save_issue_as_markdown(issue, comments)
            self.save_issue_metadata(issue)
            
        # 按标签整理
        print("📁 按标签整理...")
        self.organize_by_labels(actual_issues)
        
        # 生成总结
        self.generate_summary(actual_issues)
        
        print(f"✅ 完成！所有issues已保存到 {self.output_dir}")
        return actual_issues


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载并整理GitHub仓库的issues')
    parser.add_argument('--repo', default='intellistream/SAGE', 
                       help='GitHub仓库 (格式: owner/repo)')
    parser.add_argument('--output', default='downloaded_issues',
                       help='输出目录')
    parser.add_argument('--token', help='GitHub访问令牌 (可选，但推荐)')
    parser.add_argument('--comments', action='store_true',
                       help='是否下载评论 (会增加API调用次数)')
    
    args = parser.parse_args()
    
    # 解析仓库信息
    if '/' not in args.repo:
        print("❌ 仓库格式错误，应该是 owner/repo")
        sys.exit(1)
        
    repo_owner, repo_name = args.repo.split('/', 1)
    
    # 检查token
    token = args.token
    if not token:
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            print("⚠️  建议设置GITHUB_TOKEN环境变量或使用--token参数以避免API限制")
            
    # 开始下载
    downloader = GitHubIssuesDownloader(
        repo_owner=repo_owner,
        repo_name=repo_name, 
        output_dir=args.output,
        token=token
    )
    
    try:
        issues = downloader.download_and_organize(include_comments=args.comments)
        if issues:
            print(f"\n🎉 成功下载并整理了 {len(issues)} 个issues！")
            print(f"📁 输出目录: {Path(args.output).absolute()}")
        else:
            print(f"\n⚠️  没有找到任何issues或下载失败")
            print(f"📁 输出目录: {Path(args.output).absolute()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断下载")
    except Exception as e:
        print(f"\n❌ 下载过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
