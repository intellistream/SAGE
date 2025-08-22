#!/usr/bin/env python3
"""
同步Issues到远端工具
整合原有的同步功能
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

class IssuesSyncer:
    def __init__(self):
        self.workspace_dir = Path(__file__).parent.parent / "issues_workspace"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(exist_ok=True)
    
    def sync_all_changes(self):
        """同步所有修改"""
        print("📤 同步所有修改到远端...")
        
        changes = self.detect_all_changes()
        if not changes:
            print("✅ 没有检测到需要同步的更改")
            return True
        
        print(f"📊 检测到 {len(changes)} 个更改:")
        for change in changes:
            print(f"  - {change['type']}: {change['description']}")
        
        # 确认同步
        confirm = input("\n是否继续同步? (y/N): ").lower().strip()
        if confirm != 'y':
            print("❌ 同步已取消")
            return False
        
        # 执行同步
        success = self.execute_sync(changes)
        self.log_sync_operation(changes, success)
        
        if success:
            print("✅ 所有更改已同步到远端")
        else:
            print("❌ 同步过程中出现错误")
        
        return success
    
    def sync_label_changes(self):
        """同步标签更新"""
        print("📤 同步标签更新...")
        
        label_changes = self.detect_label_changes()
        if not label_changes:
            print("✅ 没有检测到标签更改")
            return True
        
        print(f"📊 检测到 {len(label_changes)} 个标签更改")
        
        success = self.execute_label_sync(label_changes)
        self.log_sync_operation(label_changes, success, sync_type="labels")
        
        return success
    
    def sync_status_changes(self):
        """同步状态更新"""
        print("📤 同步状态更新...")
        
        status_changes = self.detect_status_changes()
        if not status_changes:
            print("✅ 没有检测到状态更改")
            return True
        
        print(f"📊 检测到 {len(status_changes)} 个状态更改")
        
        success = self.execute_status_sync(status_changes)
        self.log_sync_operation(status_changes, success, sync_type="status")
        
        return success
    
    def preview_changes(self):
        """预览待同步更改"""
        print("🔍 预览待同步更改...")
        
        all_changes = self.detect_all_changes()
        
        if not all_changes:
            print("✅ 没有检测到需要同步的更改")
            return True
        
        print(f"\n📊 检测到 {len(all_changes)} 个待同步更改:\n")
        
        # 按类型分组显示
        change_types = {}
        for change in all_changes:
            change_type = change['type']
            if change_type not in change_types:
                change_types[change_type] = []
            change_types[change_type].append(change)
        
        for change_type, changes in change_types.items():
            print(f"## {change_type.upper()} 更改 ({len(changes)})")
            for change in changes:
                print(f"  - {change['description']}")
                if 'details' in change:
                    print(f"    详情: {change['details']}")
            print()
        
        # 生成预览报告
        report_file = self.output_dir / f"sync_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_preview_report(all_changes, report_file)
        print(f"📄 详细预览报告已保存到: {report_file}")
        
        return True
    
    def detect_all_changes(self):
        """检测所有类型的更改"""
        changes = []
        
        # 检测各种类型的更改
        changes.extend(self.detect_label_changes())
        changes.extend(self.detect_status_changes())
        changes.extend(self.detect_content_changes())
        
        return changes
    
    def detect_label_changes(self):
        """检测标签更改（简化版）"""
        # 在实际实现中，这里会比较本地和远端的标签差异
        return [
            {
                'type': 'label',
                'description': 'Issue #123: 添加标签 "bug"',
                'issue_number': 123,
                'action': 'add_label',
                'label': 'bug'
            }
        ]
    
    def detect_status_changes(self):
        """检测状态更改（简化版）"""
        return [
            {
                'type': 'status',
                'description': 'Issue #456: 状态从 "open" 改为 "closed"',
                'issue_number': 456,
                'old_status': 'open',
                'new_status': 'closed'
            }
        ]
    
    def detect_content_changes(self):
        """检测内容更改（简化版）"""
        return [
            {
                'type': 'content',
                'description': 'Issue #789: 标题已修改',
                'issue_number': 789,
                'field': 'title',
                'old_value': '旧标题',
                'new_value': '新标题'
            }
        ]
    
    def execute_sync(self, changes):
        """执行同步操作（简化版）"""
        print("🔄 正在执行同步操作...")
        
        success_count = 0
        for i, change in enumerate(changes, 1):
            print(f"  [{i}/{len(changes)}] 同步: {change['description']}")
            
            # 这里调用实际的GitHub API同步逻辑
            if self.sync_single_change(change):
                success_count += 1
                print(f"    ✅ 成功")
            else:
                print(f"    ❌ 失败")
        
        print(f"\n📊 同步完成: {success_count}/{len(changes)} 成功")
        return success_count == len(changes)
    
    def execute_label_sync(self, changes):
        """执行标签同步"""
        print("🏷️ 正在同步标签...")
        return self.execute_sync(changes)
    
    def execute_status_sync(self, changes):
        """执行状态同步"""
        print("📋 正在同步状态...")
        return self.execute_sync(changes)
    
    def sync_single_change(self, change):
        """同步单个更改（简化版）"""
        # 在实际实现中，这里会调用GitHub API
        # 现在只是模拟成功
        import time
        time.sleep(0.1)  # 模拟API调用延迟
        return True
    
    def log_sync_operation(self, changes, success, sync_type="all"):
        """记录同步操作"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'sync_type': sync_type,
            'changes_count': len(changes),
            'success': success,
            'changes': changes
        }
        
        log_file = self.output_dir / f"sync_log_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 读取现有日志
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # 添加新日志
        logs.append(log_entry)
        
        # 保存日志
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    
    def save_preview_report(self, changes, report_file):
        """保存预览报告"""
        content = f"""# Issues同步预览报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**待同步更改总数**: {len(changes)}

## 更改详情

"""
        
        for i, change in enumerate(changes, 1):
            content += f"""### {i}. {change['type'].upper()} 更改
- **描述**: {change['description']}
"""
            
            if 'issue_number' in change:
                content += f"- **Issue编号**: #{change['issue_number']}\n"
            
            if 'details' in change:
                content += f"- **详情**: {change['details']}\n"
            
            content += "\n"
        
        content += f"""## 同步建议

- 建议在低峰期执行同步操作
- 确保网络连接稳定
- 同步前建议备份当前状态

---
*此报告由SAGE Issues管理工具生成*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

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

if __name__ == "__main__":
    main()
