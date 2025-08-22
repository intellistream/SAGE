#!/usr/bin/env python3
"""
获取GitHub组织团队成员信息
用于创建课题组成员metadata
"""

import os
import json
import requests
import sys
from pathlib import Path


class TeamMembersCollector:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            sys.exit(1)
            
        self.org = "intellistream"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 团队slug列表
        self.teams = {
            "sage-apps": {
                "name": "SAGE Apps Team",
                "description": "负责SAGE应用层开发和集成",
                "members": []
            },
            "sage-middleware": {
                "name": "SAGE Middleware Team", 
                "description": "负责SAGE中间件和服务层开发",
                "members": []
            },
            "sage-kernel": {
                "name": "SAGE Kernel Team",
                "description": "负责SAGE核心引擎和内核开发", 
                "members": []
            }
        }
        
    def get_team_members(self, team_slug):
        """获取指定团队的成员列表"""
        url = f"https://api.github.com/orgs/{self.org}/teams/{team_slug}/members"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                members = response.json()
                member_list = []
                
                for member in members:
                    member_info = {
                        "username": member["login"],
                        "avatar_url": member["avatar_url"],
                        "profile_url": member["html_url"],
                        "id": member["id"],
                        "type": member["type"]
                    }
                    member_list.append(member_info)
                    
                print(f"✅ 获取团队 {team_slug} 成员: {len(member_list)} 人")
                return member_list
                
            elif response.status_code == 404:
                print(f"❌ 团队 {team_slug} 不存在或无权限访问")
                return []
                
            else:
                print(f"❌ 获取团队 {team_slug} 成员失败: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
            
    def collect_all_members(self):
        """收集所有团队成员信息"""
        print("🔍 开始收集课题组成员信息...")
        
        for team_slug, team_info in self.teams.items():
            print(f"\n📋 获取团队: {team_info['name']}")
            members = self.get_team_members(team_slug)
            team_info["members"] = members
            
        return self.teams
        
    def generate_metadata_files(self):
        """生成metadata文件"""
        print("\n📄 生成metadata文件...")
        
        # 收集成员信息
        teams_data = self.collect_all_members()
        
        # 创建输出目录
        output_dir = Path("../../output")
        output_dir.mkdir(exist_ok=True)
        
        # 1. 生成JSON格式的完整metadata
        json_file = output_dir / "team_members.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON metadata: {json_file}")
        
        # 2. 生成YAML格式的配置文件
        yaml_file = output_dir / "team_members.yaml"
        yaml_content = self.generate_yaml_content(teams_data)
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"✅ YAML metadata: {yaml_file}")
        
        # 3. 生成简化的用户名列表
        usernames_file = output_dir / "team_usernames.txt"
        usernames_content = self.generate_usernames_content(teams_data)
        with open(usernames_file, 'w', encoding='utf-8') as f:
            f.write(usernames_content)
        print(f"✅ 用户名列表: {usernames_file}")
        
        # 4. 生成Python配置模块
        py_file = output_dir / "team_config.py"
        py_content = self.generate_python_config(teams_data)
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(py_content)
        print(f"✅ Python配置: {py_file}")
        
        return teams_data
        
    def generate_yaml_content(self, teams_data):
        """生成YAML格式内容"""
        content = """# SAGE课题组成员配置
# 用于issues管理和团队协作

organization: intellistream
project: SAGE
last_updated: """ + self.get_current_time() + """

teams:
"""
        
        for team_slug, team_info in teams_data.items():
            content += f"""
  {team_slug}:
    name: "{team_info['name']}"
    description: "{team_info['description']}"
    members:
"""
            for member in team_info['members']:
                content += f"""      - username: {member['username']}
        profile: {member['profile_url']}
        id: {member['id']}
"""
                
        return content
        
    def generate_usernames_content(self, teams_data):
        """生成简化的用户名列表"""
        content = """# SAGE课题组成员GitHub用户名列表
# 生成时间: """ + self.get_current_time() + """

"""
        
        all_usernames = set()
        
        for team_slug, team_info in teams_data.items():
            content += f"\n## {team_info['name']}\n"
            team_usernames = []
            
            for member in team_info['members']:
                username = member['username']
                team_usernames.append(username)
                all_usernames.add(username)
                content += f"- {username}\n"
                
            content += f"团队成员数: {len(team_usernames)}\n"
            
        content += f"\n## 全部成员汇总\n"
        content += f"总成员数: {len(all_usernames)}\n"
        content += f"成员列表: {', '.join(sorted(all_usernames))}\n"
        
        return content
        
    def generate_python_config(self, teams_data):
        """生成Python配置模块"""
        content = '''#!/usr/bin/env python3
"""
SAGE课题组成员配置
用于issues管理脚本
"""

from datetime import datetime

# 配置元信息
CONFIG_INFO = {
    "organization": "intellistream",
    "project": "SAGE",
    "last_updated": "''' + self.get_current_time() + '''",
    "generator": "TeamMembersCollector"
}

# 团队配置
TEAMS = {
'''
        
        for team_slug, team_info in teams_data.items():
            content += f'''    "{team_slug}": {{
        "name": "{team_info['name']}",
        "description": "{team_info['description']}",
        "members": [
'''
            for member in team_info['members']:
                content += f'''            {{
                "username": "{member['username']}",
                "profile_url": "{member['profile_url']}",
                "avatar_url": "{member['avatar_url']}",
                "id": {member['id']},
                "type": "{member['type']}"
            }},
'''
            content += '''        ]
    },
'''
        
        content += '''}

# 便捷访问函数
def get_all_usernames():
    """获取所有成员的用户名列表"""
    usernames = set()
    for team_info in TEAMS.values():
        for member in team_info["members"]:
            usernames.add(member["username"])
    return sorted(list(usernames))

def get_team_usernames(team_slug):
    """获取指定团队的用户名列表"""
    if team_slug in TEAMS:
        return [member["username"] for member in TEAMS[team_slug]["members"]]
    return []

def get_user_team(username):
    """获取用户所属的团队"""
    for team_slug, team_info in TEAMS.items():
        for member in team_info["members"]:
            if member["username"] == username:
                return team_slug
    return None

def is_team_member(username):
    """检查用户是否为团队成员"""
    return username in get_all_usernames()

def get_team_stats():
    """获取团队统计信息"""
    stats = {}
    total_members = set()
    
    for team_slug, team_info in TEAMS.items():
        team_members = [member["username"] for member in team_info["members"]]
        stats[team_slug] = {
            "name": team_info["name"],
            "member_count": len(team_members),
            "members": team_members
        }
        total_members.update(team_members)
    
    stats["total"] = {
        "unique_members": len(total_members),
        "all_members": sorted(list(total_members))
    }
    
    return stats

if __name__ == "__main__":
    # 测试代码
    print("🔍 SAGE课题组成员配置测试")
    print(f"📊 配置信息: {CONFIG_INFO}")
    
    stats = get_team_stats()
    print(f"\\n📈 团队统计:")
    for team_slug, team_stat in stats.items():
        if team_slug != "total":
            print(f"  {team_stat['name']}: {team_stat['member_count']} 人")
            print(f"    成员: {', '.join(team_stat['members'])}")
    
    print(f"\\n👥 总计: {stats['total']['unique_members']} 位独特成员")
    print(f"📋 全部成员: {', '.join(stats['total']['all_members'])}")
'''
        
        return content
        
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    collector = TeamMembersCollector()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "collect":
            # 仅收集数据，不生成文件
            teams_data = collector.collect_all_members()
            print("\n📊 收集结果:")
            for team_slug, team_info in teams_data.items():
                print(f"  {team_info['name']}: {len(team_info['members'])} 人")
        else:
            print("用法: python3 get_team_members.py [collect]")
    else:
        # 完整流程：收集数据并生成metadata文件
        teams_data = collector.generate_metadata_files()
        
        print(f"\n🎉 metadata文件生成完成!")
        print(f"📁 输出目录: metadata/")
        print(f"📄 生成的文件:")
        print(f"  - team_members.json (完整JSON数据)")
        print(f"  - team_members.yaml (YAML配置)")
        print(f"  - team_usernames.txt (用户名列表)")
        print(f"  - team_config.py (Python配置模块)")
