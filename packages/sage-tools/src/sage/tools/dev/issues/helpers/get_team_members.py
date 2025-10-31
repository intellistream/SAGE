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

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# Import IssuesConfig robustly whether run as a module or as a script
try:
    # Preferred: absolute import via installed/available package path
    from sage.tools.dev.issues.config import IssuesConfig as Config
except Exception:
    # Fallback: when executed directly, ensure the package src root is on sys.path
    current = Path(__file__).resolve()
    src_path = None
    for p in current.parents:
        # Look for a 'src' directory that contains the 'sage' package
        if p.name == "src" and (p / "sage").exists():
            src_path = p
            break
    if src_path is not None:
        sys.path.insert(0, str(src_path))
        from sage.tools.dev.issues.config import IssuesConfig as Config
    else:
        # Last resort: try relative import if package context exists
        from ..config import IssuesConfig as Config


def find_token():
    config = Config()
    return config.github_token


class TeamMembersCollector:
    def __init__(self, token, org="intellistream"):
        self.token = token
        self.org = org
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.teams = {
            "sage-kernel": {"description": "负责SAGE核心算法和内核开发", "members": []},
            "sage-apps": {"description": "负责SAGE应用和前端开发", "members": []},
            "sage-middleware": {
                "description": "负责SAGE中间件和服务层开发",
                "members": [],
            },
        }
        # 使用config获取meta-data目录路径
        config = Config()
        self.meta_dir = config.metadata_path
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _get_team_members(self, team_slug):
        members = []
        url = f"https://api.github.com/orgs/{self.org}/teams/{team_slug}/members"
        params = {"per_page": 100}
        while url:
            resp = requests.get(url, headers=self.headers, params=params)
            if resp.status_code != 200:
                error_msg = f"获取团队 {team_slug} 成员失败: {resp.status_code} {resp.text}"
                print(f"❌ {error_msg}", file=sys.stderr)
                return []
            data = resp.json()
            for member in data:
                members.append(
                    {
                        "username": member.get("login"),
                        "avatar_url": member.get("avatar_url"),
                        "profile_url": member.get("html_url"),
                        "id": member.get("id"),
                        "type": member.get("type"),
                    }
                )
            # handle pagination via Link header
            link = resp.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link:
                # parse next URL
                parts = [p.strip() for p in link.split(",")]
                for part in parts:
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>").strip()
            url = next_url
            params = {}
        return members

    def collect(self):
        success_count = 0
        for slug in self.teams.keys():
            print(f"📋 获取团队 {slug} 成员...")
            members = self._get_team_members(slug)
            if members:  # Only count as success if we got members
                self.teams[slug]["members"] = members
                success_count += 1
                print(f"✅ {slug}: {len(members)} 人")
            else:
                print(f"❌ {slug}: 获取失败")

        if success_count == 0:
            print("所有团队获取失败，无法生成团队信息", file=sys.stderr)
            return None
        else:
            print(f"✅ 成功获取 {success_count}/{len(self.teams)} 个团队的信息")
            return self.teams

    def write_outputs(self, teams_data):
        # JSON
        json_file = self.meta_dir / "team_members.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(teams_data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON metadata: {json_file}")

        # YAML (simple)
        yaml_file = self.meta_dir / "team_members.yaml"
        yaml_lines = []
        yaml_lines.append("# SAGE teams")
        yaml_lines.append(f"last_updated: {datetime.now().isoformat()}")
        yaml_lines.append("teams:")
        for slug, info in teams_data.items():
            yaml_lines.append(f"  {slug}:")
            yaml_lines.append(f'    name: "{info.get("name")}"')
            yaml_lines.append(f'    description: "{info.get("description")}"')
            yaml_lines.append("    members:")
            for m in info.get("members", []):
                yaml_lines.append(f"      - username: {m.get('username')}")
                yaml_lines.append(f"        profile: {m.get('profile_url')}")
        yaml_file.write_text("\n".join(yaml_lines), encoding="utf-8")
        print(f"✅ YAML metadata: {yaml_file}")

        # usernames
        usernames_file = self.meta_dir / "team_usernames.txt"
        lines = [f"# generated: {datetime.now().isoformat()}"]
        all_usernames = set()
        for slug, info in teams_data.items():
            lines.append(f"\n## {info.get('name')}")
            for m in info.get("members", []):
                username = m.get("username")
                lines.append(f"- {username}")
                all_usernames.add(username)
            lines.append(f"team_count: {len(info.get('members', []))}")
        lines.append("\n## ALL")
        lines.append(f"total_unique: {len(all_usernames)}")
        lines.append("members: " + ", ".join(sorted(all_usernames)))
        usernames_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"✅ 用户名列表: {usernames_file}")

        # python config
        py_file = self.meta_dir / "team_config.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("# Auto-generated team_config for SAGE\n")
            f.write("TEAMS = {\n")
            for slug, info in teams_data.items():
                f.write(f"    '{slug}': {{\n")
                f.write(f"        'name': '{info.get('name')}',\n")
                f.write(f"        'description': '{info.get('description')}',\n")
                f.write("        'members': [\n")
                for m in info.get("members", []):
                    f.write("            {\n")
                    f.write(f"                'username': '{m.get('username')}',\n")
                    f.write(f"                'profile_url': '{m.get('profile_url')}',\n")
                    f.write(f"                'avatar_url': '{m.get('avatar_url')}',\n")
                    f.write(f"                'id': {m.get('id')},\n")
                    f.write(f"                'type': '{m.get('type')}'\n")
                    f.write("            },\n")
                f.write("        ]\n")
                f.write("    },\n")
            f.write("}\n")
        print(f"✅ Python config: {py_file}")


def main():
    # 使用统一的token查找方法
    token = find_token()
    if token:
        print("✅ 获取到 GitHub Token")
    else:
        print("❌ 未找到 GitHub Token")
        return

    if not token:
        token = find_token()

    if not token:
        print(
            "未找到 GitHub Token。请设置 GITHUB_TOKEN 环境变量或在仓库根目录创建 .github_token 文件",
            file=sys.stderr,
        )
        sys.exit(1)

    collector = TeamMembersCollector(token)
    teams = collector.collect()
    if teams is None:
        print("无法获取任何团队信息，退出", file=sys.stderr)
        sys.exit(1)
    collector.write_outputs(teams)
    print("\n🎉 metadata 文件生成完成")


if __name__ == "__main__":
    main()
