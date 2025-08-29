#!/usr/bin/env python3
"""
Copilot Issues格式化器 - 按团队分组整理open状态的issues
生成格式化文档供Copilot分析，去掉硬编码规则
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

class CopilotIssueFormatter:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.workspace_dir = self.project_root / "issues_workspace"
        self.output_dir = self.project_root / "output"
        self.meta_data_dir = self.project_root / "meta-data"
        
        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        
        # 加载团队配置
        self.teams = self._load_team_config()
        
    def _load_team_config(self):
        """加载团队配置信息"""
        try:
            sys.path.insert(0, str(self.meta_data_dir))
            import team_config
            return team_config.TEAMS
        except ImportError:
            print("⚠️ 未找到团队配置文件，请先运行团队成员获取脚本")
            return {}
    
    def load_open_issues(self, time_filter=None):
        """加载所有open状态的issues，支持时间过滤
        
        Args:
            time_filter (str): 时间过滤选项 - 'week', 'month', 'all'
        """
        issues_dir = self.workspace_dir / "issues"
        if not issues_dir.exists():
            print("❌ Issues目录不存在，请先下载issues")
            return []
        
        # 计算时间过滤的起始日期
        cutoff_date = None
        if time_filter == 'week':
            cutoff_date = datetime.now() - timedelta(days=7)
            print(f"📅 加载近一周的open issues (自 {cutoff_date.strftime('%Y-%m-%d')} 起)")
        elif time_filter == 'month':
            cutoff_date = datetime.now() - timedelta(days=30)
            print(f"📅 加载近一个月的open issues (自 {cutoff_date.strftime('%Y-%m-%d')} 起)")
        else:
            print(f"📅 加载全部open issues")
        
        open_issues = []
        total_open = 0
        filtered_count = 0
        
        for md_file in issues_dir.glob("open_*.md"):
            total_open += 1
            issue_data = self._parse_issue_file(md_file)
            if issue_data:
                # 应用时间过滤
                if cutoff_date and self._should_filter_by_date(issue_data, cutoff_date):
                    filtered_count += 1
                    continue
                open_issues.append(issue_data)
        
        if cutoff_date:
            print(f"📊 时间过滤结果: 总共{total_open}个open issues，过滤掉{filtered_count}个，加载了{len(open_issues)}个")
        else:
            print(f"📊 加载了 {len(open_issues)} 个open状态的issues")
        
        return open_issues
    
    def _should_filter_by_date(self, issue_data, cutoff_date):
        """判断issue是否应该被时间过滤掉"""
        created_at = issue_data.get('created_at', '')
        if not created_at:
            return False  # 没有创建时间的不过滤
        
        try:
            # 尝试多种日期格式
            for date_format in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    issue_date = datetime.strptime(created_at, date_format)
                    return issue_date < cutoff_date
                except ValueError:
                    continue
            
            # 如果所有格式都不匹配，不过滤
            print(f"⚠️ 无法解析日期格式: {created_at}")
            return False
            
        except Exception as e:
            print(f"⚠️ 处理日期时出错: {e}")
            return False
    
    def _parse_issue_file(self, md_file):
        """解析issue markdown文件"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取基本信息
            lines = content.split('\n')
            issue_data = {
                'filename': md_file.name,
                'title': '',
                'number': 0,
                'assignee': None,
                'labels': [],
                'created_at': '',
                'author': '',
                'body': '',
                'url': ''
            }
            
            # 从文件名提取issue号码
            filename = md_file.name
            if filename.startswith('open_') or filename.startswith('closed_'):
                try:
                    # 格式: open_136_[Feature]_...
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        issue_data['number'] = int(parts[1])
                except:
                    pass
            
            # 解析markdown内容
            current_section = None
            body_lines = []
            collecting_body = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 提取标题（第一行的 #）
                if line.startswith('# ') and not issue_data['title']:
                    issue_data['title'] = line[2:].strip()
                    continue
                
                # 解析元数据字段
                if line.startswith('**Issue #**:'):
                    try:
                        issue_data['number'] = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('**创建时间**:') or line.startswith('**创建者**:'):
                    if '创建时间' in line:
                        issue_data['created_at'] = line.split(':', 1)[1].strip()
                    elif '创建者' in line:
                        issue_data['author'] = line.split(':', 1)[1].strip()
                elif line.startswith('**状态**:'):
                    # 已经从文件名获取状态
                    pass
                elif line.startswith('**更新时间**:'):
                    # 可以忽略更新时间
                    pass
                
                # 处理分配部分
                elif line == '## 分配给':
                    current_section = 'assignee'
                    continue
                elif current_section == 'assignee' and line and not line.startswith('#'):
                    if line != '未分配' and line != 'null':
                        issue_data['assignee'] = line
                    current_section = None
                    continue
                
                # 处理标签部分
                elif line == '## 标签':
                    current_section = 'labels'
                    continue
                elif current_section == 'labels' and line and not line.startswith('#'):
                    if line.strip():
                        # 标签可能是逗号分隔的
                        labels = [l.strip() for l in line.split(',') if l.strip()]
                        issue_data['labels'].extend(labels)
                    else:
                        current_section = None
                
                # 处理描述部分
                elif line == '## 描述':
                    current_section = 'description'
                    collecting_body = True
                    continue
                elif collecting_body and not line.startswith('#'):
                    body_lines.append(lines[i])  # 保持原始格式包括空行
            
            # 设置body内容
            if body_lines:
                issue_data['body'] = '\n'.join(body_lines).strip()
            
            return issue_data
            
        except Exception as e:
            print(f"⚠️ 解析文件 {md_file.name} 失败: {e}")
            return None
    
    def group_issues_by_team(self, issues):
        """按团队分组issues"""
        team_issues = defaultdict(list)
        unassigned_issues = []
        external_issues = []
        
        # 创建用户名到团队的映射
        user_to_team = {}
        for team_name, team_data in self.teams.items():
            for member in team_data.get('members', []):
                username = member.get('username')
                if username:
                    user_to_team[username] = team_name
        
        for issue in issues:
            assignee = issue.get('assignee')
            author = issue.get('author')
            
            # 优先根据assignee分组
            if assignee and assignee in user_to_team:
                team_issues[user_to_team[assignee]].append(issue)
            # 其次根据author分组
            elif author and author in user_to_team:
                team_issues[user_to_team[author]].append(issue)
            # 检查是否是外部贡献者
            elif assignee or author:
                external_issues.append(issue)
            # 完全未分配
            else:
                unassigned_issues.append(issue)
        
        return dict(team_issues), unassigned_issues, external_issues
    
    def generate_team_analysis_document(self, team_name, team_issues, time_filter=None):
        """为单个团队生成分析文档"""
        if not team_issues:
            return ""
        
        team_data = self.teams.get(team_name, {})
        team_display_name = team_data.get('name', team_name)
        team_description = team_data.get('description', '')
        
        # 时间范围描述
        time_desc = {
            'week': '近一周',
            'month': '近一个月',
            None: '全部'
        }.get(time_filter, '全部')
        
        doc = f"""# {team_display_name} - Open Issues 分析 ({time_desc})

## 团队信息
- **团队名称**: {team_display_name}
- **团队描述**: {team_description}
- **成员数量**: {len(team_data.get('members', []))}
- **时间范围**: {time_desc}
- **待处理Issues**: {len(team_issues)}

## 团队成员
"""
        
        # 列出团队成员
        for member in team_data.get('members', []):
            username = member.get('username', 'Unknown')
            # 统计该成员分配的issues
            member_issues = [issue for issue in team_issues if issue.get('assignee') == username]
            doc += f"- **{username}**: {len(member_issues)} 个分配的issues\n"
        
        doc += f"""
## Open Issues 详情 ({len(team_issues)} 个)

"""
        
        # 按优先级和类型排序
        sorted_issues = self._sort_issues_by_priority(team_issues)
        
        for i, issue in enumerate(sorted_issues, 1):
            title = issue.get('title', 'No Title')
            number = issue.get('number', 'N/A')
            assignee = issue.get('assignee', '未分配')
            author = issue.get('author', 'Unknown')
            labels = issue.get('labels', [])
            created_at = issue.get('created_at', '')
            url = issue.get('url', '')
            body = issue.get('body', '')
            
            # 截取body的前300字符
            body_preview = body[:300] + "..." if len(body) > 300 else body
            
            doc += f"""### {i}. Issue #{number}: {title}

**基本信息:**
- **URL**: {url}
- **分配给**: {assignee}
- **创建者**: {author}
- **创建时间**: {created_at}
- **标签**: {', '.join(labels) if labels else '无'}

**描述预览:**
```
{body_preview}
```

---

"""
        
        return doc
    
    def _sort_issues_by_priority(self, issues):
        """根据优先级和重要性排序issues"""
        def get_priority_score(issue):
            score = 0
            title = issue.get('title', '').lower()
            labels = [label.lower() for label in issue.get('labels', [])]
            
            # 高优先级关键词
            high_priority_keywords = ['critical', 'urgent', '紧急', '重要', 'crash', '崩溃', 'bug', 'error', '错误']
            if any(keyword in title for keyword in high_priority_keywords):
                score += 100
            
            # 标签优先级
            if any(label in ['bug', 'critical', 'high-priority'] for label in labels):
                score += 50
            
            # 是否已分配
            if issue.get('assignee'):
                score += 10
            
            return score
        
        return sorted(issues, key=get_priority_score, reverse=True)
    
    def generate_comprehensive_analysis_document(self, team_issues, unassigned_issues, external_issues, time_filter=None):
        """生成综合分析文档"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 时间范围描述
        time_desc = {
            'week': '近一周',
            'month': '近一个月',
            None: '全部'
        }.get(time_filter, '全部')
        
        doc = f"""# SAGE Project - Open Issues 综合分析 ({time_desc})

**生成时间**: {timestamp}
**时间范围**: {time_desc}
**分析目的**: 为Copilot提供结构化的issues数据，便于智能分析和建议

## 📊 总体概况

### 数据统计
- **时间范围**: {time_desc}
- **总计Open Issues**: {sum(len(issues) for issues in team_issues.values()) + len(unassigned_issues) + len(external_issues)}
- **团队分配Issues**: {sum(len(issues) for issues in team_issues.values())}
- **未分配Issues**: {len(unassigned_issues)}
- **外部贡献者Issues**: {len(external_issues)}

### 团队分布
"""
        
        for team_name, issues in team_issues.items():
            team_display_name = self.teams.get(team_name, {}).get('name', team_name)
            doc += f"- **{team_display_name}**: {len(issues)} 个issues\n"
        
        doc += """
## 🎯 分析重点

请Copilot重点关注以下方面：

1. **优先级评估**: 识别需要立即处理的高优先级issues
2. **资源分配**: 分析各团队的工作负载是否均衡
3. **问题分类**: 将issues按类型分类（Bug修复、功能增强、文档改进等）
4. **依赖关系**: 识别issues之间的潜在依赖和关联
5. **工作流程**: 建议改进项目管理和issue处理流程
6. **重复问题**: 发现可能重复或相似的issues
7. **标签优化**: 建议标签使用和分类的改进方案

## 📋 请Copilot分析的问题

1. 哪些issues应该优先处理？为什么？
2. 各团队的工作负载分布是否合理？
3. 是否存在重复或相似的issues？
4. 哪些issues可能存在依赖关系？
5. 当前的标签分类是否有效？如何优化？
6. 未分配的issues应该如何分配？
7. 是否有issues可以合并或拆分？
8. 项目管理流程有哪些可以改进的地方？

---

"""
        return doc
    
    def generate_formatted_documents(self, output_format='all', time_filter=None):
        """生成格式化文档
        
        Args:
            output_format (str): 输出格式选项
            time_filter (str): 时间过滤选项 - 'week', 'month', 'all'
        """
        print("📊 开始生成格式化issues文档...")
        
        # 加载open issues with时间过滤
        issues = self.load_open_issues(time_filter)
        if not issues:
            print("❌ 没有找到符合条件的open状态issues")
            return False
        
        # 按团队分组
        team_issues, unassigned_issues, external_issues = self.group_issues_by_team(issues)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 根据时间过滤添加文件名后缀
        time_suffix = ""
        if time_filter == 'week':
            time_suffix = "_week"
        elif time_filter == 'month':
            time_suffix = "_month"
        
        generated_files = []
        
        # 生成综合分析文档
        if output_format in ['all', 'comprehensive']:
            comprehensive_doc = self.generate_comprehensive_analysis_document(team_issues, unassigned_issues, external_issues, time_filter)
            comprehensive_file = self.output_dir / f"copilot_comprehensive_analysis{time_suffix}_{timestamp}.md"
            
            with open(comprehensive_file, 'w', encoding='utf-8') as f:
                f.write(comprehensive_doc)
            
            print(f"✅ 综合分析文档: {comprehensive_file}")
            generated_files.append(str(comprehensive_file))
        
        # 生成各团队详细文档
        if output_format in ['all', 'teams']:
            for team_name, issues in team_issues.items():
                if issues:  # 只为有issues的团队生成文档
                    team_doc = self.generate_team_analysis_document(team_name, issues, time_filter)
                    team_file = self.output_dir / f"copilot_team_{team_name}{time_suffix}_{timestamp}.md"
                    
                    with open(team_file, 'w', encoding='utf-8') as f:
                        f.write(team_doc)
                    
                    print(f"✅ {team_name} 团队文档: {team_file}")
                    generated_files.append(str(team_file))
        
        # 生成未分配issues文档
        if output_format in ['all', 'unassigned'] and (unassigned_issues or external_issues):
            unassigned_doc = self._generate_unassigned_document(unassigned_issues, external_issues, timestamp, time_filter)
            unassigned_file = self.output_dir / f"copilot_unassigned_issues{time_suffix}_{timestamp}.md"
            
            with open(unassigned_file, 'w', encoding='utf-8') as f:
                f.write(unassigned_doc)
            
            print(f"✅ 未分配issues文档: {unassigned_file}")
            generated_files.append(str(unassigned_file))
        
        # 生成使用指南
        self._generate_usage_guide(generated_files, timestamp, time_filter)
        
        time_desc = {
            'week': '近一周',
            'month': '近一个月',
            None: '全部'
        }.get(time_filter, '全部')
        
        print(f"\n🎉 文档生成完成！共生成 {len(generated_files)} 个文档 (时间范围: {time_desc})")
        print("\n💡 使用建议:")
        print("1. 先查看综合分析文档获得总体概况")
        print("2. 将文档内容复制到Copilot聊天窗口")
        print("3. 请Copilot分析并提供改进建议")
        print("4. 根据分析结果制定行动计划")
        
        return True
    
    def _generate_unassigned_document(self, unassigned_issues, external_issues, timestamp, time_filter=None):
        """生成未分配issues文档"""
        time_desc = {
            'week': '近一周',
            'month': '近一个月',
            None: '全部'
        }.get(time_filter, '全部')
        
        doc = f"""# 未分配和外部贡献者 Issues ({time_desc})

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**时间范围**: {time_desc}

## 📋 未分配Issues ({len(unassigned_issues)} 个)

这些issues没有明确的负责人，需要安排团队处理：

"""
        
        for i, issue in enumerate(unassigned_issues, 1):
            title = issue.get('title', 'No Title')
            number = issue.get('number', 'N/A')
            author = issue.get('author', 'Unknown')
            labels = issue.get('labels', [])
            url = issue.get('url', '')
            body = issue.get('body', '')[:200] + "..." if len(issue.get('body', '')) > 200 else issue.get('body', '')
            
            doc += f"""### {i}. Issue #{number}: {title}

- **URL**: {url}
- **创建者**: {author}
- **标签**: {', '.join(labels) if labels else '无'}
- **描述**: {body}

---

"""
        
        doc += f"""
## 🌍 外部贡献者Issues ({len(external_issues)} 个)

这些issues由非团队成员创建或分配：

"""
        
        for i, issue in enumerate(external_issues, 1):
            title = issue.get('title', 'No Title')
            number = issue.get('number', 'N/A')
            assignee = issue.get('assignee', '未分配')
            author = issue.get('author', 'Unknown')
            labels = issue.get('labels', [])
            url = issue.get('url', '')
            body = issue.get('body', '')[:200] + "..." if len(issue.get('body', '')) > 200 else issue.get('body', '')
            
            doc += f"""### {i}. Issue #{number}: {title}

- **URL**: {url}
- **分配给**: {assignee}
- **创建者**: {author}
- **标签**: {', '.join(labels) if labels else '无'}
- **描述**: {body}

---

"""
        
        return doc
    
    def _generate_usage_guide(self, generated_files, timestamp, time_filter=None):
        """生成使用指南"""
        time_desc = {
            'week': '近一周',
            'month': '近一个月',
            None: '全部'
        }.get(time_filter, '全部')
        
        time_suffix = ""
        if time_filter == 'week':
            time_suffix = "_week"
        elif time_filter == 'month':
            time_suffix = "_month"
        
        guide_content = f"""# Copilot Issues分析使用指南 ({time_desc})

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**时间范围**: {time_desc}

## 📁 生成的文档

"""
        
        for file_path in generated_files:
            file_name = Path(file_path).name
            doc_type = "📊 综合分析" if "comprehensive" in file_name else \
                      "👥 团队分析" if "team_" in file_name else \
                      "📋 未分配Issues" if "unassigned" in file_name else "📄 其他"
            
            guide_content += f"- **{doc_type}**: `{file_name}`\n"
        
        guide_content += f"""
## 🤖 如何使用Copilot分析

### 步骤1: 复制文档内容
选择一个或多个上述文档，复制其内容到剪贴板。

### 步骤2: 与Copilot对话
在VS Code中打开Copilot聊天，粘贴文档内容，然后提问：

#### 建议的分析问题：

**优先级和紧急性分析:**
```
请分析这些open issues，识别出需要立即处理的高优先级问题，并说明原因。
```

**工作负载和资源分配:**
```
请分析各团队的工作负载分布，是否存在不均衡的情况？哪些团队可能需要支援？
```

**问题分类和标签优化:**
```
请将这些issues按类型分类（Bug修复、功能增强、文档改进等），并建议标签优化方案。
```

**重复和相似性分析:**
```
请识别是否存在重复或相似的issues，哪些可以合并处理？
```

**依赖关系分析:**
```
请分析这些issues之间是否存在依赖关系，建议处理顺序。
```

**项目管理改进:**
```
基于这些issues的状态，请建议项目管理流程的改进方案。
```

### 步骤3: 深入分析
根据Copilot的初步分析，可以进一步提问：

- "请详细分析XX团队的issues，给出具体的处理建议"
- "这些Bug类issues中，哪些可能相关联？"
- "未分配的issues应该如何分配给合适的团队？"
- "请制定一个2周的issues处理计划"

### 步骤4: 生成行动计划
让Copilot帮助生成具体的行动计划：

```
基于以上分析，请生成一个具体的行动计划，包括：
1. 立即处理的高优先级issues
2. 各团队的任务分配建议
3. 时间安排和里程碑
4. 流程改进措施
```

## 💡 分析技巧

1. **分块分析**: 如果issues太多，可以先分析单个团队，再综合
2. **对比分析**: 比较不同团队的issues特点和处理方式
3. **趋势分析**: 请Copilot分析issues的创建趋势和类型分布
4. **优化建议**: 重点关注流程和效率的改进建议

## 🔄 后续更新

要更新分析数据：
1. 重新下载最新的issues
2. 运行此脚本生成新的分析文档
3. 与Copilot分析变化和趋势

---
*由SAGE Issues管理工具自动生成*
"""
        
        guide_file = self.output_dir / f"copilot_usage_guide{time_suffix}_{timestamp}.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"📖 使用指南: {guide_file}")

def main():
    parser = argparse.ArgumentParser(description="生成格式化的issues文档供Copilot分析")
    parser.add_argument("--format", choices=["all", "comprehensive", "teams", "unassigned"], 
                       default="all", help="生成文档类型")
    parser.add_argument("--team", help="只生成指定团队的文档")
    parser.add_argument("--time", choices=["all", "week", "month"], 
                       default="all", help="时间过滤选项: all(全部), week(近一周), month(近一个月)")
    
    args = parser.parse_args()
    
    formatter = CopilotIssueFormatter()
    
    # 处理时间过滤参数
    time_filter = None if args.time == "all" else args.time
    
    if args.team:
        # 单独生成指定团队的文档
        issues = formatter.load_open_issues(time_filter)
        team_issues, _, _ = formatter.group_issues_by_team(issues)
        
        if args.team in team_issues:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            time_suffix = f"_{args.time}" if args.time != "all" else ""
            
            team_doc = formatter.generate_team_analysis_document(args.team, team_issues[args.team], time_filter)
            team_file = formatter.output_dir / f"copilot_team_{args.team}{time_suffix}_{timestamp}.md"
            
            with open(team_file, 'w', encoding='utf-8') as f:
                f.write(team_doc)
            
            print(f"✅ {args.team} 团队文档: {team_file}")
        else:
            print(f"❌ 未找到团队 '{args.team}' 的issues")
    else:
        # 生成指定格式的文档
        success = formatter.generate_formatted_documents(args.format, time_filter)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()
