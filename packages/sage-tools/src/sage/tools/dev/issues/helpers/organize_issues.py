#!/usr/bin/env python3
"""
Issues整理脚本 - 根据关闭时间将issues移动到不同状态列

功能:
- 最近一周完成的issues -> "Done" 状态
- 超过一周但一个月以内的 -> "Archive" 状态
- 超过一个月的 -> "History" 状态

使用方法:
    python3 organize_issues.py --preview          # 预览整理计划
    python3 organize_issues.py --apply --confirm  # 执行整理

作者: SAGE Team
日期: 2025-09-21
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# 动态导入config模块
try:
    # 尝试相对导入（当作为模块运行时）
    from ..config import IssuesConfig
except ImportError:
    # 如果相对导入失败，使用绝对导入
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ..config import IssuesConfig


class IssuesOrganizer:
    """Issues整理器"""

    def __init__(self):
        # 使用IssuesConfig来获取配置和token
        self.config = IssuesConfig()
        self.project_root = self.config.project_root
        self.workspace_path = self.config.workspace_path
        self.data_dir = self.workspace_path / "data"

        # 获取GitHub token
        self.github_token = self.config.github_token

        if not self.github_token:
            raise Exception(
                "未找到GitHub Token，请设置GITHUB_TOKEN环境变量或创建.github_token文件"
            )

        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json",
        }

    def get_closed_issues(self):
        """获取所有已关闭的issues"""
        print("🔍 加载已关闭的issues...")

        closed_issues = []

        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在: {self.data_dir}")
            return []

        # 加载所有issue文件
        for issue_file in self.data_dir.glob("issue_*.json"):
            try:
                with open(issue_file, "r", encoding="utf-8") as f:
                    issue_data = json.load(f)

                # 检查是否已关闭
                if issue_data.get("metadata", {}).get("state") == "closed":
                    closed_issues.append(issue_data)

            except Exception as e:
                print(f"⚠️ 读取issue文件失败: {issue_file.name}: {e}")

        print(f"✅ 找到 {len(closed_issues)} 个已关闭的issues")
        return closed_issues

    def categorize_issues(self, issues):
        """根据关闭时间分类issues"""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)
        one_month_ago = now - timedelta(days=30)

        categories = {
            "Done": [],  # 最近一周
            "Archive": [],  # 一周到一个月
            "History": [],  # 超过一个月
        }

        for issue in issues:
            # 处理两种格式：从文件加载的格式和从API获取的格式
            if "metadata" in issue:
                # 从文件加载的格式
                closed_at_str = issue.get("metadata", {}).get("closed_at")
                if not closed_at_str:
                    continue
                try:
                    closed_at = datetime.fromisoformat(
                        closed_at_str.replace("Z", "+00:00")
                    )
                except Exception:
                    continue
                issue_info = {
                    "number": issue["metadata"]["number"],
                    "title": issue["metadata"]["title"],
                    "closed_at": closed_at,
                    "closed_by": issue["metadata"].get("closed_by"),
                }
            else:
                # 从API获取的格式
                closed_at = issue.get("closed_at")
                if not closed_at:
                    continue
                issue_info = {
                    "number": issue["number"],
                    "title": issue["title"],
                    "closed_at": closed_at,
                    "closed_by": None,
                }

            if closed_at >= one_week_ago:
                categories["Done"].append(issue_info)
            elif closed_at >= one_month_ago:
                categories["Archive"].append(issue_info)
            else:
                categories["History"].append(issue_info)

        return categories

    def get_project_info(self):
        """获取GitHub项目信息"""
        print("🔍 获取GitHub项目信息...")

        # 查询组织的所有项目 - 使用正确的union语法
        query = """
        {
          organization(login: "intellistream") {
            projectsV2(first: 20) {
              nodes {
                id
                number
                title
                fields(first: 20) {
                  nodes {
                    ... on ProjectV2FieldCommon {
                      id
                      name
                      dataType
                    }
                    ... on ProjectV2SingleSelectField {
                      id
                      name
                      dataType
                      options {
                        id
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": query},
        )

        if response.status_code != 200:
            print(f"❌ 获取项目信息失败: {response.status_code}")
            return None

        data = response.json()
        if "errors" in data:
            print(f"❌ GraphQL错误: {data['errors']}")
            return None

        projects = (
            data.get("data", {})
            .get("organization", {})
            .get("projectsV2", {})
            .get("nodes", [])
        )

        # 找到状态字段 - 优先选择SAGE项目
        sage_project = None
        for project in projects:
            if project["title"] == "SAGE":
                sage_project = project
                break

        if sage_project:
            projects = [sage_project]  # 只处理SAGE项目
        else:
            print("⚠️ 未找到SAGE项目，使用第一个有状态字段的项目")

        for project in projects:
            print(f"📋 项目: {project['title']} (#{project['number']})")

            # 显示所有字段
            print("  📋 字段列表:")
            for field in project.get("fields", {}).get("nodes", []):
                field_name = field.get("name", "Unknown")
                field_type = field.get("dataType", "Unknown")
                print(f"    • {field_name} ({field_type})")
                if field_type == "SINGLE_SELECT" and "options" in field:
                    options = [opt["name"] for opt in field["options"]]
                    print(f"      选项: {options}")

            status_field = None
            for field in project.get("fields", {}).get("nodes", []):
                if (
                    field.get("name") == "Status"
                    and field.get("dataType") == "SINGLE_SELECT"
                ):
                    status_field = field
                    break

            if status_field:
                print(
                    f"  ✅ 找到状态字段，选项: {[opt['name'] for opt in status_field.get('options', [])]}"
                )
                return {
                    "project_id": project["id"],
                    "status_field_id": status_field["id"],
                    "status_options": {
                        opt["name"]: opt["id"]
                        for opt in status_field.get("options", [])
                    },
                }

    def get_project_issues(self, project_info):
        """获取项目中的所有issues"""
        print("🔍 获取项目中的issues...")

        query = f"""
        {{
          node(id: "{project_info['project_id']}") {{
            ... on ProjectV2 {{
              items(first: 100) {{
                nodes {{
                  id
                  content {{
                    ... on Issue {{
                      number
                      title
                      closed
                      closedAt
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": query},
        )

        if response.status_code != 200:
            print(f"❌ 获取项目issues失败: {response.status_code}")
            return []

        data = response.json()
        if "errors" in data:
            print(f"❌ GraphQL错误: {data['errors']}")
            return []

        items = data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])
        project_issues = []

        for item in items:
            content = item.get("content")
            if content and content.get("closed"):
                project_issues.append(
                    {
                        "number": content["number"],
                        "title": content["title"],
                        "closed_at": datetime.fromisoformat(
                            content["closedAt"].replace("Z", "+00:00")
                        ),
                    }
                )

        print(f"✅ 找到 {len(project_issues)} 个项目中的已关闭issues")
        return project_issues

    def update_issue_status(self, issue_number, status_name, project_info):
        """更新issue在项目中的状态"""
        if status_name not in project_info["status_options"]:
            print(f"⚠️ 状态 '{status_name}' 不存在，跳过issue #{issue_number}")
            return False

        status_option_id = project_info["status_options"][status_name]

        # 首先检查issue是否已经在项目中
        check_query = f"""
        {{
          repository(owner: "intellistream", name: "SAGE") {{
            issue(number: {issue_number}) {{
              projectItems(first: 10) {{
                nodes {{
                  id
                  project {{
                    id
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": check_query},
        )

        if response.status_code != 200:
            print(f"❌ 检查issue #{issue_number} 项目状态失败: {response.status_code}")
            return False

        data = response.json()
        if "errors" in data:
            print(f"❌ GraphQL错误: {data['errors']}")
            return False

        issue_data = data.get("data", {}).get("repository", {}).get("issue", {})

        if not issue_data:
            print(f"⚠️ Issue #{issue_number} 不存在或无法访问")
            return False

        project_item = None
        for item in issue_data.get("projectItems", {}).get("nodes", []):
            if item.get("project", {}).get("id") == project_info["project_id"]:
                project_item = item
                break

        if not project_item:
            print(f"⚠️ Issue #{issue_number} 不在目标项目中，跳过")
            return False

        # 更新状态
        update_mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(
            input: {
              projectId: $projectId
              itemId: $itemId
              fieldId: $fieldId
              value: {
                singleSelectOptionId: $optionId
              }
            }
          ) {
            projectV2Item {
              id
            }
          }
        }
        """

        variables = {
            "projectId": project_info["project_id"],
            "itemId": project_item["id"],
            "fieldId": project_info["status_field_id"],
            "optionId": status_option_id,
        }

        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": update_mutation, "variables": variables},
        )

        if response.status_code == 200 and "errors" not in response.json():
            print(f"✅ Issue #{issue_number} 状态更新为 '{status_name}'")
            return True
        else:
            print(f"❌ 更新issue #{issue_number} 状态失败: {response.text}")
            return False

    def preview_organization(self):
        """预览整理计划"""
        print("📋 Issues整理预览")
        print("=" * 50)

        issues = self.get_closed_issues()
        categories = self.categorize_issues(issues)

        for category, items in categories.items():
            print(f"\n📁 {category} ({len(items)} 个issues):")
            for item in items[:5]:  # 只显示前5个
                print(f"  • #{item['number']} - {item['title'][:50]}...")
                print(f"    关闭时间: {item['closed_at'].strftime('%Y-%m-%d %H:%M')}")
            if len(items) > 5:
                print(f"  ... 还有 {len(items) - 5} 个issues")

        total = sum(len(items) for items in categories.values())
        print(f"\n📊 总计: {total} 个已关闭的issues待整理")

    def apply_organization(self, confirm=False):
        """执行整理"""
        if not confirm:
            print("❌ 需要 --confirm 参数来确认执行")
            return False

        print("🚀 开始执行Issues整理...")
        print("=" * 50)

        # 获取项目信息
        project_info = self.get_project_info()
        if not project_info:
            print("❌ 无法获取项目信息，退出")
            return False

        # 获取项目中的issues并分类
        project_issues = self.get_project_issues(project_info)
        if not project_issues:
            print("⚠️ 项目中没有已关闭的issues")
            return False

        categories = self.categorize_issues(project_issues)

        total_processed = 0
        total_success = 0

        for category, items in categories.items():
            print(f"\n📁 处理 {category} 分类 ({len(items)} 个issues)...")

            for item in items:
                success = self.update_issue_status(
                    item["number"], category, project_info
                )
                total_processed += 1

                if success:
                    total_success += 1

                # 添加延迟避免API限制
                import time

                time.sleep(0.5)

        print("\n📊 整理完成!")
        print(f"  • 处理总数: {total_processed}")
        print(f"  • 成功更新: {total_success}")
        print(f"  • 更新失败: {total_processed - total_success}")

        return total_success > 0


def main():
    parser = argparse.ArgumentParser(description="Issues整理工具")
    parser.add_argument("--preview", action="store_true", help="预览整理计划")
    parser.add_argument("--apply", action="store_true", help="执行整理")
    parser.add_argument(
        "--confirm", action="store_true", help="确认执行（与--apply一起使用）"
    )

    args = parser.parse_args()

    if not args.preview and not args.apply:
        parser.print_help()
        return

    try:
        organizer = IssuesOrganizer()

        if args.preview:
            organizer.preview_organization()
        elif args.apply:
            organizer.apply_organization(confirm=args.confirm)

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
