#!/usr/bin/env python3
"""
修复和完善parent issues设置脚本

1. 为github-actions[bot]的issues设置parent为#612
2. 使用更好的关联语法来建立parent-child关系
"""

import json
import sys
import os
import requests
from datetime import datetime
from pathlib import Path

# 导入配置
sys.path.insert(0, str(Path(__file__).parent / "_scripts"))
from config import config, github_client

# 设置路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = config.workspace_path
DATA_DIR = WORKSPACE_DIR / "data"

# 检查GitHub token
if not config.github_token:
    print("❌ 错误: 未找到GitHub Token，请参考上述说明创建token文件")
    sys.exit(1)

# GitHub API配置
HEADERS = {
    'Authorization': f'token {config.github_token}',
    'Accept': 'application/vnd.github.v3+json',
    'X-GitHub-Api-Version': '2022-11-28'
}

# 团队成员映射
TEAM_MEMBERS = {
    "sage-kernel": {
        "members": ["CubeLander", "Yang-YJY", "peilin9990", "iliujunn", "LIXINYI33"],
        "parent_issue": 609
    },
    "sage-apps": {
        "members": ["zslchase", "FirmamentumX", "LaughKing", "Jerry01020", "yamatanooroch", 
                   "kms12425-ctrl", "LuckyWindovo", "cybber695", "Li-changwu", "huanghaonan1231"],
        "parent_issue": 611
    },
    "sage-middleware": {
        "members": ["ZeroJustMe", "leixy2004", "hongrugao", "wrp-wrp", "Kwan-Yiu", 
                   "Pygone", "KimmoZAG", "MingqiWang-coder"],
        "parent_issue": 610
    },
    "intellistream": {
        "members": ["ShuhaoZhangTony"],
        "parent_issue": 612  # 管理层issues归到公共issue
    },
    "github-actions": {
        "members": ["github-actions[bot]"],
        "parent_issue": 612  # 自动化issues归到公共issue
    }
}

# 特殊parent issues（不设置parent）
PARENT_ISSUES = [609, 610, 611, 612]

# Documentation类型issue的parent
DOCUMENTATION_PARENT = 612

def load_issue_data(issue_number):
    """加载issue数据"""
    issue_file = DATA_DIR / f"issue_{issue_number}.json"
    if not issue_file.exists():
        return None
    
    try:
        with open(issue_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载Issue #{issue_number}数据失败: {e}")
        return None

def save_issue_data(issue_number, data):
    """保存issue数据"""
    issue_file = DATA_DIR / f"issue_{issue_number}.json"
    try:
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 保存Issue #{issue_number}数据失败: {e}")
        return False

def is_documentation_issue(issue_data):
    """判断是否为documentation类型的issue (仅通过labels)"""
    # 只通过标签判断
    labels = issue_data.get('metadata', {}).get('labels', [])
    doc_keywords = ['doc', 'documentation', 'docs', 'readme', 'manual', 'guide', 'tutorial']
    
    for label in labels:
        if isinstance(label, str) and any(keyword in label.lower() for keyword in doc_keywords):
            return True
    
    return False

def get_team_for_assignees(assignees):
    """根据assignees确定团队"""
    if not assignees:
        return None
    
    # 统计每个团队的成员数
    team_counts = {}
    for team_name, team_info in TEAM_MEMBERS.items():
        count = sum(1 for assignee in assignees if assignee in team_info["members"])
        if count > 0:
            team_counts[team_name] = count
    
    if not team_counts:
        return None
    
    # 返回成员数最多的团队
    return max(team_counts.items(), key=lambda x: x[1])[0]

def set_parent_issue_github(issue_number, parent_issue_number, max_retries=3):
    """通过GitHub API设置parent issue - 使用更好的关联语法"""
    url = f"https://api.github.com/repos/intellistream/SAGE/issues/{issue_number}"
    
    for attempt in range(max_retries):
        try:
            # 获取当前issue信息
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                print(f"❌ 获取Issue #{issue_number}失败: {response.status_code}")
                return False
            
            current_issue = response.json()
            current_body = current_issue.get('body', '') or ''
            
            # 检查是否已经有parent issue设置
            if (f"Parent issue: #{parent_issue_number}" in current_body or 
                f"parent: #{parent_issue_number}" in current_body.lower() or
                f"Related to #{parent_issue_number}" in current_body):
                print(f"✅ Issue #{issue_number} 已经设置了parent issue #{parent_issue_number}")
                return True
            
            # 使用GitHub标准的关联语法
            # 在body开头添加关联信息，这样GitHub会自动识别和显示关联
            related_line = f"Related to #{parent_issue_number}"
            parent_note = f"Parent issue: #{parent_issue_number}"
            
            if not current_body.strip():
                # 如果body为空
                new_body = f"{related_line}\n\n{parent_note}"
            else:
                # 如果body不为空，在开头添加关联信息
                new_body = f"{related_line}\n\n{current_body}\n\n---\n{parent_note}"
            
            # 更新issue
            update_data = {
                'body': new_body
            }
            
            response = requests.patch(url, headers=HEADERS, json=update_data, timeout=30)
            if response.status_code == 200:
                print(f"✅ Issue #{issue_number} parent设置为 #{parent_issue_number}")
                
                # 更新本地缓存
                updated_issue = response.json()
                update_local_cache(issue_number, updated_issue)
                
                return True
            else:
                print(f"❌ 设置Issue #{issue_number} parent失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.SSLError as e:
            print(f"⚠️  SSL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                print(f"❌ 设置Issue #{issue_number} parent失败，SSL连接问题")
                return False
        except requests.exceptions.RequestException as e:
            print(f"⚠️  网络错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"❌ 设置Issue #{issue_number} parent失败，网络问题")
                return False
        except Exception as e:
            print(f"❌ 设置Issue #{issue_number} parent时发生未知错误: {e}")
            return False
    
    return False

def update_local_cache(issue_number, updated_issue):
    """更新本地缓存的issue数据"""
    try:
        issue_data = load_issue_data(issue_number)
        if issue_data:
            # 更新metadata中的相关字段
            if 'metadata' in issue_data:
                issue_data['metadata']['updated_at'] = updated_issue.get('updated_at')
                
            # 更新content中的body
            if 'content' in issue_data:
                issue_data['content']['body'] = updated_issue.get('body', '')
            
            # 更新tracking信息
            if 'tracking' in issue_data:
                issue_data['tracking']['last_synced'] = datetime.now().isoformat()
                issue_data['tracking']['update_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'parent_issue_update',
                    'github_updated': updated_issue.get('updated_at')
                })
            
            # 保存更新后的数据
            save_issue_data(issue_number, issue_data)
            print(f"🔄 已更新Issue #{issue_number}的本地缓存")
    except Exception as e:
        print(f"⚠️  更新Issue #{issue_number}本地缓存失败: {e}")

def get_all_v01_issues():
    """获取所有milestone为v0.1的issues"""
    v01_issues = []
    
    if not DATA_DIR.exists():
        print(f"❌ 数据目录不存在: {DATA_DIR}")
        return v01_issues
    
    for issue_file in DATA_DIR.glob("issue_*.json"):
        try:
            issue_number = int(issue_file.stem.split('_')[1])
            issue_data = load_issue_data(issue_number)
            
            if not issue_data:
                continue
            
            # 检查milestone
            milestone = issue_data.get('metadata', {}).get('milestone')
            if milestone and milestone.get('title') == 'v0.1':
                v01_issues.append((issue_number, issue_data))
                
        except (ValueError, IndexError):
            continue
    
    return sorted(v01_issues, key=lambda x: x[0])

def main():
    print("🚀 开始修复和完善milestone为v0.1的issues的parent issues...")
    print(f"📂 数据目录: {DATA_DIR}")
    
    # 获取所有v0.1 milestone的issues
    v01_issues = get_all_v01_issues()
    
    if not v01_issues:
        print("❌ 没有找到milestone为v0.1的issues")
        return
    
    print(f"📊 找到 {len(v01_issues)} 个milestone为v0.1的issues")
    
    # 统计
    stats = {
        'total': 0,
        'skipped_parent_issues': 0,
        'documentation': 0,
        'kernel': 0,
        'apps': 0,
        'middleware': 0,
        'intellistream': 0,
        'github_actions': 0,  # 新增github-actions统计
        'no_team': 0,
        'success': 0,
        'failed': 0
    }
    
    # 逐个处理
    for issue_number, issue_data in v01_issues:
        stats['total'] += 1
        
        # 跳过parent issues本身
        if issue_number in PARENT_ISSUES:
            print(f"⏭️  跳过parent issue #{issue_number}")
            stats['skipped_parent_issues'] += 1
            continue
        
        # 判断是否为documentation类型
        if is_documentation_issue(issue_data):
            print(f"📚 Issue #{issue_number} 识别为documentation类型，设置parent为 #{DOCUMENTATION_PARENT}")
            if set_parent_issue_github(issue_number, DOCUMENTATION_PARENT):
                stats['documentation'] += 1
                stats['success'] += 1
            else:
                stats['failed'] += 1
            continue
        
        # 根据assignees确定团队
        assignees = issue_data.get('metadata', {}).get('assignees', [])
        team = get_team_for_assignees(assignees)
        
        if not team:
            print(f"⚠️  Issue #{issue_number} 无法确定团队归属 (assignees: {assignees})")
            stats['no_team'] += 1
            continue
        
        parent_issue = TEAM_MEMBERS[team]["parent_issue"]
        print(f"👥 Issue #{issue_number} 属于 {team} 团队，设置parent为 #{parent_issue}")
        
        if set_parent_issue_github(issue_number, parent_issue):
            # 正确统计团队类型
            if team == 'sage-kernel':
                stats['kernel'] += 1
            elif team == 'sage-apps':
                stats['apps'] += 1
            elif team == 'sage-middleware':
                stats['middleware'] += 1
            elif team == 'intellistream':
                stats['intellistream'] += 1
            elif team == 'github-actions':
                stats['github_actions'] += 1
            stats['success'] += 1
        else:
            stats['failed'] += 1
    
    # 输出统计结果
    print("\n" + "="*50)
    print("📊 设置parent issues统计结果:")
    print(f"   总issues数: {stats['total']}")
    print(f"   跳过的parent issues: {stats['skipped_parent_issues']}")
    print(f"   Documentation类型: {stats['documentation']} (parent: #612)")
    print(f"   Kernel团队: {stats['kernel']} (parent: #609)")
    print(f"   Apps团队: {stats['apps']} (parent: #611)")
    print(f"   Middleware团队: {stats['middleware']} (parent: #610)")
    print(f"   IntelliStream团队: {stats['intellistream']} (parent: #612)")
    print(f"   GitHub Actions: {stats['github_actions']} (parent: #612)")
    print(f"   无法确定团队: {stats['no_team']}")
    print(f"   成功设置: {stats['success']}")
    print(f"   设置失败: {stats['failed']}")
    print("="*50)

if __name__ == "__main__":
    main()
