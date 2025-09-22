#!/usr/bin/env python3
"""
Restore Assignees Tool for SAGE

This script analyzes GitHub Issues timeline to find and restore previous assignees
that may have been overwritten by script errors.
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime

# Add the parent directory to Python path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from config import Config
from helpers.github_helper import GitHubProjectManager


class AssigneeRestorer:
    """恢复Issues的正确assignee"""
    
    def __init__(self):
        self.config = Config()
        self.pm = GitHubProjectManager()
        self.github_token = self.pm.github_token
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_issue_timeline(self, issue_number):
        """获取Issue的时间线，包含assignee变更历史"""
        url = f"https://api.github.com/repos/{self.pm.ORG}/{self.pm.REPO}/issues/{issue_number}/timeline"
        
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"  ❌ 获取Issue #{issue_number}历史失败: HTTP {resp.status_code}")
                return []
        except Exception as e:
            print(f"  ❌ 获取Issue #{issue_number}历史出错: {e}")
            return []
    
    def get_issue_events(self, issue_number):
        """获取Issue的事件历史（包含assignee变更）"""
        url = f"https://api.github.com/repos/{self.pm.ORG}/{self.pm.REPO}/issues/{issue_number}/events"
        
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"  ❌ 获取Issue #{issue_number}事件失败: HTTP {resp.status_code}")
                return []
        except Exception as e:
            print(f"  ❌ 获取Issue #{issue_number}事件出错: {e}")
            return []
    
    def analyze_assignee_history(self, issue_number):
        """分析Issue的assignee变更历史"""
        print(f"  🔍 分析Issue #{issue_number}的assignee历史...")
        
        events = self.get_issue_events(issue_number)
        timeline = self.get_issue_timeline(issue_number)
        
        assignee_changes = []
        
        # 分析events中的assigned/unassigned事件
        for event in events:
            if event.get('event') in ['assigned', 'unassigned']:
                assignee_changes.append({
                    'type': event.get('event'),
                    'assignee': event.get('assignee', {}).get('login') if event.get('assignee') else None,
                    'actor': event.get('actor', {}).get('login'),
                    'created_at': event.get('created_at'),
                    'source': 'events'
                })
        
        # 分析timeline中的assignee变更
        for item in timeline:
            if item.get('event') in ['assigned', 'unassigned']:
                assignee_changes.append({
                    'type': item.get('event'),
                    'assignee': item.get('assignee', {}).get('login') if item.get('assignee') else None,
                    'actor': item.get('actor', {}).get('login'),
                    'created_at': item.get('created_at'),
                    'source': 'timeline'
                })
        
        # 按时间排序
        assignee_changes.sort(key=lambda x: x['created_at'])
        
        return assignee_changes
    
    def find_last_human_assignee(self, assignee_changes):
        """找到最后一个由人工分配的assignee（排除脚本操作）"""
        
        # 脚本相关的actor（可能需要根据实际情况调整）
        script_actors = ['ShuhaoZhangTony']  # 如果脚本是通过这个账号运行的
        
        last_human_assignee = None
        
        for change in reversed(assignee_changes):  # 从最新往回找
            actor = change.get('actor')
            assignee = change.get('assignee')
            event_type = change.get('type')
            
            # 跳过脚本操作（这里可能需要更复杂的判断逻辑）
            if actor in script_actors:
                continue
            
            # 找到assigned事件
            if event_type == 'assigned' and assignee:
                last_human_assignee = assignee
                break
        
        return last_human_assignee
    
    def get_misplaced_issues_from_project6(self):
        """获取项目#6中分配给ShuhaoZhangTony的Issues"""
        print("🔍 获取项目#6中分配给ShuhaoZhangTony的Issues...")
        
        items = self.pm.get_project_items(6)
        misplaced_issues = []
        
        for item in items:
            content = item.get('content', {})
            if content.get('__typename') == 'Issue':
                assignees = content.get('assignees', {}).get('nodes', [])
                assignee_names = [a.get('login') for a in assignees if a.get('login')]
                
                if 'ShuhaoZhangTony' in assignee_names:
                    misplaced_issues.append({
                        'number': content.get('number'),
                        'title': content.get('title', ''),
                        'author': content.get('author', {}).get('login', 'Unknown'),
                        'current_assignees': assignee_names,
                        'repository': content.get('repository', {}).get('name', 'Unknown')
                    })
        
        print(f"  📋 找到 {len(misplaced_issues)} 个需要检查的Issues")
        return misplaced_issues
    
    def restore_assignees(self, dry_run=True):
        """恢复正确的assignees"""
        print("🚀 开始分析和恢复assignees...")
        print(f"📋 运行模式: {'预览模式' if dry_run else '执行模式'}")
        print()
        
        misplaced_issues = self.get_misplaced_issues_from_project6()
        
        restoration_plan = []
        
        for issue in misplaced_issues:
            issue_number = issue['number']
            print(f"📝 处理Issue #{issue_number}: {issue['title'][:50]}...")
            
            # 分析assignee历史
            assignee_changes = self.analyze_assignee_history(issue_number)
            
            if assignee_changes:
                print(f"  📊 找到 {len(assignee_changes)} 个assignee变更记录")
                
                # 显示变更历史
                for change in assignee_changes[-5:]:  # 显示最近5个变更
                    actor = change.get('actor', 'Unknown')
                    assignee = change.get('assignee', 'None')
                    event_type = change.get('type')
                    created_at = change.get('created_at', '')[:10]  # 只显示日期
                    
                    print(f"    {created_at}: {actor} {event_type} {assignee}")
                
                # 找到最后一个人工分配的assignee
                last_human_assignee = self.find_last_human_assignee(assignee_changes)
                
                if last_human_assignee and last_human_assignee != 'ShuhaoZhangTony':
                    print(f"  ✅ 建议恢复assignee: {last_human_assignee}")
                    restoration_plan.append({
                        'issue_number': issue_number,
                        'title': issue['title'],
                        'current_assignee': 'ShuhaoZhangTony',
                        'suggested_assignee': last_human_assignee,
                        'history': assignee_changes
                    })
                else:
                    print(f"  ⚠️ 未找到合适的历史assignee，保持当前状态")
            else:
                print(f"  ❌ 未找到assignee变更历史")
            
            print()
            time.sleep(0.5)  # 避免API限制
        
        # 总结恢复计划
        print("=" * 60)
        print(f"📊 Assignee恢复计划 ({len(restoration_plan)} 个Issues):")
        print()
        
        for plan in restoration_plan:
            print(f"#{plan['issue_number']}: {plan['title'][:50]}...")
            print(f"  {plan['current_assignee']} → {plan['suggested_assignee']}")
            print()
        
        if not dry_run and restoration_plan:
            return self.execute_restoration_plan(restoration_plan)
        
        return restoration_plan
    
    def execute_restoration_plan(self, restoration_plan):
        """执行assignee恢复计划"""
        print("🚀 开始执行assignee恢复...")
        
        success_count = 0
        
        for plan in restoration_plan:
            issue_number = plan['issue_number']
            new_assignee = plan['suggested_assignee']
            
            print(f"  🔄 恢复Issue #{issue_number}的assignee到{new_assignee}...")
            
            # 使用GitHub API更新assignee
            url = f"https://api.github.com/repos/{self.pm.ORG}/{self.pm.REPO}/issues/{issue_number}"
            data = {
                'assignees': [new_assignee]
            }
            
            try:
                resp = requests.patch(url, headers=self.headers, json=data)
                if resp.status_code == 200:
                    print(f"  ✅ 成功恢复Issue #{issue_number}")
                    success_count += 1
                else:
                    print(f"  ❌ 恢复Issue #{issue_number}失败: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  ❌ 恢复Issue #{issue_number}出错: {e}")
            
            time.sleep(1)  # 避免API限制
        
        print(f"\n✨ 恢复完成: {success_count}/{len(restoration_plan)} 个Issues成功")
        return success_count == len(restoration_plan)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="恢复Issues的正确assignee")
    parser.add_argument('--execute', action='store_true', help='执行恢复操作（默认为预览模式）')
    
    args = parser.parse_args()
    
    restorer = AssigneeRestorer()
    restorer.restore_assignees(dry_run=not args.execute)


if __name__ == '__main__':
    main()
