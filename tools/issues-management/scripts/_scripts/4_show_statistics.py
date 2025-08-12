#!/usr/bin/env python3
"""
Issues统计信息展示工具
提供详细的issues数据统计和可视化信息
"""

import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter


class IssuesStatistics:
    def __init__(self, issues_dir="issues"):
        self.issues_dir = Path(issues_dir)
        self.stats = {
            'open_issues': [],
            'closed_issues': [],
            'by_label': defaultdict(int),
            'by_assignee': defaultdict(int),
            'by_month': defaultdict(int),
            'recent_updates': []
        }
        
    def collect_statistics(self):
        """收集统计信息"""
        print("📊 收集Issues统计信息...")
        
        # 统计开放issues
        for file_path in self.issues_dir.glob("open_*.md"):
            issue_data = self._parse_issue_file(file_path, "open")
            if issue_data:
                self.stats['open_issues'].append(issue_data)
                self._update_stats(issue_data)
                
        # 统计关闭issues
        for file_path in self.issues_dir.glob("closed_*.md"):
            issue_data = self._parse_issue_file(file_path, "closed")
            if issue_data:
                self.stats['closed_issues'].append(issue_data)
                self._update_stats(issue_data)
                
        print(f"✅ 统计完成: {len(self.stats['open_issues'])} 开放, {len(self.stats['closed_issues'])} 关闭")
        
    def _parse_issue_file(self, file_path, state):
        """解析issue文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 解析基本信息
            number_match = re.search(rf'{state}_(\d+)_', file_path.name)
            if not number_match:
                return None
                
            number = int(number_match.group(1))
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "无标题"
            
            # 解析创建时间
            created_match = re.search(r'\*\*创建时间\*\*: (.+)', content)
            created_at = created_match.group(1) if created_match else None
            
            # 解析更新时间
            updated_match = re.search(r'\*\*更新时间\*\*: (.+)', content)
            updated_at = updated_match.group(1) if updated_match else None
            
            # 解析标签
            labels_match = re.search(r'\*\*标签\*\*: `(.+?)`', content)
            labels = []
            if labels_match:
                labels_text = labels_match.group(1)
                labels = [label.strip() for label in labels_text.replace('`', '').split(',') if label.strip()]
            
            # 解析分配人
            assignee_match = re.search(r'\*\*分配给\*\*: (.+)', content)
            assignee = assignee_match.group(1) if assignee_match else "未分配"
            
            # 获取文件修改时间作为最近更新
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            return {
                'number': number,
                'title': title,
                'state': state,
                'labels': labels,
                'assignee': assignee,
                'created_at': created_at,
                'updated_at': updated_at,
                'file_mtime': file_mtime,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            print(f"  ⚠️ 解析文件 {file_path} 失败: {e}")
            return None
            
    def _update_stats(self, issue_data):
        """更新统计数据"""
        # 按标签统计
        for label in issue_data['labels']:
            self.stats['by_label'][label] += 1
            
        # 按分配人统计
        self.stats['by_assignee'][issue_data['assignee']] += 1
        
        # 按月份统计（使用文件修改时间）
        month_key = issue_data['file_mtime'].strftime('%Y-%m')
        self.stats['by_month'][month_key] += 1
        
        # 最近更新的issues
        self.stats['recent_updates'].append({
            'number': issue_data['number'],
            'title': issue_data['title'],
            'state': issue_data['state'],
            'mtime': issue_data['file_mtime']
        })
        
    def display_statistics(self):
        """显示统计信息"""
        print("📊 Issues统计信息")
        print("=" * 32)
        
        # 基础统计
        open_count = len(self.stats['open_issues'])
        closed_count = len(self.stats['closed_issues'])
        total_count = open_count + closed_count
        
        print(f"📂 Issues目录: {self.issues_dir}")
        print(f"📈 开放Issues: {open_count} 个")
        print(f"📉 关闭Issues: {closed_count} 个")
        print(f"📊 总计Issues: {total_count} 个")
        
        if total_count > 0:
            open_rate = (open_count / total_count) * 100
            print(f"📈 开放率: {open_rate:.1f}%")
            
        # 标签分布
        print(f"\n🏷️ 标签分布 (Top 10):")
        label_counter = Counter(self.stats['by_label'])
        for label, count in label_counter.most_common(10):
            print(f"  - {label}: {count} 个")
            
        # 分配人统计
        print(f"\n👥 分配情况 (Top 10):")
        assignee_counter = Counter(self.stats['by_assignee'])
        for assignee, count in assignee_counter.most_common(10):
            display_name = assignee if assignee != "未分配" else "未分配"
            print(f"  - {display_name}: {count} 个")
            
        # 活跃度分析
        print(f"\n📅 月度活跃度 (最近6个月):")
        sorted_months = sorted(self.stats['by_month'].items(), reverse=True)
        for month, count in sorted_months[:6]:
            print(f"  - {month}: {count} 个issues")
            
        # 最近更新
        print(f"\n🕐 最近更新的Issues:")
        recent_issues = sorted(
            self.stats['recent_updates'], 
            key=lambda x: x['mtime'], 
            reverse=True
        )[:10]
        
        for issue in recent_issues:
            state_icon = "🟢" if issue['state'] == "open" else "🔴"
            title_short = issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title']
            print(f"  {state_icon} #{issue['number']} - {title_short}")
            
        # 质量指标
        print(f"\n📋 质量指标:")
        
        # 无标签issues
        no_label_count = sum(1 for issue in self.stats['open_issues'] if not issue['labels'])
        print(f"  - 无标签Issues: {no_label_count} 个")
        
        # 未分配issues
        unassigned_count = sum(1 for issue in self.stats['open_issues'] 
                              if issue['assignee'] == "未分配")
        print(f"  - 未分配Issues: {unassigned_count} 个")
        
        # 长期开放issues (假设超过30天算长期)
        current_time = datetime.now()
        long_open_count = 0
        for issue in self.stats['open_issues']:
            if issue['file_mtime']:
                days_open = (current_time - issue['file_mtime']).days
                if days_open > 30:
                    long_open_count += 1
        print(f"  - 长期开放Issues (>30天): {long_open_count} 个")
        
        # 输出路径信息
        output_dir = Path("output")
        if output_dir.exists():
            report_count = len(list(output_dir.glob("*.md")))
            print(f"\n📁 输出目录: {output_dir}")
            print(f"📄 已生成报告: {report_count} 个")
            
    def generate_detailed_report(self):
        """生成详细的统计报告"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = output_dir / f"issues_statistics_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# SAGE Issues统计分析报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**数据源**: {self.issues_dir}\n\n")
            
            # 概览
            open_count = len(self.stats['open_issues'])
            closed_count = len(self.stats['closed_issues'])
            total_count = open_count + closed_count
            
            f.write("## 📊 概览统计\n\n")
            f.write(f"| 指标 | 数量 | 比例 |\n")
            f.write(f"|------|------|------|\n")
            f.write(f"| 开放Issues | {open_count} | {(open_count/total_count*100):.1f}% |\n")
            f.write(f"| 关闭Issues | {closed_count} | {(closed_count/total_count*100):.1f}% |\n")
            f.write(f"| 总计Issues | {total_count} | 100% |\n\n")
            
            # 标签分析
            f.write("## 🏷️ 标签分析\n\n")
            label_counter = Counter(self.stats['by_label'])
            for label, count in label_counter.most_common(15):
                percentage = (count / total_count) * 100
                f.write(f"- **{label}**: {count} 个 ({percentage:.1f}%)\n")
            f.write("\n")
            
            # 分配分析
            f.write("## 👥 分配分析\n\n")
            assignee_counter = Counter(self.stats['by_assignee'])
            for assignee, count in assignee_counter.most_common(10):
                percentage = (count / total_count) * 100
                f.write(f"- **{assignee}**: {count} 个 ({percentage:.1f}%)\n")
            f.write("\n")
            
            # 时间趋势
            f.write("## 📈 时间趋势\n\n")
            sorted_months = sorted(self.stats['by_month'].items())
            for month, count in sorted_months[-12:]:  # 最近12个月
                f.write(f"- **{month}**: {count} 个issues\n")
            f.write("\n")
            
            f.write("---\n")
            f.write("*由SAGE Issues统计工具自动生成*\n")
            
        print(f"✅ 详细统计报告已生成: {report_path}")
        return str(report_path)
        
    def run(self):
        """运行统计分析"""
        self.collect_statistics()
        self.display_statistics()
        
        print(f"\n💾 是否生成详细报告? (y/n): ", end="")
        if input().lower().startswith('y'):
            self.generate_detailed_report()


if __name__ == "__main__":
    stats = IssuesStatistics()
    stats.run()
