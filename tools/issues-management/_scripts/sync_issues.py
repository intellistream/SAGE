#!/usr/bin/env python3
"""
Issues 同步脚本
提供预览、标签同步、状态同步和全部同步功能（基于 legacy 实现的简化版）
"""
import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import config


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

    def detect_content_changes(self):
        return []

    def execute_sync(self, changes):
        print("🔄 正在执行同步操作...")
        success_count = 0
        for i, change in enumerate(changes, 1):
            print(f"  [{i}/{len(changes)}] 同步: {change['description']}")
            # TODO: 调用 GitHub API
            success_count += 1
        print(f"\n📊 同步完成: {success_count}/{len(changes)} 成功")
        return True

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
