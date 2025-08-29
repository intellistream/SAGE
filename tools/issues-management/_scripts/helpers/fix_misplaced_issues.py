#!/usr/bin/env python3
"""
Issues错误分配检测和修复计划生成脚本

功能:
- 扫描所有GitHub项目板 (sage-kernel #12, sage-middleware #13, sage-apps #14)
- 检测错误分配的issues (基于作者的团队归属)
- 生成详细的修复计划JSON文件

使用方法:
    python3 fix_misplaced_issues.py

输出:
- 修复计划文件: output/issues_fix_plan_<timestamp>.json
- 详细的错误分配统计报告

作者: SAGE Team
日期: 2025-08-30
"""

import json
import time
from pathlib import Path
from datetime import datetime
from github_helper import GitHubProjectManager

def main():
    """
    主函数 - 扫描所有项目并生成修复计划
    """
    import sys
    
    # 检查命令行参数
    dry_run = '--dry-run' in sys.argv
    
    print("🔧 开始修复错误分配的Issues...")
    
    pm = GitHubProjectManager()
    
    # 项目信息
    projects_to_check = [12, 13, 14]
    project_names = {12: 'sage-kernel', 13: 'sage-middleware', 14: 'sage-apps'}
    
    all_fixes = []
    
    for project_num in projects_to_check:
        print(f'\n🔍 检查项目#{project_num} ({project_names[project_num]})...')
        
        # 设置项目编号
        project_data = pm.get_project_items(project_num)
        
        try:
            if project_data:
                items = project_data
                
                print(f'  总共有 {len(items)} 个items')
                
                # 检查错误分配的issues
                misplaced_count = 0
                
                for item in items:
                    content = item.get('content', {})
                    if content.get('__typename') == 'Issue':
                        issue_number = content.get('number')
                        author = content.get('author', {}).get('login', '') if content.get('author') else 'Unknown'
                        title = content.get('title', '')
                        
                        # 获取仓库信息
                        repository = content.get('repository', {})
                        repo_name = repository.get('name', 'SAGE')  # 默认为SAGE
                        repo_owner = repository.get('owner', {}).get('login', 'intellistream')
                        
                        # 获取assignees信息
                        assignees = content.get('assignees', {}).get('nodes', [])
                        assignee_logins = [assignee.get('login') for assignee in assignees if assignee.get('login')]
                        
                        # 确定应该负责这个issue的用户：优先考虑assignee，其次是author
                        responsible_user = None
                        decision_basis = None
                        
                        if assignee_logins:
                            # 如果有多个assignee，取第一个作为主要负责人
                            responsible_user = assignee_logins[0]
                            decision_basis = f"assignee ({', '.join(assignee_logins)})"
                        elif author and author != 'Unknown':
                            responsible_user = author
                            decision_basis = f"author ({author})"
                        
                        if responsible_user:
                            # 获取负责用户应该分配到的团队和项目
                            expected_team, expected_project = pm.get_target_project_for_user(responsible_user)
                            
                            # 如果应该分配到不同的项目，则记录为需要修复
                            if expected_project and expected_project != project_num:
                                misplaced_count += 1
                                
                                fix_action = {
                                    'action': 'move_issue',
                                    'issue_number': issue_number,
                                    'issue_title': title,
                                    'author': author,
                                    'assignees': assignee_logins,
                                    'responsible_user': responsible_user,
                                    'decision_basis': decision_basis,
                                    'repository': repo_name,
                                    'repository_owner': repo_owner,
                                    'current_project': project_num,
                                    'current_project_name': project_names[project_num],
                                    'target_project': expected_project,
                                    'target_project_name': project_names[expected_project],
                                    'target_team': expected_team,
                                    'item_id': item.get('id'),
                                    'issue_url': content.get('url', ''),
                                    'issue_state': content.get('state', '')
                                }
                                
                                all_fixes.append(fix_action)
                
                if misplaced_count > 0:
                    print(f'  ❌ 发现 {misplaced_count} 个错误分配的issues')
                else:
                    print(f'  ✅ 没有发现错误分配的issues')
            else:
                print(f'  ❌ 无法获取项目#{project_num}的数据')
                
        except Exception as e:
            print(f'  ❌ 处理项目#{project_num}时出错: {e}')
    
    # 生成修复计划文件
    if all_fixes:
        print(f'\n📝 生成修复计划...')
        
        fix_plan = {
            'timestamp': int(time.time()),
            'scan_time': datetime.now().isoformat(),
            'total_fixes_needed': len(all_fixes),
            'summary': {
                'total_misplaced': len(all_fixes),
                'by_project': {}
            },
            'fixes': all_fixes
        }
        
        # 统计每个项目的错误分配数量
        for fix in all_fixes:
            current_proj = fix['current_project']
            target_proj = fix['target_project']
            
            if current_proj not in fix_plan['summary']['by_project']:
                fix_plan['summary']['by_project'][current_proj] = {
                    'name': fix['current_project_name'],
                    'misplaced_issues': 0,
                    'moving_to': {}
                }
            
            fix_plan['summary']['by_project'][current_proj]['misplaced_issues'] += 1
            
            if target_proj not in fix_plan['summary']['by_project'][current_proj]['moving_to']:
                fix_plan['summary']['by_project'][current_proj]['moving_to'][target_proj] = 0
            fix_plan['summary']['by_project'][current_proj]['moving_to'][target_proj] += 1
        
        # 保存到文件
        output_dir = Path(__file__).parent.parent.parent / "output"
        output_file = output_dir / f"issues_fix_plan_{int(time.time())}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fix_plan, f, indent=2, ensure_ascii=False)
        
        print(f'✅ 修复计划已保存到: {output_file}')
        
        # 显示摘要
        print(f'\n📊 修复摘要:')
        print(f'  总共需要修复: {len(all_fixes)} 个issues')
        
        for proj_num, info in fix_plan['summary']['by_project'].items():
            print(f'  项目#{proj_num} ({info["name"]}): {info["misplaced_issues"]} 个错误分配')
            for target_proj, count in info['moving_to'].items():
                target_name = project_names[target_proj]
                print(f'    → 移动到项目#{target_proj} ({target_name}): {count} 个')
        
        # 如果不是dry-run模式，询问是否立即执行修复
        if not dry_run:
            try:
                response = input(f'\n🤔 是否立即执行这 {len(all_fixes)} 个issues的修复? (y/N): ').strip().lower()
                if response in ['y', 'yes']:
                    print(f'🚀 开始执行修复...')
                    
                    # 导入执行模块
                    from execute_fix_plan import execute_fix_plan
                    
                    # 直接执行修复计划
                    success_count, error_count, errors = execute_fix_plan(fix_plan, dry_run=False, live_mode=True)
                    
                    print(f'\n📊 修复执行结果:')
                    print(f'  ✅ 成功: {success_count}')
                    print(f'  ❌ 失败: {error_count}')
                    
                    if errors:
                        print(f'\n❌ 错误详情:')
                        for error in errors:
                            print(f'  {error}')
                    
                    return success_count > 0
                else:
                    print(f'\n⚠️  修复计划已保存，可以稍后使用 execute_fix_plan.py 执行')
                    return True
            except KeyboardInterrupt:
                print(f'\n✅ 操作被用户取消')
                return True
        else:
            print(f'\n⚠️  请检查修复计划文件，确认无误后可以执行修复操作')
        
    else:
        print(f'\n✅ 没有发现需要修复的错误分配issues')
        return True

if __name__ == "__main__":
    main()
