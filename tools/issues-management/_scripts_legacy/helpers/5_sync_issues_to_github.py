#!/usr/bin/env python3
"""
将本地issues数据的更改同步回GitHub的脚本
支持更新标题、标签、状态、分配给等信息
"""

import os
import json
import requests
from pathlib import Path
import sys
import time
import re
from datetime import datetime

class IssuesSyncToGitHub:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            sys.exit(1)
            
        self.repo = "intellistream/SAGE"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        self.issues_dir = Path("../downloaded_issues/issues")
        self.updated_issues = []
        
    def parse_issue_file(self, file_path):
        """解析单个issue文件，提取所有信息"""
        try:
            content = file_path.read_text(encoding='utf-8')
            issue_data = {}
            
            # 提取基本信息
            for line in content.split('\n'):
                if line.startswith('**Issue #**:'):
                    issue_data['number'] = int(line.split(':')[1].strip())
                elif line.startswith('**标题:**') or line.startswith('**Title:**'):
                    issue_data['title'] = line.split(':', 1)[1].strip()
                elif line.startswith('**状态:**') or line.startswith('**State:**'):
                    state = line.split(':', 1)[1].strip().lower()
                    issue_data['state'] = 'open' if state in ['open', '开放'] else 'closed'
                elif line.startswith('**作者:**') or line.startswith('**Author:**'):
                    issue_data['author'] = line.split(':', 1)[1].strip()
                elif line.startswith('**分配给:**') or line.startswith('**Assignee:**'):
                    assignee = line.split(':', 1)[1].strip()
                    issue_data['assignee'] = assignee if assignee and assignee != 'None' else None
                elif line.startswith('**标签:**') or line.startswith('**Labels:**'):
                    labels_str = line.split(':', 1)[1].strip()
                    if labels_str and labels_str != 'None':
                        # 解析标签，支持多种分隔符
                        labels = [label.strip() for label in re.split(r'[,，、]', labels_str) if label.strip()]
                        issue_data['labels'] = labels
                    else:
                        issue_data['labels'] = []
            
            # 提取主标题（如果没有从标题字段获取到）
            if 'title' not in issue_data:
                for line in content.split('\n'):
                    if line.startswith('# '):
                        issue_data['title'] = line[2:].strip()
                        break
            
            # 提取内容
            lines = content.split('\n')
            content_start = False
            issue_content = []
            
            for line in lines:
                if line.startswith('## 内容') or line.startswith('## Content') or line.startswith('## Description'):
                    content_start = True
                    continue
                elif content_start and line.startswith('##'):
                    break
                elif content_start:
                    issue_content.append(line)
            
            if issue_content:
                issue_data['body'] = '\n'.join(issue_content).strip()
            
            return issue_data
            
        except Exception as e:
            print(f"⚠️ 解析文件 {file_path} 失败: {e}")
            return None
    
    def get_github_issue(self, issue_number):
        """从GitHub获取issue的当前信息"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 获取GitHub issue #{issue_number} 失败: {e}")
            return None
    
    def compare_issues(self, local_issue, github_issue):
        """比较本地和GitHub的issue，找出差异"""
        changes = {}
        
        # 检查标题
        if local_issue.get('title') and local_issue['title'] != github_issue['title']:
            changes['title'] = {
                'local': local_issue['title'],
                'github': github_issue['title']
            }
        
        # 检查状态
        if local_issue.get('state') and local_issue['state'] != github_issue['state']:
            changes['state'] = {
                'local': local_issue['state'],
                'github': github_issue['state']
            }
        
        # 检查分配者
        local_assignee = local_issue.get('assignee')
        github_assignee = github_issue['assignee']['login'] if github_issue['assignee'] else None
        if local_assignee != github_assignee:
            changes['assignee'] = {
                'local': local_assignee,
                'github': github_assignee
            }
        
        # 检查标签
        local_labels = set(local_issue.get('labels', []))
        github_labels = set([label['name'] for label in github_issue['labels']])
        if local_labels != github_labels:
            changes['labels'] = {
                'local': list(local_labels),
                'github': list(github_labels)
            }
        
        # 检查内容（如果本地有内容的话）
        if local_issue.get('body') and local_issue['body'].strip():
            # 简单比较，去除空白字符的影响
            local_body = re.sub(r'\s+', ' ', local_issue['body']).strip()
            github_body = re.sub(r'\s+', ' ', github_issue['body'] or '').strip()
            if local_body != github_body:
                changes['body'] = {
                    'local': local_issue['body'],
                    'github': github_issue['body']
                }
        
        return changes
    
    def update_github_issue(self, issue_number, changes):
        """更新GitHub issue"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}"
        update_data = {}
        
        # 准备更新数据
        if 'title' in changes:
            update_data['title'] = changes['title']['local']
        
        if 'state' in changes:
            update_data['state'] = changes['state']['local']
        
        if 'assignee' in changes:
            if changes['assignee']['local']:
                update_data['assignee'] = changes['assignee']['local']
            else:
                update_data['assignee'] = None
        
        if 'labels' in changes:
            update_data['labels'] = changes['labels']['local']
        
        if 'body' in changes:
            update_data['body'] = changes['body']['local']
        
        try:
            response = requests.patch(url, headers=self.headers, json=update_data)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"❌ 更新issue #{issue_number} 失败: {e}")
            return False
    
    def scan_local_issues(self):
        """扫描本地issues文件"""
        print("🔍 扫描本地issues文件...")
        
        if not self.issues_dir.exists():
            print("❌ issues目录不存在，请先下载issues")
            return []
        
        local_issues = []
        
        for issue_file in self.issues_dir.glob("*.md"):
            issue_data = self.parse_issue_file(issue_file)
            if issue_data and 'number' in issue_data:
                issue_data['file'] = issue_file.name
                local_issues.append(issue_data)
        
        print(f"✅ 找到 {len(local_issues)} 个本地issue文件")
        return sorted(local_issues, key=lambda x: x['number'])
    
    def find_changes(self, local_issues):
        """查找需要同步的更改"""
        print("🔍 比较本地和GitHub的issues，查找差异...")
        
        issues_with_changes = []
        
        for i, local_issue in enumerate(local_issues, 1):
            issue_number = local_issue['number']
            print(f"[{i}/{len(local_issues)}] 检查issue #{issue_number}...")
            
            # 获取GitHub上的issue
            github_issue = self.get_github_issue(issue_number)
            if not github_issue:
                continue
            
            # 比较差异
            changes = self.compare_issues(local_issue, github_issue)
            if changes:
                issues_with_changes.append({
                    'number': issue_number,
                    'title': local_issue.get('title', github_issue['title']),
                    'changes': changes,
                    'local_data': local_issue
                })
                print(f"   ✅ 发现 {len(changes)} 个差异")
            else:
                print(f"   ✅ 无差异")
            
            # 避免API限制
            time.sleep(0.2)
        
        return issues_with_changes
    
    def display_changes(self, issues_with_changes):
        """显示待同步的更改"""
        if not issues_with_changes:
            print("✅ 没有发现需要同步的更改")
            return False
        
        print(f"\n📋 发现 {len(issues_with_changes)} 个issues需要同步:")
        print("=" * 80)
        
        for issue in issues_with_changes:
            print(f"\n🔧 Issue #{issue['number']}: {issue['title']}")
            
            for field, change in issue['changes'].items():
                print(f"   📝 {field}:")
                print(f"      GitHub: {change['github']}")
                print(f"      本地:   {change['local']}")
                print(f"      操作:   GitHub -> 本地")
        
        return True
    
    def sync_changes(self, issues_with_changes):
        """执行同步操作"""
        print(f"\n🔄 开始同步 {len(issues_with_changes)} 个issues的更改...")
        
        success_count = 0
        
        for i, issue in enumerate(issues_with_changes, 1):
            print(f"\n[{i}/{len(issues_with_changes)}] 同步issue #{issue['number']}: {issue['title']}")
            
            if self.update_github_issue(issue['number'], issue['changes']):
                success_count += 1
                print(f"   ✅ 同步成功")
            else:
                print(f"   ❌ 同步失败")
            
            # 避免API限制
            time.sleep(1)
        
        print(f"\n🎉 同步完成！成功同步 {success_count}/{len(issues_with_changes)} 个issues")
        return success_count
    
    def run(self):
        """执行主流程"""
        print("🚀 开始同步本地issues数据到GitHub")
        print("=" * 60)
        
        # 1. 扫描本地issues
        local_issues = self.scan_local_issues()
        if not local_issues:
            print("❌ 未找到本地issues")
            return
        
        # 2. 查找更改
        issues_with_changes = self.find_changes(local_issues)
        
        # 3. 显示更改
        if not self.display_changes(issues_with_changes):
            return
        
        # 4. 确认同步
        print(f"\n❓ 确认将以上更改同步到GitHub吗? (y/N): ", end="")
        confirm = input().strip().lower()
        if confirm != 'y':
            print("❌ 同步已取消")
            return
        
        # 5. 执行同步
        self.sync_changes(issues_with_changes)

if __name__ == "__main__":
    try:
        print("🔧 初始化Issues同步工具...")
        syncer = IssuesSyncToGitHub()
        print("✅ 初始化完成，开始执行...")
        syncer.run()
    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
