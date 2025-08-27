#!/usr/bin/env python3
"""
Fetch GitHub organization team members for SAGE teams and write metadata files.

Creates in `output/`:
 - team_members.json
 - team_members.yaml
 - team_usernames.txt
 - team_config.py

Token resolution order: GITHUB_TOKEN env var -> .github_token file searched upward from repo -> user's home .github_token
"""
import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime


def find_token():
    token = os.getenv('GITHUB_TOKEN')
    if token:
        return token

    # search upward from this script
    p = Path(__file__).resolve()
    for parent in [p.parent, p.parent.parent, p.parent.parent.parent]:
        candidate = parent / '.github_token'
        if candidate.exists():
            t = candidate.read_text().strip()
            if t:
                return t

    home_candidate = Path.home() / '.github_token'
    if home_candidate.exists():
        t = home_candidate.read_text().strip()
        if t:
            return t

    return None


class TeamMembersCollector:
    def __init__(self, token, org='intellistream'):
        self.token = token
        self.org = org
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.teams = {
            'sage-apps': {
                'name': 'SAGE Apps Team',
                'description': '负责SAGE应用层开发和集成',
                'members': []
            },
            'sage-kernel': {
                'name': 'SAGE Kernel Team',
                'description': '负责SAGE核心引擎和内核开发',
                'members': []
            },
            'sage-middleware': {
                'name': 'SAGE Middleware Team',
                'description': '负责SAGE中间件和服务层开发',
                'members': []
            }
        }
        # meta-data directory relative to repository tools/issues-management (up one level)
        # __file__ -> .../_scripts/helpers, parent.parent.parent -> tools/issues-management
        self.meta_dir = Path(__file__).parent.parent.parent / 'meta-data'
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _get_team_members(self, team_slug):
        members = []
        url = f'https://api.github.com/orgs/{self.org}/teams/{team_slug}/members'
        params = {'per_page': 100}
        while url:
            resp = requests.get(url, headers=self.headers, params=params)
            if resp.status_code != 200:
                print(f'❌ 获取团队 {team_slug} 成员失败: {resp.status_code} {resp.text}')
                return []
            data = resp.json()
            for member in data:
                members.append({
                    'username': member.get('login'),
                    'avatar_url': member.get('avatar_url'),
                    'profile_url': member.get('html_url'),
                    'id': member.get('id'),
                    'type': member.get('type')
                })
            # handle pagination via Link header
            link = resp.headers.get('Link', '')
            next_url = None
            if 'rel="next"' in link:
                # parse next URL
                parts = [p.strip() for p in link.split(',')]
                for part in parts:
                    if 'rel="next"' in part:
                        next_url = part.split(';')[0].strip().strip('<>').strip()
            url = next_url
            params = {}
        return members

    def collect(self):
        for slug in self.teams.keys():
            print(f'📋 获取团队 {slug} 成员...')
            members = self._get_team_members(slug)
            self.teams[slug]['members'] = members
            print(f'✅ {slug}: {len(members)} 人')
        return self.teams

    def write_outputs(self, teams_data):
        # JSON
        json_file = self.meta_dir / 'team_members.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, indent=2, ensure_ascii=False)
        print(f'✅ JSON metadata: {json_file}')

        # YAML (simple)
        yaml_file = self.meta_dir / 'team_members.yaml'
        yaml_lines = []
        yaml_lines.append('# SAGE teams')
        yaml_lines.append(f'last_updated: {datetime.now().isoformat()}')
        yaml_lines.append('teams:')
        for slug, info in teams_data.items():
            yaml_lines.append(f'  {slug}:')
            yaml_lines.append(f'    name: "{info.get("name")}"')
            yaml_lines.append(f'    description: "{info.get("description")}"')
            yaml_lines.append('    members:')
            for m in info.get('members', []):
                yaml_lines.append(f'      - username: {m.get("username")}')
                yaml_lines.append(f'        profile: {m.get("profile_url")}')
        yaml_file.write_text('\n'.join(yaml_lines), encoding='utf-8')
        print(f'✅ YAML metadata: {yaml_file}')

        # usernames
        usernames_file = self.meta_dir / 'team_usernames.txt'
        lines = [f'# generated: {datetime.now().isoformat()}']
        all_usernames = set()
        for slug, info in teams_data.items():
            lines.append(f'\n## {info.get("name")}')
            for m in info.get('members', []):
                username = m.get('username')
                lines.append(f'- {username}')
                all_usernames.add(username)
            lines.append(f'team_count: {len(info.get("members", []))}')
        lines.append('\n## ALL')
        lines.append(f'total_unique: {len(all_usernames)}')
        lines.append('members: ' + ', '.join(sorted(all_usernames)))
        usernames_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f'✅ 用户名列表: {usernames_file}')

        # python config
        py_file = self.meta_dir / 'team_config.py'
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write('# Auto-generated team_config for SAGE\n')
            f.write('TEAMS = {\n')
            for slug, info in teams_data.items():
                f.write(f"    '{slug}': {{\n")
                f.write(f"        'name': '{info.get('name')}',\n")
                f.write(f"        'description': '{info.get('description')}',\n")
                f.write("        'members': [\n")
                for m in info.get('members', []):
                    f.write('            {\n')
                    f.write(f"                'username': '{m.get('username')}',\n")
                    f.write(f"                'profile_url': '{m.get('profile_url')}',\n")
                    f.write(f"                'avatar_url': '{m.get('avatar_url')}',\n")
                    f.write(f"                'id': {m.get('id')},\n")
                    f.write(f"                'type': '{m.get('type')}'\n")
                    f.write('            },\n')
                f.write('        ]\n')
                f.write('    },\n')
            f.write('}\n')
        print(f'✅ Python config: {py_file}')


def main():
    # 优先使用项目统一配置中的 token（_scripts/config.py）
    token = None
    try:
        # 添加 _scripts 目录到 sys.path，便于导入 config
        # helpers is one level deeper, so insert parent.parent
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import config as project_config
        token = getattr(project_config, 'github_token', None)
        if token:
            print('✅ 从 _scripts/config.py 获取到 GitHub Token')
    except Exception:
        # 如果导入失败，则回退到本地查找
        token = None

    if not token:
        token = find_token()

    if not token:
        print('❌ 未找到 GitHub Token。请设置 GITHUB_TOKEN 环境变量或在仓库根目录创建 .github_token 文件')
        sys.exit(1)

    collector = TeamMembersCollector(token)
    teams = collector.collect()
    collector.write_outputs(teams)
    print('\n🎉 metadata 文件生成完成')


if __name__ == '__main__':
    main()
