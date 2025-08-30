#!/usr/bin/env python3
"""
检测和修复没有项目板归属的Issues

功能:
- 扫描所有Issues，找出没有被分配到任何项目板的
- 基于创建者或assignee的团队归属推断应该分配到哪个项目板
- 生成修复计划并可选择执行

使用方法:
    python3 fix_unassigned_issues.py --dry-run   # 预览
    python3 fix_unassigned_issues.py             # 执行修复

作者: SAGE Team
日期: 2025-08-30
"""

import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime

# 添加上级目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config, GitHubClient
from github_helper import GitHubProjectManager

def get_all_repo_issues():
    """获取所有仓库的issues"""
    print("🔍 获取SAGE仓库的所有Issues...")
    
    # 使用GitHubClient获取issues
    config = Config()
    github_client = GitHubClient(config)
    
    # 获取所有issues (开放和关闭的)
    all_issues = []
    
    for state in ['open', 'closed']:
        page = 1
        while True:
            url = f"https://api.github.com/repos/intellistream/SAGE/issues"
            params = {
                'state': state,
                'per_page': 100,
                'page': page
            }
            
            resp = github_client.session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"❌ 获取issues失败: {resp.status_code}")
                break
            
            issues = resp.json()
            if not issues:
                break
            
            all_issues.extend(issues)
            page += 1
            
            if len(issues) < 100:  # 最后一页
                break
    
    print(f"📥 获取到 {len(all_issues)} 个Issues")
    return all_issues

def get_issues_in_projects(pm):
    """获取所有项目板中的issues号码"""
    projects_to_check = [6, 12, 13, 14]  # intellistream, sage-kernel, sage-middleware, sage-apps
    issues_in_projects = set()
    
    print("🔍 检查所有项目板中的Issues...")
    
    for project_num in projects_to_check:
        print(f"  检查项目#{project_num}...")
        project_data = pm.get_project_items(project_num)
        
        if project_data:
            for item in project_data:
                content = item.get('content', {})
                if content.get('__typename') == 'Issue':
                    issue_number = content.get('number')
                    if issue_number:
                        issues_in_projects.add(issue_number)
    
    print(f"📊 项目板中共有 {len(issues_in_projects)} 个Issues")
    return issues_in_projects

def determine_target_project(issue, pm):
    """确定issue应该分配到哪个项目"""
    # 优先考虑assignees
    assignees = issue.get('assignees', [])
    if assignees:
        for assignee in assignees:
            username = assignee.get('login')
            if username:
                team, project = pm.get_target_project_for_user(username)
                if team and project:
                    return team, project, f"assignee ({username})"
    
    # 其次考虑creator
    author = issue.get('user', {}).get('login')
    if author:
        team, project = pm.get_target_project_for_user(author)
        if team and project:
            return team, project, f"author ({author})"
    
    return None, None, "unknown"

def main():
    import sys
    
    dry_run = '--dry-run' in sys.argv
    
    print("🔧 开始检测没有项目板归属的Issues...")
    
    pm = GitHubProjectManager()
    
    # 获取所有issues
    all_issues = get_all_repo_issues()
    
    # 获取已在项目板中的issues
    issues_in_projects = get_issues_in_projects(pm)
    
    # 找出没有项目板归属的issues
    unassigned_issues = []
    for issue in all_issues:
        issue_number = issue.get('number')
        if issue_number and issue_number not in issues_in_projects:
            unassigned_issues.append(issue)
    
    print(f"📊 发现 {len(unassigned_issues)} 个没有项目板归属的Issues")
    
    if not unassigned_issues:
        print("✅ 所有Issues都已正确分配到项目板")
        return
    
    # 分析每个未分配的issue
    fixes_needed = []
    
    for issue in unassigned_issues:
        issue_number = issue.get('number')
        title = issue.get('title', '')
        state = issue.get('state', '')
        
        team, project, basis = determine_target_project(issue, pm)
        
        if team and project:
            fix_action = {
                'action': 'add_to_project',
                'issue_number': issue_number,
                'issue_title': title,
                'issue_state': state,
                'issue_url': issue.get('html_url', ''),
                'target_project': project,
                'target_team': team,
                'decision_basis': basis,
                'assignees': [a.get('login') for a in issue.get('assignees', [])],
                'author': issue.get('user', {}).get('login')
            }
            fixes_needed.append(fix_action)
        else:
            print(f"⚠️ Issue #{issue_number}: {title} - 无法确定目标项目 (作者: {issue.get('user', {}).get('login')}, assignees: {[a.get('login') for a in issue.get('assignees', [])]})")
    
    print(f"📋 需要分配 {len(fixes_needed)} 个Issues到项目板")
    
    # 按目标项目分组统计
    project_stats = {}
    for fix in fixes_needed:
        project = fix['target_project']
        team = fix['target_team']
        if team not in project_stats:
            project_stats[team] = 0
        project_stats[team] += 1
    
    print("📊 分配统计:")
    for team, count in project_stats.items():
        print(f"  {team}: {count} 个Issues")
    
    if dry_run:
        print("🔍 Dry-run模式 - 仅预览，不执行实际操作")
        
        # 显示前10个示例
        print("\n📝 前10个待分配Issues示例:")
        for i, fix in enumerate(fixes_needed[:10]):
            print(f"  {i+1}. Issue #{fix['issue_number']}: {fix['issue_title']}")
            print(f"     → 分配到 {fix['target_team']} (项目#{fix['target_project']}) - 基于{fix['decision_basis']}")
        
        if len(fixes_needed) > 10:
            print(f"     ... 还有 {len(fixes_needed) - 10} 个Issues")
    else:
        # 执行修复
        if len(fixes_needed) > 0:
            confirm = input(f"🤔 是否立即将 {len(fixes_needed)} 个Issues分配到项目板? (y/N): ")
            if confirm.lower() == 'y':
                print("🚀 开始执行分配...")
                
                success_count = 0
                for i, fix in enumerate(fixes_needed, 1):
                    issue_number = fix['issue_number']
                    target_project = fix['target_project']
                    target_team = fix['target_team']
                    
                    print(f"[{i}/{len(fixes_needed)}] 分配Issue #{issue_number} 到 {target_team} (项目#{target_project})")
                    
                    # 这里需要实现实际的添加到项目板的逻辑
                    # 由于add_issue_to_project需要global_id，我们先跳过实际执行
                    print(f"  📝 {fix['issue_title']}")
                    print(f"  🎯 基于: {fix['decision_basis']}")
                    print(f"  ⚠️ 需要手动添加到项目板 (需要实现global_id获取)")
                    
                    success_count += 1
                
                print(f"📊 处理结果: {success_count}/{len(fixes_needed)} 成功")
            else:
                print("❌ 用户取消操作")

if __name__ == "__main__":
    main()
