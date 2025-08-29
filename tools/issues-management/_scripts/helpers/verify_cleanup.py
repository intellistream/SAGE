#!/usr/bin/env python3
"""
验证和清理脚本

用于验证已移动的Issues的状态，并清理可能存在的API数据不一致问题。
"""

import os
import sys
import requests
import time
from pathlib import Path


class StatusVerifier:
    def __init__(self):
        # Get GitHub token
        self.github_token = None
        token_file = Path('/home/shuhao/SAGE/.github_token')
        if token_file.exists():
            self.github_token = token_file.read_text().strip()
        
        if not self.github_token:
            print("❌ 未找到GitHub Token")
            sys.exit(1)
        
        self.headers = {"Authorization": f"Bearer {self.github_token}"}
        self.ORG = "intellistream"
        self.REPO = "SAGE"

    def check_issue_project_status(self, issue_number):
        """检查Issue的完整项目关联状态"""
        print(f"\n🔍 检查 Issue #{issue_number} 的状态...")
        
        # 1. 获取Issue基本信息
        issue_url = f"https://api.github.com/repos/{self.ORG}/{self.REPO}/issues/{issue_number}"
        resp = requests.get(issue_url, headers=self.headers)
        
        if resp.status_code != 200:
            print(f"❌ 无法获取Issue #{issue_number}: {resp.status_code}")
            return None
        
        issue_data = resp.json()
        issue_id = issue_data.get('node_id')
        
        print(f"📄 Issue #{issue_number}: {issue_data.get('title', '无标题')[:80]}...")
        print(f"📊 状态: {issue_data.get('state', 'unknown')}")
        print(f"🔗 GraphQL ID: {issue_id}")
        
        # 2. 使用GraphQL检查项目关联
        query = f'''query {{
  node(id: "{issue_id}") {{
    ... on Issue {{
      number
      title
      projectItems(first: 10) {{
        nodes {{
          id
          project {{
            title
            number
          }}
        }}
      }}
    }}
  }}
}}'''
        
        resp2 = requests.post("https://api.github.com/graphql", headers=self.headers, json={"query": query})
        
        if resp2.status_code != 200:
            print(f"❌ GraphQL查询失败: {resp2.status_code}")
            return None
        
        data = resp2.json()
        if "errors" in data:
            print(f"❌ GraphQL错误: {data['errors']}")
            return None
        
        project_items = data.get("data", {}).get("node", {}).get("projectItems", {}).get("nodes", [])
        
        if project_items:
            print("🔗 根据GraphQL API，关联的项目:")
            for item in project_items:
                project = item.get("project", {})
                item_id = item.get("id")
                print(f"   - {project.get('title', 'Unknown')} (#{project.get('number', '?')}) [Item ID: {item_id}]")
        else:
            print("✅ 根据GraphQL API，不在任何项目中")
        
        # 3. 直接检查各个项目中是否真的包含这个Issue
        print("\n🔍 验证各个项目的实际内容:")
        
        for project_num in [6, 12, 13, 14]:
            self.verify_issue_in_project(issue_number, project_num)
        
        return {
            "issue_data": issue_data,
            "project_items": project_items
        }

    def verify_issue_in_project(self, issue_number, project_number):
        """直接验证Issue是否真的在指定项目中"""
        print(f"   🔍 检查项目 #{project_number}...")
        
        # 使用分页获取项目的所有条目
        all_items = []
        after = None
        
        while True:
            after_clause = f', after: "{after}"' if after else ''
            query = f'''query {{
  organization(login: "{self.ORG}") {{
    projectV2(number: {project_number}) {{
      title
      items(first: 100{after_clause}) {{
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          id
          content {{
            __typename
            ... on Issue {{ 
              number
              repository {{ name }}
            }}
          }}
        }}
      }}
    }}
  }}
}}'''
            
            resp = requests.post("https://api.github.com/graphql", headers=self.headers, json={"query": query})
            if resp.status_code != 200:
                print(f"      ❌ 查询失败: {resp.status_code}")
                return False
            
            data = resp.json()
            if "errors" in data:
                print(f"      ❌ GraphQL错误: {data['errors']}")
                return False
            
            project = data.get("data", {}).get("organization", {}).get("projectV2")
            if not project:
                print(f"      ❌ 项目不存在")
                return False
            
            items_block = project.get("items", {})
            nodes = items_block.get("nodes", [])
            all_items.extend(nodes)
            
            page_info = items_block.get("pageInfo", {})
            if page_info.get("hasNextPage"):
                after = page_info.get("endCursor")
                time.sleep(0.1)
                continue
            else:
                break
        
        # 检查是否包含目标Issue
        found = False
        for item in all_items:
            content = item.get("content", {})
            if (content.get("__typename") == "Issue" and 
                content.get("number") == issue_number and
                content.get("repository", {}).get("name") == self.REPO):
                found = True
                print(f"      ✅ 项目 #{project_number} ({project.get('title', 'Unknown')}) 实际包含 Issue #{issue_number}")
                break
        
        if not found:
            print(f"      ❌ 项目 #{project_number} ({project.get('title', 'Unknown')}) 实际不包含 Issue #{issue_number}")
        
        return found

    def clean_orphaned_project_items(self, issue_number, dry_run=True):
        """清理孤立的项目条目（GraphQL显示存在但项目中实际不存在的）"""
        print(f"\n🧹 {'预览' if dry_run else '执行'}清理 Issue #{issue_number} 的孤立项目条目...")
        
        status = self.check_issue_project_status(issue_number)
        if not status:
            return False
        
        project_items = status["project_items"]
        
        if not project_items:
            print("✅ 没有需要清理的项目关联")
            return True
        
        # 对每个GraphQL显示的项目关联，验证是否真实存在
        for item in project_items:
            project = item.get("project", {})
            project_num = project.get("number")
            project_title = project.get("title", "Unknown")
            item_id = item.get("id")
            
            print(f"\n📋 处理项目关联: {project_title} (#{project_num})")
            
            # 验证是否真实存在
            actually_exists = self.verify_issue_in_project(issue_number, project_num)
            
            if not actually_exists:
                print(f"⚠️ 发现孤立的项目关联: Item ID {item_id}")
                if not dry_run:
                    # 尝试删除孤立的项目条目
                    success = self.remove_project_item(project_num, item_id)
                    if success:
                        print(f"✅ 成功清理孤立的项目关联")
                    else:
                        print(f"❌ 清理失败")
                else:
                    print(f"🔍 预览模式: 将删除 Item ID {item_id}")
        
        return True

    def remove_project_item(self, project_number, item_id):
        """删除项目中的指定条目"""
        # 首先获取项目ID
        query = f'''query {{
  organization(login: "{self.ORG}") {{
    projectV2(number: {project_number}) {{
      id
      title
    }}
  }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql", headers=self.headers, json={"query": query})
        if resp.status_code != 200:
            return False
        
        data = resp.json()
        if "errors" in data:
            return False
        
        project = data.get("data", {}).get("organization", {}).get("projectV2")
        if not project:
            return False
        
        project_id = project.get("id")
        
        # 删除项目条目
        mutation = '''mutation($projectId: ID!, $itemId: ID!) {
  deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
    deletedItemId
  }
}'''
        
        variables = {"projectId": project_id, "itemId": item_id}
        resp2 = requests.post("https://api.github.com/graphql", headers=self.headers, json={"query": mutation, "variables": variables})
        
        if resp2.status_code != 200:
            return False
        
        data2 = resp2.json()
        if "errors" in data2:
            print(f"      ❌ 删除错误: {data2['errors']}")
            return False
        
        return True


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_cleanup.py <issue_number> [--clean]")
        print("例如: python3 verify_cleanup.py 379")
        print("      python3 verify_cleanup.py 379 --clean  # 实际执行清理")
        sys.exit(1)
    
    try:
        issue_number = int(sys.argv[1])
    except ValueError:
        print("❌ Issue编号必须是数字")
        sys.exit(1)
    
    dry_run = "--clean" not in sys.argv[2:]
    
    verifier = StatusVerifier()
    
    print(f"🔍 验证 Issue #{issue_number} 的状态...")
    verifier.check_issue_project_status(issue_number)
    
    print(f"\n🧹 清理孤立的项目关联 ({'预览模式' if dry_run else '执行模式'})...")
    verifier.clean_orphaned_project_items(issue_number, dry_run=dry_run)
    
    if dry_run:
        print(f"\n💡 要实际执行清理，请运行: python3 {__file__} {issue_number} --clean")


if __name__ == "__main__":
    main()
