#!/usr/bin/env python3
"""
SAGE Issues下载工具
根据issues_manager.sh的调用需求重新设计
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import re

# 导入配置
from config import config, github_client

class IssuesDownloader:
    """Issues下载器"""
    
    def __init__(self):
        self.config = config
        self.github = github_client
        self.workspace = self.config.workspace_path
        
        # 创建输出目录结构
        self.issues_dir = self.workspace / "issues"
        self.metadata_dir = self.workspace / "metadata"

        for d in (self.issues_dir, self.metadata_dir):
            d.mkdir(parents=True, exist_ok=True)
        
        # 加载project映射信息
        self.project_mapping = self.load_project_mapping()
        # 添加issue到project的映射缓存
        self.issue_project_cache = {}
        # 加载团队配置
        self.team_config = self.load_team_config()
    
    def load_team_config(self):
        """加载团队配置"""
        try:
            config_path = self.config.metadata_path / "team_config.py"
            if config_path.exists():
                team_config = {}
                exec(open(config_path).read(), team_config)
                return team_config.get('TEAMS', {})
            else:
                print("⚠️ 团队配置文件不存在，将不进行自动分配")
                return {}
        except Exception as e:
            print(f"⚠️ 加载团队配置失败: {e}")
            return {}
    
    def load_project_mapping(self):
        """加载project映射信息"""
        try:
            boards_file = self.config.metadata_path / "boards_metadata.json"
            if boards_file.exists():
                with open(boards_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 从boards_metadata.json读取实际的team_to_project映射
                    team_to_project = data.get('team_to_project', {})
                    # 反转映射：project_number -> team_name
                    return {int(project_num): team_name for team_name, project_num in team_to_project.items()}
            else:
                # 如果文件不存在，返回默认映射
                return {
                    6: 'intellistream',  # IntelliStream总体项目
                    12: 'sage-kernel',
                    13: 'sage-middleware', 
                    14: 'sage-apps'
                }
        except Exception as e:
            print(f"⚠️ 加载project映射失败: {e}")
            # 返回默认映射作为备选
            return {
                6: 'intellistream',  # IntelliStream总体项目
                12: 'sage-kernel',
                13: 'sage-middleware', 
                14: 'sage-apps'
            }
    
    def bulk_get_project_info(self, issue_numbers: list):
        """批量获取多个issues的project归属信息，提高性能"""
        if not issue_numbers:
            return
            
        print(f"📊 批量获取 {len(issue_numbers)} 个issues的项目信息...")
        
        try:
            # 首先获取所有项目基本信息
            projects_query = """
            {
              organization(login: "intellistream") {
                projectsV2(first: 20) {
                  nodes {
                    number
                    title
                  }
                }
              }
            }
            """
            
            response = self.github.session.post(
                "https://api.github.com/graphql",
                json={"query": projects_query},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"GraphQL API错误: {response.status_code}")
                return
                
            data = response.json()
            
            if 'errors' in data:
                print(f"GraphQL查询错误: {data['errors']}")
                return
                
            projects = data.get('data', {}).get('organization', {}).get('projectsV2', {}).get('nodes', [])
            if not projects:
                print("未找到projects数据")
                return
            
            # 构建issue到project的映射
            found_count = 0
            
            # 对每个项目，分页获取所有items
            for project in projects:
                project_num = project['number']
                project_title = project['title']
                team_name = self.project_mapping.get(project_num, f"unknown-{project_num}")
                
                # 分页获取项目中的所有items
                has_next_page = True
                after_cursor = None
                
                while has_next_page:
                    # 构建分页查询，动态获取直到没有更多数据
                    items_query = f"""
                    {{
                      organization(login: "intellistream") {{
                        projectV2(number: {project_num}) {{
                          items(first: 100{f', after: "{after_cursor}"' if after_cursor else ''}) {{
                            pageInfo {{
                              hasNextPage
                              endCursor
                            }}
                            nodes {{
                              content {{
                                ... on Issue {{
                                  number
                                  repository {{
                                    name
                                  }}
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                    """
                    
                    items_response = self.github.session.post(
                        "https://api.github.com/graphql",
                        json={"query": items_query},
                        timeout=30
                    )
                    
                    if items_response.status_code != 200:
                        print(f"获取项目 {project_num} items失败: {items_response.status_code}")
                        break
                    
                    items_data = items_response.json()
                    
                    if 'errors' in items_data:
                        print(f"获取项目 {project_num} items错误: {items_data['errors']}")
                        break
                    
                    project_data = items_data.get('data', {}).get('organization', {}).get('projectV2', {})
                    if not project_data:
                        break
                        
                    items_info = project_data.get('items', {})
                    items = items_info.get('nodes', [])
                    page_info = items_info.get('pageInfo', {})
                    
                    # 处理当前页的items
                    for item in items:
                        content = item.get('content')
                        if not content:
                            continue
                            
                        issue_number = content.get('number')
                        if (issue_number in issue_numbers and
                            content.get('repository', {}).get('name') == 'SAGE'):
                            
                            if issue_number not in self.issue_project_cache:
                                self.issue_project_cache[issue_number] = []
                            
                            self.issue_project_cache[issue_number].append({
                                'number': project_num,
                                'title': project_title,
                                'team': team_name
                            })
                            found_count += 1
                    
                    # 检查是否有下一页
                    has_next_page = page_info.get('hasNextPage', False)
                    after_cursor = page_info.get('endCursor')
            
            print(f"✅ 成功获取 {found_count} 个issues的项目信息")
                        
        except Exception as e:
            print(f"⚠️ 批量获取项目信息失败: {e}")
            import traceback
            traceback.print_exc()
    
    def get_issue_project_info(self, issue_number: int):
        """获取issue的project归属信息（优先从缓存获取）"""
        # 首先检查缓存
        if issue_number in self.issue_project_cache:
            return self.issue_project_cache[issue_number]
        
        # 如果缓存中没有，返回空列表（避免单独的API请求）
        return []
    
    def sanitize_filename(self, text: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法的文件名字符
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'\s+', '_', text)
        return text[:50]  # 限制长度
    
    def clean_issue_body(self, body: str) -> str:
        """清理issue body，移除重复的元数据"""
        if not body:
            return '无描述'
            
        lines = body.split('\n')
        cleaned_lines = []
        skip_metadata = False
        
        for line in lines:
            # 如果遇到标题行，可能开始了重复的元数据
            if line.startswith('# ') and ('Issue #' in body[body.find(line):body.find(line)+200] or 
                                       '**状态**' in body[body.find(line):body.find(line)+200]):
                skip_metadata = True
                continue
            
            # 如果遇到了明确的描述开始标记，停止跳过
            if line.strip() == '## 描述' and skip_metadata:
                skip_metadata = False
                continue
                
            # 如果遇到了原始内容的开始（通常是 ## 开头但不是我们的元数据字段）
            if (line.startswith('## ') and 
                not any(field in line for field in ['Project归属', '标签', '分配给', '描述']) and
                skip_metadata):
                skip_metadata = False
                cleaned_lines.append(line)
                continue
            
            if not skip_metadata:
                cleaned_lines.append(line)
        
        cleaned_body = '\n'.join(cleaned_lines).strip()
        return cleaned_body if cleaned_body else '无描述'
    
    def extract_update_history(self, filepath):
        """从现有文件中提取更新记录"""
        if not filepath.exists():
            return ""
        
        try:
            content = filepath.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # 查找 "## 更新记录" 部分
            update_history_start = -1
            for i, line in enumerate(lines):
                if line.strip() == "## 更新记录":
                    update_history_start = i
                    break
            
            if update_history_start == -1:
                return ""
            
            # 提取更新记录部分，直到遇到 "---" 或文件结束
            history_lines = []
            for i in range(update_history_start, len(lines)):
                line = lines[i]
                if line.strip() == "---":
                    break
                history_lines.append(line)
            
            return '\n'.join(history_lines)
        except Exception:
            return ""

    def generate_update_record(self, issue: dict, old_content: str = "") -> str:
        """生成新的更新记录"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否有变更
        changes = []
        
        if old_content:
            # 这里可以添加更详细的变更检测逻辑
            # 简单起见，我们记录下载时间和基本信息
            changes.append(f"- **{current_time}**: 内容同步更新")
        else:
            changes.append(f"- **{current_time}**: 初始下载")
        
        # 如果issue最近有更新，记录GitHub更新时间
        github_updated = issue.get('updated_at', '')
        if github_updated:
            try:
                from dateutil import parser
                updated_dt = parser.parse(github_updated)
                github_time = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
                changes.append(f"  - GitHub最后更新: {github_time}")
            except:
                pass
        
        return '\n'.join(changes)

    def _format_assignees(self, assignees):
        """格式化assignees字段为字符串"""
        if not assignees:
            return '未分配'
        
        # 处理assignees可能是字符串列表或字典列表的情况
        formatted_assignees = []
        for assignee in assignees:
            if isinstance(assignee, dict):
                # 如果是字典，取login字段
                formatted_assignees.append(assignee.get('login', str(assignee)))
            elif isinstance(assignee, str):
                # 如果已经是字符串，直接使用
                formatted_assignees.append(assignee)
            else:
                # 其他情况转为字符串
                formatted_assignees.append(str(assignee))
        
        return '\n'.join(formatted_assignees)

    def format_issue_content(self, issue: dict, project_info: list = None, existing_filepath = None) -> str:
        """格式化Issue内容为Markdown"""
        
        # 格式化project信息
        project_section = ""
        if project_info:
            project_section = "\n## Project归属\n"
            for proj in project_info:
                project_section += f"- **{proj['team']}** (Project Board ID: {proj['number']}: {proj['title']})\n"
        else:
            project_section = "\n## Project归属\n未归属到任何Project\n"
        
        # 清理body内容
        cleaned_body = self.clean_issue_body(issue.get('body', ''))
        
        # 提取现有的更新记录
        existing_history = ""
        old_content = ""
        if existing_filepath and existing_filepath.exists():
            existing_history = self.extract_update_history(existing_filepath)
            old_content = existing_filepath.read_text(encoding='utf-8')
        
        # 生成新的更新记录
        new_update_record = self.generate_update_record(issue, old_content)
        
        # 合并更新记录
        update_history_section = ""
        if existing_history:
            # 保留现有记录并添加新记录
            update_history_section = f"\n{existing_history}\n{new_update_record}\n"
        else:
            # 创建新的更新记录部分
            update_history_section = f"\n## 更新记录\n\n{new_update_record}\n"
        
        # 处理milestone信息
        milestone_section = ""
        if issue.get('milestone'):
            milestone = issue['milestone']
            milestone_section = f"""
## Milestone
**{milestone.get('title', 'N/A')}** ({milestone.get('state', 'unknown')})
- 描述: {milestone.get('description', '无描述')}
- 截止日期: {milestone.get('due_on', '未设定')}
- [查看详情]({milestone.get('html_url', '#')})
"""

        # 处理统计信息
        stats_section = ""
        comments_count = issue.get('comments', 0)
        reactions = issue.get('reactions', {})
        total_reactions = reactions.get('total_count', 0) if reactions else 0
        is_locked = issue.get('locked', False)
        
        if comments_count > 0 or total_reactions > 0 or is_locked:
            stats_section = "\n## 统计信息\n"
            if comments_count > 0:
                stats_section += f"- 评论数: {comments_count}\n"
            if total_reactions > 0:
                stats_section += f"- 反应数: {total_reactions}\n"
                if reactions:
                    reaction_details = []
                    for emoji, count in reactions.items():
                        if emoji != 'total_count' and emoji != 'url' and count > 0:
                            reaction_details.append(f"{emoji}: {count}")
                    if reaction_details:
                        stats_section += f"  - 详情: {', '.join(reaction_details)}\n"
            if is_locked:
                stats_section += "- 状态: 已锁定\n"

        content = f"""# {issue['title']}

**Issue #**: {issue['number']}
**状态**: {issue['state']}
**创建时间**: {issue['created_at']}
**更新时间**: {issue['updated_at']}
**创建者**: {issue['user']['login']}
{project_section}{milestone_section}{stats_section}
## 标签
{', '.join([label['name'] for label in issue.get('labels', [])])}

## 分配给
{self._format_assignees(issue.get('assignees', []))}

## 描述

{cleaned_body}
{update_history_section}
---
**GitHub链接**: {issue['html_url']}
**下载时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return content
    
    def auto_assign_project_and_assignee(self, issue: dict, project_info: list):
        """自动分配project和assignee（如果缺失）"""
        if not self.team_config:
            return issue, None  # 如果没有团队配置，直接返回原issue
        
        # 获取创建者信息
        creator = issue.get('user', {}).get('login')
        if not creator:
            return issue, None
        
        # 检查是否已有project分配
        has_project = project_info and len(project_info) > 0
        
        # 检查是否已有assignee
        has_assignee = (
            (issue.get('assignees') and len(issue.get('assignees', [])) > 0) or
            issue.get('assignee')
        )
        
        # 如果已有project和assignee，不需要自动分配
        if has_project and has_assignee:
            return issue, None
        
        # 确定创建者所属的团队
        creator_team = None
        for team_name, team_info in self.team_config.items():
            team_members = [member['username'] for member in team_info.get('members', [])]
            if creator in team_members:
                creator_team = team_name
                break
        
        if not creator_team:
            # 创建者不在任何已知团队中，默认分配到intellistream
            creator_team = 'intellistream'
        
        updated_project_info = project_info
        
        # 如果没有project分配，尝试自动分配
        if not has_project:
            # 根据团队名称确定project
            project_assignments = {
                'intellistream': {'number': 6, 'title': 'IntelliStream Project', 'team': 'intellistream'},
                'sage-kernel': {'number': 12, 'title': 'SAGE Kernel Development', 'team': 'sage-kernel'},
                'sage-middleware': {'number': 13, 'title': 'SAGE Middleware', 'team': 'sage-middleware'},
                'sage-apps': {'number': 14, 'title': 'SAGE Applications', 'team': 'sage-apps'}
            }
            
            if creator_team in project_assignments:
                updated_project_info = [project_assignments[creator_team]]
                print(f"🎯 Issue #{issue['number']} 自动分配到project: {creator_team} (基于创建者 {creator})")
        
        # 如果没有assignee，分配给创建者
        if not has_assignee:
            # 确保创建者在团队中
            if creator_team and creator_team in self.team_config:
                team_members = [member['username'] for member in self.team_config[creator_team].get('members', [])]
                if creator in team_members:
                    # 修改issue的assignee信息
                    issue['assignees'] = [{'login': creator}]
                    issue['assignee'] = {'login': creator}
                    print(f"👤 Issue #{issue['number']} 自动分配给创建者: {creator}")
        
        return issue, updated_project_info

    def save_issue(self, issue: dict):
        """保存单个Issue到文件"""
        # 获取project信息
        project_info = self.get_issue_project_info(issue['number'])
        
        # 自动分配project和assignee (如果缺失)
        issue, updated_project_info = self.auto_assign_project_and_assignee(issue, project_info)
        
        # 使用更新后的project信息
        if updated_project_info is not None:
            project_info = updated_project_info
        
        # 生成文件名
        safe_title = self.sanitize_filename(issue['title'])
        filename = f"{issue['state']}_{issue['number']}_{safe_title}.md"
        filepath = self.issues_dir / filename

        # 保存内容（传递现有文件路径以保留更新记录）
        content = self.format_issue_content(issue, project_info, filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存简化的元数据
        try:
            self.save_issue_metadata(issue, project_info)
        except Exception:
            pass

        return filepath

    def get_issue_comments(self, issue_number: int):
        """通过 GitHubClient 的 session 获取 issue 评论（简化实现）"""
        try:
            base = f"https://api.github.com/repos/{self.config.GITHUB_OWNER}/{self.config.GITHUB_REPO}"
            url = f"{base}/issues/{issue_number}/comments"
            resp = self.github.session.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️ 获取 Issue #{issue_number} 评论失败: {e}")
            return []

    def save_issue_metadata(self, issue: dict, project_info: list = None):
        """保存简化元数据到 metadata 目录"""
        # 处理milestone信息
        milestone_info = None
        if issue.get('milestone'):
            milestone_info = {
                'number': issue['milestone'].get('number'),
                'title': issue['milestone'].get('title'),
                'description': issue['milestone'].get('description'),
                'state': issue['milestone'].get('state'),
                'due_on': issue['milestone'].get('due_on'),
                'html_url': issue['milestone'].get('html_url')
            }
        
        # 处理reactions信息
        reactions_info = None
        if issue.get('reactions'):
            reactions = issue['reactions']
            reactions_info = {
                'total_count': reactions.get('total_count', 0),
                '+1': reactions.get('+1', 0),
                '-1': reactions.get('-1', 0),
                'laugh': reactions.get('laugh', 0),
                'hooray': reactions.get('hooray', 0),
                'confused': reactions.get('confused', 0),
                'heart': reactions.get('heart', 0),
                'rocket': reactions.get('rocket', 0),
                'eyes': reactions.get('eyes', 0)
            }
        
        data = {
            'number': issue.get('number'),
            'title': issue.get('title'),
            'state': issue.get('state'),
            'labels': [l.get('name') for l in issue.get('labels', [])],
            'assignees': [a.get('login') for a in issue.get('assignees', [])] if issue.get('assignees') else (
                [issue.get('assignee', {}).get('login')] if issue.get('assignee') else []),
            'milestone': milestone_info,
            'reactions': reactions_info,
            'comments_count': issue.get('comments', 0),
            'locked': issue.get('locked', False),
            'created_at': issue.get('created_at'),
            'updated_at': issue.get('updated_at'),
            'closed_at': issue.get('closed_at'),
            'html_url': issue.get('html_url'),
            'user': issue.get('user', {}).get('login'),
            'projects': project_info or []
        }
        fname = f"issue_{data['number']}_metadata.json"
        with open(self.metadata_dir / fname, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def download_issues(self, state="all") -> bool:
        """下载Issues
        
        Args:
            state: Issues状态 ("open", "closed", "all")
        
        Returns:
            bool: 下载是否成功
        """
        print(f"🚀 开始下载 {state} 状态的Issues...")
        
        try:
            # 获取Issues
            issues = self.github.get_issues(state=state)
            
            if not issues:
                print("📭 没有找到符合条件的Issues")
                return True
            
            print(f"📥 共找到 {len(issues)} 个Issues，开始下载...")
            
            # 批量获取所有issues的项目信息（优化性能）
            issue_numbers = [issue['number'] for issue in issues]
            self.bulk_get_project_info(issue_numbers)
            
            # 保存Issues
            saved_count = 0
            for issue in issues:
                try:
                    filepath = self.save_issue(issue)
                    saved_count += 1
                    if saved_count % 10 == 0:
                        print(f"✅ 已保存 {saved_count}/{len(issues)} 个Issues")
                except Exception as e:
                    print(f"❌ 保存Issue #{issue['number']} 失败: {e}")
            
            # 生成下载报告
            self.generate_download_report(issues, saved_count, state)
            
            print(f"🎉 下载完成！成功保存 {saved_count}/{len(issues)} 个Issues")
            print(f"📁 保存位置: {self.issues_dir}")
            
            return True
            
        except Exception as e:
            print(f"💥 下载失败: {e}")
            return False
    
    def generate_download_report(self, issues: list, saved_count: int, state: str):
        """生成下载报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.config.output_path / f"download_report_{state}_{timestamp}.md"
        
        # 统计信息
        total_issues = len(issues)
        open_count = len([i for i in issues if i['state'] == 'open'])
        closed_count = len([i for i in issues if i['state'] == 'closed'])
        
        # 标签统计
        label_stats = {}
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label['name']
                label_stats[label_name] = label_stats.get(label_name, 0) + 1
        
        # 生成报告内容
        report_content = f"""# Issues下载报告

**下载时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**请求状态**: {state}
**下载结果**: {saved_count}/{total_issues} 成功

## 统计信息

- 开放Issues: {open_count}
- 已关闭Issues: {closed_count}
- 总计: {total_issues}

## 标签分布

"""
        
        # 添加标签统计
        for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {label}: {count}\n"
        
        report_content += f"""
## 存储位置

Issues保存在: `{self.issues_dir}`
所有标签信息都包含在每个Issue的markdown文件中

## 文件命名规则

格式: `{{状态}}_{{编号}}_{{标题}}.md`
例如: `open_123_Fix_bug_in_parser.md`
"""
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 下载报告已保存: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="下载GitHub Issues")
    parser.add_argument("--state", 
                       choices=["open", "closed", "all"], 
                       default="all",
                       help="要下载的Issues状态 (default: all)")
    parser.add_argument("--verbose", "-v", 
                       action="store_true",
                       help="显示详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"🔧 配置信息:")
        print(f"   仓库: {config.GITHUB_OWNER}/{config.GITHUB_REPO}")
        print(f"   工作目录: {config.workspace_path}")
        print(f"   Token状态: {'✅' if config.github_token else '❌'}")
        print()
    
    # 执行下载
    downloader = IssuesDownloader()
    success = downloader.download_issues(state=args.state)
    
    if success:
        print("\n🎉 下载完成！")
        sys.exit(0)
    else:
        print("\n💥 下载失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
