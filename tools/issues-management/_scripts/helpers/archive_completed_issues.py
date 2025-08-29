#!/usr/bin/env python3
"""
Archive Completed Issues Tool for SAGE

This script automatically archives completed issues based on their completion time:
- Issues completed within 1 week → Move to "Done" column
- Issues completed 1 week to 1 month ago → Move to "Archive" column  
- Issues completed over 1 month ago → Move to "History" column (create if not exists)

Features:
- --preview: Show what would be moved without making changes
- Automatically handles GitHub Projects v2 API
- Creates "History" column if it doesn't exist
- Respects rate limits with proper delays
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


class CompletedIssuesArchiver:
    ORG = "intellistream"
    REPO = "SAGE"
    # 处理多个项目: sage-kernel (#12), sage-middleware (#13), sage-app (#14)
    PROJECT_NUMBERS = [12, 13, 14]
    PROJECT_NAMES = {
        12: "sage-kernel",
        13: "sage-middleware", 
        14: "sage-app"
    }
    
    # Time thresholds
    ONE_WEEK = timedelta(days=7)
    ONE_MONTH = timedelta(days=30)
    
    # Status field and option IDs will be determined per project
    STATUS_OPTIONS = {
        "Done": None,
        "Archive": None,
        "History": None
    }

    def __init__(self, preview_mode=False):
        self.preview_mode = preview_mode
        self.github_token = self._get_github_token()
        
        if not self.github_token:
            print("❌ 未找到GitHub Token，请确保已正确配置")
            sys.exit(1)
            
        self.headers = {
            'Authorization': f'Bearer {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        self.graphql_headers = {
            'Authorization': f'Bearer {self.github_token}',
            'Content-Type': 'application/json'
        }
        
        # Cache for project data
        self.projects_data = {}  # Will store data for each project
        self.all_categorized_issues = {
            "to_done": [],
            "to_archive": [],
            "to_history": [],
            "already_correct": [],
            "not_applicable": []
        }

    def _get_github_token(self):
        """Get GitHub token from various sources"""
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
            
        # Try config.py
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import config as project_config
            token = getattr(project_config, 'github_token', None)
            if token:
                print('✅ 从 _scripts/config.py 获取到 GitHub Token')
                return token
        except Exception:
            pass
            
        # Try .github_token file
        current_dir = Path(__file__).parent
        for _ in range(5):  # Search up to 5 levels up
            token_file = current_dir / ".github_token"
            if token_file.exists():
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                    print(f'✅ 从 {token_file} 获取到 GitHub Token')
                    return token
            current_dir = current_dir.parent
            
        return None

    def get_projects_info(self):
        """Get info for all target projects and ensure they have proper status fields"""
        print(f"🔍 获取项目信息 (项目 #{', #'.join(map(str, self.PROJECT_NUMBERS))})...")
        
        for project_number in self.PROJECT_NUMBERS:
            project_name = self.PROJECT_NAMES[project_number]
            print(f"\n📋 处理项目 #{project_number} ({project_name})...")
            
            query = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {project_number}) {{
            id
            title
            fields(first: 20) {{
                nodes {{
                    ... on ProjectV2SingleSelectField {{
                        id
                        name
                        options {{
                            id
                            name
                        }}
                    }}
                }}
            }}
        }}
    }}
}}'''
            
            resp = requests.post("https://api.github.com/graphql", 
                               headers=self.graphql_headers, 
                               json={"query": query})
            
            if resp.status_code != 200:
                print(f"❌ 获取项目 #{project_number} 信息失败: {resp.status_code} - {resp.text}")
                continue
                
            data = resp.json()
            if "errors" in data:
                print(f"❌ GraphQL 返回错误 (项目 #{project_number}): {data['errors']}")
                continue
                
            project = data.get("data", {}).get("organization", {}).get("projectV2")
            if not project:
                print(f"❌ 未找到项目 #{project_number}")
                continue
                
            project_id = project["id"]
            project_title = project["title"]
            print(f"✅ 找到项目: {project_title} (ID: {project_id})")
            
            # Find Status field and extract options
            status_field_id = None
            status_options = {}
            
            for field in project["fields"]["nodes"]:
                if field.get("name") == "Status":
                    status_field_id = field["id"]
                    for option in field.get("options", []):
                        status_options[option["name"]] = option["id"]
                    break
            
            if not status_field_id:
                print(f"❌ 项目 #{project_number} 中未找到 Status 字段")
                continue
            
            # Check required status options
            required_statuses = ["Done", "Archive"]
            missing_statuses = []
            
            for status in required_statuses:
                if status not in status_options:
                    missing_statuses.append(status)
            
            # Check if History exists, create if needed
            if "History" not in status_options:
                print(f"📝 项目 #{project_number} 中 History 状态选项不存在，将创建...")
                if not self.preview_mode:
                    history_option_id = self._create_history_option(status_field_id, project_number)
                    if history_option_id:
                        status_options["History"] = history_option_id
                        print(f"✅ 成功在项目 #{project_number} 中创建 History 状态选项")
                    else:
                        print(f"❌ 在项目 #{project_number} 中创建 History 状态选项失败")
                        continue
                else:
                    print(f"🔍 预览模式：将在项目 #{project_number} 中创建 History 状态选项")
                    status_options["History"] = "preview_history_id"  # Placeholder for preview
            else:
                print(f"✅ 项目 #{project_number} 中找到现有的 History 状态选项")
            
            if missing_statuses:
                print(f"❌ 项目 #{project_number} 中缺少必要的状态选项: {', '.join(missing_statuses)}")
                continue
            
            # Store project data
            self.projects_data[project_number] = {
                "id": project_id,
                "title": project_title,
                "name": project_name,
                "status_field_id": status_field_id,
                "status_options": status_options
            }
            
            print(f"✅ 项目 #{project_number} 配置完成")
        
        if not self.projects_data:
            print("❌ 未找到任何可用的项目")
            return False
            
        print(f"\n✅ 成功配置 {len(self.projects_data)} 个项目")
        return True

    def _create_history_option(self, status_field_id, project_number):
        """Create History option in Status field for a specific project"""
        mutation = f'''mutation {{
    updateProjectV2Field(input: {{
        fieldId: "{status_field_id}"
        singleSelectField: {{
            options: [
                {{ name: "History", color: "GRAY", description: "Issues completed over 1 month ago" }}
            ]
        }}
    }}) {{
        projectV2Field {{
            ... on ProjectV2SingleSelectField {{
                options {{
                    id
                    name
                }}
            }}
        }}
    }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql",
                           headers=self.graphql_headers,
                           json={"query": mutation})
        
        if resp.status_code != 200:
            print(f"❌ 在项目 #{project_number} 中创建 History 选项失败: {resp.status_code} - {resp.text}")
            return None
            
        data = resp.json()
        if "errors" in data:
            print(f"❌ 在项目 #{project_number} 中创建 History 选项失败: {data['errors']}")
            return None
            
        # Find the new History option ID
        field_data = data.get("data", {}).get("updateProjectV2Field", {}).get("projectV2Field", {})
        options = field_data.get("options", [])
        
        for option in options:
            if option["name"] == "History":
                return option["id"]
                
        print(f"❌ 未能获取项目 #{project_number} 中新创建的 History 选项ID")
        return None

    def get_completed_issues_from_projects(self):
        """Get all issues from all target projects to check their status and completion time"""
        all_project_items = []
        
        for project_number, project_data in self.projects_data.items():
            project_name = project_data["name"]
            project_id = project_data["id"]
            
            print(f"\n🔍 获取项目 #{project_number} ({project_name}) 中的Issues...")
            
            project_items = []
            after = None
            
            while True:
                after_clause = f', after: "{after}"' if after else ''
                query = f'''query {{
    organization(login: "{self.ORG}") {{
        projectV2(number: {project_number}) {{
            items(first: 100{after_clause}) {{
                pageInfo {{ hasNextPage endCursor }}
                nodes {{
                    id
                    fieldValues(first: 10) {{
                        nodes {{
                            ... on ProjectV2ItemFieldSingleSelectValue {{
                                field {{
                                    ... on ProjectV2SingleSelectField {{
                                        name
                                    }}
                                }}
                                optionId
                                name
                            }}
                        }}
                    }}
                    content {{
                        __typename
                        ... on Issue {{
                            id
                            number
                            title
                            state
                            closedAt
                            repository {{
                                name
                                owner {{ login }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
}}'''

                resp = requests.post("https://api.github.com/graphql", 
                                   headers=self.graphql_headers, 
                                   json={"query": query})
                
                if resp.status_code != 200:
                    print(f"❌ 获取项目 #{project_number} Issues失败: {resp.status_code} - {resp.text}")
                    break
                    
                data = resp.json()
                if "errors" in data:
                    print(f"❌ GraphQL 返回错误 (项目 #{project_number}): {data['errors']}")
                    break

                items_data = data.get("data", {}).get("organization", {}).get("projectV2", {}).get("items", {})
                nodes = items_data.get("nodes", [])
                
                # Add project context to each item
                for node in nodes:
                    node["_project_number"] = project_number
                    node["_project_data"] = project_data
                
                project_items.extend(nodes)

                page_info = items_data.get("pageInfo", {})
                if page_info.get("hasNextPage"):
                    after = page_info.get("endCursor")
                    time.sleep(0.2)  # Rate limiting
                    continue
                else:
                    break
            
            print(f"✅ 从项目 #{project_number} 获取到 {len(project_items)} 个项目项")
            all_project_items.extend(project_items)
        
        print(f"\n✅ 总计获取到 {len(all_project_items)} 个项目项")
        return all_project_items

    def analyze_and_categorize_issues(self, project_items):
        """Analyze issues and categorize them based on completion time"""
        now = datetime.now()
        categorized = {
            "to_done": [],      # Within 1 week
            "to_archive": [],   # 1 week to 1 month
            "to_history": [],   # Over 1 month
            "already_correct": [], # Already in correct status
            "not_applicable": []   # Not closed or no close date
        }
        
        print("\n🔍 分析Issues完成时间...")
        
        # Group by project for better reporting
        project_stats = {}
        for project_number in self.projects_data.keys():
            project_stats[project_number] = {
                "processed": 0,
                "to_move": 0,
                "already_correct": 0,
                "not_applicable": 0
            }
        
        for item in project_items:
            content = item.get("content", {})
            if content.get("__typename") != "Issue":
                continue
            
            # Get project context
            project_number = item.get("_project_number")
            project_data = item.get("_project_data")
            
            if not project_number or not project_data:
                continue
                
            project_stats[project_number]["processed"] += 1
                
            issue = content
            issue_number = issue.get("number")
            title = issue.get("title", "")
            state = issue.get("state")
            closed_at_str = issue.get("closedAt")
            
            # Get current status from project field values
            current_status = None
            for field_value in item.get("fieldValues", {}).get("nodes", []):
                field = field_value.get("field", {})
                if field.get("name") == "Status":
                    current_status = field_value.get("name")
                    break
            
            # Skip if not closed
            if state != "CLOSED" or not closed_at_str:
                categorized["not_applicable"].append({
                    "item": item,
                    "issue": issue,
                    "project_number": project_number,
                    "project_name": project_data["name"],
                    "reason": "Not closed or no close date"
                })
                project_stats[project_number]["not_applicable"] += 1
                continue
            
            # Parse close date
            try:
                closed_at = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                # Convert to naive datetime for comparison
                closed_at = closed_at.replace(tzinfo=None)
            except Exception as e:
                categorized["not_applicable"].append({
                    "item": item,
                    "issue": issue,
                    "project_number": project_number,
                    "project_name": project_data["name"],
                    "reason": f"Cannot parse close date: {e}"
                })
                project_stats[project_number]["not_applicable"] += 1
                continue
            
            time_since_closed = now - closed_at
            target_status = None
            
            # Determine target status based on time
            if time_since_closed <= self.ONE_WEEK:
                target_status = "Done"
            elif time_since_closed <= self.ONE_MONTH:
                target_status = "Archive"
            else:
                target_status = "History"
            
            # Check if already in correct status
            if current_status == target_status:
                categorized["already_correct"].append({
                    "item": item,
                    "issue": issue,
                    "project_number": project_number,
                    "project_name": project_data["name"],
                    "current_status": current_status,
                    "days_since_closed": time_since_closed.days
                })
                project_stats[project_number]["already_correct"] += 1
            else:
                # Add to appropriate category
                category_key = f"to_{target_status.lower()}"
                categorized[category_key].append({
                    "item": item,
                    "issue": issue,
                    "project_number": project_number,
                    "project_name": project_data["name"],
                    "current_status": current_status,
                    "target_status": target_status,
                    "days_since_closed": time_since_closed.days,
                    "closed_at": closed_at
                })
                project_stats[project_number]["to_move"] += 1
        
        # Print per-project statistics
        print("\n📋 各项目处理统计:")
        for project_number, stats in project_stats.items():
            project_name = self.projects_data[project_number]["name"]
            print(f"  项目 #{project_number} ({project_name}):")
            print(f"    处理: {stats['processed']}, 需移动: {stats['to_move']}, "
                  f"已正确: {stats['already_correct']}, 不适用: {stats['not_applicable']}")
        
        return categorized

    def print_categorization_summary(self, categorized):
        """Print summary of categorization results"""
        print("\n📊 归档分析结果:")
        print("=" * 60)
        
        total_to_move = len(categorized["to_done"]) + len(categorized["to_archive"]) + len(categorized["to_history"])
        
        print(f"📋 需要移动到 Done 列: {len(categorized['to_done'])} 个Issues")
        for item_data in categorized["to_done"]:
            issue = item_data["issue"]
            days = item_data["days_since_closed"]
            project_name = item_data["project_name"]
            project_number = item_data["project_number"]
            print(f"   #{issue['number']} (项目#{project_number}-{project_name}): {issue['title'][:40]}... ({days}天前完成)")
        
        print(f"\n📦 需要移动到 Archive 列: {len(categorized['to_archive'])} 个Issues")
        for item_data in categorized["to_archive"]:
            issue = item_data["issue"]
            days = item_data["days_since_closed"]
            project_name = item_data["project_name"]
            project_number = item_data["project_number"]
            print(f"   #{issue['number']} (项目#{project_number}-{project_name}): {issue['title'][:40]}... ({days}天前完成)")
        
        print(f"\n📚 需要移动到 History 列: {len(categorized['to_history'])} 个Issues")
        for item_data in categorized["to_history"]:
            issue = item_data["issue"]
            days = item_data["days_since_closed"]
            project_name = item_data["project_name"]
            project_number = item_data["project_number"]
            print(f"   #{issue['number']} (项目#{project_number}-{project_name}): {issue['title'][:40]}... ({days}天前完成)")
        
        print(f"\n✅ 已在正确状态: {len(categorized['already_correct'])} 个Issues")
        print(f"⏭️ 不适用: {len(categorized['not_applicable'])} 个Issues")
        
        print(f"\n📈 总计需要移动: {total_to_move} 个Issues")
        
        # Show breakdown by project
        if total_to_move > 0:
            print("\n📋 按项目分类的移动统计:")
            project_move_stats = {}
            
            for category in ["to_done", "to_archive", "to_history"]:
                for item_data in categorized[category]:
                    project_number = item_data["project_number"]
                    project_name = item_data["project_name"]
                    
                    if project_number not in project_move_stats:
                        project_move_stats[project_number] = {
                            "name": project_name,
                            "to_done": 0,
                            "to_archive": 0,
                            "to_history": 0
                        }
                    
                    project_move_stats[project_number][category] += 1
            
            for project_number, stats in project_move_stats.items():
                total_for_project = stats["to_done"] + stats["to_archive"] + stats["to_history"]
                print(f"  项目 #{project_number} ({stats['name']}): {total_for_project} 个")
                if stats["to_done"] > 0:
                    print(f"    → Done: {stats['to_done']} 个")
                if stats["to_archive"] > 0:
                    print(f"    → Archive: {stats['to_archive']} 个")
                if stats["to_history"] > 0:
                    print(f"    → History: {stats['to_history']} 个")

    def move_issue_to_status(self, item_data, target_status):
        """Move an issue to target status in the appropriate project"""
        item = item_data["item"]
        project_number = item_data["project_number"]
        project_data = item_data["project_data"]
        
        item_id = item["id"]
        project_id = project_data["id"]
        status_field_id = project_data["status_field_id"]
        status_options = project_data["status_options"]
        
        target_option_id = status_options.get(target_status)
        if not target_option_id:
            print(f"❌ 项目 #{project_number} 中未找到状态 '{target_status}' 的选项ID")
            return False
        
        mutation = f'''mutation {{
    updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}"
        itemId: "{item_id}"
        fieldId: "{status_field_id}"
        value: {{
            singleSelectOptionId: "{target_option_id}"
        }}
    }}) {{
        projectV2Item {{
            id
        }}
    }}
}}'''
        
        resp = requests.post("https://api.github.com/graphql",
                           headers=self.graphql_headers,
                           json={"query": mutation})
        
        if resp.status_code != 200:
            print(f"❌ 移动失败: {resp.status_code} - {resp.text}")
            return False
            
        data = resp.json()
        if "errors" in data:
            print(f"❌ 移动失败: {data['errors']}")
            return False
            
        return True

    def execute_moves(self, categorized):
        """Execute the status moves for categorized issues"""
        if self.preview_mode:
            print("\n🔍 预览模式：不会实际移动Issues")
            return
            
        print("\n⚡ 开始执行Issues状态移动...")
        
        total_success = 0
        total_failed = 0
        
        # Process each category
        for category, target_status in [
            ("to_done", "Done"),
            ("to_archive", "Archive"), 
            ("to_history", "History")
        ]:
            items = categorized[category]
            if not items:
                continue
                
            print(f"\n📝 移动 {len(items)} 个Issues到 {target_status} 列...")
            
            for item_data in items:
                issue = item_data["issue"]
                project_number = item_data["project_number"]
                project_name = item_data["project_name"]
                
                # Add project_data reference for move_issue_to_status
                item_data["project_data"] = self.projects_data[project_number]
                
                print(f"   移动 #{issue['number']} (项目#{project_number}-{project_name}): {issue['title'][:30]}...")
                
                if self.move_issue_to_status(item_data, target_status):
                    total_success += 1
                    print(f"     ✅ 成功移动到 {target_status}")
                else:
                    total_failed += 1
                    print(f"     ❌ 移动失败")
                
                # Rate limiting
                time.sleep(0.5)
        
        print(f"\n🎉 归档完成！")
        print(f"   ✅ 成功移动: {total_success} 个Issues")
        if total_failed > 0:
            print(f"   ❌ 移动失败: {total_failed} 个Issues")

    def run(self):
        """Main execution function"""
        print("🗂️ SAGE Issues 自动归档工具")
        print("=" * 40)
        
        if self.preview_mode:
            print("🔍 运行模式: 预览模式")
        else:
            print("⚡ 运行模式: 执行模式")
        
        print(f"📋 目标项目: {', '.join(f'#{num}({name})' for num, name in self.PROJECT_NAMES.items())}")
        
        # Get projects info and ensure History options exist
        if not self.get_projects_info():
            return False
        
        # Get all project items from all target projects
        project_items = self.get_completed_issues_from_projects()
        if not project_items:
            print("❌ 未找到任何项目项")
            return False
        
        # Analyze and categorize issues
        categorized = self.analyze_and_categorize_issues(project_items)
        
        # Print summary
        self.print_categorization_summary(categorized)
        
        # Execute moves if not in preview mode
        if not self.preview_mode:
            total_to_move = len(categorized["to_done"]) + len(categorized["to_archive"]) + len(categorized["to_history"])
            if total_to_move > 0:
                self.execute_moves(categorized)
            else:
                print("\n✅ 所有Issues已在正确状态，无需移动")
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Archive completed issues based on completion time")
    parser.add_argument("--preview", action="store_true", 
                       help="Preview mode: show what would be moved without making changes")
    
    args = parser.parse_args()
    
    archiver = CompletedIssuesArchiver(preview_mode=args.preview)
    success = archiver.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
