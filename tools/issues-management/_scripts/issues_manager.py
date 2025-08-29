#!/usr/bin/env python3
"""
Issues manager (non-AI helpers)
Lightweight manager that uses the centralized `_scripts/config.py` config
and calls helper scripts from `_scripts/helpers/` when available.

Supported actions: statistics, create, team, project, update-team
"""
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

from config import config


class IssuesManager:
    def __init__(self):
        self.workspace_dir = config.workspace_path
        self.output_dir = config.output_path
        self.scripts_dir = Path(__file__).parent
        self.helpers_dir = self.scripts_dir / 'helpers'
        self.ensure_output_dir()
        self.team_info = self._load_team_info()

    def ensure_output_dir(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_team_info(self):
        """Try to import generated `team_config.py` from the meta-data directory."""
        # 首先尝试从 meta-data 目录加载
        meta_data_dir = self.workspace_dir / 'meta-data'
        team_config_path = meta_data_dir / 'team_config.py'
        
        if team_config_path.exists():
            try:
                # 清理可能存在的模块缓存
                if 'team_config' in sys.modules:
                    del sys.modules['team_config']
                
                sys.path.insert(0, str(meta_data_dir))
                import team_config
                TEAMS = getattr(team_config, 'TEAMS', None)
                if TEAMS is not None:
                    # 手动收集所有用户名
                    all_usernames = []
                    for team_name, team_data in TEAMS.items():
                        members = team_data.get('members', [])
                        for member in members:
                            username = member.get('username')
                            if username and username not in all_usernames:
                                all_usernames.append(username)
                    
                    # 清理sys.path
                    if str(meta_data_dir) in sys.path:
                        sys.path.remove(str(meta_data_dir))
                    
                    print(f"✅ 已加载团队信息: {len(all_usernames)} 位成员")
                    return {'teams': TEAMS, 'all_usernames': all_usernames}
            except Exception as e:
                print(f"⚠️ 加载团队配置失败: {e}")
                # 清理sys.path
                if str(meta_data_dir) in sys.path:
                    sys.path.remove(str(meta_data_dir))
        
        # 备用：尝试从 output_dir 加载
        try:
            # 清理可能存在的模块缓存
            if 'team_config' in sys.modules:
                del sys.modules['team_config']
                
            sys.path.insert(0, str(self.output_dir))
            import team_config as output_team_config
            TEAMS = getattr(output_team_config, 'TEAMS', None)
            get_all_usernames = getattr(output_team_config, 'get_all_usernames', None)
            if TEAMS is not None:
                all_usernames = []
                if callable(get_all_usernames):
                    try:
                        all_usernames = get_all_usernames()
                    except Exception:
                        all_usernames = []
                else:
                    # 手动收集所有用户名
                    for team_name, team_data in TEAMS.items():
                        members = team_data.get('members', [])
                        for member in members:
                            username = member.get('username')
                            if username and username not in all_usernames:
                                all_usernames.append(username)
                
                # 清理sys.path
                if str(self.output_dir) in sys.path:
                    sys.path.remove(str(self.output_dir))
                
                print(f"✅ 已加载团队信息: {len(all_usernames)} 位成员")
                return {'teams': TEAMS, 'all_usernames': all_usernames}
        except Exception:
            # 清理sys.path
            if str(self.output_dir) in sys.path:
                sys.path.remove(str(self.output_dir))

        print("⚠️ 团队信息未找到")
        print("💡 运行以下命令获取团队信息:")
        print("   python3 _scripts/helpers/get_team_members.py")
        return None

    def load_issues(self):
        """Load issues from workspace directory."""
        issues_dir = self.workspace_dir / 'issues'
        if not issues_dir.exists():
            print(f"❌ Issues目录不存在: {issues_dir}")
            print("💡 请先运行下载Issues命令:")
            print("   python3 _scripts/download_issues.py")
            return []

        issues = []
        for issue_file in issues_dir.glob('*.md'):
            try:
                content = issue_file.read_text(encoding='utf-8')
                # Parse markdown format issues
                issue_data = self._parse_markdown_issue(content, issue_file.name)
                issues.append(issue_data)
            except Exception as e:
                print(f"⚠️ 读取issue文件失败: {issue_file.name}: {e}")
        
        print(f"✅ 加载了 {len(issues)} 个Issues")
        return issues
    
    def _parse_markdown_issue(self, content: str, filename: str):
        """Parse markdown format issue file"""
        lines = content.split('\n')
        
        # Initialize issue data
        issue_data = {
            'title': '',
            'body': content,
            'state': 'open',  # default
            'user': {'login': 'unknown'},
            'labels': [],
            'assignees': []
        }
        
        # Extract title from first line (usually starts with #)
        if lines and lines[0].startswith('#'):
            issue_data['title'] = lines[0].strip('#').strip()
        
        # Extract state from filename
        if filename.startswith('open_'):
            issue_data['state'] = 'open'
        elif filename.startswith('closed_'):
            issue_data['state'] = 'closed'
        
        # Parse markdown content for metadata
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Extract creator/author
            if line.startswith('**创建者**:') or line.startswith('**作者**:') or line.startswith('**Creator**:'):
                author = line.split(':', 1)[1].strip()
                issue_data['user'] = {'login': author}
            
            # Extract state from content
            elif line.startswith('**状态**:') or line.startswith('**State**:'):
                state = line.split(':', 1)[1].strip()
                issue_data['state'] = state
            
            # Extract labels (looking for label section)
            elif line == '## 标签' or line == '## Labels':
                # Check next few lines for labels
                j = i + 1
                while j < len(lines) and j < i + 5:  # Look ahead max 5 lines
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('**'):
                        # Found label content
                        if next_line != '无' and next_line != 'None' and next_line:
                            # Split by comma and clean up
                            labels = [label.strip() for label in next_line.split(',') if label.strip()]
                            issue_data['labels'] = [{'name': label} for label in labels]
                        break
                    j += 1
            
            # Extract assignees
            elif line == '## 分配给' or line == '## Assigned to':
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('**'):
                        if next_line != '未分配' and next_line != 'Unassigned' and next_line:
                            assignees = [assignee.strip() for assignee in next_line.split(',') if assignee.strip()]
                            issue_data['assignees'] = [{'login': assignee} for assignee in assignees]
                        break
                    j += 1
        
        return issue_data

    def _generate_statistics(self, issues):
        """Generate statistics from issues data."""
        stats = {
            'total': len(issues),
            'open': 0,
            'closed': 0,
            'labels': {},
            'assignees': {},
            'authors': {}
        }

        for issue in issues:
            # Count by state
            state = issue.get('state', 'open')
            if state == 'open':
                stats['open'] += 1
            else:
                stats['closed'] += 1

            # Count labels
            labels = issue.get('labels', [])
            if isinstance(labels, list):
                for label in labels:
                    label_name = label if isinstance(label, str) else label.get('name', 'unknown')
                    stats['labels'][label_name] = stats['labels'].get(label_name, 0) + 1

            # Count assignees
            assignees = issue.get('assignees', [])
            if isinstance(assignees, list):
                for assignee in assignees:
                    assignee_name = assignee if isinstance(assignee, str) else assignee.get('login', 'unknown')
                    stats['assignees'][assignee_name] = stats['assignees'].get(assignee_name, 0) + 1

            # Count authors
            author = issue.get('user', {})
            author_name = author.get('login', 'unknown') if isinstance(author, dict) else str(author)
            stats['authors'][author_name] = stats['authors'].get(author_name, 0) + 1

        return stats

    def show_statistics(self):
        """显示Issues统计信息"""
        print("📊 显示Issues统计信息...")
        issues = self.load_issues()
        if not issues:
            return False

        stats = self._generate_statistics(issues)
        
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
            print(f"\n👤 分配情况 (前10):")
            for assignee, count in sorted(stats['assignees'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {assignee}: {count}")

        if stats['authors']:
            print(f"\n✍️ 作者分布 (前10):")
            for author, count in sorted(stats['authors'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {author}: {count}")

        # Save detailed report
        report_file = self.output_dir / f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\n📄 详细报告已保存到: {report_file}")
        return True

    def create_new_issue(self):
        """创建新Issue"""
        print("✨ 创建新Issue...")
        # Check if helper script exists
        helper_script = self.helpers_dir / 'create_issue.py'
        if helper_script.exists():
            print("🔄 调用创建Issue助手...")
            result = subprocess.run([sys.executable, str(helper_script)], 
                                  capture_output=False, text=True)
            return result.returncode == 0
        else:
            print("⚠️ 创建Issue助手不存在")
            print("📝 请手动创建Issue或实现create_issue.py助手")
            return True

    def team_analysis(self):
        """团队分析"""
        print("👥 团队分析...")
        if not self.team_info:
            print("❌ 没有团队信息，无法进行分析")
            return False

        # Check if helper script exists
        helper_script = self.helpers_dir / 'get_team_members.py'
        if helper_script.exists():
            print("🔄 调用团队分析助手...")
            result = subprocess.run([sys.executable, str(helper_script)], 
                                  capture_output=False, text=True)
            return result.returncode == 0
        else:
            print("📊 基本团队信息:")
            teams = self.team_info.get('teams', {})
            for team_name, members in teams.items():
                print(f"  - {team_name}: {len(members)} 成员")
            return True

    def project_management(self):
        """项目管理 - 自动检测并修复错误分配的Issues"""
        print("📋 项目管理...")
        
        # Check if our fix script exists
        fix_script = self.helpers_dir / 'fix_misplaced_issues.py'
        execute_script = self.helpers_dir / 'execute_fix_plan.py'
        
        if fix_script.exists():
            print("� 扫描错误分配的Issues...")
            
            # First, run detection to generate fix plan
            detection_result = subprocess.run([
                sys.executable, str(fix_script), '--dry-run'
            ], capture_output=True, text=True, cwd=str(self.scripts_dir))
            
            if detection_result.returncode != 0:
                print(f"❌ 检测脚本执行失败: {detection_result.stderr}")
                return False
                
            print(detection_result.stdout)
            
            # Check if there's a fix plan file generated
            output_dir = self.scripts_dir.parent / 'output'
            fix_plan_files = list(output_dir.glob('issues_fix_plan_*.json'))
            
            if fix_plan_files:
                latest_plan = max(fix_plan_files, key=lambda x: x.stat().st_mtime)
                print(f"📋 发现修复计划: {latest_plan.name}")
                
                # Ask user if they want to execute the fix
                try:
                    response = input("🤔 是否执行修复计划? (y/N): ").strip().lower()
                    if response in ['y', 'yes']:
                        print("🚀 执行修复计划...")
                        execute_result = subprocess.run([
                            sys.executable, str(execute_script), str(latest_plan), '--live'
                        ], capture_output=False, text=True, cwd=str(self.scripts_dir))
                        
                        return execute_result.returncode == 0
                    else:
                        print("✅ 跳过执行，仅进行了检测")
                        return True
                except KeyboardInterrupt:
                    print("\n✅ 操作被用户取消")
                    return True
            else:
                print("✅ 没有发现需要修复的Issues")
                return True
                
        else:
            print("⚠️ Issues修复助手不存在")
            print("📝 请检查 helpers/fix_misplaced_issues.py")
            return True

    def update_team_info(self):
        """更新团队信息"""
        print("🔄 更新团队信息...")
        helper_script = self.helpers_dir / 'get_team_members.py'
        if helper_script.exists():
            result = subprocess.run([sys.executable, str(helper_script)], 
                                  capture_output=False, text=True)
            if result.returncode == 0:
                # Reload team info
                self.team_info = self._load_team_info()
                return True
            return False
        else:
            print("❌ get_team_members.py助手不存在")
            return False


def main():
    parser = argparse.ArgumentParser(description="Issues管理工具 - 非AI功能")
    parser.add_argument("--action", choices=["statistics", "create", "team", "project", "update-team"], 
                       required=True, help="要执行的操作")
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
        print("\n🎉 操作完成！")
    else:
        print("\n💥 操作失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()
