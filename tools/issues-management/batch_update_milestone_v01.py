#!/usr/bin/env python3
"""
临时脚本V2：批量修改SAGE项目在8月15日前创建的issues的milestone为v0.1

条件：
1. 属于SAGE项目（intellistream/SAGE）
2. 状态为closed或open
3. 在2025年8月15日之前创建的issues（不管是否已关闭）
4. 将milestone设置为v0.1 (milestone #1)

修复：
- 使用GitHub API标准的milestone格式
- 包括open状态的issues
"""

import json
import sys
import requests
from datetime import datetime
from pathlib import Path

# 设置路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = Path("/home/shuhao/SAGE/output/issues-workspace")
DATA_DIR = WORKSPACE_DIR / "data"

# 截止日期
CUTOFF_DATE = datetime(2025, 8, 15)

def load_github_token():
    """加载GitHub Token"""
    token_file = Path("/home/shuhao/SAGE/.github_token")
    if token_file.exists():
        return token_file.read_text().strip()
    return None

def get_milestone_from_github():
    """从GitHub API获取v0.1 milestone的标准格式"""
    token = load_github_token()
    if not token:
        print("❌ 无法加载GitHub Token")
        return None
    
    headers = {"Authorization": f"token {token}"}
    url = "https://api.github.com/repos/intellistream/SAGE/milestones"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        milestones = response.json()
        
        for milestone in milestones:
            if milestone.get('title') == 'v0.1':
                print(f"✅ 获取到v0.1 milestone标准格式")
                return milestone
        
        print("❌ 未找到v0.1 milestone")
        return None
        
    except Exception as e:
        print(f"❌ 获取milestone失败: {e}")
        return None

def load_issue_data(issue_number):
    """加载issue数据"""
    issue_file = DATA_DIR / f"issue_{issue_number}.json"
    if not issue_file.exists():
        return None
    
    try:
        with open(issue_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取issue {issue_number}失败: {e}")
        return None

def save_issue_data(issue_number, data):
    """保存issue数据"""
    issue_file = DATA_DIR / f"issue_{issue_number}.json"
    try:
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 保存issue {issue_number}失败: {e}")
        return False

def parse_datetime(date_str):
    """解析GitHub时间格式"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        return None

def check_conditions(issue_data):
    """检查issue是否符合修改条件"""
    metadata = issue_data.get('metadata', {})
    
    # 1. 检查状态（现在接受both closed和open）
    state = metadata.get('state')
    if state not in ['closed', 'open']:
        return False, f"状态不是closed或open: {state}"
    
    # 2. 检查是否已经有v0.1 milestone
    current_milestone = metadata.get('milestone')
    if current_milestone and current_milestone.get('title') == 'v0.1':
        return False, "已经是v0.1 milestone"
    
    # 3. 检查创建时间是否在8月15日之前（改为created_at而不是closed_at）
    created_at_str = metadata.get('created_at')
    if not created_at_str:
        return False, "没有创建时间"
    
    created_at = parse_datetime(created_at_str)
    if not created_at or created_at >= CUTOFF_DATE:
        return False, f"创建时间不符合条件: {created_at}"
    
    # 4. 检查URL确认是SAGE项目
    html_url = metadata.get('html_url', '')
    if 'intellistream/SAGE' not in html_url:
        return False, "不是SAGE项目的issue"
    
    return True, "符合条件"

def main():
    print("🔍 扫描SAGE项目issues，查找需要修改milestone的issues...")
    print(f"📅 条件：在{CUTOFF_DATE.strftime('%Y-%m-%d')}之前创建的issues（包括open和closed）")
    print(f"🎯 目标：设置milestone为v0.1")
    print()
    
    # 获取GitHub API标准的milestone格式
    target_milestone = get_milestone_from_github()
    if not target_milestone:
        return 1
    
    if not DATA_DIR.exists():
        print(f"❌ 数据目录不存在: {DATA_DIR}")
        return 1
    
    # 扫描所有issue文件
    issue_files = list(DATA_DIR.glob("issue_*.json"))
    print(f"📁 发现 {len(issue_files)} 个issue文件")
    
    matching_issues = []
    
    for issue_file in issue_files:
        issue_number = int(issue_file.stem.split('_')[1])
        issue_data = load_issue_data(issue_number)
        
        if not issue_data:
            continue
        
        meets_conditions, reason = check_conditions(issue_data)
        if meets_conditions:
            metadata = issue_data['metadata']
            created_at = parse_datetime(metadata.get('created_at'))
            current_milestone = metadata.get('milestone')
            current_milestone_title = current_milestone.get('title') if current_milestone else 'None'
            
            matching_issues.append({
                'number': issue_number,
                'title': metadata.get('title', ''),
                'state': metadata.get('state'),
                'created_at': created_at,
                'current_milestone': current_milestone_title,
                'data': issue_data
            })
            
            print(f"✅ Issue #{issue_number} ({metadata.get('state')}): {metadata.get('title', '')[:50]}...")
            print(f"   创建时间: {created_at}")
            print(f"   当前milestone: {current_milestone_title}")
    
    if not matching_issues:
        print("\n✅ 没有找到符合条件的issues")
        return 0
    
    # 统计
    open_count = len([i for i in matching_issues if i['state'] == 'open'])
    closed_count = len([i for i in matching_issues if i['state'] == 'closed'])
    
    print(f"\n📋 总共找到 {len(matching_issues)} 个符合条件的issues:")
    print(f"   🟢 Open: {open_count} 个")
    print(f"   🔴 Closed: {closed_count} 个")
    
    # 确认操作
    response = input(f"\n是否要将这 {len(matching_issues)} 个issues的milestone设置为v0.1? (y/N): ").lower().strip()
    
    if response != 'y':
        print("❌ 操作已取消")
        return 0
    
    # 执行修改
    print(f"\n🚀 开始修改milestone...")
    success_count = 0
    
    for issue_info in matching_issues:
        issue_number = issue_info['number']
        issue_data = issue_info['data']
        
        # 修改milestone为GitHub API标准格式
        issue_data['metadata']['milestone'] = target_milestone
        
        # 更新tracking信息
        if 'tracking' not in issue_data:
            issue_data['tracking'] = {}
        
        if 'update_history' not in issue_data['tracking']:
            issue_data['tracking']['update_history'] = []
        
        issue_data['tracking']['update_history'].append({
            'timestamp': datetime.now().isoformat(),
            'action': 'milestone_batch_update_v2',
            'changes': 'Set milestone to v0.1 (using GitHub API format)',
            'script': 'batch_update_milestone_v01_v2.py',
            'state': issue_info['state']
        })
        
        # 保存文件
        if save_issue_data(issue_number, issue_data):
            success_count += 1
            print(f"✅ Issue #{issue_number} ({issue_info['state']}): milestone已更新为v0.1")
        else:
            print(f"❌ Issue #{issue_number}: 更新失败")
    
    print(f"\n🎉 批量更新完成!")
    print(f"✅ 成功: {success_count}/{len(matching_issues)} 个issues")
    
    if success_count > 0:
        print(f"\n💡 接下来的步骤:")
        print(f"1. 检查修改结果")
        print(f"2. 使用sync脚本同步到GitHub:")
        print(f"   cd /home/shuhao/SAGE/tools/issues-management")
        print(f"   python3 _scripts/sync_issues.py quick-preview --limit {min(success_count, 20)}")
        print(f"   python3 _scripts/sync_issues.py sync --auto-confirm")
    
    print(f"\n📊 格式说明:")
    print(f"   现在使用GitHub API标准milestone格式，避免同步冲突")
    print(f"   包括open和closed状态的issues")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
