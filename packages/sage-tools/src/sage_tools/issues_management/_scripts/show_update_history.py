#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
显示Issues的本地更新记录
"""

import argparse
import re
from pathlib import Path
from config import Config

class UpdateHistoryViewer:
    def __init__(self):
        self.config = Config()
        self.workspace_dir = self.config.workspace_path
        
    def extract_update_history(self, text):
        """从issue文件中提取更新记录部分"""
        lines = text.splitlines()
        
        # 找到更新记录部分
        history_start = -1
        for i, line in enumerate(lines):
            if line.strip() == "## 更新记录":
                history_start = i + 1
                break
                
        if history_start == -1:
            return []
            
        # 提取更新记录内容
        history_lines = []
        for i in range(history_start, len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            # 停止条件：遇到分隔线或GitHub链接
            if (stripped == "---" or
                stripped.startswith("**GitHub链接**:") or
                stripped.startswith("**下载时间**:")):
                break
                
            if stripped:  # 只保留非空行
                history_lines.append(line)
                
        return history_lines
    
    def show_issues_with_updates(self):
        """显示所有有更新记录的issues"""
        issues_dir = self.workspace_dir / 'issues'
        if not issues_dir.exists():
            print("❌ Issues目录不存在，请先下载issues")
            return
            
        files = sorted(issues_dir.glob('*.md'))
        issues_with_updates = []
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # 提取issue编号
                match = re.search(r'(?:open|closed)_(\d+)_', file_path.name)
                if not match:
                    continue
                issue_number = int(match.group(1))
                
                # 提取标题
                title = "未知标题"
                for line in content.splitlines():
                    if line.strip().startswith('# '):
                        title = line.strip().lstrip('# ').strip()
                        break
                
                # 检查是否有更新记录
                history = self.extract_update_history(content)
                if history:
                    issues_with_updates.append({
                        'number': issue_number,
                        'title': title,
                        'file': file_path.name,
                        'updates_count': len([line for line in history if line.strip().startswith('- **')])
                    })
                    
            except Exception as e:
                print(f"⚠️ 读取文件 {file_path.name} 时出错: {e}")
                continue
        
        if not issues_with_updates:
            print("📝 没有找到包含更新记录的issues")
            return
            
        print(f"📋 找到 {len(issues_with_updates)} 个包含更新记录的issues:")
        print()
        
        for item in sorted(issues_with_updates, key=lambda x: x['number']):
            print(f"#{item['number']:>3} | {item['updates_count']} 条更新 | {item['title'][:60]}")
            
        print()
        print("💡 使用 --issue-id <编号> 查看具体的更新记录")
    
    def show_issue_update_history(self, issue_id):
        """显示特定issue的更新记录"""
        issues_dir = self.workspace_dir / 'issues'
        
        # 查找对应的文件
        file_pattern = f"*_{issue_id}_*.md"
        matching_files = list(issues_dir.glob(file_pattern))
        
        if not matching_files:
            print(f"❌ 未找到issue #{issue_id}的文件")
            return
            
        file_path = matching_files[0]
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 提取标题
            title = "未知标题"
            for line in content.splitlines():
                if line.strip().startswith('# '):
                    title = line.strip().lstrip('# ').strip()
                    break
            
            print(f"📋 Issue #{issue_id}: {title}")
            print("=" * 60)
            print()
            
            # 提取并显示更新记录
            history = self.extract_update_history(content)
            if not history:
                print("📝 该issue没有更新记录")
                return
            
            print("## 更新记录")
            print()
            for line in history:
                print(line)
                
        except Exception as e:
            print(f"❌ 读取文件时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description='显示Issues的本地更新记录')
    parser.add_argument('--issue-id', type=int, help='显示特定issue的更新记录')
    parser.add_argument('--list', action='store_true', help='列出所有有更新记录的issues')
    
    args = parser.parse_args()
    
    viewer = UpdateHistoryViewer()
    
    if args.issue_id:
        viewer.show_issue_update_history(args.issue_id)
    else:
        viewer.show_issues_with_updates()

if __name__ == '__main__':
    main()
