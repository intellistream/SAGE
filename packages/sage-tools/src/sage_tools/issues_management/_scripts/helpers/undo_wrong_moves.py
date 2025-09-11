#!/usr/bin/env python3
"""
撤销错误的项目板移动操作
"""

import sys
import json
from pathlib import Path

# 添加上级目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from github_helper import GitHubProjectManager

def main():
    # 读取错误的修复计划
    plan_file = Path("/home/shuhao/SAGE/output/issues-output/issues_fix_plan_1756542040.json")
    
    if not plan_file.exists():
        print("❌ 修复计划文件不存在")
        return
    
    with open(plan_file, 'r', encoding='utf-8') as f:
        plan_data = json.load(f)
    
    pm = GitHubProjectManager()
    
    print("🔄 开始撤销错误的项目板移动...")
    
    # 需要撤销的ShuhaoZhangTony相关的移动
    shuhaozhangtony_issues = [
        260, 314, 235,  # 从intellistream -> sage-apps (错误)
        445, 377  # 从sage-kernel -> sage-apps (错误) 
    ]
    
    for fix in plan_data["fixes"]:
        issue_number = fix["issue_number"]
        responsible_user = fix["responsible_user"]
        
        # 只撤销ShuhaoZhangTony相关的错误移动
        if responsible_user == "ShuhaoZhangTony" and issue_number in shuhaozhangtony_issues:
            current_project = fix["target_project"]  # 当前错误的位置
            original_project = fix["current_project"]  # 原来正确的位置
            
            print(f"🔄 撤销Issue #{issue_number}: 从项目#{current_project} 回到 项目#{original_project}")
            
            # 添加回原项目
            success1 = pm.add_issue_to_project("intellistream", "SAGE", issue_number, original_project)
            if success1:
                print(f"  ✅ 成功添加到项目#{original_project}")
                
                # 从错误项目中删除
                success2 = pm.remove_issue_from_project("intellistream", "SAGE", issue_number, current_project)
                if success2:
                    print(f"  ✅ 成功从项目#{current_project}中删除")
                else:
                    print(f"  ⚠️ 从项目#{current_project}删除失败")
            else:
                print(f"  ❌ 添加到项目#{original_project}失败")
    
    print("✅ 撤销操作完成")

if __name__ == "__main__":
    main()
