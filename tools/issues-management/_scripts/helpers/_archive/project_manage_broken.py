#!/usr/bin/env python3
"""
Move issu    def __init__(self):
        # Use main config from _scripts/config.py
        if not config.github_token:
            print("❌ 未找到GitHub Token，请先配置")
            sys.exit(1)
        
        self.github_token = config.github_token
        
        # Load team to project mapping from boards_metadata.json
        self.target_teams = self._load_boards_metadata()
        
        # Setup directories
        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        self.github_client = GitHubAPIClient(self.github_token, self.ORG)
        
        # Load cached team members if available
        cache_file = self._get_cached_team_members_path()
        if cache_file.exists():
            self.github_client.load_cached_team_members(cache_file)
    
    def _load_boards_metadata(self):
        """加载boards metadata配置"""
        import json
        
        # Look for boards_metadata.json in parent directories
        base_path = Path(__file__).parent
        candidate_paths = [
            base_path.parent / 'boards_metadata.json',
            base_path.parent.parent / 'boards_metadata.json',
            base_path.parent.parent.parent / 'boards_metadata.json',
        ]
        
        for meta_path in candidate_paths:
            if meta_path.exists():
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    mapping = metadata.get('team_to_project', {})
                    if mapping:
                        target_teams = {k: int(v) for k, v in mapping.items()}
                        print(f"✅ Loaded boards metadata from {meta_path}")
                        return target_teams
                except Exception as e:
                    print(f"⚠️ 读取 {meta_path} 失败: {e}")
                    continue
        
        print("❌ 未找到 boards_metadata.json 中的 team -> project 映射")
        sys.exit(1)
    
    def _get_cached_team_members_path(self):
        """获取缓存团队成员文件路径"""
        # meta-data directory: tools/issues-management/meta-data
        meta_dir = Path(__file__).parent.parent.parent / 'meta-data'
        meta_dir.mkdir(parents=True, exist_ok=True)
        return meta_dir / 'team_members.json'tion's public project (org project #6)
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

import sys
import time
import json
from pathlib import Path

# Import helper modules
from progress_bar import ProgressBar
from github_api import GitHubAPIClient
from file_utils import FileUtils

# Import main config from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config


class IssueProjectMover:
    ORG = "intellistream"
    REPO = "SAGE"
    ORG_PROJECT_NUMBER = 6

    def __init__(self):
        # Initialize configuration loader
        self.config_loader = ConfigLoader(Path(__file__).parent)
        
        # Load GitHub token
        self.github_token = self.config_loader.load_github_token()
        
        # Load team to project mapping
        self.target_teams = self.config_loader.load_boards_metadata()
        
        # Setup directories
        self.output_dir, self.meta_dir = self.config_loader.setup_directories()
        
        # Initialize GitHub API client
        self.github_client = GitHubAPIClient(self.github_token, self.ORG)
        
        # Load cached team members if available
        cached_members_file = self.config_loader.get_cached_team_members_path()
        if cached_members_file.exists():
            self.github_client.load_cached_team_members(cached_members_file)

    def get_repo_issues_without_projects(self, limit=None, preview_mode=False):
        """获取仓库中未分配到任何项目的Issues"""
        print(f"🔍 扫描 {self.ORG}/{self.REPO} 中未分配项目的Issues...")
        if preview_mode:
            print("📋 预览模式：快速扫描前200个Issues")
        
        # 初始化进度条
        progress_bar = ProgressBar(description="扫描未分配Issues")
        progress_bar.update(0, force=True)
        
        try:
            # 使用GitHub API客户端获取未分配Issues
            all_issues = self.github_client.get_repo_issues_without_projects(
                self.REPO, 
                limit=limit, 
                preview_mode=preview_mode,
                progress_callback=lambda count: progress_bar.update(count)
            )
            
            # 确保显示最终的正确数量
            progress_bar.current = len(all_issues)
            progress_bar.finish()
            
            print(f"\n📊 扫描完成：共发现 {len(all_issues)} 个未分配项目的Issues")
            return all_issues
            
        except Exception as e:
            progress_bar.newline()
            print(f"❌ 扫描过程中出错: {e}")
            return []

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
        proj = self.github_client.get_org_project(self.ORG_PROJECT_NUMBER)
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
                    member = self.github_client.is_user_in_team(author, team_slug)
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
            target_project = self.github_client.get_org_project(target_project_number)
            if not target_project:
                print(f"  ❌ 未找到组织项目 #{target_project_number}，跳过")
                continue

            print(f"  📦 目标组织项目: {target_project.get('title')} (number={target_project.get('number')} id={target_project.get('id')})")

            if stage_local:
                # Find and update local markdown file
                issues_dir = FileUtils.find_issues_workspace()
                matched_file = FileUtils.find_issue_markdown_file(issue_number, issues_dir)
                
                if matched_file:
                    success = FileUtils.update_issue_frontmatter(matched_file, target_project)
                    if success:
                        print(f"  ✅ 已在本地 front-matter 中标注: {matched_file}")
                    else:
                        print(f"  ⚠️ 更新本地文件失败: {matched_file}")
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
                ok, resp = self.github_client.add_issue_to_project(target_project.get('id'), issue_id)
                if not ok:
                    print(f"  ❌ 添加到目标项目失败: {resp}")
                    continue
                print(f"  ✅ 已添加到目标项目")

                # Remove original item from org project
                ok2, resp2 = self.github_client.delete_project_item(item_id)
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

        # Save reports
        if not apply_changes and not stage_local:
            report_path = FileUtils.save_json_report(actions, self.output_dir, "project_move_plan")
            if report_path:
                print(f"\n📋 计划已写入: {report_path} (未实际执行，传入 --apply 来执行移动)")
        elif stage_local:
            report_path = FileUtils.save_json_report(actions, self.output_dir, "project_move_plan")
            if report_path:
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
