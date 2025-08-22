#!/usr/bin/env python3
"""
将KimmoZAG创建的issues移动到SAGE-Middleware项目的脚本
"""

import os
import json
import requests
from pathlib import Path
import sys
import time

class IssueProjectMover:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            sys.exit(1)
            
        self.repo = "intellistream/SAGE"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        self.graphql_headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json"
        }
        
        self.issues_dir = Path("../downloaded_issues/issues")
        
    def find_kimmo_issues(self):
        """查找KimmoZAG创建的issues"""
        print("🔍 查找KimmoZAG创建的issues...")
        
        kimmo_issues = []
        
        if not self.issues_dir.exists():
            print("❌ issues目录不存在，请先下载issues")
            return []
            
        # 遍历所有issue文件
        for issue_file in self.issues_dir.glob("*.md"):
            try:
                content = issue_file.read_text(encoding='utf-8')
                
                # 检查是否包含KimmoZAG作为作者
                if "**作者**: KimmoZAG" in content:
                    # 提取issue编号
                    issue_number = None
                    for line in content.split('\n'):
                        if line.startswith('**Issue #**:'):
                            issue_number = line.split(':')[1].strip()
                            break
                    
                    if issue_number:
                        kimmo_issues.append({
                            'number': int(issue_number),
                            'file': issue_file.name,
                            'title': self.extract_title(content)
                        })
                        
            except Exception as e:
                print(f"⚠️ 读取文件 {issue_file} 失败: {e}")
                
        print(f"✅ 找到 {len(kimmo_issues)} 个KimmoZAG创建的issues")
        return sorted(kimmo_issues, key=lambda x: x['number'])
    
    def extract_title(self, content):
        """从issue内容中提取标题"""
        for line in content.split('\n'):
            if line.startswith('# '):
                return line[2:].strip()
        return "未知标题"
    
    def get_organization_projects(self):
        """获取组织的所有项目（使用GraphQL API）"""
        print("🔍 查询组织项目...")
        
        query = """
        query {
          organization(login: "intellistream") {
            projectsV2(first: 100) {
              nodes {
                id
                title
                number
                url
              }
            }
          }
        }
        """
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.graphql_headers,
            json={"query": query}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ GraphQL错误: {data['errors']}")
                return []
            
            projects = data['data']['organization']['projectsV2']['nodes']
            print(f"✅ 找到 {len(projects)} 个项目")
            
            for project in projects:
                print(f"   📋 {project['title']} (#{project['number']}) - {project['url']}")
                
            return projects
        else:
            print(f"❌ 查询项目失败: {response.status_code} - {response.text}")
            return []
    
    def find_sage_middleware_project(self, projects):
        """查找SAGE-Middleware项目"""
        for project in projects:
            if "SAGE-Middleware" in project['title'] or "sage-middleware" in project['title'].lower():
                return project
        return None
    
    def add_issue_to_project(self, issue_number, project_id):
        """将issue添加到项目中"""
        print(f"📌 将issue #{issue_number} 添加到项目...")
        
        # 首先获取issue的node_id
        issue_response = requests.get(
            f"https://api.github.com/repos/{self.repo}/issues/{issue_number}",
            headers=self.headers
        )
        
        if issue_response.status_code != 200:
            print(f"❌ 获取issue #{issue_number} 失败: {issue_response.status_code}")
            return False
            
        issue_node_id = issue_response.json()['node_id']
        
        # 使用GraphQL添加issue到项目
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        
        variables = {
            "projectId": project_id,
            "contentId": issue_node_id
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.graphql_headers,
            json={"query": mutation, "variables": variables}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ 添加issue #{issue_number} 到项目失败: {data['errors']}")
                return False
            print(f"✅ issue #{issue_number} 已添加到项目")
            return True
        else:
            print(f"❌ 添加issue #{issue_number} 到项目失败: {response.status_code} - {response.text}")
            return False
    
    def run(self):
        """执行主流程"""
        print("🚀 开始将KimmoZAG的issues移动到SAGE-Middleware项目")
        print("=" * 60)
        
        # 1. 查找KimmoZAG的issues
        kimmo_issues = self.find_kimmo_issues()
        if not kimmo_issues:
            print("❌ 未找到KimmoZAG创建的issues")
            return
            
        print(f"\n📋 找到的KimmoZAG issues:")
        for issue in kimmo_issues[:5]:  # 显示前5个
            print(f"   #{issue['number']}: {issue['title']}")
        if len(kimmo_issues) > 5:
            print(f"   ... 还有 {len(kimmo_issues) - 5} 个issues")
        
        # 2. 查询组织项目
        projects = self.get_organization_projects()
        if not projects:
            print("❌ 未找到任何项目")
            return
            
        # 3. 查找SAGE-Middleware项目
        sage_middleware_project = self.find_sage_middleware_project(projects)
        if not sage_middleware_project:
            print("❌ 未找到SAGE-Middleware项目")
            print("\n💡 可用的项目:")
            for project in projects:
                print(f"   📋 {project['title']} (#{project['number']})")
            
            # 让用户选择项目
            print(f"\n请选择要使用的项目编号 (1-{len(projects)}):")
            try:
                choice = int(input("输入项目编号: ")) - 1
                if 0 <= choice < len(projects):
                    sage_middleware_project = projects[choice]
                else:
                    print("❌ 无效选择")
                    return
            except ValueError:
                print("❌ 无效输入")
                return
        
        print(f"\n✅ 将使用项目: {sage_middleware_project['title']}")
        project_id = sage_middleware_project['id']
        
        # 4. 确认操作
        print(f"\n✅ 自动确认：将 {len(kimmo_issues)} 个KimmoZAG的issues添加到项目 '{sage_middleware_project['title']}'")
        # confirm = input(f"\n❓ 确认将 {len(kimmo_issues)} 个KimmoZAG的issues添加到项目 '{sage_middleware_project['title']}' 吗? (y/N): ")
        # if confirm.lower() != 'y':
        #     print("❌ 操作已取消")
        #     return
        
        # 5. 执行添加操作
        print(f"\n🔄 开始添加issues到项目...")
        success_count = 0
        
        for i, issue in enumerate(kimmo_issues, 1):
            print(f"\n[{i}/{len(kimmo_issues)}] 处理issue #{issue['number']}: {issue['title']}")
            
            if self.add_issue_to_project(issue['number'], project_id):
                success_count += 1
            
            # 避免API限制
            time.sleep(1)
        
        print(f"\n🎉 完成！成功添加 {success_count}/{len(kimmo_issues)} 个issues到项目")

if __name__ == "__main__":
    try:
        print("🔧 初始化IssueProjectMover...")
        mover = IssueProjectMover()
        print("✅ 初始化完成，开始执行...")
        mover.run()
    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
