#!/usr/bin/env python3
"""
Enhanced Project Management Tool for SAGE Issues

This script can operate in two modes:
1. Scan organization project #6 for existing items (original mode)
2. Scan all repository issues and assign them to appropriate projects based on author team membership

Features:
- --scan-all: Scan all repository issues (not just project items)
- --scan-project: Scan only organization project #6 items (original mode)
- --apply: Actually execute the moves
- --limit N: Limit processing to N items for testing
"""

import os
import sys
import time
import json
import requests
from pathlib import Path


class IssueProjectMover:
    ORG = "intellistream"
    REPO = "SAGE"
    ORG_PROJECT_NUMBER = 6
    TARGET_TEAMS = {}

    def __init__(self):
        # Get GitHub token from config
        self.github_token = None
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import config as project_config
            self.github_token = getattr(project_config, 'github_token', None)
            if self.github_token:
                print('✅ 从 _scripts/config.py 获取到 GitHub Token')
        except Exception:
            self.github_token = None

        if not self.github_token:
            self.github_token = os.getenv("GITHUB_TOKEN")

        if not self.github_token:
            # Try to find .github_token file
            current_dir = Path(__file__).parent
            for _ in range(5):  # Search up to 5 levels up
                token_file = current_dir / ".github_token"
                if token_file.exists():
                    try:
                        self.github_token = token_file.read_text().strip()
                        print(f'✅ 从文件加载GitHub Token: {token_file}')
                        break
                    except Exception as e:
                        print(f'❌ 读取token文件失败: {e}')
                current_dir = current_dir.parent

        if not self.github_token:
            print("❌ 未找到GitHub Token")
            sys.exit(1)

        self.headers = {"Authorization": f"Bearer {self.github_token}"}
        self.graphql_headers = self.headers.copy()

        # Load team mappings and cached team members
        self.load_team_mappings()
        self.load_cached_team_members()

    def load_team_mappings(self):
        """Load team to project mappings from boards_metadata.json"""
        boards_file = Path(__file__).parent.parent.parent / "boards_metadata.json"
        if boards_file.exists():
            try:
                with open(boards_file, 'r', encoding='utf-8') as f:
                    boards_data = json.load(f)
                    self.TARGET_TEAMS = boards_data.get('team_to_project', {})
                print(f'✅ Loaded boards metadata from {boards_file}')
            except Exception as e:
                print(f'❌ Failed to load boards metadata: {e}')
        else:
            print(f'❌ Boards metadata not found: {boards_file}')

    def load_cached_team_members(self):
        """Load cached team members from meta-data directory"""
        team_file = Path(__file__).parent.parent.parent / "meta-data" / "team_members.json"
        self.cached_team_members = {}
        if team_file.exists():
            try:
                with open(team_file, 'r', encoding='utf-8') as f:
                    self.cached_team_members = json.load(f)
                print(f'✅ Loaded cached team members from {team_file}')
            except Exception as e:
                print(f"⚠️ 无法解析 cached team members: {e}")

        # Load boards metadata if available (team -> org project number)
        try:
            # look in multiple likely locations: meta-data/ first, then fallback locations
            candidate_paths = [
                self.meta_dir / 'boards_metadata.json',  # preferred location: meta-data/
                Path(__file__).parent.parent / 'boards_metadata.json',
                Path(__file__).parent.parent.parent / 'boards_metadata.json',
                Path(__file__).parent.parent.parent.parent / 'boards_metadata.json',
            ]
            loaded = False
            for meta_path in candidate_paths:
                if meta_path and meta_path.exists():
                    mj = json.loads(meta_path.read_text(encoding='utf-8'))
                    mapping = mj.get('team_to_project', {})
                    if mapping:
                        # convert keys to expected dict
                        self.target_teams = {k: int(v) for k, v in mapping.items()}
                        print(f"✅ Loaded boards metadata from {meta_path}")
                        loaded = True
                        break
            if not loaded:
                print("❌ 未找到 boards_metadata.json 中的 team -> project 映射。请在 tools/issues-management/boards_metadata.json 中提供映射后重试。")
                sys.exit(1)
        except Exception as e:
            print(f"❌ 获取Issues失败: {e}")
            return []

    def get_org_project(self):
        """Get organization project data (original functionality)"""
        # Implementation from original project_manage.py
        query = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {self.ORG_PROJECT_NUMBER}) {{
            id title number
        }}
    }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query})
        if resp.status_code != 200:
            print(f"❌ GraphQL 查询失败: {resp.status_code} - {resp.text}")
            return None
            
        data = resp.json()
        if "errors" in data:
            print(f"❌ GraphQL 返回错误: {data['errors']}")
            return None
            
        proj_meta = data.get("data", {}).get("organization", {}).get("projectV2")
        if not proj_meta:
            print(f"❌ 未找到组织项目 #{self.ORG_PROJECT_NUMBER}")
            return None

        # Get project items (issues)
        all_nodes = []
        after = None
        
        while True:
            after_clause = f', after: "{after}"' if after else ''
            query_items = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {self.ORG_PROJECT_NUMBER}) {{
            items(first: 100{after_clause}) {{
                pageInfo {{ hasNextPage endCursor }}
                nodes {{
                    id
                    content {{
                        __typename
                        ... on Issue {{ id number title author {{ login }} repository {{ name owner {{ login }} }} }}
                    }}
                }}
            }}
        }}
    }}
}}'''

            resp2 = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query_items})
            if resp2.status_code != 200:
                print(f"❌ GraphQL items 查询失败: {resp2.status_code} - {resp2.text}")
                break
                
            data2 = resp2.json()
            if "errors" in data2:
                print(f"❌ GraphQL items 返回错误: {data2['errors']}")
                break

            items_block = data2.get("data", {}).get("organization", {}).get("projectV2", {}).get("items", {})
            nodes = items_block.get("nodes", [])
            all_nodes.extend(nodes)

            page_info = items_block.get("pageInfo", {})
            if page_info.get("hasNextPage"):
                after = page_info.get("endCursor")
                time.sleep(0.2)
                continue
            else:
                break

        proj_meta["items"] = {"nodes": all_nodes}
        return proj_meta

    def is_user_in_team(self, username, team_slug):
        """Check if user is in team using cached data"""
        if self.cached_team_members:
            team_info = self.cached_team_members.get(team_slug, {})
            members = team_info.get('members', [])
            
            # Handle both list of strings and list of dicts
            if members:
                if isinstance(members[0], dict):
                    member_usernames = [member.get('username', member.get('login', '')) for member in members]
                else:
                    member_usernames = members
                
                return username in member_usernames
        
        return False

    def add_issue_to_project(self, project_id, issue_id):
        """Add an issue to a project using GraphQL"""
        mutation = '''mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item {
      id
    }
  }
}'''
        variables = {"projectId": project_id, "contentId": issue_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("addProjectV2ItemById", {})

    def delete_project_item(self, project_id, item_id):
        """Delete an item from a project using GraphQL"""
        mutation = '''mutation($projectId: ID!, $itemId: ID!) {
  deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
    deletedItemId
  }
}'''
        variables = {"projectId": project_id, "itemId": item_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("deleteProjectV2Item", {})

    def get_project_by_number(self, project_number):
        """Get project metadata by project number"""
        query = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {project_number}) {{
            id title number
        }}
    }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query})
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if "errors" in data:
            return None
            
        return data.get("data", {}).get("organization", {}).get("projectV2")
        """Determine target project for a user based on team membership"""
        for team_slug, project_number in self.TARGET_TEAMS.items():
            if self.is_user_in_team(username, team_slug):
                return team_slug, project_number
        return None, None

    def add_issue_to_project(self, project_id, issue_id):
        """Add issue to project using GraphQL"""
        mutation = '''mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item {
      id
    }
  }
}'''
        variables = {"projectId": project_id, "contentId": issue_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("addProjectV2ItemById", {})

    def delete_project_item(self, project_id, item_id):
        """Delete item from project using GraphQL"""
        mutation = '''mutation($projectId: ID!, $itemId: ID!) {
  deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
    deletedItemId
  }
}'''
        variables = {"projectId": project_id, "itemId": item_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("deleteProjectV2Item", {})

    def get_project_by_number(self, project_number):
        """Get project metadata by project number"""
        query = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {project_number}) {{
            id title number
        }}
    }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query})
        if resp.status_code != 200:
            print(f"❌ GraphQL 查询项目#{project_number}失败: {resp.status_code} - {resp.text}")
            return None
            
        data = resp.json()
        if "errors" in data:
            print(f"❌ GraphQL 返回错误: {data['errors']}")
            return None
            
        return data.get("data", {}).get("organization", {}).get("projectV2")

    def get_target_project_for_user(self, username):
        """Determine target project for a user based on team membership"""
        for team_slug, project_number in self.TARGET_TEAMS.items():
            if self.is_user_in_team(username, team_slug):
                return team_slug, project_number
        return None, None

    def scan_all_issues(self, limit=None):
        """Scan all repository issues and generate move plan"""
        print("🔍 扫描仓库中的所有Issues...")
        
        issues = self.get_all_repository_issues()
        if not issues:
            print("❌ 无法获取Issues数据")
            return []

        actions = []
        processed = 0
        
        for idx, issue in enumerate(issues, 1):
            if limit and processed >= limit:
                print(f"已达到 limit={limit}，停止处理")
                break
                
            issue_number = issue.get('number')
            issue_title = issue.get('title', '')
            author_login = issue.get('user', {}).get('login', '') if issue.get('user') else ''
            issue_state = issue.get('state', 'unknown')
            
            print(f"[{idx}/{len(issues)}] Issue #{issue_number} ({issue_title}) by {author_login}")
            
            if not author_login:
                print(f"  ⚠️ 作者信息缺失，跳过")
                continue
            
            # Check team membership
            target_team, target_project = self.get_target_project_for_user(author_login)
            
            if target_team and target_project:
                print(f"  ✅ 作者属于团队 '{target_team}'，目标项目编号: {target_project}")
                
                # Add to actions list
                action = {
                    'type': 'add_to_project',
                    'issue_number': issue_number,
                    'issue_title': issue_title,
                    'author': author_login,
                    'target_team': target_team,
                    'target_project': target_project,
                    'issue_state': issue_state,
                    'issue_url': issue.get('html_url', '')
                }
                actions.append(action)
                processed += 1
            else:
                print(f"  ⚠️ 作者 '{author_login}' 不属于任何目标团队")

        return actions

    def scan_project_issues(self, limit=None):
        """Scan organization project issues (original mode)"""
        print(f"🔍 扫描组织项目 #{self.ORG_PROJECT_NUMBER} 中的Issues...")
        
        proj = self.get_org_project()
        if not proj:
            print("❌ 未能获取组织项目，请检查权限或编号是否正确")
            return []

        project_title = proj.get("title")
        items = proj.get("items", {}).get("nodes", [])
        print(f"✅ 项目: {project_title}，条目数: {len(items)}")

        actions = []
        processed = 0

        for idx, node in enumerate(items, 1):
            if limit and processed >= limit:
                print(f"已达到 limit={limit}，停止处理")
                break

            item_id = node.get("id")
            content = node.get("content") or {}
            typename = content.get("__typename")

            if typename != "Issue":
                print(f"[{idx}/{len(items)}] 跳过非Issue项目: item_id={item_id} type={typename}")
                continue

            issue_number = content.get("number")
            issue_title = content.get("title")
            author = (content.get("author") or {}).get("login")
            repo_name = (content.get("repository") or {}).get("name")

            print(f"[{idx}/{len(items)}] Issue #{issue_number} ({issue_title}) by {author} in repo {repo_name}")

            if not author:
                print(f"  ⚠️ 作者信息缺失，跳过")
                continue

            target_team, target_project = self.get_target_project_for_user(author)
            
            if target_team and target_project:
                print(f"  ✅ 作者属于团队 '{target_team}'，目标项目编号: {target_project}")
                
                action = {
                    'type': 'move_from_org_project',
                    'item_id': item_id,
                    'issue_number': issue_number,
                    'issue_title': issue_title,
                    'author': author,
                    'target_team': target_team,
                    'target_project': target_project,
                    'repo_name': repo_name
                }
                actions.append(action)
                processed += 1
            else:
                print(f"  ⚠️ 作者 '{author}' 不属于任何目标团队")

        return actions

    def save_plan(self, actions, scan_mode):
        """Save the move plan to a JSON file"""
        timestamp = int(time.time())
        output_dir = Path(__file__).parent.parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        plan_file = output_dir / f"project_move_plan_{timestamp}.json"
        
        plan_data = {
            'timestamp': timestamp,
            'scan_mode': scan_mode,
            'total_actions': len(actions),
            'actions': actions,
            'summary': f"Generated {len(actions)} move actions using {scan_mode} mode"
        }
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 计划已写入: {plan_file} (未实际执行，传入 --apply 来执行移动)")
        return plan_file

    def execute_actions(self, actions):
        """Execute the move actions for repository issues"""
        if not actions:
            print("📭 没有需要执行的操作")
            return True
        
        print(f"⚡ 开始执行 {len(actions)} 个移动操作...")
        
        success_count = 0
        for i, action in enumerate(actions, 1):
            print(f"[{i}/{len(actions)}] 处理 Issue #{action['issue_number']}: {action['issue_title']}")
            
            try:
                # Get target project metadata
                target_project = self.get_project_by_number(action['target_project'])
                if not target_project:
                    print(f"  ❌ 无法获取目标项目 #{action['target_project']}")
                    continue
                
                # Get the issue's GraphQL node ID
                issue_query = f'''query {{
    repository(owner: "{self.ORG}", name: "{self.REPO}") {{
        issue(number: {action['issue_number']}) {{
            id
        }}
    }}
}}'''
                
                resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": issue_query})
                if resp.status_code != 200:
                    print(f"  ❌ 无法获取Issue GraphQL ID")
                    continue
                
                issue_data = resp.json()
                if "errors" in issue_data:
                    print(f"  ❌ GraphQL错误: {issue_data['errors']}")
                    continue
                
                issue_id = issue_data.get("data", {}).get("repository", {}).get("issue", {}).get("id")
                if not issue_id:
                    print(f"  ❌ 无法获取Issue ID")
                    continue
                
                # Add to target project
                success, result = self.add_issue_to_project(target_project['id'], issue_id)
                if success:
                    print(f"  ✅ 已添加到项目 {target_project['title']}")
                    success_count += 1
                else:
                    print(f"  ❌ 添加到项目失败: {result}")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"  ❌ 执行失败: {e}")
        
        print(f"\n🎉 执行完成！成功处理 {success_count}/{len(actions)} 个操作")
        return success_count > 0

    def execute_plan(self, actions):
        """Execute the move plan by actually adding issues to projects"""
        if not actions:
            print("📭 没有操作需要执行")
            return True
        
        print(f"🚀 开始执行 {len(actions)} 个移动操作...")
        success_count = 0
        
        for idx, action in enumerate(actions, 1):
            print(f"\n[{idx}/{len(actions)}] 处理 Issue #{action.get('issue_number')}...")
            
            try:
                # Get target project metadata
                target_project_number = action.get('target_project')
                if not target_project_number:
                    print(f"  ❌ 缺少目标项目编号")
                    continue
                
                target_project = self.get_project_by_number(target_project_number)
                if not target_project:
                    print(f"  ❌ 无法获取目标项目 #{target_project_number}")
                    continue
                
                print(f"  📦 目标项目: {target_project.get('title')} (#{target_project.get('number')})")
                
                # For scan-all mode, we need to get the issue GraphQL ID
                if action.get('type') == 'add_to_project':
                    # Get issue GraphQL ID using REST API
                    issue_number = action.get('issue_number')
                    
                    # Convert issue number to GraphQL node ID
                    issue_url = f"https://api.github.com/repos/{self.ORG}/{self.REPO}/issues/{issue_number}"
                    resp = requests.get(issue_url, headers=self.headers)
                    
                    if resp.status_code != 200:
                        print(f"  ❌ 获取Issue信息失败: {resp.status_code}")
                        continue
                    
                    issue_data = resp.json()
                    issue_node_id = issue_data.get('node_id')
                    
                    if not issue_node_id:
                        print(f"  ❌ 无法获取Issue的GraphQL节点ID")
                        continue
                    
                    # Add issue to target project
                    ok, resp = self.add_issue_to_project(target_project.get('id'), issue_node_id)
                    if ok:
                        print(f"  ✅ 已添加到项目 {target_project.get('title')}")
                        success_count += 1
                    else:
                        print(f"  ❌ 添加到项目失败: {resp}")
                
                elif action.get('type') == 'move_from_org_project':
                    # This is for moving from org project #6 to target project
                    issue_node_id = action.get('issue_node_id')
                    item_id = action.get('item_id')
                    
                    if not issue_node_id or not item_id:
                        print(f"  ❌ 缺少必要的ID信息")
                        continue
                    
                    # Add to target project
                    ok, resp = self.add_issue_to_project(target_project.get('id'), issue_node_id)
                    if not ok:
                        print(f"  ❌ 添加到目标项目失败: {resp}")
                        continue
                    print(f"  ✅ 已添加到目标项目")
                    
                    # Remove from original org project
                    org_project = self.get_project_by_number(self.ORG_PROJECT_NUMBER)
                    if org_project:
                        ok2, resp2 = self.delete_project_item(org_project.get('id'), item_id)
                        if ok2:
                            print(f"  ✅ 已从组织项目移除")
                            success_count += 1
                        else:
                            print(f"  ❌ 从组织项目删除失败: {resp2}")
                    else:
                        print(f"  ⚠️ 无法获取组织项目信息，跳过删除步骤")
                        success_count += 1  # 仍然算作成功，因为已添加到目标项目
                
                # Be gentle with the API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
                continue
        
        print(f"\n🎉 执行完成！成功处理 {success_count}/{len(actions)} 个操作")
        return success_count > 0

    def run(self, scan_mode="project", apply_changes=False, limit=None):
        """Main execution function"""
        if scan_mode == "all":
            actions = self.scan_all_issues(limit=limit)
        else:
            actions = self.scan_project_issues(limit=limit)
        
        if actions:
            plan_file = self.save_plan(actions, scan_mode)
            
            if apply_changes:
                print(f"\n⚡ 开始执行移动计划...")
                return self.execute_actions(actions)
            else:
                print(f"\n💡 要执行计划，请运行: python3 {__file__} --apply --scan-{scan_mode}")
                return True
        else:
            print("\n📭 没有找到需要移动的Issues")
            return True


def parse_args(argv):
    """Parse command line arguments"""
    apply_changes = False
    scan_mode = "project"  # default to original mode for backward compatibility
    limit = None
    
    if "--scan-all" in argv:
        scan_mode = "all"
    elif "--scan-project" in argv:
        scan_mode = "project"
    
    if "--apply" in argv:
        apply_changes = True
    
    if "--limit" in argv:
        try:
            i = argv.index("--limit")
            limit = int(argv[i+1])
        except Exception:
            print("--limit 需要一个整数参数，例如 --limit 10")
            sys.exit(1)
    
    if "-h" in argv or "--help" in argv:
        print("""用法: project_manage.py [选项]

选项:
  --scan-all        扫描仓库中的所有Issues (新功能)
  --scan-project    扫描组织项目#6中的Issues (原始模式，默认)
  --apply           实际执行移动操作 (默认只生成计划)
  --limit N         限制处理数量 (用于测试)
  -h, --help        显示此帮助信息

示例:
  python3 project_manage.py                    # 扫描组织项目#6 (默认，兼容原版本)
  python3 project_manage.py --scan-all         # 扫描所有仓库Issues  
  python3 project_manage.py --apply            # 扫描组织项目#6并执行移动
  python3 project_manage.py --scan-all --apply # 扫描所有Issues并执行移动
""")
        sys.exit(0)
    
    return apply_changes, scan_mode, limit


if __name__ == "__main__":
    try:
        apply_changes, scan_mode, limit = parse_args(sys.argv[1:])
        mover = IssueProjectMover()
        mover.run(scan_mode=scan_mode, apply_changes=apply_changes, limit=limit)
    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
