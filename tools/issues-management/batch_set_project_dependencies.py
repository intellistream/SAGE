#!/usr/bin/env python3
"""
在GitHub Projects中设置issue依赖关系的脚本

这个脚本将：
1. 获取GitHub Projects的信息
2. 为milestone为v0.1的issues在相应的项目中设置依赖关系
3. 使用GraphQL API操作新版GitHub Projects
"""

import json
import sys
import os
import requests
from datetime import datetime
from pathlib import Path

# 导入配置
sys.path.insert(0, str(Path(__file__).parent / "_scripts"))
from config import config

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
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28'
}

# GraphQL Headers
GRAPHQL_HEADERS = {
    'Authorization': f'token {config.github_token}',
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json'
}

# 项目映射
PROJECTS = {
    "sage-kernel": {
        "project_id": "PVT_kwDOBQvkz84A_3XD",
        "project_number": 12,
        "parent_issue": 609
    },
    "sage-middleware": {
        "project_id": "PVT_kwDOBQvkz84BBJ_R", 
        "project_number": 13,
        "parent_issue": 610
    },
    "sage-apps": {
        "project_id": "PVT_kwDOBQvkz84BBKB_",
        "project_number": 14,
        "parent_issue": 611
    },
    "intellistream": {
        "project_id": "PVT_kwDOBQvkz84AzzVQ",
        "project_number": 6,
        "parent_issue": 612
    }
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
        "parent_issue": 612
    },
    "github-actions": {
        "members": ["github-actions[bot]"],
        "parent_issue": 612
    }
}

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

def is_documentation_issue(issue_data):
    """判断是否为documentation类型的issue (仅通过labels)"""
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

def graphql_request(query, variables=None):
    """发送GraphQL请求"""
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    response = requests.post(
        "https://api.github.com/graphql",
        headers=GRAPHQL_HEADERS,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ GraphQL请求失败: {response.status_code} - {response.text}")
        return None

def get_project_items(project_id):
    """获取项目中的所有items"""
    query = """
    query($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                items(first: 100) {
                    nodes {
                        id
                        content {
                            ... on Issue {
                                number
                                title
                                url
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {"projectId": project_id}
    result = graphql_request(query, variables)
    
    if result and "data" in result and result["data"]["node"]:
        return result["data"]["node"]["items"]["nodes"]
    return []

def add_issue_to_project(project_id, issue_id):
    """将issue添加到项目中"""
    query = """
    mutation($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
                id
            }
        }
    }
    """
    
    variables = {
        "projectId": project_id,
        "contentId": issue_id
    }
    
    result = graphql_request(query, variables)
    if result and "data" in result and result["data"]["addProjectV2ItemById"]:
        return result["data"]["addProjectV2ItemById"]["item"]["id"]
    return None

def get_issue_node_id(issue_number):
    """获取issue的node ID"""
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
            issue(number: $number) {
                id
                title
                url
            }
        }
    }
    """
    
    variables = {
        "owner": "intellistream",
        "repo": "SAGE", 
        "number": issue_number
    }
    
    result = graphql_request(query, variables)
    if result and "data" in result and result["data"]["repository"]["issue"]:
        return result["data"]["repository"]["issue"]["id"]
    return None

def set_project_dependency(project_id, item_id, dependency_item_id):
    """在项目中设置依赖关系（如果支持的话）"""
    # 注意：GitHub Projects V2的依赖关系功能可能有限制或需要特殊权限
    # 这里先尝试基本的实现
    print(f"⚠️  项目依赖关系设置功能可能需要特殊权限或不完全支持")
    print(f"   项目ID: {project_id}")
    print(f"   Item ID: {item_id}")
    print(f"   依赖Item ID: {dependency_item_id}")
    return True

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
    print("🚀 开始在GitHub Projects中设置issue依赖关系...")
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
        'github_actions': 0,
        'no_team': 0,
        'success': 0,
        'failed': 0,
        'added_to_project': 0
    }
    
    # 首先获取parent issues的node IDs
    parent_node_ids = {}
    for parent_issue in [609, 610, 611, 612]:
        node_id = get_issue_node_id(parent_issue)
        if node_id:
            parent_node_ids[parent_issue] = node_id
            print(f"✅ 获取到parent issue #{parent_issue} 的node ID")
        else:
            print(f"❌ 无法获取parent issue #{parent_issue} 的node ID")
    
    print("\n🔍 开始处理各个team的issues...")
    
    # 按团队处理issues
    for team_name, project_info in PROJECTS.items():
        project_id = project_info["project_id"]
        parent_issue = project_info["parent_issue"]
        
        print(f"\n📋 处理{team_name}团队的项目 (Project #{project_info['project_number']})...")
        
        # 获取该项目的现有items
        existing_items = get_project_items(project_id)
        existing_issue_numbers = set()
        for item in existing_items:
            if item.get("content") and item["content"].get("number"):
                existing_issue_numbers.add(item["content"]["number"])
        
        print(f"   项目中已有 {len(existing_issue_numbers)} 个issues")
        
        # 处理该团队的issues
        team_issues = []
        for issue_number, issue_data in v01_issues:
            stats['total'] += 1
            
            # 跳过parent issues本身
            if issue_number in [609, 610, 611, 612]:
                continue
            
            # 判断team归属
            assignees = issue_data.get('metadata', {}).get('assignees', [])
            issue_team = None
            
            # 判断是否为documentation类型
            if is_documentation_issue(issue_data):
                issue_team = "intellistream"  # documentation归到intellistream项目
            else:
                issue_team = get_team_for_assignees(assignees)
            
            if issue_team == team_name:
                team_issues.append((issue_number, issue_data))
        
        print(f"   找到 {len(team_issues)} 个属于{team_name}团队的issues")
        
        # 将issues添加到项目中
        for issue_number, issue_data in team_issues:
            if issue_number not in existing_issue_numbers:
                # 获取issue的node ID
                issue_node_id = get_issue_node_id(issue_number)
                if issue_node_id:
                    # 将issue添加到项目
                    item_id = add_issue_to_project(project_id, issue_node_id)
                    if item_id:
                        print(f"   ✅ Issue #{issue_number} 已添加到项目")
                        stats['added_to_project'] += 1
                        
                        # 尝试设置依赖关系
                        parent_node_id = parent_node_ids.get(parent_issue)
                        if parent_node_id:
                            set_project_dependency(project_id, item_id, parent_node_id)
                    else:
                        print(f"   ❌ Issue #{issue_number} 添加到项目失败")
                        stats['failed'] += 1
                else:
                    print(f"   ❌ 无法获取Issue #{issue_number} 的node ID")
                    stats['failed'] += 1
            else:
                print(f"   ⏭️  Issue #{issue_number} 已在项目中")
                stats['success'] += 1
    
    # 输出统计结果
    print("\n" + "="*60)
    print("📊 GitHub Projects依赖关系设置统计结果:")
    print(f"   总issues数: {stats['total']}")
    print(f"   添加到项目: {stats['added_to_project']}")
    print(f"   已在项目中: {stats['success']}")
    print(f"   设置失败: {stats['failed']}")
    print("="*60)
    
    print("\n💡 提示:")
    print("   - Issues已被添加到相应的GitHub Projects中")
    print("   - 依赖关系设置可能需要在GitHub Projects界面中手动完成")
    print("   - 新版GitHub Projects的依赖关系API可能有限制")

if __name__ == "__main__":
    main()
