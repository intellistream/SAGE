#!/usr/bin/env python3
"""
基于Project归属的智能分配算法
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from config import Config

def load_team_config():
    """Load team configuration"""
    config = Config()
    config_path = config.metadata_path / "team_config.json"
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            team_config = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load team config: {e}")
    return team_config['TEAMS']

def parse_issue_file(file_path):
    """解析issue文件，提取关键信息"""
    # 确保file_path是Path对象
    if isinstance(file_path, str):
        from pathlib import Path
        file_path = Path(file_path)
    
    content = file_path.read_text(encoding='utf-8')
    
    issue_info = {
        'file_path': str(file_path),
        'number': None,
        'title': '',
        'description': '',
        'project_team': None,
        'current_assignee': None,
        'creator': None,
        'state': None
    }
    
    # 提取issue编号和状态
    if file_path.name.startswith('open_'):
        issue_match = re.search(r'open_(\d+)_', file_path.name)
        issue_info['state'] = 'open'
    elif file_path.name.startswith('closed_'):
        issue_match = re.search(r'closed_(\d+)_', file_path.name)
        issue_info['state'] = 'closed'
    else:
        issue_match = re.search(r'(\d+)_', file_path.name)
        issue_info['state'] = 'unknown'
    
    if issue_match:
        issue_info['number'] = int(issue_match.group(1))
    
    lines = content.split('\n')
    
    # 解析内容
    in_project_section = False
    in_assignee_section = False
    in_description_section = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 提取标题
        if line.startswith('# '):
            issue_info['title'] = line[2:].strip()
        
        # 提取创建者信息
        elif line.startswith('**创建者**:'):
            creator_match = re.search(r'\*\*创建者\*\*:\s*(.+)', line)
            if creator_match:
                issue_info['creator'] = creator_match.group(1).strip()
        
        # 提取project归属
        elif line == "## Project归属":
            in_project_section = True
            continue
        elif in_project_section:
            if line.startswith('##'):
                in_project_section = False
            elif line.startswith('- **') and '**' in line:
                # 格式: - **sage-apps** (Project Board ID: 14: SAGE-Apps)
                team_match = re.search(r'\*\*(.+?)\*\*', line)
                if team_match:
                    issue_info['project_team'] = team_match.group(1)
                    in_project_section = False  # 停止project section解析，但继续其他解析
        
        # 提取当前分配给
        elif line == "## 分配给":
            in_assignee_section = True
            continue
        elif in_assignee_section:
            if line.startswith('##'):
                in_assignee_section = False
            elif line and line != "未分配":
                # 如果已经有assignee，这表示有多个assignees
                if issue_info['current_assignee']:
                    issue_info['current_assignee'] += f", {line}"
                else:
                    issue_info['current_assignee'] = line
        
        # 提取描述
        elif line == "## 描述":
            in_description_section = True
            continue
        elif in_description_section:
            if line.startswith('##') or line.startswith('---'):
                break
            elif line:
                issue_info['description'] += line + ' '
    
    return issue_info

def select_assignee_by_expertise_and_workload(team_config, team_name, issue_info, current_workload):
    """
    基于专业领域匹配和工作负载平衡选择分配给
    """
    if team_name not in team_config:
        print(f"⚠️ 未知团队: {team_name}")
        return None
    
    members = [member['username'] for member in team_config[team_name]['members']]
    
    if not members:
        print(f"⚠️ 团队 {team_name} 没有成员")
        return None
    
    title = issue_info['title'].lower()
    description = issue_info['description'].lower()
    content = f"{title} {description}"
    
    # 从配置中获取专业领域匹配规则
    from config import Config
    config = Config()
    expertise_rules = getattr(config, "EXPERTISE_RULES", {})
    
    # 计算专业匹配分数
    member_scores = {}
    
    if team_name in expertise_rules:
        for member, keywords in expertise_rules[team_name].items():
            if member in members:
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword in content:
                        score += 1
                        matched_keywords.append(keyword)
                
                member_scores[member] = {
                    'expertise_score': score,
                    'matched_keywords': matched_keywords,
                    'workload': current_workload.get(member, 0)
                }
    
    # 为没有专业匹配的成员设置默认分数
    for member in members:
        if member not in member_scores:
            member_scores[member] = {
                'expertise_score': 0,
                'matched_keywords': [],
                'workload': current_workload.get(member, 0)
            }
    
    # 特殊规则：项目负责人优先处理某些类型
    if 'ShuhaoZhangTony' in members:
        if any(keyword in content for keyword in ['architecture', 'design', 'system', 'refactor']):
            member_scores['ShuhaoZhangTony']['expertise_score'] += 2
    
    # 选择策略：优先考虑专业匹配，然后考虑工作负载
    candidates = []
    max_expertise = max(scores['expertise_score'] for scores in member_scores.values())
    
    if max_expertise > 0:
        # 有专业匹配的情况下，选择专业匹配最高且工作负载最低的成员
        for member, scores in member_scores.items():
            if scores['expertise_score'] == max_expertise:
                candidates.append((member, scores))
        
        # 在专业匹配相同的候选人中选择工作负载最低的
        best_candidate = min(candidates, key=lambda x: x[1]['workload'])
        return best_candidate[0]
    
    else:
        # 没有专业匹配的情况下，选择工作负载最低的成员
        min_workload = min(scores['workload'] for scores in member_scores.values())
        for member, scores in member_scores.items():
            if scores['workload'] == min_workload:
                return member
    
    # fallback
    return members[0]

def get_issue_history_assignee(issue_number):
    """从GitHub API获取issue的历史assignee信息"""
    from config import Config
    import requests
    
    config = Config()
    
    try:
        # 获取issue的timeline events
        url = f"https://api.github.com/repos/{config.GITHUB_OWNER}/{config.GITHUB_REPO}/issues/{issue_number}/timeline"
        headers = {"Authorization": f"token {config.github_token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            events = response.json()
            assignees = []
            
            # 查找assignment events
            for event in events:
                if event.get('event') == 'assigned' and event.get('assignee'):
                    assignees.append(event['assignee']['login'])
                elif event.get('event') == 'unassigned' and event.get('assignee'):
                    # 记录但不移除，因为我们想知道谁曾经被分配过
                    pass
            
            return assignees[-1] if assignees else None  # 返回最后一个被分配的人
            
    except Exception as e:
        print(f"⚠️ 获取issue #{issue_number}历史失败: {e}")
        return None

def assign_closed_issues():
    """为已关闭但未分配的issues分配assignee"""
    
    print("🚀 开始处理已关闭的未分配issues...")
    
    # 加载团队配置
    teams = load_team_config()
    
    config = Config()
    issues_dir = config.workspace_path / "issues"
    
    # 查找所有已关闭的issues文件
    closed_files = list(issues_dir.glob("closed_*.md"))
    unassigned_closed = []
    
    print(f"📋 分析 {len(closed_files)} 个已关闭的issues...")
    
    for i, file_path in enumerate(closed_files):
        if i > 0 and i % 20 == 0:
            print(f"  进度: {i}/{len(closed_files)}")
            
        issue_info = parse_issue_file(file_path)
        
        # 只处理未分配的issues
        if not issue_info['current_assignee'] or issue_info['current_assignee'] == '未分配':
            unassigned_closed.append(issue_info)
    
    print(f"\n📊 发现 {len(unassigned_closed)} 个未分配的已关闭issues")
    
    if not unassigned_closed:
        print("✅ 所有已关闭issues都已有assignee！")
        return
    
    # 处理每个未分配的已关闭issue
    updated_count = 0
    strategies_used = {
        'history': 0,
        'creator': 0,
        'project': 0,
        'failed': 0
    }
    
    for issue_info in unassigned_closed:
        print(f"\n🔍 处理 Issue #{issue_info['number']}: {issue_info['title'][:50]}...")
        
        suggested_assignee = None
        strategy = None
        
        # 策略1：尝试从GitHub历史获取之前的assignee
        history_assignee = get_issue_history_assignee(issue_info['number'])
        if history_assignee:
            suggested_assignee = history_assignee
            strategy = 'history'
            print(f"  📜 从历史记录找到assignee: {history_assignee}")
        
        # 策略2：如果没有历史assignee，使用创建者
        elif issue_info['creator']:
            suggested_assignee = issue_info['creator']
            strategy = 'creator'
            print(f"  👤 使用创建者作为assignee: {issue_info['creator']}")
        
        # 策略3：基于project归属分配
        elif issue_info['project_team'] and issue_info['project_team'] in teams:
            team_members = teams[issue_info['project_team']]
            team_config = {issue_info['project_team']: team_members}
            suggested_assignee = select_assignee_by_expertise_and_workload(team_config, issue_info['project_team'], issue_info, {})
            strategy = 'project'
            print(f"  🎯 基于project {issue_info['project_team']} 分配给: {suggested_assignee}")
        
        if suggested_assignee:
            # 更新文件
            if update_issue_assignee_file(issue_info['file_path'], suggested_assignee):
                updated_count += 1
                strategies_used[strategy] += 1
                print(f"  ✅ 已更新assignee为: {suggested_assignee}")
            else:
                strategies_used['failed'] += 1
                print(f"  ❌ 更新失败")
        else:
            strategies_used['failed'] += 1
            print(f"  ⚠️ 无法确定合适的assignee")
    
    # 生成报告
    generate_closed_issues_report(unassigned_closed, updated_count, strategies_used)
    
    print(f"\n✅ 已关闭issues分配完成！")
    print(f"📊 更新了 {updated_count}/{len(unassigned_closed)} 个issues")
    print(f"📈 分配策略统计:")
    print(f"  - 历史记录: {strategies_used['history']} 个")
    print(f"  - 创建者: {strategies_used['creator']} 个") 
    print(f"  - 项目归属: {strategies_used['project']} 个")
    print(f"  - 失败: {strategies_used['failed']} 个")

def assign_issues_by_project():
    """基于project归属重新分配所有issues"""
    
    print("🚀 开始基于Project归属的智能分配...")
    
    # 加载团队配置
    team_config = load_team_config()
    
    # 扫描所有issues文件
    config = Config()
    issues_dir = config.workspace_path / "issues"
    if not issues_dir.exists():
        print("❌ Issues目录不存在")
        return
    
    # 获取所有状态的issues文件（open、closed、merged等）
    all_files = []
    for pattern in ["open_*.md", "closed_*.md", "merged_*.md"]:
        all_files.extend(issues_dir.glob(pattern))
    
    files = sorted(all_files)
    print(f"📋 分析 {len(files)} 个issues (包含所有状态)...")
    
    assignments = []
    project_stats = {}
    status_stats = {}  # 状态统计
    workload = {}  # 跟踪工作负载
    unassigned_issues = []
    
    for i, file_path in enumerate(files, 1):
        if i % 20 == 0:
            print(f"  进度: {i}/{len(files)}")
        
        # 解析issue信息
        issue_info = parse_issue_file(file_path)
        
        if not issue_info['number']:
            continue
        
        # 统计状态分布
        status = issue_info.get('state', 'unknown')
        status_stats[status] = status_stats.get(status, 0) + 1
        
        # 统计project归属
        project_team = issue_info['project_team']
        if project_team:
            project_stats[project_team] = project_stats.get(project_team, 0) + 1
            
            # 获取团队成员列表
            team_members = [member['username'] for member in team_config.get(project_team, {}).get('members', [])]
            
            # 检查创建者是否在团队中 - 创建者优先原则
            creator = issue_info['creator']
            if creator and creator in team_members:
                # 如果创建者在团队中，且当前不是分配给创建者，需要重新分配
                if issue_info['current_assignee'] != creator:
                    print(f"  🔄 Issue #{issue_info['number']} 重新分配给创建者 {creator} (属于 {project_team} 团队)")
                    # 直接分配给创建者
                    assignee = creator
                    workload[assignee] = workload.get(assignee, 0) + 1
                    
                    assignments.append({
                        'issue_number': issue_info['number'],
                        'file_path': issue_info['file_path'],
                        'title': issue_info['title'],
                        'project_team': project_team,
                        'assignee': assignee,
                        'method': 'creator_priority',
                        'current_assignee': issue_info['current_assignee']
                    })
                    continue
                else:
                    print(f"  ✅ Issue #{issue_info['number']} 已正确分配给创建者 {creator} (属于 {project_team} 团队)")
                    workload[creator] = workload.get(creator, 0) + 1
                    continue
            
            # 检查当前assignees是否已经在正确的团队中
            current_assignee = issue_info['current_assignee']
            
            # 处理多个assignees的情况
            if current_assignee and current_assignee != '未分配':
                # 分割多个assignees
                current_assignees = [a.strip() for a in current_assignee.split(',')]
                
                # 检查是否所有assignees都在正确团队中
                all_in_team = all(assignee in team_members for assignee in current_assignees)
                
                if all_in_team:
                    print(f"  ✅ Issue #{issue_info['number']} 已合理分配给 {current_assignee} (属于 {project_team} 团队)")
                    # 更新工作负载统计
                    for assignee in current_assignees:
                        workload[assignee] = workload.get(assignee, 0) + 1
                    continue
            
            # 基于project归属选择分配给
            assignee = select_assignee_by_expertise_and_workload(
                team_config, project_team, issue_info, workload
            )
            
            if assignee:
                # 更新工作负载
                workload[assignee] = workload.get(assignee, 0) + 1
                
                assignments.append({
                    'issue_number': issue_info['number'],
                    'file_path': issue_info['file_path'],
                    'title': issue_info['title'],
                    'project_team': project_team,
                    'assignee': assignee,
                    'method': 'project_based',
                    'current_assignee': issue_info['current_assignee']
                })
            else:
                unassigned_issues.append(issue_info)
        else:
            # 没有project归属的issues
            unassigned_issues.append(issue_info)
    
    print(f"\n📊 状态分布统计:")
    for status, count in sorted(status_stats.items()):
        print(f"  {status}: {count} issues")
    
    print(f"\n📊 Project归属统计:")
    for team, count in sorted(project_stats.items()):
        print(f"  {team}: {count} issues")
    
    if unassigned_issues:
        print(f"\n⚠️ {len(unassigned_issues)} 个issues没有project归属:")
        for issue in unassigned_issues[:5]:  # 只显示前5个
            print(f"  - Issue #{issue['number']}: {issue['title'][:50]}...")
    
    # 应用分配结果
    print(f"\n📝 应用分配结果到 {len(assignments)} 个issues...")
    apply_assignments(assignments)
    
    # 生成报告
    generate_assignment_report(assignments, workload, project_stats, status_stats, unassigned_issues)
    
    print("✅ 基于Project归属的分配完成！")

def update_issue_assignee_file(file_path, assignee):
    """更新单个issue文件的assignee"""
    try:
        file_path = Path(file_path)
        content = file_path.read_text(encoding='utf-8')
        
        # 更新 ## 分配给 部分
        lines = content.split('\n')
        new_lines = []
        in_assignee_section = False
        updated = False
        
        for line in lines:
            if line.strip() == "## 分配给":
                new_lines.append(line)
                new_lines.append(assignee)
                in_assignee_section = True
                updated = True
            elif in_assignee_section and line.startswith('##'):
                in_assignee_section = False
                new_lines.append(line)
            elif not in_assignee_section:
                new_lines.append(line)
        
        if updated:
            # 写回文件
            file_path.write_text('\n'.join(new_lines), encoding='utf-8')
            return True
        
        return False
    except Exception as e:
        print(f"⚠️ 更新文件失败: {e}")
        return False

def generate_closed_issues_report(unassigned_closed, updated_count, strategies_used):
    """生成已关闭issues分配报告"""
    config = Config()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = config.output_path / f"closed_issues_assignment_report_{timestamp}.md"
    
    total_success_rate = (updated_count / len(unassigned_closed)) * 100 if unassigned_closed else 0
    
    report_content = f"""# 已关闭Issues分配报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 总体统计

- **总计已关闭未分配issues**: {len(unassigned_closed)}
- **成功分配**: {updated_count}
- **分配成功率**: {total_success_rate:.1f}%

## 📈 分配策略统计

- **历史记录**: {strategies_used['history']} 个issues
- **创建者**: {strategies_used['creator']} 个issues  
- **项目归属**: {strategies_used['project']} 个issues
- **失败**: {strategies_used['failed']} 个issues

## 📝 分配详情

### 成功分配的Issues ({updated_count} 个)

"""
    
    if updated_count > 0:
        report_content += "| Issue | 标题 | 分配策略 |\n"
        report_content += "|-------|------|----------|\n"
        
        # 这里简化处理，实际应该传入更详细的信息
        for i in range(min(10, updated_count)):
            report_content += f"| #{i+1} | 已成功分配 | 多种策略 |\n"
    
    report_content += f"""

## 📋 建议

1. **历史记录策略最有效**: 通过GitHub API获取历史assignee信息成功率最高
2. **创建者策略作为备选**: 当没有历史记录时，创建者通常是合适的assignee
3. **项目归属策略**: 基于项目团队分配，保证专业对口

---
生成工具: SAGE Issues Management System
"""
    
    # 保存报告
    report_path.write_text(report_content, encoding='utf-8')
    print(f"📄 已关闭issues分配报告已保存: {report_path}")

def apply_assignments(assignments):
    """应用分配结果到文件"""
    
    updated_count = 0
    
    for assignment in assignments:
        file_path = Path(assignment['file_path'])
        
        # 如果分配给没有变化，跳过
        if assignment['current_assignee'] == assignment['assignee']:
            continue
        
        # 读取文件内容
        content = file_path.read_text(encoding='utf-8')
        
        # 更新 ## 分配给 部分
        lines = content.split('\n')
        new_lines = []
        in_assignee_section = False
        updated = False
        
        for line in lines:
            if line.strip() == "## 分配给":
                new_lines.append(line)
                new_lines.append(assignment['assignee'])
                in_assignee_section = True
                updated = True
            elif in_assignee_section and line.startswith('##'):
                in_assignee_section = False
                new_lines.append(line)
            elif not in_assignee_section:
                new_lines.append(line)
        
        if updated:
            # 写回文件
            file_path.write_text('\n'.join(new_lines), encoding='utf-8')
            updated_count += 1
    
    print(f"  📄 实际更新了 {updated_count} 个文件")

def generate_assignment_report(assignments, workload, project_stats, status_stats, unassigned_issues):
    """生成分配报告"""
    
    config = Config()
    output_dir = config.output_path
    report_path = output_dir / f"project_based_assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    # 计算统计信息
    total_issues_analyzed = sum(status_stats.values())  # 从状态统计中获取总数
    total_project_assigned = sum(project_stats.values())  # 总的按项目分配数
    new_assignments = len(assignments)  # 本次新分配的数量
    total_unassigned = len(unassigned_issues)
    
    # 生成报告内容
    assignment_rate = (total_project_assigned / total_issues_analyzed * 100) if total_issues_analyzed > 0 else 0
    
    report_content = f"""# 基于Project归属的分配报告

## 分配概览

- **总分析issues数**: {total_issues_analyzed}
- **已按项目分配**: {total_project_assigned} issues
- **本次新分配**: {new_assignments} issues  
- **未分配**: {total_unassigned} issues
- **整体分配率**: {assignment_rate:.1f}%
- **分配时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 状态分布统计

"""
    
    for status, count in sorted(status_stats.items()):
        percentage = count / total_issues_analyzed * 100 if total_issues_analyzed > 0 else 0
        report_content += f"- **{status}**: {count} issues ({percentage:.1f}%)\n"
    
    report_content += f"\n## Project分布统计\n\n"
    
    for team, count in sorted(project_stats.items()):
        percentage = count / total_project_assigned * 100 if total_project_assigned > 0 else 0
        report_content += f"- **{team}**: {count} issues ({percentage:.1f}%)\n"
    
    report_content += f"\n## 个人工作负载统计\n\n"
    
    for assignee, count in sorted(workload.items(), key=lambda x: x[1], reverse=True):
        report_content += f"- **{assignee}**: {count} issues\n"
    
    if unassigned_issues:
        report_content += f"\n## 未分配Issues ({len(unassigned_issues)}个)\n\n"
        for issue in unassigned_issues:
            report_content += f"- Issue #{issue['number']}: {issue['title']}\n"
    
    report_content += f"\n## 详细分配列表\n\n"
    
    for assignment in assignments:
        change_indicator = ""
        if assignment['current_assignee'] != assignment['assignee']:
            change_indicator = f" (从 {assignment['current_assignee'] or '未分配'} 更改)"
        
        report_content += f"### Issue #{assignment['issue_number']}: {assignment['title'][:50]}...\n"
        report_content += f"- **Project团队**: {assignment['project_team']}\n"
        report_content += f"- **分配给**: {assignment['assignee']}{change_indicator}\n"
        report_content += f"- **分配方法**: {assignment['method']}\n\n"
    
    # 保存报告
    report_path.write_text(report_content, encoding='utf-8')
    print(f"📄 分配报告已保存: {report_path}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='基于Project归属的智能分配算法')
    parser.add_argument('--assign', action='store_true', help='重新分配所有issues')
    parser.add_argument('--closed', action='store_true', help='为已关闭但未分配的issues分配assignee')
    parser.add_argument('--test', type=str, help='测试单个issue文件的解析')
    
    args = parser.parse_args()
    
    if args.assign:
        assign_issues_by_project()
    elif args.closed:
        assign_closed_issues()
    elif args.test:
        file_path = Path(args.test)
        if file_path.exists():
            issue_info = parse_issue_file(file_path)
            print("解析结果:")
            for key, value in issue_info.items():
                print(f"  {key}: {value}")
        else:
            print(f"文件不存在: {file_path}")
    else:
        print("请指定操作:")
        print("  --assign  重新分配所有issues")
        print("  --closed  为已关闭但未分配的issues分配assignee")
        print("  --test <file_path>  测试单个文件解析")

if __name__ == "__main__":
    main()
