#!/usr/bin/env python3
"""
Issues 同步脚本
"""
import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import config
from config import github_client
import requests
import time
import glob


def graphql_request(session: requests.Session, query: str, variables: dict = None, retries: int = 2):
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    attempt = 0
    while True:
        try:
            resp = session.post("https://api.github.com/graphql", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return True, data
        except Exception as e:
            attempt += 1
            if attempt > retries:
                return False, str(e)
            time.sleep(1 * attempt)


class IssuesSyncer:
    def __init__(self):
        self.workspace_dir = Path(__file__).parent.parent / "issues_workspace"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sync_all_changes(self):
        changes = self.detect_all_changes()
        if not changes:
            print("✅ 没有检测到需要同步的更改")
            return True

        print(f"� 检测到 {len(changes)} 个更改:")
        for change in changes:
            print(f"  - {change['type']}: {change['description']}")

        confirm = input("\n是否继续同步? (y/N): ").lower().strip()
        if confirm != 'y':
            print("❌ 同步已取消")
            return False

        success = self.execute_sync(changes)
        self.log_sync_operation(changes, success)
        return success

    def sync_label_changes(self):
        label_changes = self.detect_label_changes()
        if not label_changes:
            print("✅ 没有检测到标签更改")
            return True
        return self.execute_sync(label_changes)

    def sync_status_changes(self):
        status_changes = self.detect_status_changes()
        if not status_changes:
            print("✅ 没有检测到状态更改")
            return True
        return self.execute_sync(status_changes)

    def preview_changes(self):
        all_changes = self.detect_all_changes()
        if not all_changes:
            print("✅ 没有检测到需要同步的更改")
            return True

        print(f"\n� 检测到 {len(all_changes)} 个待同步更改:\n")
        for change in all_changes:
            print(f" - [{change['type']}] {change['description']}")

        report_file = self.output_dir / f"sync_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_preview_report(all_changes, report_file)
        print(f"📄 详细预览报告已保存到: {report_file}")
        return True

    def find_latest_plan(self):
        plans = sorted(self.output_dir.glob('project_move_plan_*.json'), reverse=True)
        if plans:
            return plans[0]
        return None

    def load_plan(self, path=None):
        if path:
            p = Path(path)
        else:
            p = self.find_latest_plan()
        if not p or not p.exists():
            print("❌ 未找到 plan 文件，请先运行 project_manage.py --stage-local")
            return []
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            print(f"✅ 已加载计划: {p}，{len(data)} 项")
            return data
        except Exception as e:
            print(f"❌ 解析 plan 失败: {e}")
            return []

    def preview_plan(self, plan):
        if not plan:
            print("✅ 计划为空")
            return True
        print(f"\n🔎 计划预览 ({len(plan)} 项):")
        for i, act in enumerate(plan, 1):
            print(f" [{i}/{len(plan)}] #{act.get('issue_number')} -> project {act.get('to_project')} ({act.get('to_project_number')}) staged={act.get('staged')}")
        return True

    def apply_plan(self, plan, dry_run=True, batch_size=5):
        session = github_client.session
        logs = []
        total = len(plan)
        for idx, act in enumerate(plan, 1):
            issue_number = act.get('issue_number')
            issue_node_id = act.get('issue_node_id')
            item_id = act.get('item_id')
            project_id = act.get('to_project_id')
            project_number = act.get('to_project_number')
            entry = { 'issue_number': issue_number, 'project_number': project_number }
            print(f"[{idx}/{total}] 处理 Issue #{issue_number} -> project #{project_number}")

            # Idempotency check: does project already contain this contentId?
            q_check = '''query($projectId: ID!) { node(id: $projectId) { ... on ProjectV2 { items(first:100) { nodes { content { __typename ... on Issue { id } } } pageInfo { hasNextPage endCursor } } } } }'''
            ok, resp = graphql_request(session, q_check, { 'projectId': project_id }, retries=1)
            already = False
            if ok:
                nodes = resp.get('data', {}).get('node', {}).get('items', {}).get('nodes', [])
                for n in nodes:
                    c = n.get('content') or {}
                    if c.get('id') == issue_node_id:
                        already = True
                        break

            if already:
                print(f"  ⏭️ 目标 project 已包含此 issue，跳过 add")
                entry['added'] = False
            else:
                if dry_run:
                    print(f"  [dry-run] 会执行 addProjectV2ItemById(projectId={project_id}, contentId={issue_node_id})")
                    entry['added'] = 'dry-run'
                else:
                    mut = '''mutation($projectId: ID!, $contentId: ID!) { addProjectV2ItemById(input:{projectId:$projectId, contentId:$contentId}) { item { id } } }'''
                    ok2, resp2 = graphql_request(session, mut, { 'projectId': project_id, 'contentId': issue_node_id }, retries=2)
                    if not ok2 or 'errors' in (resp2 or {}):
                        print(f"  ❌ add 失败: {resp2}")
                        entry['added'] = False
                        entry['add_response'] = resp2
                    else:
                        print(f"  ✅ 已添加到目标 project")
                        entry['added'] = True
                        entry['add_response'] = resp2

            # If we added (or existed), we should remove the original org project item
            if dry_run:
                print(f"  [dry-run] 会执行 deleteProjectV2Item(itemId={item_id})")
                entry['deleted'] = 'dry-run'
            else:
                mut_del = '''mutation($itemId: ID!) { deleteProjectV2Item(input: {itemId: $itemId}) { deletedItemId } }'''
                ok3, resp3 = graphql_request(session, mut_del, { 'itemId': item_id }, retries=2)
                if not ok3 or 'errors' in (resp3 or {}):
                    print(f"  ❌ delete 失败: {resp3}")
                    entry['deleted'] = False
                    entry['delete_response'] = resp3
                else:
                    print(f"  ✅ 已从原组织 project 删除 item")
                    entry['deleted'] = True
                    entry['delete_response'] = resp3

            logs.append(entry)
            # gentle rate limiting
            time.sleep(0.5)

        # write log
        log_path = self.output_dir / f"project_move_log_{int(time.time())}.json"
        log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n📝 日志已写入: {log_path}")
        return logs

    def detect_all_changes(self):
        changes = []
        changes.extend(self.detect_label_changes())
        changes.extend(self.detect_status_changes())
        changes.extend(self.detect_content_changes())
        return changes

    def detect_label_changes(self):
        # 简化：示例返回空或单条变更
        return []

    def detect_status_changes(self):
        return []

    def detect_content_changes(self, limit=None):
        # Scan local markdown files and compare with remote issues for title/body/labels
        changes = []
        issues_dir = self.workspace_dir / 'issues'
        if not issues_dir.exists():
            return changes

        files = sorted(issues_dir.glob('open_*.md'))
        total_files = len(files)
        for f in files:
            if total_files and (files.index(f) % 50 == 0):
                print(f"🔎 scanning files... progress: {files.index(f)+1}/{total_files}")
            name = f.name
            # extract issue number from filename
            import re
            m = re.match(r'open_(\d+)_', name)
            if not m:
                continue
            issue_number = int(m.group(1))
            text = f.read_text(encoding='utf-8')
            # strip front-matter if present
            body_text = text
            if text.startswith('---'):
                parts = text.split('---', 2)
                if len(parts) == 3:
                    body_text = parts[2]

            # title: first line starting with '# '
            local_title = None
            for line in body_text.splitlines():
                if line.strip().startswith('# '):
                    local_title = line.strip().lstrip('# ').strip()
                    break

            # labels: parse '## 标签' section
            local_labels = []
            lines = body_text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith('## 标签'):
                    # read following non-empty lines as labels until blank or next section
                    for j in range(i+1, min(i+10, len(lines))):
                        l = lines[j].strip()
                        if not l:
                            break
                        # labels may be comma-separated or single per line
                        for part in l.split(','):
                            lab = part.strip()
                            if lab:
                                local_labels.append(lab)
                    break

            # local body: everything after title and sections
            local_body = body_text
            # Get remote issue
            owner = config.GITHUB_OWNER
            repo = config.GITHUB_REPO
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
            try:
                resp = github_client.session.get(url, timeout=20)
                if resp.status_code != 200:
                    # couldn't fetch remote issue; skip
                    continue
                remote = resp.json()
            except Exception:
                continue

            remote_title = remote.get('title')
            remote_body = remote.get('body') or ''
            remote_labels = [l.get('name') for l in remote.get('labels', [])]
            remote_updated_at = remote.get('updated_at')

            # normalize for comparison
            def norm(s):
                return (s or '').strip().replace('\r\n', '\n')

            title_changed = local_title and norm(local_title) != norm(remote_title)
            body_changed = local_body and norm(local_body) != norm(remote_body)
            labels_changed = set(local_labels) != set(remote_labels)

            if title_changed or body_changed or labels_changed:
                changes.append({
                    'type': 'content',
                    'issue_number': issue_number,
                    'file': str(f),
                    'local_title': local_title,
                    'local_body': local_body,
                    'local_labels': local_labels,
                    'remote_title': remote_title,
                    'remote_body': remote_body,
                    'remote_labels': remote_labels,
                    'remote_updated_at': remote_updated_at,
                })

            if limit and len(changes) >= limit:
                print(f"已达到 content-limit={limit}，停止扫描")
                break

        return changes

    def execute_sync(self, changes):
        print("🔄 正在执行同步操作...")
        success_count = 0
        for i, change in enumerate(changes, 1):
            print(f"  [{i}/{len(changes)}] 同步: {change['description']}")
            # TODO: 调用 GitHub API
            success_count += 1
        print(f"\n📊 同步完成: {success_count}/{len(changes)} 成功")
        return True

    # Content sync helpers
    def save_content_plan(self, changes):
        path = self.output_dir / f"content_sync_plan_{int(time.time())}.json"
        path.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"📋 内容同步计划已写入: {path}")
        return path

    def apply_content_plan(self, plan, dry_run=True, force=False, limit=None):
        logs = []
        count = 0
        for act in plan:
            issue_number = act['issue_number']
            entry = {'issue_number': issue_number}
            # conflict detection: compare remote updated_at with local (from file)
            local_mtime = None
            try:
                local_mtime = int(Path(act['file']).stat().st_mtime)
            except Exception:
                local_mtime = None

            # fetch remote current updated_at
            owner = config.GITHUB_OWNER
            repo = config.GITHUB_REPO
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
            try:
                resp = github_client.session.get(url, timeout=20)
                resp.raise_for_status()
                remote = resp.json()
            except Exception as e:
                entry['error'] = f"fetch failed: {e}"
                logs.append(entry)
                continue

            remote_updated = remote.get('updated_at')
            # If remote was updated after local file mtime and not forced, skip
            if local_mtime and remote_updated:
                # parse remote_updated to timestamp
                from datetime import datetime
                try:
                    t_remote = int(datetime.fromisoformat(remote_updated.replace('Z', '+00:00')).timestamp())
                except Exception:
                    t_remote = None
                if t_remote and local_mtime and t_remote > local_mtime and not force:
                    entry['skipped'] = 'remote_newer'
                    print(f"  ⚠️ Issue #{issue_number} 远端比本地更新，跳过（使用 --force-content 强制覆盖）")
                    logs.append(entry)
                    continue

            # prepare update payload
            payload = {}
            if act.get('local_title') and act.get('local_title') != remote.get('title'):
                payload['title'] = act.get('local_title')
            # limit body size? just send
            if act.get('local_body') and act.get('local_body') != remote.get('body'):
                payload['body'] = act.get('local_body')
            if set(act.get('local_labels', [])) != set(act.get('remote_labels', [])):
                payload['labels'] = act.get('local_labels', [])

            if not payload:
                entry['noop'] = True
                logs.append(entry)
                continue

            if dry_run:
                print(f"  [dry-run] Issue #{issue_number} 将被 PATCH 字段: {list(payload.keys())}")
                entry['planned_update'] = payload
            else:
                # perform PATCH via github_client
                res = github_client.update_issue(issue_number, **payload)
                if res is None:
                    entry['updated'] = False
                    entry['error'] = 'update failed'
                    print(f"  ❌ Issue #{issue_number} 更新失败")
                else:
                    entry['updated'] = True
                    entry['update_response'] = res
                    print(f"  ✅ Issue #{issue_number} 已更新")

            logs.append(entry)
            count += 1
            if limit and count >= limit:
                break
            time.sleep(0.3)

        # write log
        log_path = self.output_dir / f"content_sync_log_{int(time.time())}.json"
        log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"📝 内容同步日志已写入: {log_path}")
        return logs

    def log_sync_operation(self, changes, success, sync_type="all"):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'sync_type': sync_type,
            'changes_count': len(changes),
            'success': success,
            'changes': changes
        }
        log_file = self.output_dir / f"sync_log_{datetime.now().strftime('%Y%m%d')}.json"
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                logs = []
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding='utf-8')

    def save_preview_report(self, changes, report_file):
        content = f"""# Issues同步预览报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**待同步更改总数**: {len(changes)}

## 更改详情

"""
        for i, change in enumerate(changes, 1):
            content += f"### {i}. {change['type'].upper()} 更改\n- **描述**: {change['description']}\n\n"
        content += "\n---\n*此报告由SAGE Issues管理工具生成*\n"
        report_file.write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="同步Issues到远端")
    parser.add_argument("--all", action="store_true", help="同步所有更改")
    parser.add_argument("--labels-only", action="store_true", help="仅同步标签更改")
    parser.add_argument("--status-only", action="store_true", help="仅同步状态更改")
    parser.add_argument("--preview", action="store_true", help="预览待同步更改")
    parser.add_argument("--plan-preview", action="store_true", help="预览 project_move_plan_*.json 中的计划")
    parser.add_argument("--apply-plan", action="store_true", help="对 plan 执行远端变更（需 --confirm 才会真正 apply）")
    parser.add_argument("--plan-file", type=str, help="指定 plan 文件路径（可选，默认取最新的 project_move_plan_*.json）")
    parser.add_argument("--confirm", action="store_true", help="确认执行（与 --apply-plan 一起使用以实际 apply）")
    parser.add_argument("--batch-size", type=int, default=5, help="每批处理数量（默认 5）")
    parser.add_argument("--content-preview", action="store_true", help="预览本地 content 更改（title/body/labels）")
    parser.add_argument("--apply-content", action="store_true", help="对本地 content 更改执行远端更新（需 --confirm ）")
    parser.add_argument("--force-content", action="store_true", help="强制覆盖远端（忽略远端更新时间）")
    parser.add_argument("--content-limit", type=int, default=None, help="只处理前 N 个 content 更改（用于试点）")
    args = parser.parse_args()

    syncer = IssuesSyncer()
    success = False
    if args.all:
        success = syncer.sync_all_changes()
    elif args.labels_only:
        success = syncer.sync_label_changes()
    elif args.status_only:
        success = syncer.sync_status_changes()
    elif args.preview:
        success = syncer.preview_changes()
    elif args.plan_preview:
        plan = syncer.load_plan(args.plan_file)
        success = syncer.preview_plan(plan)
    elif args.apply_plan:
        plan = syncer.load_plan(args.plan_file)
        if not plan:
            sys.exit(1)
        dry = not args.confirm
        print(f"🔔 apply_plan dry_run={dry} batch_size={args.batch_size}")
        syncer.apply_plan(plan, dry_run=dry, batch_size=args.batch_size)
        success = True
    elif args.content_preview:
        changes = syncer.detect_content_changes(limit=args.content_limit)
        if not changes:
            print("✅ 未检测到内容差异")
        else:
            p = syncer.save_content_plan(changes)
            print(f"预览 {len(changes)} 项内容差异，计划已保存: {p}")
        success = True
    elif args.apply_content:
        changes = syncer.detect_content_changes(limit=args.content_limit)
        if not changes:
            print("✅ 未检测到内容差异")
            sys.exit(0)
        plan_path = syncer.save_content_plan(changes)
        dry = not args.confirm
        syncer.apply_content_plan(changes, dry_run=dry, force=args.force_content, limit=args.content_limit)
        success = True
    else:
        print("❌ 请指定同步模式")
        parser.print_help()
        sys.exit(1)

    if success:
        print("🎉 操作完成！")
    else:
        print("💥 操作失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()
