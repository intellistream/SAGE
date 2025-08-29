#!/usr/bin/env python3
"""
基于Project归属的智能分配算法
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

def load_team_config():
    """Load team configuration"""
    config_path = Path(__file__).parent.parent / "meta-data" / "team_config.py"
    
    team_config = {}
    exec(open(config_path).read(), team_config)
    return team_config['TEAMS']

def parse_issue_file(file_path):
    """解析issue文件，提取关键信息"""
    content = file_path.read_text(encoding='utf-8')
    
    issue_info = {
        'file_path': str(file_path),
        'number': None,
        'title': '',
        'description': '',
        'project_team': None,
        'current_assignee': None
    }
    
    # 提取issue编号
    issue_match = re.search(r'open_(\d+)_', file_path.name)
    if issue_match:
        issue_info['number'] = int(issue_match.group(1))
    
    lines = content.split('\n')
    
    # 解析内容
    in_project_section = False
    in_assignee_section = False
    in_description_section = False
    
    for line in lines:
        line = line.strip()
        
        # 提取标题
        if line.startswith('# '):
            issue_info['title'] = line[2:].strip()
        
        # 提取project归属
        elif line == "## Project归属":
            in_project_section = True
            continue
        elif in_project_section:
            if line.startswith('##'):
                in_project_section = False
            elif line.startswith('- **') and '**' in line:
                # 格式: - **sage-apps** (Project #14: SAGE-Apps)
                team_match = re.search(r'\*\*(.+?)\*\*', line)
                if team_match:
                    issue_info['project_team'] = team_match.group(1)
                    break
        
        # 提取当前分配给
        elif line == "## 分配给":
            in_assignee_section = True
            continue
        elif in_assignee_section:
            if line.startswith('##'):
                in_assignee_section = False
            elif line and line != "未分配":
                issue_info['current_assignee'] = line
                break
        
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
    
    # 专业领域匹配规则
    expertise_rules = {
        'sage-kernel': {
            'CubeLander': ['ray', 'distributed', 'actor', 'performance', 'c++', 'optimization'],
            'ShuhaoZhangTony': ['engine', 'compiler', 'architecture', 'system', 'design'],
            'Yang-YJY': ['memory', 'serialization', 'state', 'storage', 'keyed'],
            'peilin9990': ['streaming', 'execution', 'runtime', 'task'],
            'iliujunn': ['optimization', 'scalability', 'efficiency', 'performance']
        },
        'sage-middleware': {
            'KimmoZAG': ['rag', 'retrieval', 'dataset', 'data', 'management'],
            'zslchase': ['embedding', 'vector', 'similarity', 'search', 'index'],
            'hongrugao': ['knowledge graph', 'kg', 'graph', 'memory', 'collection'],
            'LaughKing': ['context', 'compression', 'optimization', 'buffer'],
            'ZeroJustMe': ['inference', 'vllm', 'model', 'serving', 'gpu'],
            'wrp-wrp': ['document', 'parsing', 'storage', 'reranker']
        },
        'sage-apps': {
            'leixy2004': ['ui', 'frontend', 'interface', 'demo', 'application'],
            'MingqiWang-coder': ['example', 'tutorial', 'integration', 'app'],
            'Pygone': ['documentation', 'guide', 'manual', 'docs'],
            'LIXINYI33': ['dataset', 'management', 'integration', 'data'],
            'Kwan-Yiu': ['literature', 'research', 'analysis', 'paper'],
            'cybber695': ['code completion', 'suggestion', 'dag', 'operator'],
            'kms12425-ctrl': ['testing', 'validation', 'quality'],
            'Li-changwu': ['deployment', 'devops', 'infrastructure'],
            'Jerry01020': ['mobile', 'android', 'ios'],
            'huanghaonan1231': ['web', 'javascript', 'nodejs']
        }
    }
    
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

def assign_issues_by_project():
    """基于project归属重新分配所有issues"""
    
    print("🚀 开始基于Project归属的智能分配...")
    
    # 加载团队配置
    team_config = load_team_config()
    
    # 扫描所有issues文件
    issues_dir = Path(__file__).parent.parent / "issues_workspace" / "issues"
    if not issues_dir.exists():
        print("❌ Issues目录不存在")
        return
    
    files = sorted(list(issues_dir.glob("open_*.md")))
    print(f"📋 分析 {len(files)} 个issues...")
    
    assignments = []
    project_stats = {}
    workload = {}  # 跟踪工作负载
    unassigned_issues = []
    
    for i, file_path in enumerate(files, 1):
        if i % 20 == 0:
            print(f"  进度: {i}/{len(files)}")
        
        # 解析issue信息
        issue_info = parse_issue_file(file_path)
        
        if not issue_info['number']:
            continue
        
        # 统计project归属
        project_team = issue_info['project_team']
        if project_team:
            project_stats[project_team] = project_stats.get(project_team, 0) + 1
            
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
    generate_assignment_report(assignments, workload, project_stats, unassigned_issues)
    
    print("✅ 基于Project归属的分配完成！")

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

def generate_assignment_report(assignments, workload, project_stats, unassigned_issues):
    """生成分配报告"""
    
    output_dir = Path(__file__).parent.parent / "output"
    report_path = output_dir / f"project_based_assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    # 计算统计信息
    total_assigned = len(assignments)
    total_unassigned = len(unassigned_issues)
    
    # 生成报告内容
    report_content = f"""# 基于Project归属的分配报告

## 分配概览

- **总issues数**: {total_assigned + total_unassigned}
- **已分配**: {total_assigned} issues
- **未分配**: {total_unassigned} issues
- **分配率**: {total_assigned/(total_assigned+total_unassigned)*100:.1f}%
- **分配时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Project分布统计

"""
    
    for team, count in sorted(project_stats.items()):
        percentage = count / total_assigned * 100 if total_assigned > 0 else 0
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
    parser.add_argument('--test', type=str, help='测试单个issue文件的解析')
    
    args = parser.parse_args()
    
    if args.assign:
        assign_issues_by_project()
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
        print("  --test <file_path>  测试单个文件解析")

if __name__ == "__main__":
    main()
