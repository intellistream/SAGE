#!/usr/bin/env python3
"""
Issues manager (non-AI helpers) — new _scripts implementation.
Uses unified `config` and `github_client` from `_scripts/config.py`.

Supports actions: statistics, create (best-effort), team, project, update-team
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
        # use config paths
        self.workspace_dir = config.workspace_path
        self.output_dir = config.output_path
        self.scripts_dir = Path(__file__).parent
        self.ensure_output_dir()

        # load team info from generated team_config in output if present
        self.team_info = self._load_team_info()

    def _load_team_info(self):
        """Try to import generated team_config.py from output dir."""
        try:
            sys.path.insert(0, str(self.output_dir))
            import team_config
            TEAMS = getattr(team_config, 'TEAMS', None)
            get_all_usernames = getattr(team_config, 'get_all_usernames', None)
            if TEAMS and get_all_usernames:
                print(f"✅ 已加载团队信息: {len(get_all_usernames())} 位成员")
                return {
                    'teams': TEAMS,
                    'all_usernames': get_all_usernames(),
                    'team_count': len(TEAMS)
                }
        except Exception:
            pass

        print("⚠️ 团队信息未找到")
        print("💡 运行以下命令获取团队信息:")
        print("   python3 _scripts/get_team_members.py")
        return None

    def ensure_output_dir(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def show_statistics(self):
        print("📊 显示Issues统计信息...")
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
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
            print(f"\n👤 分配情况:")
            for assignee, count in sorted(stats['assignees'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {assignee}: {count}")

        report_file = self.output_dir / f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_statistics_report(stats, report_file)
        print(f"\n📄 详细报告已保存到: {report_file}")
        return True

    def create_new_issue(self):
        print("✨ 创建新Issue... (如果存在新实现，将调用 _scripts/create_issue.py)")
        # prefer new script if exists
        new_script = self.scripts_dir / 'create_issue.py'
        if new_script.exists():
            r = subprocess.run([sys.executable, str(new_script)], capture_output=True, text=True)
            #!/usr/bin/env python3
            """Issues manager (non-AI helpers)

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
                    """Try to import generated `team_config.py` from the output directory."""
                    try:
                        sys.path.insert(0, str(self.output_dir))
                        import team_config
                        TEAMS = getattr(team_config, 'TEAMS', None)
                        get_all_usernames = getattr(team_config, 'get_all_usernames', None)
                        get_team_usernames = getattr(team_config, 'get_team_usernames', None)
                        if TEAMS is not None:
                            all_usernames = []
                            if callable(get_all_usernames):
                                try:
                                    all_usernames = get_all_usernames()
                                except Exception:
                                    all_usernames = []
                            return {'teams': TEAMS, 'all_usernames': all_usernames}
                    except Exception:
                        pass

                    # fallback: no team info
                    return None

                def show_statistics(self):
                    issues = self.load_issues()
                    if not issues:
                        print("❌ 未找到Issues数据")
                        return False

                    stats = self._generate_statistics(issues)
                    print("\n📈 Issues统计报告")
                    print("=" * 40)
                    print(f"总Issues数: {stats['total']}")
                    print(f"开放Issues: {stats['open']}")
                    print(f"已关闭Issues: {stats['closed']}")

                    report_file = self.output_dir / f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    self._save_statistics_report(stats, report_file)
                    print(f"📄 详细报告已保存到: {report_file}")
                    return True

                def create_new_issue(self):
                    # try helper first
                    script = self.helpers_dir / 'create_issue.py'
                    if script.exists():
                        return self._run_script(script)

                    # fallback to legacy helper if present
                    legacy = Path(__file__).parent.parent / '_scripts_legacy' / 'helpers' / '1_create_github_issue.py'
                    if legacy.exists():
                        return self._run_script(legacy)

                    print("❌ 创建Issue脚本未找到")
                    return False

                def project_management(self):
                    script = self.helpers_dir / 'project_manage.py'
                    if script.exists():
                        return self._run_script(script)

                    legacy = Path(__file__).parent.parent / '_scripts_legacy' / 'helpers' / '6_move_issues_to_project.py'
                    if legacy.exists():
                        return self._run_script(legacy)

                    print("❌ 项目管理脚本未找到")
                    return False

                def update_team_info(self):
                    script = self.helpers_dir / 'get_team_members.py'
                    if script.exists():
                        ok = self._run_script(script)
                        # reload team info after run
                        self.team_info = self._load_team_info()
                        return ok

                    # fallback message
                    print("❌ 团队信息获取脚本未找到 (expected _scripts/helpers/get_team_members.py)")
                    return False

                def _run_script(self, path: Path):
                    try:
                        r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
                        if r.stdout:
                            print(r.stdout)
                        if r.stderr:
                            print(f"⚠️ 脚本错误输出: {r.stderr}")
                        return r.returncode == 0
                    except Exception as e:
                        print(f"❌ 无法执行脚本 {path}: {e}")
                        return False

                def team_analysis(self):
                    if not self.team_info:
                        print("❌ 团队信息未加载，请先运行 --action=update-team")
                        return False

                    issues = self.load_issues()
                    if not issues:
                        print("❌ 未找到Issues数据")
                        return False

                    team_stats = self._analyze_by_team(issues)
                    report_file = self.output_dir / f"team_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    self._save_team_report(team_stats, report_file)
                    print(f"📄 团队分析报告已保存到: {report_file}")
                    return True

                def load_issues(self):
                    issues_dir = self.workspace_dir / 'issues'
                    if not issues_dir.exists():
                        # try to fall back to any saved JSON
                        alt = self.output_dir / 'github_issues.json'
                        if alt.exists():
                            try:
                                return json.loads(alt.read_text(encoding='utf-8'))
                            except Exception:
                                return []
                        return []

                    issues = []
                    for md in issues_dir.glob('*.md'):
                        parsed = self._parse_issue_markdown(md)
                        if parsed:
                            issues.append(parsed)
                    return issues

                def _parse_issue_markdown(self, md_file: Path):
                    try:
                        text = md_file.read_text(encoding='utf-8')
                        lines = text.splitlines()
                        title = lines[0].lstrip('# ').strip() if lines else ''
                        issue = {'title': title, 'filename': md_file.name, 'content': text, 'labels': [], 'assignee': None}
                        for i, line in enumerate(lines):
                            if line.startswith('## 标签') and i + 1 < len(lines):
                                v = lines[i+1].strip()
                                if v:
                                    issue['labels'] = [{'name': s.strip()} for s in v.split(',')]
                            if line.startswith('## 分配者') and i + 1 < len(lines):
                                v = lines[i+1].strip()
                                if v and v != '无':
                                    issue['assignee'] = {'login': v}
                        # very small heuristic for open/closed based on filename
                        issue['state'] = 'open' if 'open_' in md_file.name or 'open' in md_file.name else 'closed'
                        return issue
                    except Exception as e:
                        print(f"❌ 解析文件失败 {md_file}: {e}")
                        return None

                def _generate_statistics(self, issues):
                    stats = {'total': len(issues), 'open': 0, 'closed': 0, 'labels': {}, 'assignees': {}}
                    for issue in issues:
                        state = issue.get('state')
                        if state == 'open':
                            stats['open'] += 1
                        else:
                            stats['closed'] += 1
                        for label in issue.get('labels', []):
                            name = label if isinstance(label, str) else label.get('name', 'unknown')
                            stats['labels'][name] = stats['labels'].get(name, 0) + 1
                        assignee = issue.get('assignee')
                        if assignee:
                            an = assignee if isinstance(assignee, str) else assignee.get('login', 'unknown')
                            stats['assignees'][an] = stats['assignees'].get(an, 0) + 1
                        else:
                            stats['assignees']['未分配'] = stats['assignees'].get('未分配', 0) + 1
                    return stats

                def _analyze_by_team(self, issues):
                    if not self.team_info:
                        return {}
                    team_stats = {}
                    teams = self.team_info.get('teams', {})
                    for slug, info in teams.items():
                        members = [m.get('username') for m in info.get('members', [])]
                        ts = {'total': 0, 'open': 0, 'closed': 0, 'members': members}
                        for issue in issues:
                            assignee = issue.get('assignee')
                            if assignee:
                                an = assignee if isinstance(assignee, str) else assignee.get('login')
                                if an in members:
                                    ts['total'] += 1
                                    if issue.get('state') == 'open':
                                        ts['open'] += 1
                                    else:
                                        ts['closed'] += 1
                        team_stats[slug] = ts
                    return team_stats

                def _save_statistics_report(self, stats, report_file: Path):
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
                    report_file.write_text(content, encoding='utf-8')

                def _save_team_report(self, team_stats, report_file: Path):
                    content = f"""# 团队Issues分析报告

            **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            ## 团队概况

            """
                    for slug, stats in team_stats.items():
                        team_data = self.team_info['teams'].get(slug, {})
                        content += f"### {team_data.get('name', slug)}\n\n"
                        content += f"- **描述**: {team_data.get('description', '无描述')}\n"
                        content += f"- **成员数**: {len(stats.get('members', []))}\n"
                        content += f"- **Issues总数**: {stats.get('total', 0)}\n"
                        content += f"- **开放Issues**: {stats.get('open', 0)}\n"
                        content += f"- **已关闭Issues**: {stats.get('closed', 0)}\n"
                        content += f"- **成员**: {', '.join(stats.get('members', []))}\n\n"
                    report_file.write_text(content, encoding='utf-8')


            def main():
                parser = argparse.ArgumentParser(description="Issues管理工具 - 非AI功能")
                parser.add_argument("--action", choices=["statistics", "create", "team", "project", "update-team"], required=True)
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


            if __name__ == '__main__':
                main()
