#!/usr/bin/env python3
"""
Move issues from the organization's public project (org project #6)
into repo-level projects for sage-apps, sage-middleware, and sage-kernel
based on the issue author's team membership.

Behavior:
- Lists items in org project number 6
- For each item that is an Issue, checks the author's username
- Determines which target team the author belongs to (checks teams: sage-apps, sage-middleware, sage-kernel)
- Finds the corresponding repository project (repo: sage-apps / sage-middleware / sage-kernel) and adds the issue
- Removes the item from the org project

The script defaults to --dry-run to avoid accidental destructive changes; pass --apply to perform the moves.
"""

import os
import sys
import time
import json
import requests
from pathlib import Path


class ProgressBar:
    """简单的文本进度条类"""
    
    def __init__(self, total=None, description="处理中"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.dynamic_mode = (total is None)  # 动态模式：无预设总数
        self.last_update_time = 0  # 限制更新频率
        
    def update(self, current, force=False):
        """更新进度"""
        self.current = current
        
        # 限制更新频率：每0.2秒更新一次，除非强制更新
        now = time.time()
        if not force and now - self.last_update_time < 0.2:
            return
        self.last_update_time = now
        
        # 计算经过时间
        elapsed = now - self.start_time
        
        if self.dynamic_mode:
            # 动态模式：只显示当前数量和时间
            print(f"\r  📊 {self.description}: {current} 个 ({elapsed:.1f}s)", 
                  end="", flush=True)
        else:
            # 固定模式：显示百分比进度条
            if self.total > 0:
                percentage = min(100, (current * 100) // self.total)
            else:
                percentage = 0
                
            # 计算进度条
            bar_length = 20
            filled_length = int(bar_length * percentage // 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # 输出进度（覆盖当前行）
            print(f"\r  📊 {self.description}: [{bar}] {percentage}% ({current}/{self.total}) {elapsed:.1f}s", 
                  end="", flush=True)
    
    def newline(self):
        """输出换行，为其他信息让位"""
        print()
    
    def finish(self):
        """完成进度条"""
        elapsed = time.time() - self.start_time
        if self.dynamic_mode:
            print(f"\r  ✅ {self.description}: 完成，共 {self.current} 个 ({elapsed:.1f}s)")
        else:
            print(f"\r  ✅ {self.description}: 完成 ({self.current}/{self.total}) {elapsed:.1f}s)")


class IssueProjectMover:
    ORG = "intellistream"
    REPO = "SAGE"  # 添加仓库名
    ORG_PROJECT_NUMBER = 6
    # Mapping is intentionally empty here. The canonical mapping must live in
    # tools/issues-management/boards_metadata.json and will be loaded at runtime.
    TARGET_TEAMS = {}

    def __init__(self):
        # Try to reuse project central config token if available
        self.github_token = None
        try:
            # allow importing _scripts/config.py (helpers is one level deeper)
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import config as project_config
            self.github_token = getattr(project_config, 'github_token', None)
            if self.github_token:
                print('✅ 从 _scripts/config.py 获取到 GitHub Token')
        except Exception:
            self.github_token = None

        # fallback to environment
        if not self.github_token:
            self.github_token = os.getenv("GITHUB_TOKEN")

        # fallback to .github_token files upward from repo
        if not self.github_token:
            # search upward from this file's parent (helpers -> _scripts -> repo)
            p = Path(__file__).resolve()
            for parent in [p.parent, p.parent.parent, p.parent.parent.parent, p.parent.parent.parent.parent]:
                candidate = parent / '.github_token'
                if candidate.exists():
                    t = candidate.read_text().strip()
                    if t:
                        self.github_token = t
                        print(f"✅ 从文件加载GitHub Token: {candidate}")
                        break

        if not self.github_token:
            print("❌ 请设置 GITHUB_TOKEN 环境变量 或 在仓库根目录创建 .github_token 文件")
            sys.exit(1)

        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.graphql_headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json",
        }

        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # prefer meta-data directory for cached team members and boards metadata
        # repo-level meta-data directory: tools/issues-management/meta-data
        self.meta_dir = Path(__file__).parent.parent.parent / 'meta-data'
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        # load cached team members if present
        self.cached_team_members = {}
        cached_members_file = self.meta_dir / 'team_members.json'
        if cached_members_file.exists():
            try:
                self.cached_team_members = json.loads(cached_members_file.read_text(encoding='utf-8'))
                print(f"✅ Loaded cached team members from {cached_members_file}")
            except Exception as e:
                print(f"⚠️ 无法解析 cached team members: {e}")

        # Load boards metadata if available (team -> org project number)
        try:
            # look in multiple likely locations: _scripts/ and repo root (tools/issues-management/)
            candidate_paths = [
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
            print(f"⚠️ 无法加载 boards_metadata.json: {e}")
            self.target_teams = dict(self.TARGET_TEAMS)

    def get_repo_issues_without_projects(self, limit=None, preview_mode=False):
        """获取仓库中未分配到任何项目的Issues
        
        Args:
            limit: 限制返回的Issues数量
            preview_mode: 预览模式，只检查前2页
        """
        print(f"🔍 扫描 {self.ORG}/{self.REPO} 中未分配项目的Issues...")
        if preview_mode:
            print("📋 预览模式：快速扫描前200个Issues")
        
        query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            issues(first: 100, after: $cursor, states: [OPEN]) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                number
                title
                author {
                  login
                }
                assignees(first: 10) {
                  nodes {
                    login
                  }
                }
                projectItems {
                  totalCount
                }
              }
            }
          }
        }
        """
        
        # 假设REPO已经定义，如果没有则使用SAGE
        repo_name = getattr(self, 'REPO', 'SAGE')
        
        variables = {
            "owner": self.ORG,
            "name": repo_name
        }
        
        all_issues = []
        cursor = None
        page = 1
        processed_count = 0
        progress_bar = None
        
        try:
            # 初始化动态进度条 - 跟踪处理的Issues数量
            progress_bar = ProgressBar(description="扫描未分配Issues")
            progress_bar.update(0, force=True)  # 立即显示进度条
            
            while True:
                if cursor:
                    variables["cursor"] = cursor
                else:
                    variables.pop("cursor", None)
                    
                try:
                    resp = requests.post("https://api.github.com/graphql", 
                                       json={"query": query, "variables": variables},
                                       headers={"Authorization": f"Bearer {self.github_token}"},
                                       timeout=30)
                    
                    # 添加API速率限制延迟
                    time.sleep(1)
                    
                    if resp.status_code != 200:
                        progress_bar.newline()
                        print(f"  ❌ API请求失败: {resp.status_code} {resp.text}")
                        break
                        
                    data = resp.json()
                    if "errors" in data:
                        progress_bar.newline()
                        print(f"  ❌ GraphQL错误: {data['errors']}")
                        break
                        
                    issues = data["data"]["repository"]["issues"]
                    nodes = issues["nodes"]
                    
                    # 筛选未分配项目的Issues
                    unassigned_in_page = []
                    for i, issue in enumerate(nodes, 1):
                        project_count = issue.get("projectItems", {}).get("totalCount", 0)
                        if project_count == 0:  # 未分配到任何项目
                            unassigned_in_page.append(issue)
                            processed_count += 1
                            
                            # 实时更新进度条显示新发现的Issues数量
                            total_found = len(all_issues) + len(unassigned_in_page)
                            progress_bar.update(total_found)
                            
                            # 如果达到限制，停止
                            if limit and processed_count >= limit:
                                break
                    
                    all_issues.extend(unassigned_in_page)
                    
                    # 页面完成后显示摘要
                    if unassigned_in_page:
                        progress_bar.newline()
                        print(f"  ✅ 第{page}页: 发现{len(unassigned_in_page)}个未分配Issues")
                    
                    # 检查是否还有下一页和是否达到限制
                    page_info = issues["pageInfo"]
                    
                    # 预览模式只检查前2页
                    if preview_mode and page >= 2:
                        progress_bar.newline()
                        print(f"  📋 预览模式：已检查前{page}页，停止扫描")
                        break
                        
                    if not page_info["hasNextPage"] or (limit and processed_count >= limit):
                        break
                        
                    cursor = page_info["endCursor"]
                    page += 1
                    
                except requests.RequestException as e:
                    print(f"\n  ❌ 网络请求错误: {e}")
                    break
                except Exception as e:
                    print(f"\n  ❌ 处理Issues时出错: {e}")
                    break
        
        finally:
            # 完成进度条（如果已初始化）
            if progress_bar:
                # 确保显示最终的正确数量
                progress_bar.current = len(all_issues)
                progress_bar.finish()
        
        print(f"\n📊 扫描完成：共发现 {len(all_issues)} 个未分配项目的Issues")
        return all_issues

    def get_org_project(self, number=None):
                number = number or self.ORG_PROJECT_NUMBER

                # First fetch basic project info and get the project id
                query_proj = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {number}) {{
            id
            title
            number
            url
        }}
    }}
}}'''

                resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query_proj})
                if resp.status_code != 200:
                        print(f"❌ GraphQL 查询失败: {resp.status_code} - {resp.text}")
                        return None
                data = resp.json()
                if "errors" in data:
                        print(f"❌ GraphQL 返回错误: {data['errors']}")
                        return None

                proj_meta = data.get("data", {}).get("organization", {}).get("projectV2")
                if not proj_meta:
                        return None

                # Page through items (limit 100 per page) to avoid EXCESSIVE_PAGINATION
                all_nodes = []
                after = None
                while True:
                        after_clause = f', after: "{after}"' if after else ''
                        query_items = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {number}) {{
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
                                # gentle pause
                                time.sleep(0.2)
                                continue
                        else:
                                break

                # attach aggregated items
                proj_meta["items"] = {"nodes": all_nodes}
                return proj_meta

    def is_user_in_team(self, username, team_slug):
        # First consult cached_team_members if available
        try:
            if self.cached_team_members:
                team_info = self.cached_team_members.get(team_slug, {})
                members = team_info.get('members', [])
                # members may be list of dicts with 'username' key
                for m in members:
                    if m.get('username') == username:
                        return True
        except Exception:
            pass

        # GitHub REST: GET /orgs/{org}/teams/{team_slug}/members/{username}
        url = f"https://api.github.com/orgs/{self.ORG}/teams/{team_slug}/members/{username}"
        r = requests.get(url, headers=self.headers)
        # 204 or 200 means member (some endpoints return 204). 404 means not a member
        return r.status_code in (200, 204)

    def find_target_repo_project(self, repo_name):
        # Find the first projectV2 of the repository
        query = f'''query {{
  repository(owner: "{self.ORG}", name: "{repo_name}") {{
    projectsV2(first: 20) {{
      nodes {{ id title number url }}
    }}
  }}
}}'''

        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": query})
        if resp.status_code != 200:
            print(f"❌ GraphQL 查询仓库项目失败: {resp.status_code} - {resp.text}")
            return None
        data = resp.json()
        if "errors" in data:
            # No project or permission issue
            return None
        nodes = data.get("data", {}).get("repository", {}).get("projectsV2", {}).get("nodes", [])
        if not nodes:
            return None
        # Prefer a project with the repo name in title or just take first
        for node in nodes:
            if repo_name.lower() in (node.get("title") or "").lower():
                return node
        return nodes[0]

    def add_issue_to_project(self, project_id, issue_node_id):
        mutation = '''mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}'''
        variables = {"projectId": project_id, "contentId": issue_node_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("addProjectV2ItemById", {})

    def delete_project_item(self, item_id):
        mutation = '''mutation($itemId: ID!) {
  deleteProjectV2Item(input: {itemId: $itemId}) {
    deletedItemId
  }
}'''
        variables = {"itemId": item_id}
        resp = requests.post("https://api.github.com/graphql", headers=self.graphql_headers, json={"query": mutation, "variables": variables})
        if resp.status_code != 200:
            return False, resp.text
        data = resp.json()
        if "errors" in data:
            return False, data["errors"]
        return True, data.get("data", {}).get("deleteProjectV2Item", {})

    def run_unassigned_scan(self, apply_changes=False, stage_local=False, limit=None, preview_mode=False):
        """运行未分配Issues扫描模式"""
        print("🔍 模式：扫描仓库中未分配项目的Issues")
        unassigned_issues = self.get_repo_issues_without_projects(limit=limit, preview_mode=preview_mode)
        
        if not unassigned_issues:
            print("✅ 没有发现未分配项目的Issues")
            return
        
        print(f"\n📋 发现 {len(unassigned_issues)} 个未分配项目的Issues:")
        for i, issue in enumerate(unassigned_issues[:10], 1):  # 只显示前10个
            print(f"  {i}. #{issue['number']} - {issue['title'][:50]}{'...' if len(issue['title']) > 50 else ''}")
        
        if len(unassigned_issues) > 10:
            print(f"  ... 还有 {len(unassigned_issues) - 10} 个Issues")
        
        return unassigned_issues

    def run(self, apply_changes=False, stage_local=False, limit=None, scan_unassigned=False):
        # 如果是扫描未分配Issues模式
        if scan_unassigned:
            # 扫描模式不使用预览模式，直接扫描所有Issues
            return self.run_unassigned_scan(apply_changes, stage_local, limit, preview_mode=False)
        
        # 原有的组织项目移动逻辑
        print(f"🔎 检查组织项目 #{self.ORG_PROJECT_NUMBER} ({self.ORG}) 的条目...")
        proj = self.get_org_project()
        if not proj:
            print("❌ 未能获取组织项目，请检查权限或编号是否正确")
            return

        project_title = proj.get("title")
        items = proj.get("items", {}).get("nodes", [])
        print(f"✅ 项目: {project_title}，条目数: {len(items)}")

        actions = []

        processed = 0
        for idx, node in enumerate(items, 1):
            item_id = node.get("id")
            content = node.get("content") or {}
            typename = content.get("__typename")

            if typename != "Issue":
                print(f"[{idx}/{len(items)}] 跳过非Issue项目: item_id={item_id} type={typename}")
                continue

            issue_id = content.get("id")  # GraphQL node id
            issue_number = content.get("number")
            issue_title = content.get("title")
            author = (content.get("author") or {}).get("login")
            repo_name = (content.get("repository") or {}).get("name")

            print(f"[{idx}/{len(items)}] Issue #{issue_number} ({issue_title}) by {author} in repo {repo_name}")

            if not author:
                print("  ⚠️ 无作者信息，跳过")
                continue

            # Determine which team the author belongs to and target org project number
            target_project_number = None
            matched_team = None
            for team_slug, project_number in self.target_teams.items():
                try:
                    member = self.is_user_in_team(author, team_slug)
                except Exception as e:
                    print(f"  ⚠️ 检查团队成员失败: {e}")
                    member = False
                if member:
                    target_project_number = project_number
                    matched_team = team_slug
                    print(f"  ✅ 作者属于团队 '{team_slug}'，目标组织项目编号: {target_project_number}")
                    break

            if not target_project_number:
                print("  ⚠️ 作者不在目标团队列表中，跳过")
                continue

            # Fetch the target org project (ProjectV2) metadata
            target_project = self.get_org_project(number=target_project_number)
            if not target_project:
                print(f"  ❌ 未找到组织项目 #{target_project_number}，跳过")
                continue

            print(f"  📦 目标组织项目: {target_project.get('title')} (number={target_project.get('number')} id={target_project.get('id')})")

            if stage_local:
                # find local markdown file for this issue and annotate it via YAML front-matter
                # try multiple likely locations: _scripts/issues_workspace, repo_root/issues_workspace, tools/issues-management/issues_workspace
                candidates = [
                    Path(__file__).parent.parent / 'issues_workspace' / 'issues',
                    Path(__file__).parent.parent.parent / 'issues_workspace' / 'issues',
                    Path(__file__).parent.parent.parent.parent / 'issues_workspace' / 'issues',
                    Path(__file__).parent.parent.parent / 'issues' ,
                    Path(__file__).parent.parent / 'issues' ,
                    Path(__file__).parent.parent.parent / 'issues' ,
                ]
                issues_dir = None
                for c in candidates:
                    if c and c.exists():
                        issues_dir = c
                        break

                matched = None
                if issues_dir and issues_dir.exists():
                    for f in issues_dir.glob(f"*{issue_number}*.md"):
                        matched = f
                        break
                if matched:
                    file_text = matched.read_text(encoding='utf-8')
                    # Prepare yaml snippet
                    fm = {
                        'to_project_number': target_project_number,
                        'to_project_id': target_project.get('id'),
                        'to_project_title': target_project.get('title'),
                        'staged_at': int(time.time()),
                        'staged_by': 'project_manage.py',
                        'status': 'staged'
                    }
                    # simple front-matter injection/update
                    if file_text.startswith('---'):
                        # split existing front-matter
                        parts = file_text.split('---', 2)
                        # parts: ['', '\nkey: val\n', '\nrest'] or ['', 'yaml', 'rest']
                        if len(parts) >= 3:
                            existing_fm = parts[1]
                            body = parts[2]
                            # if project_move exists, replace it; otherwise append
                            if 'project_move:' in existing_fm:
                                # naive replace: remove old project_move block
                                before, _, after = existing_fm.partition('project_move:')
                                # keep before and append new project_move
                                new_fm = before + 'project_move:\n'
                                for k, v in fm.items():
                                    new_fm += f"  {k}: {v}\n"
                            else:
                                new_fm = existing_fm + '\nproject_move:\n'
                                for k, v in fm.items():
                                    new_fm += f"  {k}: {v}\n"
                            new_text = '---' + new_fm + '---' + body
                        else:
                            # malformed front-matter: replace entirely
                            new_text = '---\nproject_move:\n'
                            for k, v in fm.items():
                                new_text += f"  {k}: {v}\n"
                            new_text += '---\n' + file_text
                    else:
                        # no front-matter: create one
                        new_text = '---\nproject_move:\n'
                        for k, v in fm.items():
                            new_text += f"  {k}: {v}\n"
                        new_text += '---\n\n' + file_text

                    matched.write_text(new_text, encoding='utf-8')
                    print(f"  ✅ 已在本地 front-matter 中标注: {matched}")
                else:
                    print(f"  ⚠️ 未找到本地 markdown 文件来标注 issue #{issue_number}")

                actions.append({
                    "issue_number": issue_number,
                    "issue_title": issue_title,
                    "author": author,
                    "from_project": project_title,
                    "to_team": matched_team,
                    "to_project_number": target_project_number,
                    "to_project_id": target_project.get('id'),
                    "to_project": target_project.get('title'),
                    "item_id": item_id,
                    "issue_node_id": issue_id,
                    "staged": True,
                })
                processed += 1
            elif apply_changes:
                # Add to repo project
                ok, resp = self.add_issue_to_project(target_project.get('id'), issue_id)
                if not ok:
                    print(f"  ❌ 添加到目标项目失败: {resp}")
                    continue
                print(f"  ✅ 已添加到目标项目")

                # Remove original item from org project
                ok2, resp2 = self.delete_project_item(item_id)
                if not ok2:
                    print(f"  ❌ 从原组织项目删除失败: {resp2}")
                else:
                    print(f"  ✅ 已从组织项目移除 (item id: {item_id})")
                # be gentle with the API
                time.sleep(0.5)
            else:
                actions.append({
                    "issue_number": issue_number,
                    "issue_title": issue_title,
                    "author": author,
                    "from_project": project_title,
                    "to_team": matched_team,
                    "to_project_number": target_project_number,
                    "to_project": target_project.get('title'),
                    "item_id": item_id,
                    "issue_node_id": issue_id,
                })
                processed += 1

            if limit and processed >= limit:
                print(f"已达到 limit={limit}，停止处理")
                break

        # Dry-run summary
        if not apply_changes and not stage_local:
            report_path = self.output_dir / f"project_move_plan_{int(time.time())}.json"
            report_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"\n📋 计划已写入: {report_path} (未实际执行，传入 --apply 来执行移动)")
        elif stage_local:
            report_path = self.output_dir / f"project_move_plan_{int(time.time())}.json"
            report_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"\n📋 本地阶段计划已写入: {report_path} (请审查并提交到仓库，随后使用 sync 脚本执行远端变更)")


def parse_args(argv):
    # supported flags:
    # --apply           : perform remote mutations
    # --stage-local     : write plan and annotate local markdown files (local-first staging)
    # --limit N         : limit to N items (for small-batch testing)
    # --scan-unassigned : scan repository for issues not assigned to any project
    apply_changes = False
    stage_local = False
    limit = None
    scan_unassigned = False
    if "--apply" in argv:
        apply_changes = True
    if "--stage-local" in argv:
        stage_local = True
    if "--scan-unassigned" in argv:
        scan_unassigned = True
    if "--limit" in argv:
        try:
            i = argv.index("--limit")
            limit = int(argv[i+1])
        except Exception:
            print("--limit 需要一个整数参数，例如 --limit 10")
            sys.exit(1)
    if "-h" in argv or "--help" in argv:
        print("用法: project_manage.py [--stage-local] [--apply] [--limit N] [--scan-unassigned]\n  --stage-local: 写本地变更并生成 plan（不触达远端）\n  --apply: 对远端执行移动（谨慎）\n  --limit N: 仅处理前 N 条记录（用于试点）\n  --scan-unassigned: 扫描仓库中未分配到任何项目的Issues")
        sys.exit(0)
    return apply_changes, stage_local, limit, scan_unassigned


if __name__ == "__main__":
    try:
        apply_changes, stage_local, limit, scan_unassigned = parse_args(sys.argv[1:])
        mover = IssueProjectMover()
        mover.run(apply_changes=apply_changes, stage_local=stage_local, limit=limit, scan_unassigned=scan_unassigned)
    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
