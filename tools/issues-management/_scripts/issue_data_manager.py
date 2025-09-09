#!/usr/bin/env python3
"""
SAGE Issues 数据管理器
实现单一数据源 + 视图分离的新架构
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

class IssueDataManager:
    """统一的Issue数据管理器"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        
        # 新架构目录
        self.data_dir = self.workspace_path / "data"
        self.views_dir = self.workspace_path / "views" 
        self.cache_dir = self.workspace_path / "cache"
        
        # 视图子目录
        self.markdown_dir = self.views_dir / "markdown"
        self.metadata_dir = self.views_dir / "metadata"
        self.summaries_dir = self.views_dir / "summaries"
        
        # 旧架构目录（用于迁移）
        self.old_issues_dir = self.workspace_path / "issues"
        self.old_metadata_dir = self.workspace_path / "metadata"
        
        # 创建目录结构
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for directory in [
            self.data_dir, self.views_dir, self.cache_dir,
            self.markdown_dir, self.metadata_dir, self.summaries_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save_issue(self, issue_data: Dict[str, Any], comments: List[Dict] = None) -> bool:
        """保存issue到单一数据源
        
        Args:
            issue_data: 从GitHub API获取的issue数据
            comments: issue的评论列表
            
        Returns:
            bool: 保存是否成功
        """
        try:
            issue_number = issue_data.get('number')
            if not issue_number:
                print(f"❌ Issue数据缺少编号")
                return False
            
            # 处理milestone信息
            milestone_info = None
            if issue_data.get('milestone'):
                milestone = issue_data['milestone']
                milestone_info = {
                    'number': milestone.get('number'),
                    'title': milestone.get('title'),
                    'description': milestone.get('description'),
                    'state': milestone.get('state'),
                    'due_on': milestone.get('due_on'),
                    'html_url': milestone.get('html_url'),
                    'created_at': milestone.get('created_at'),
                    'updated_at': milestone.get('updated_at')
                }
            
            # 处理reactions信息
            reactions_info = None
            if issue_data.get('reactions'):
                reactions = issue_data['reactions']
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
            
            # 处理项目信息（这里假设已经通过其他方式获取）
            projects_info = issue_data.get('projects', [])
            
            # 构建统一的数据结构
            unified_data = {
                'metadata': {
                    'number': issue_number,
                    'title': issue_data.get('title', ''),
                    'state': issue_data.get('state', 'open'),
                    'state_reason': issue_data.get('state_reason'),
                    'labels': [l.get('name') if isinstance(l, dict) else l 
                              for l in issue_data.get('labels', [])],
                    'assignees': [a.get('login') if isinstance(a, dict) else a 
                                 for a in issue_data.get('assignees', [])],
                    'assignee': issue_data.get('assignee', {}).get('login') if issue_data.get('assignee') else None,
                    'milestone': milestone_info,
                    'reactions': reactions_info,
                    'comments_count': issue_data.get('comments', 0),
                    'locked': issue_data.get('locked', False),
                    'active_lock_reason': issue_data.get('active_lock_reason'),
                    'created_at': issue_data.get('created_at'),
                    'updated_at': issue_data.get('updated_at'),
                    'closed_at': issue_data.get('closed_at'),
                    'closed_by': issue_data.get('closed_by', {}).get('login') if issue_data.get('closed_by') else None,
                    'html_url': issue_data.get('html_url'),
                    'url': issue_data.get('url'),
                    'comments_url': issue_data.get('comments_url'),
                    'events_url': issue_data.get('events_url'),
                    'labels_url': issue_data.get('labels_url'),
                    'repository_url': issue_data.get('repository_url'),
                    'timeline_url': issue_data.get('timeline_url'),
                    'node_id': issue_data.get('node_id'),
                    'id': issue_data.get('id'),
                    'user': issue_data.get('user', {}).get('login') if isinstance(issue_data.get('user'), dict) else issue_data.get('user'),
                    'user_info': {
                        'login': issue_data.get('user', {}).get('login'),
                        'id': issue_data.get('user', {}).get('id'),
                        'node_id': issue_data.get('user', {}).get('node_id'),
                        'avatar_url': issue_data.get('user', {}).get('avatar_url'),
                        'html_url': issue_data.get('user', {}).get('html_url'),
                        'type': issue_data.get('user', {}).get('type'),
                        'site_admin': issue_data.get('user', {}).get('site_admin')
                    } if isinstance(issue_data.get('user'), dict) else None,
                    'author_association': issue_data.get('author_association'),
                    'performed_via_github_app': issue_data.get('performed_via_github_app'),
                    'type': issue_data.get('type'),
                    'projects': projects_info,
                    # 新增：关系和依赖信息
                    'issue_dependencies_summary': issue_data.get('issue_dependencies_summary', {
                        'blocked_by': 0,
                        'total_blocked_by': 0,
                        'blocking': 0,
                        'total_blocking': 0
                    }),
                    'sub_issues_summary': issue_data.get('sub_issues_summary', {
                        'total': 0,
                        'completed': 0,
                        'percent_completed': 0
                    }),
                    # 新增：父子关系信息
                    'parent_issue_url': issue_data.get('parent_issue_url'),
                    # 新增：issue类型信息
                    'type': issue_data.get('type')
                },
                'content': {
                    'body': issue_data.get('body', ''),
                    'comments': comments or []
                },
                'tracking': {
                    'downloaded_at': datetime.now().isoformat(),
                    'last_synced': datetime.now().isoformat(),
                    'update_history': [
                        {
                            'timestamp': datetime.now().isoformat(),
                            'action': 'data_save',
                            'github_updated': issue_data.get('updated_at')
                        }
                    ]
                }
            }
            
            # 保存到数据文件
            data_file = self.data_dir / f"issue_{issue_number}.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Issue #{issue_number} 数据已保存")
            return True
            
        except Exception as e:
            print(f"❌ 保存Issue数据失败: {e}")
            return False
    
    def get_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """获取完整的issue数据
        
        Args:
            issue_number: Issue编号
            
        Returns:
            Dict: Issue的完整数据，如果不存在返回None
        """
        try:
            data_file = self.data_dir / f"issue_{issue_number}.json"
            if not data_file.exists():
                return None
            
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取Issue #{issue_number} 数据失败: {e}")
            return None
    
    def list_all_issues(self) -> List[int]:
        """获取所有issue编号列表"""
        issue_numbers = []
        for data_file in self.data_dir.glob("issue_*.json"):
            try:
                # 从文件名提取issue编号
                name = data_file.stem  # issue_123
                number = int(name.split('_')[1])
                issue_numbers.append(number)
            except (ValueError, IndexError):
                continue
        return sorted(issue_numbers)
    
    def generate_markdown_view(self, issue_number: int) -> bool:
        """生成markdown视图
        
        Args:
            issue_number: Issue编号
            
        Returns:
            bool: 生成是否成功
        """
        try:
            issue_data = self.get_issue(issue_number)
            if not issue_data:
                print(f"❌ Issue #{issue_number} 数据不存在")
                return False
            
            metadata = issue_data['metadata']
            content = issue_data['content']
            tracking = issue_data['tracking']
            
            # 生成文件名
            safe_title = self._sanitize_filename(metadata['title'])
            filename = f"{metadata['state']}_{issue_number}_{safe_title}.md"
            
            # 处理项目信息
            project_section = ""
            if metadata.get('projects'):
                project_section = "\n## Project归属\n"
                for proj in metadata['projects']:
                    project_section += f"- **{proj['team']}** (Project Board ID: {proj['number']}: {proj['title']})\n"
            else:
                project_section = "\n## Project归属\n未归属到任何Project\n"
            
            # 处理milestone信息
            milestone_section = ""
            if metadata.get('milestone'):
                milestone = metadata['milestone']
                milestone_section = f"""
## Milestone
**{milestone.get('title', 'N/A')}** ({milestone.get('state', 'unknown')})
- 描述: {milestone.get('description', '无描述')}
- 截止日期: {milestone.get('due_on', '未设定')}
- [查看详情]({milestone.get('html_url', '#')})
"""
            
            # 处理统计信息
            stats_section = ""
            comments_count = metadata.get('comments_count', 0)
            reactions = metadata.get('reactions', {})
            total_reactions = reactions.get('total_count', 0) if reactions else 0
            is_locked = metadata.get('locked', False)
            
            if comments_count > 0 or total_reactions > 0 or is_locked:
                stats_section = "\n## 统计信息\n"
                if comments_count > 0:
                    stats_section += f"- 评论数: {comments_count}\n"
                if total_reactions > 0:
                    stats_section += f"- 反应数: {total_reactions}\n"
                    if reactions:
                        reaction_details = []
                        for emoji, count in reactions.items():
                            if emoji != 'total_count' and count > 0:
                                reaction_details.append(f"{emoji}: {count}")
                        if reaction_details:
                            stats_section += f"  - 详情: {', '.join(reaction_details)}\n"
                if is_locked:
                    stats_section += "- 状态: 已锁定\n"
            
            # 处理分配信息
            assignees_text = "未分配"
            if metadata.get('assignees'):
                assignees_text = '\n'.join(metadata['assignees'])
            
            # 处理更新记录
            update_history_section = ""
            if tracking.get('update_history'):
                update_history_section = "\n## 更新记录\n\n"
                for record in tracking['update_history']:
                    timestamp = record.get('timestamp', '')
                    action = record.get('action', '')
                    github_updated = record.get('github_updated', '')
                    
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            time_str = timestamp
                        
                        update_history_section += f"- **{time_str}**: {action}\n"
                        if github_updated:
                            try:
                                dt = datetime.fromisoformat(github_updated.replace('Z', '+00:00'))
                                github_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                                update_history_section += f"  - GitHub最后更新: {github_time_str}\n"
                            except:
                                pass
                update_history_section += "\n"
            
            # 生成markdown内容
            markdown_content = f"""# {metadata['title']}

**Issue #**: {metadata['number']}
**状态**: {metadata['state']}
**创建时间**: {metadata['created_at']}
**更新时间**: {metadata['updated_at']}
**创建者**: {metadata['user']}
{project_section}{milestone_section}{stats_section}
## 标签
{', '.join(metadata.get('labels', []))}

## 分配给
{assignees_text}

## 描述

{content.get('body', '无描述')}
{update_history_section}
---
**GitHub链接**: {metadata['html_url']}
**下载时间**: {tracking.get('downloaded_at', '')}
"""
            
            # 保存markdown文件
            markdown_file = self.markdown_dir / filename
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成Issue #{issue_number} markdown视图失败: {e}")
            return False
    
    def generate_metadata_view(self, issue_number: int) -> bool:
        """生成元数据视图（向后兼容）
        
        Args:
            issue_number: Issue编号
            
        Returns:
            bool: 生成是否成功
        """
        try:
            issue_data = self.get_issue(issue_number)
            if not issue_data:
                return False
            
            metadata = issue_data['metadata']
            
            # 构建向后兼容的元数据格式
            compat_metadata = {
                'number': metadata['number'],
                'title': metadata['title'],
                'state': metadata['state'],
                'labels': metadata.get('labels', []),
                'assignees': metadata.get('assignees', []),
                'milestone': metadata.get('milestone'),
                'reactions': metadata.get('reactions'),
                'comments_count': metadata.get('comments_count', 0),
                'locked': metadata.get('locked', False),
                'created_at': metadata.get('created_at'),
                'updated_at': metadata.get('updated_at'),
                'closed_at': metadata.get('closed_at'),
                'html_url': metadata.get('html_url'),
                'user': metadata.get('user'),
                'projects': metadata.get('projects', [])
            }
            
            # 保存元数据文件
            metadata_file = self.metadata_dir / f"issue_{issue_number}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(compat_metadata, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成Issue #{issue_number} 元数据视图失败: {e}")
            return False
    
    def generate_all_views(self) -> Dict[str, int]:
        """生成所有视图
        
        Returns:
            Dict: 生成结果统计
        """
        issue_numbers = self.list_all_issues()
        
        results = {
            'total': len(issue_numbers),
            'markdown_success': 0,
            'metadata_success': 0,
            'failed': 0
        }
        
        print(f"🚀 开始生成 {results['total']} 个Issue的视图...")
        
        for issue_number in issue_numbers:
            try:
                markdown_ok = self.generate_markdown_view(issue_number)
                metadata_ok = self.generate_metadata_view(issue_number)
                
                if markdown_ok:
                    results['markdown_success'] += 1
                if metadata_ok:
                    results['metadata_success'] += 1
                if not (markdown_ok and metadata_ok):
                    results['failed'] += 1
                    
                if (results['markdown_success'] + results['failed']) % 10 == 0:
                    print(f"📊 已处理 {results['markdown_success'] + results['failed']}/{results['total']} 个Issue")
                    
            except Exception as e:
                print(f"❌ 处理Issue #{issue_number} 失败: {e}")
                results['failed'] += 1
        
        # 生成汇总视图
        self.generate_summary_views()
        
        return results
    
    def generate_summary_views(self):
        """生成汇总视图"""
        try:
            print("📊 生成汇总视图...")
            
            # 按团队汇总
            issues_by_team = {}
            # 按milestone汇总  
            issues_by_milestone = {}
            # 按状态汇总
            issues_by_state = {'open': 0, 'closed': 0}
            
            for issue_number in self.list_all_issues():
                issue_data = self.get_issue(issue_number)
                if not issue_data:
                    continue
                
                metadata = issue_data['metadata']
                
                # 按状态统计
                state = metadata.get('state', 'unknown')
                issues_by_state[state] = issues_by_state.get(state, 0) + 1
                
                # 按团队统计
                projects = metadata.get('projects', [])
                for project in projects:
                    team = project.get('team', 'unknown')
                    if team not in issues_by_team:
                        issues_by_team[team] = []
                    issues_by_team[team].append({
                        'number': metadata['number'],
                        'title': metadata['title'],
                        'state': metadata['state']
                    })
                
                # 按milestone统计
                milestone = metadata.get('milestone')
                if milestone:
                    milestone_title = milestone.get('title', 'unknown')
                    if milestone_title not in issues_by_milestone:
                        issues_by_milestone[milestone_title] = []
                    issues_by_milestone[milestone_title].append({
                        'number': metadata['number'],
                        'title': metadata['title'],
                        'state': metadata['state']
                    })
            
            # 保存汇总文件
            with open(self.summaries_dir / "issues_by_team.json", 'w', encoding='utf-8') as f:
                json.dump(issues_by_team, f, ensure_ascii=False, indent=2)
            
            with open(self.summaries_dir / "issues_by_milestone.json", 'w', encoding='utf-8') as f:
                json.dump(issues_by_milestone, f, ensure_ascii=False, indent=2)
            
            with open(self.summaries_dir / "issues_by_state.json", 'w', encoding='utf-8') as f:
                json.dump(issues_by_state, f, ensure_ascii=False, indent=2)
            
            print("✅ 汇总视图生成完成")
            
        except Exception as e:
            print(f"❌ 生成汇总视图失败: {e}")
    
    def migrate_from_old_format(self) -> Dict[str, int]:
        """从旧格式迁移数据
        
        Returns:
            Dict: 迁移结果统计
        """
        print("🔄 开始从旧格式迁移数据...")
        
        results = {
            'markdown_processed': 0,
            'metadata_processed': 0,
            'data_created': 0,
            'failed': 0
        }
        
        # 处理旧的markdown文件
        if self.old_issues_dir.exists():
            for md_file in self.old_issues_dir.glob("*.md"):
                try:
                    results['markdown_processed'] += 1
                    issue_data = self._parse_old_markdown_file(md_file)
                    if issue_data:
                        # 尝试加载对应的metadata文件
                        issue_number = issue_data['number']
                        metadata_file = self.old_metadata_dir / f"issue_{issue_number}_metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                old_metadata = json.load(f)
                            # 合并数据
                            issue_data.update(old_metadata)
                            results['metadata_processed'] += 1
                        
                        # 保存到新格式
                        if self.save_issue(issue_data):
                            results['data_created'] += 1
                        
                except Exception as e:
                    print(f"❌ 迁移文件 {md_file} 失败: {e}")
                    results['failed'] += 1
        
        print(f"📊 迁移完成: 处理了 {results['markdown_processed']} 个markdown文件")
        print(f"📊 创建了 {results['data_created']} 个数据文件")
        
        return results
    
    def _parse_old_markdown_file(self, md_file: Path) -> Optional[Dict]:
        """解析旧格式的markdown文件"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            issue_data = {}
            
            # 从文件名提取信息
            filename = md_file.name
            if filename.startswith(('open_', 'closed_')):
                parts = filename.split('_')
                if len(parts) >= 2:
                    try:
                        issue_data['number'] = int(parts[1])
                        issue_data['state'] = parts[0]
                    except ValueError:
                        pass
            
            # 解析内容
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    issue_data['title'] = line[2:].strip()
                elif line.startswith('**Issue #**:'):
                    try:
                        issue_data['number'] = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('**状态**:'):
                    issue_data['state'] = line.split(':')[1].strip()
                elif line.startswith('**创建时间**:'):
                    issue_data['created_at'] = line.split(':', 1)[1].strip()
                elif line.startswith('**更新时间**:'):
                    issue_data['updated_at'] = line.split(':', 1)[1].strip()
                elif line.startswith('**创建者**:'):
                    issue_data['user'] = line.split(':')[1].strip()
                elif line.startswith('**GitHub链接**:'):
                    issue_data['html_url'] = line.split(':', 1)[1].strip()
            
            # 提取body内容
            body_start = content.find('## 描述')
            if body_start != -1:
                body_content = content[body_start + len('## 描述'):content.find('## 更新记录') if '## 更新记录' in content else content.find('---')]
                issue_data['body'] = body_content.strip()
            
            return issue_data
            
        except Exception as e:
            print(f"❌ 解析文件 {md_file} 失败: {e}")
            return None
    
    def _sanitize_filename(self, text: str) -> str:
        """清理文件名，移除不合法字符"""
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'\s+', '_', text)
        return text[:50]
    
    def create_backward_compatibility_links(self):
        """创建向后兼容的符号链接"""
        try:
            # 创建指向markdown视图的符号链接
            issues_link = self.workspace_path / "issues"
            if not issues_link.exists():
                issues_link.symlink_to(self.markdown_dir, target_is_directory=True)
                print("✅ 创建issues目录的向后兼容链接")
            
            # 创建指向metadata视图的符号链接  
            metadata_link = self.workspace_path / "metadata"
            if not metadata_link.exists():
                metadata_link.symlink_to(self.metadata_dir, target_is_directory=True)
                print("✅ 创建metadata目录的向后兼容链接")
                
        except Exception as e:
            print(f"⚠️ 创建向后兼容链接失败: {e}")


def main():
    """测试新架构"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Issue数据管理器")
    parser.add_argument("--workspace", default="/home/shuhao/SAGE/output/issues-workspace", 
                       help="工作目录路径")
    parser.add_argument("--migrate", action="store_true", 
                       help="从旧格式迁移数据")
    parser.add_argument("--generate-views", action="store_true",
                       help="生成所有视图")
    parser.add_argument("--create-links", action="store_true",
                       help="创建向后兼容链接")
    
    args = parser.parse_args()
    
    manager = IssueDataManager(args.workspace)
    
    if args.migrate:
        results = manager.migrate_from_old_format()
        print(f"📊 迁移结果: {results}")
    
    if args.generate_views:
        results = manager.generate_all_views()
        print(f"📊 视图生成结果: {results}")
    
    if args.create_links:
        manager.create_backward_compatibility_links()


if __name__ == "__main__":
    main()
