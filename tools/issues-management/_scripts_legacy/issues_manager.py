#!/usr/bin/env python3
"""
Issues管理工具
处理不需要AI的基础Issues管理功能，从AI分析器中分离出来
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 导入辅助工具
sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))

class IssuesManager:
    def __init__(self):
        self.workspace_dir = Path(__file__).parent.parent / "issues_workspace"
        self.helpers_dir = Path(__file__).parent / "helpers"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.tools_dir = Path(__file__).parent.parent.parent  # tools目录
        self.ensure_output_dir()
        
        # 加载团队信息
        self.team_info = self._load_team_info()
    
    def _load_team_info(self):
        """加载团队信息"""
        try:
            sys.path.append(str(self.tools_dir / "metadata"))
            from team_config import TEAMS, get_all_usernames, get_team_usernames
            print(f"✅ 已加载团队信息: {len(get_all_usernames())} 位成员")
            return {
                'teams': TEAMS,
                'all_usernames': get_all_usernames(),
                'team_count': len(TEAMS)
            }
        except ImportError:
            print("⚠️ 团队信息未找到")
            print("💡 运行以下命令获取团队信息:")
            print("   python3 _scripts/legacy/get_team_members.py")
            return None
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(exist_ok=True)
    
    def show_statistics(self):
        """显示Issues统计信息"""
        print("📊 显示Issues统计信息...")
        
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
            return False
        
        stats = self._generate_statistics(issues)
        
        # 显示统计信息
        print(f"\n📈 Issues统计报告")
        print("=" * 40)
        print(f"总Issues数: {stats['total']}")
        print(f"开放Issues: {stats['open']}")
        print(f"已关闭Issues: {stats['closed']}")
        
        if stats['labels']:
            print(f"\n🏷️ 标签分布 (前10):")
            for label, count in sorted(stats['labels'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {label}: {count}")
        
        if stats['assignees']:
            print(f"\n👤 分配情况:")
            for assignee, count in sorted(stats['assignees'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {assignee}: {count}")
        
        # 保存详细统计报告
        report_file = self.output_dir / f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_statistics_report(stats, report_file)
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return True
    
    def create_new_issue(self):
        """创建新Issue"""
        print("✨ 创建新Issue...")
        
        try:
            # 调用legacy脚本
            script_path = self.tools_dir / "1_create_github_issue.py"
            if script_path.exists():
                result = subprocess.run([sys.executable, str(script_path)], 
                                      capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print(f"⚠️ 警告: {result.stderr}")
                return result.returncode == 0
            else:
                print("❌ 创建Issue脚本未找到")
                return False
        except Exception as e:
            print(f"❌ 创建Issue失败: {e}")
            return False
    
    def team_analysis(self):
        """团队Issues分析"""
        print("👥 团队Issues分析...")
        
        if not self.team_info:
            print("❌ 需要团队信息才能进行团队分析")
            return False
        
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
            return False
        
        # 按团队分析Issues
        team_stats = self._analyze_by_team(issues)
        
        print(f"\n👥 团队Issues分布:")
        print("=" * 40)
        
        for team_name, team_data in self.team_info['teams'].items():
            team_members = team_data.get('members', [])
            team_issues = team_stats.get(team_name, {'total': 0, 'open': 0, 'closed': 0})
            
            print(f"\n🏢 {team_data.get('name', team_name)}")
            print(f"   成员数: {len(team_members)}")
            print(f"   Issues总数: {team_issues['total']}")
            print(f"   开放Issues: {team_issues['open']}")
            print(f"   已关闭Issues: {team_issues['closed']}")
        
        # 保存团队分析报告
        report_file = self.output_dir / f"team_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_team_report(team_stats, report_file)
        print(f"\n📄 团队分析报告已保存到: {report_file}")
        
        return True
    
    def project_management(self):
        """项目Issues管理"""
        print("📋 项目Issues管理...")
        
        try:
            # 调用legacy脚本
            script_path = self.tools_dir / "6_move_issues_to_project.py"
            if script_path.exists():
                result = subprocess.run([sys.executable, str(script_path)], 
                                      capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print(f"⚠️ 警告: {result.stderr}")
                return result.returncode == 0
            else:
                print("❌ 项目管理脚本未找到")
                return False
        except Exception as e:
            print(f"❌ 项目管理失败: {e}")
            return False
    
    def update_team_info(self):
        """更新团队信息"""
        print("🔄 更新团队信息...")
        
        try:
            # 调用团队信息获取脚本
            script_path = self.tools_dir / "get_team_members.py"
            if script_path.exists():
                result = subprocess.run([sys.executable, str(script_path)], 
                                      capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print(f"⚠️ 警告: {result.stderr}")
                
                # 重新加载团队信息
                self.team_info = self._load_team_info()
                return result.returncode == 0
            else:
                print("❌ 团队信息获取脚本未找到")
                return False
        except Exception as e:
            print(f"❌ 更新团队信息失败: {e}")
            return False
    
    def load_issues(self):
        """加载Issues数据"""
        issues_dir = self.workspace_dir / "issues"
        if not issues_dir.exists():
            print("⚠️ Issues目录不存在，尝试查找其他位置...")
            # 尝试其他位置的数据
            alt_file = Path(__file__).parent.parent / "downloaded_issues" / "github_issues.json"
            if alt_file.exists():
                print(f"✅ 找到Issues数据: {alt_file}")
                with open(alt_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        
        issues = []
        for md_file in issues_dir.glob("*.md"):
            issue_data = self._parse_issue_markdown(md_file)
            if issue_data:
                issues.append(issue_data)
        
        return issues
    
    def _parse_issue_markdown(self, md_file):
        """解析Markdown格式的Issue文件"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            title = lines[0].replace('# ', '') if lines else ""
            
            issue_data = {
                'title': title,
                'filename': md_file.name,
                'content': content,
                'state': 'open' if 'open_' in md_file.name else 'closed',
                'labels': [],
                'assignee': None
            }
            
            # 解析更多信息
            for line in lines:
                if line.startswith('**编号**:'):
                    try:
                        issue_data['number'] = int(line.split('#')[1].strip())
                    except:
                        pass
                elif line.startswith('## 标签'):
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        labels_line = lines[idx + 1].strip()
                        if labels_line:
                            issue_data['labels'] = [{'name': label.strip()} for label in labels_line.split(',')]
                elif line.startswith('## 分配给'):
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        assignee_line = lines[idx + 1].strip()
                        if assignee_line and assignee_line != '无':
                            issue_data['assignee'] = {'login': assignee_line}
            
            return issue_data
        except Exception as e:
            print(f"❌ 解析文件失败 {md_file}: {e}")
            return None
    
    def _generate_statistics(self, issues):
        """生成统计信息"""
        stats = {
            'total': len(issues),
            'open': len([i for i in issues if i.get('state') == 'open']),
            'closed': len([i for i in issues if i.get('state') == 'closed']),
            'labels': {},
            'assignees': {},
            'creation_trend': {},
        }
        
        # 统计标签
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label if isinstance(label, str) else label.get('name', 'unknown')
                stats['labels'][label_name] = stats['labels'].get(label_name, 0) + 1
        
        # 统计分配给
        for issue in issues:
            assignee = issue.get('assignee')
            if assignee:
                assignee_name = assignee if isinstance(assignee, str) else assignee.get('login', 'unknown')
                stats['assignees'][assignee_name] = stats['assignees'].get(assignee_name, 0) + 1
            else:
                stats['assignees']['未分配'] = stats['assignees'].get('未分配', 0) + 1
        
        return stats
    
    def _analyze_by_team(self, issues):
        """按团队分析Issues"""
        team_stats = {}
        
        for team_name, team_data in self.team_info['teams'].items():
            team_members = [member['login'] for member in team_data.get('members', [])]
            team_issues = {
                'total': 0,
                'open': 0,
                'closed': 0,
                'members': team_members
            }
            
            for issue in issues:
                assignee = issue.get('assignee')
                if assignee:
                    assignee_name = assignee if isinstance(assignee, str) else assignee.get('login')
                    if assignee_name in team_members:
                        team_issues['total'] += 1
                        if issue.get('state') == 'open':
                            team_issues['open'] += 1
                        else:
                            team_issues['closed'] += 1
            
            team_stats[team_name] = team_issues
        
        return team_stats
    
    def _save_statistics_report(self, stats, report_file):
        """保存统计报告"""
        content = f"""# Issues统计报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总体统计

- **总Issues数**: {stats['total']}
- **开放Issues**: {stats['open']}
- **已关闭Issues**: {stats['closed']}

## 标签分布

"""
        for label, count in sorted(stats['labels'].items(), key=lambda x: x[1], reverse=True):
            content += f"- **{label}**: {count} 次使用\n"
        
        content += "\n## 分配情况\n\n"
        for assignee, count in sorted(stats['assignees'].items(), key=lambda x: x[1], reverse=True):
            content += f"- **{assignee}**: {count} 个Issues\n"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _save_team_report(self, team_stats, report_file):
        """保存团队分析报告"""
        content = f"""# 团队Issues分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 团队概况

"""
        for team_name, stats in team_stats.items():
            team_data = self.team_info['teams'][team_name]
            content += f"""### {team_data.get('name', team_name)}

- **描述**: {team_data.get('description', '无描述')}
- **成员数**: {len(stats['members'])}
- **Issues总数**: {stats['total']}
- **开放Issues**: {stats['open']} 
- **已关闭Issues**: {stats['closed']}
- **成员**: {', '.join(stats['members'])}

"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Issues管理工具 - 非AI功能")
    parser.add_argument("--action", choices=["statistics", "create", "team", "project", "update-team"], 
                       required=True, help="管理操作")
    
    args = parser.parse_args()
    
    manager = IssuesManager()
    
    success = False
    if args.action == "statistics":
        success = manager.show_statistics()
    elif args.action == "create":
        success = manager.create_new_issue()
    elif args.action == "team":
        success = manager.team_analysis()
    elif args.action == "project":
        success = manager.project_management()
    elif args.action == "update-team":
        success = manager.update_team_info()
    
    if success:
        print("🎉 操作完成！")
    else:
        print("💥 操作失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
