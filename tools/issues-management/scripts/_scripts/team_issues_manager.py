#!/usr/bin/env python3
"""
基于团队成员信息的Issues管理增强功能
结合团队metadata进行智能issue分配和分类
"""

import os
import sys
import json
from pathlib import Path

# 添加metadata目录到Python路径
sys.path.append(str(Path(__file__).parent / "metadata"))

try:
    from team_config import TEAMS, get_all_usernames, get_team_usernames, get_user_team, is_team_member, get_team_stats
except ImportError:
    print("❌ 无法导入team_config模块，请先运行 get_team_members.py 生成团队配置")
    sys.exit(1)


class TeamBasedIssuesManager:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            sys.exit(1)
            
        self.repo = "intellistream/SAGE"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 加载团队配置
        self.teams = TEAMS
        self.all_usernames = get_all_usernames()
        
        print(f"✅ 已加载团队配置: {len(self.all_usernames)} 位成员, {len(self.teams)} 个团队")
        
    def analyze_issues_by_team(self, issues_file="downloaded_issues/github_issues.json"):
        """按团队分析issues分布"""
        issues_path = Path(issues_file)
        if not issues_path.exists():
            print(f"❌ Issues文件不存在: {issues_file}")
            return None
            
        with open(issues_path, 'r', encoding='utf-8') as f:
            issues = json.load(f)
            
        print(f"\\n📊 分析 {len(issues)} 个issues的团队分布...")
        
        team_stats = {
            "sage-apps": {"created": 0, "assigned": 0, "mentioned": 0, "issues": []},
            "sage-middleware": {"created": 0, "assigned": 0, "mentioned": 0, "issues": []},
            "sage-kernel": {"created": 0, "assigned": 0, "mentioned": 0, "issues": []},
            "external": {"created": 0, "assigned": 0, "mentioned": 0, "issues": []},
            "unassigned": {"count": 0, "issues": []}
        }
        
        for issue in issues:
            issue_num = issue["number"]
            creator = issue["user"]  # 直接取字符串值
            assignees = issue.get("assignees", [])  # 直接是用户名列表
            
            # 分析创建者
            creator_team = get_user_team(creator)
            if creator_team:
                team_stats[creator_team]["created"] += 1
                team_stats[creator_team]["issues"].append({
                    "number": issue_num,
                    "title": issue["title"],
                    "role": "creator",
                    "user": creator
                })
            else:
                team_stats["external"]["created"] += 1
                team_stats["external"]["issues"].append({
                    "number": issue_num,
                    "title": issue["title"], 
                    "role": "creator",
                    "user": creator
                })
                
            # 分析分配者
            if assignees:
                for assignee in assignees:
                    assignee_team = get_user_team(assignee)
                    if assignee_team:
                        team_stats[assignee_team]["assigned"] += 1
                        # 避免重复记录同一个issue
                        if not any(item["number"] == issue_num and item["role"] == "assignee" 
                                 for item in team_stats[assignee_team]["issues"]):
                            team_stats[assignee_team]["issues"].append({
                                "number": issue_num,
                                "title": issue["title"],
                                "role": "assignee", 
                                "user": assignee
                            })
                    else:
                        team_stats["external"]["assigned"] += 1
            else:
                # 未分配的issues
                team_stats["unassigned"]["count"] += 1
                team_stats["unassigned"]["issues"].append({
                    "number": issue_num,
                    "title": issue["title"],
                    "creator": creator
                })
                
        return team_stats
        
    def load_ai_team_assignments(self):
        """从AI分析结果中加载团队分配建议"""
        print("🔍 寻找AI团队分配分析结果...")
        
        # 查找最新的AI团队分配分析文件
        output_dir = Path("output")
        analysis_files = []
        
        # 团队分配分析
        team_files = list(output_dir.glob("team_assignment_analysis_*.md"))
        if team_files:
            latest_team = max(team_files, key=lambda x: x.stat().st_mtime)
            analysis_files.append(("团队分配", latest_team))
            
        # 综合管理分析（可能包含团队分配建议）
        management_files = list(output_dir.glob("comprehensive_management_*.md"))
        if management_files:
            latest_management = max(management_files, key=lambda x: x.stat().st_mtime)
            analysis_files.append(("综合管理", latest_management))
        
        if not analysis_files:
            print("⚠️ 未找到AI团队分配分析结果")
            print("💡 建议先运行: python3 4_ai_unified_manager.py team-assignment")
            return {}
            
        print(f"✅ 找到 {len(analysis_files)} 个AI分析文件:")
        for analysis_type, file_path in analysis_files:
            print(f"   📄 {analysis_type}: {file_path.name}")
            
        # 解析分析结果
        return self.parse_team_assignment_analysis(analysis_files)
        
    def parse_team_assignment_analysis(self, analysis_files):
        """解析AI团队分配分析结果"""
        print("\n📖 解析AI团队分配建议...")
        
        suggestions = {}
        
        for analysis_type, file_path in analysis_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # 解析团队分配建议
                import re
                
                # 匹配模式：Issue #xxx: 建议团队: xxx 和建议分配给: member1, member2
                assignment_patterns = [
                    # 匹配团队建议
                    r'Issue #(\d+)[：:]\s*建议团队[：:]\s*(sage-\w+)',
                    r'Issue #(\d+)[：:]\s*推荐团队[：:]\s*(sage-\w+)',
                    # 匹配具体成员分配
                    r'Issue #(\d+)[：:]\s*建议分配给[：:]\s*([^\\n]+)',
                    r'Issue #(\d+)[：:]\s*分配给[：:]\s*([^\\n]+)',
                    r'建议将\s*Issue #(\d+)\s*分配给[：:]\s*([^\\n]+)',
                ]
                
                for pattern in assignment_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        issue_num = int(match[0])
                        
                        # 解析团队建议
                        if 'sage-' in match[1]:
                            team_slug = match[1].lower()
                            
                            if team_slug in self.teams:
                                suggestions[issue_num] = {
                                    "suggested_team": team_slug,
                                    "team_name": self.teams[team_slug]["name"],
                                    "source": analysis_type,
                                    "suggested_assignees": get_team_usernames(team_slug)[:2],
                                    "all_team_members": get_team_usernames(team_slug),
                                    "reasoning": "基于AI分析的团队专长匹配"
                                }
                        else:
                            # 解析具体成员分配
                            assignees_str = match[1].strip()
                            # 解析用户名列表（可能是逗号分隔）
                            potential_assignees = [name.strip() for name in assignees_str.replace('，', ',').split(',')]
                            
                            # 验证用户名是否为团队成员
                            valid_assignees = []
                            suggested_team = None
                            
                            for assignee in potential_assignees:
                                assignee = assignee.strip()
                                if is_team_member(assignee):
                                    valid_assignees.append(assignee)
                                    if not suggested_team:
                                        suggested_team = get_user_team(assignee)
                            
                            if valid_assignees and suggested_team:
                                suggestions[issue_num] = {
                                    "suggested_team": suggested_team,
                                    "team_name": self.teams[suggested_team]["name"],
                                    "source": analysis_type,
                                    "suggested_assignees": valid_assignees,
                                    "all_team_members": get_team_usernames(suggested_team),
                                    "reasoning": "基于AI分析的具体成员分配"
                                }
                            
            except Exception as e:
                print(f"❌ 解析 {analysis_type} 文件失败: {e}")
                
        print(f"✅ 解析完成: 找到 {len(suggestions)} 个团队分配建议")
        return suggestions
        
    def generate_team_assignment_report(self):
        """生成团队分配报告（基于AI分析结果）"""
        print("\\n📋 生成基于AI分析的团队issue分配报告...")
        
        # 分析现有分布
        team_stats = self.analyze_issues_by_team()
        if not team_stats:
            return None
            
        # 加载AI分配建议（替代硬编码逻辑）
        ai_suggestions = self.load_ai_team_assignments()
        
        # 将AI建议转换为旧格式以兼容报告生成
        suggestions = []
        for issue_num, suggestion in ai_suggestions.items():
            suggestions.append({
                "issue_number": issue_num,
                "title": f"Issue #{issue_num}",  # 简化标题，实际可从issues文件获取
                "suggested_team": suggestion["suggested_team"],
                "team_name": suggestion["team_name"],
                "confidence_score": "AI分析",
                "suggested_assignees": suggestion["suggested_assignees"],
                "all_team_members": suggestion["all_team_members"],
                "reasoning": suggestion["reasoning"]
            })
        
        if not suggestions:
            print("⚠️ 没有AI团队分配建议")
            print("💡 建议运行: python3 4_ai_unified_manager.py team-assignment")
            
        # 生成报告
        report_content = f"""# SAGE项目团队Issues分配分析报告

**生成时间**: {self.get_current_time()}
**分析范围**: SAGE项目所有开放issues
**团队配置**: {len(self.teams)} 个团队, {len(self.all_usernames)} 位成员

## 📊 当前Issues团队分布

### 🏢 团队统计
"""
        
        for team_slug, team_info in self.teams.items():
            team_name = team_info["name"]
            stats = team_stats[team_slug]
            
            report_content += f"""
#### {team_name} ({team_slug})
- **团队成员**: {len(team_info['members'])} 人
- **创建的issues**: {stats['created']} 个
- **分配的issues**: {stats['assigned']} 个
- **参与的issues**: {len(stats['issues'])} 个
- **成员列表**: {', '.join([member['username'] for member in team_info['members']])}
"""
            
        # 外部贡献者统计
        external_stats = team_stats["external"]
        unassigned_stats = team_stats["unassigned"]
        
        report_content += f"""
#### 外部贡献者
- **创建的issues**: {external_stats['created']} 个
- **分配的issues**: {external_stats['assigned']} 个

#### 未分配Issues
- **未分配数量**: {unassigned_stats['count']} 个
"""

        # 分配建议（基于AI分析）
        if suggestions:
            report_content += f"""
## 🤖 AI智能分配建议

基于AI分析结果的团队分配建议：

"""
            for suggestion in suggestions[:10]:  # 显示前10个建议
                report_content += f"""### Issue #{suggestion['issue_number']}: {suggestion['title']}
- **AI建议团队**: {suggestion['team_name']} ({suggestion['suggested_team']})
- **建议分配给**: {', '.join(suggestion['suggested_assignees'])}
- **分析来源**: {suggestion['confidence_score']}
- **AI理由**: {suggestion['reasoning']}

"""
        else:
            report_content += f"""
## ⚠️ 缺少AI分析

当前没有AI团队分配建议。建议运行以下命令生成AI分析：

```bash
python3 4_ai_unified_manager.py team-assignment
```

AI将基于以下维度进行分析：
- Issues内容语义理解
- 团队历史贡献记录
- 技术栈匹配度
- 工作负载平衡
- 成员专长领域

"""
        
        # 团队专长领域
        report_content += """
## 🔧 团队专长领域

### SAGE Apps Team
- 前端开发、用户界面、可视化
- 应用集成、用户体验、演示程序
- Web技术、客户端开发

### SAGE Middleware Team  
- 服务架构、API设计、后端开发
- 微服务、中间件、系统集成
- 部署运维、安全认证、配置管理

### SAGE Kernel Team
- 核心引擎、算法优化、性能调优
- 分布式计算、并行处理、内存管理
- 任务调度、执行引擎、底层优化

## 📈 改进建议

1. **AI驱动分配**: 使用AI分析而非硬编码规则进行团队分配
2. **增加team标签**: 为每个team创建专用标签便于分类
3. **工作负载平衡**: 关注各团队的issue负载分布
4. **跨团队协作**: 对涉及多个组件的复杂issues建立协作机制
5. **持续学习**: 基于历史分配效果优化AI分析模型

## 🤖 AI分析流程

本系统采用AI驱动的团队分配策略：

1. **语义分析**: AI理解issues的技术内容和需求
2. **团队匹配**: 基于团队专长和历史贡献进行匹配
3. **负载均衡**: 考虑各团队当前工作负载
4. **专长评估**: 分析团队成员的技术专长领域
5. **协作需求**: 识别需要跨团队协作的复杂issues

使用命令 `python3 4_ai_unified_manager.py team-assignment` 生成AI分析结果。

---
*本报告由SAGE团队Issues管理系统生成，基于AI分析结果*
"""
        
        # 保存报告
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        report_path = output_dir / "team_assignment_analysis.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"✅ 团队分配分析报告已生成: {report_path}")
        
        # 输出摘要
        print(f"""
📊 分配摘要:
- SAGE Apps Team: {team_stats['sage-apps']['created']} 创建, {team_stats['sage-apps']['assigned']} 分配
- SAGE Middleware Team: {team_stats['sage-middleware']['created']} 创建, {team_stats['sage-middleware']['assigned']} 分配  
- SAGE Kernel Team: {team_stats['sage-kernel']['created']} 创建, {team_stats['sage-kernel']['assigned']} 分配
- 外部贡献者: {team_stats['external']['created']} 创建, {team_stats['external']['assigned']} 分配
- 未分配issues: {team_stats['unassigned']['count']} 个
- AI分配建议: {len(suggestions)} 个

💡 提示: 
  如需更多AI分配建议，请运行: python3 4_ai_unified_manager.py team-assignment
""")
        
        return {
            "team_stats": team_stats,
            "ai_suggestions": ai_suggestions,
            "suggestions": suggestions,
            "report_path": report_path
        }
        
    def create_team_labels(self):
        """为每个团队创建专用标签"""
        import requests
        import time
        
        print("\\n🏷️ 创建团队专用标签...")
        
        team_labels = {
            "team:apps": {
                "color": "0052cc",
                "description": "SAGE Apps Team - 应用层开发和集成"
            },
            "team:middleware": {
                "color": "5319e7", 
                "description": "SAGE Middleware Team - 中间件和服务层开发"
            },
            "team:kernel": {
                "color": "d93f0b",
                "description": "SAGE Kernel Team - 核心引擎和内核开发"
            }
        }
        
        for label_name, label_info in team_labels.items():
            url = f"https://api.github.com/repos/{self.repo}/labels/{label_name}"
            
            # 检查标签是否存在
            response = requests.get(url, headers=self.headers)
            
            data = {
                "name": label_name,
                "color": label_info["color"],
                "description": label_info["description"]
            }
            
            if response.status_code == 200:
                # 更新现有标签
                response = requests.patch(url, headers=self.headers, json=data)
                if response.status_code == 200:
                    print(f"  ✅ 更新团队标签: {label_name}")
                else:
                    print(f"  ❌ 更新失败: {label_name} - {response.text}")
            else:
                # 创建新标签
                create_url = f"https://api.github.com/repos/{self.repo}/labels"
                response = requests.post(create_url, headers=self.headers, json=data)
                if response.status_code == 201:
                    print(f"  ✅ 创建团队标签: {label_name}")
                else:
                    print(f"  ❌ 创建失败: {label_name} - {response.text}")
                    
            time.sleep(0.2)  # 避免API限制
            
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def apply_ai_assignments(self, dry_run=True):
        """应用AI分配建议到GitHub issues"""
        import requests
        import time
        
        print(f"🤖 开始应用AI团队分配建议{'（预览模式）' if dry_run else ''}...")
        
        # 加载AI建议
        ai_suggestions = self.load_ai_team_assignments()
        
        if not ai_suggestions:
            print("❌ 没有AI分配建议可应用")
            return
            
        print(f"📋 找到 {len(ai_suggestions)} 个AI分配建议")
        
        applied_count = 0
        error_count = 0
        
        for issue_num, suggestion in ai_suggestions.items():
            print(f"\n📝 处理 Issue #{issue_num}")
            print(f"   团队: {suggestion['team_name']}")
            print(f"   建议分配给: {', '.join(suggestion['suggested_assignees'])}")
            
            if dry_run:
                print(f"   🔍 预览: 将分配给 {', '.join(suggestion['suggested_assignees'])}")
                applied_count += 1
                continue
                
            # 检查issue是否存在且未关闭
            issue_url = f"https://api.github.com/repos/{self.repo}/issues/{issue_num}"
            issue_response = requests.get(issue_url, headers=self.headers)
            
            if issue_response.status_code != 200:
                print(f"   ❌ 无法获取Issue #{issue_num}: {issue_response.status_code}")
                error_count += 1
                continue
                
            issue_data = issue_response.json()
            if issue_data.get("state") == "closed":
                print(f"   ⏭️ 跳过已关闭的Issue #{issue_num}")
                continue
                
            # 获取现有assignees
            current_assignees = [assignee["login"] for assignee in issue_data.get("assignees", [])]
            suggested_assignees = suggestion['suggested_assignees']
            
            # 检查是否需要更新
            if set(current_assignees) == set(suggested_assignees):
                print(f"   ⏭️ Issue #{issue_num} 已正确分配")
                continue
                
            # 应用分配
            assign_url = f"https://api.github.com/repos/{self.repo}/issues/{issue_num}/assignees"
            assign_data = {"assignees": suggested_assignees}
            
            assign_response = requests.post(assign_url, headers=self.headers, json=assign_data)
            
            if assign_response.status_code == 201:
                print(f"   ✅ 成功分配给: {', '.join(suggested_assignees)}")
                applied_count += 1
                
                # 添加团队标签
                team_label = f"team:{suggestion['suggested_team'].split('-')[1]}"
                labels_url = f"https://api.github.com/repos/{self.repo}/issues/{issue_num}/labels"
                current_labels = [label["name"] for label in issue_data.get("labels", [])]
                
                if team_label not in current_labels:
                    label_response = requests.post(labels_url, headers=self.headers, json={"labels": [team_label]})
                    if label_response.status_code == 200:
                        print(f"   🏷️ 添加团队标签: {team_label}")
                    
            else:
                print(f"   ❌ 分配失败: {assign_response.status_code} - {assign_response.text}")
                error_count += 1
                
            time.sleep(0.5)  # 避免API限制
            
        print(f"""
📊 分配结果:
- 成功处理: {applied_count} 个issues
- 出现错误: {error_count} 个issues
- 总计建议: {len(ai_suggestions)} 个

💡 提示:
  使用 --dry-run 参数可预览而不实际执行分配
  使用 python3 team_issues_manager.py apply 实际执行分配
""")
        
        return {"applied": applied_count, "errors": error_count}
        
    def smart_assignment_with_load_balancing(self):
        """智能分配考虑负载均衡"""
        print("⚖️ 开始智能负载均衡分配...")
        
        # 分析当前团队工作负载
        team_stats = self.analyze_issues_by_team()
        ai_suggestions = self.load_ai_team_assignments()
        
        if not ai_suggestions:
            print("❌ 没有AI分配建议")
            return
            
        # 计算团队成员当前负载
        member_loads = {}
        for team_slug, team_info in self.teams.items():
            for member in team_info['members']:
                username = member['username']
                member_loads[username] = 0
                
        # 统计当前分配情况
        issues_file = Path("downloaded_issues/github_issues.json")
        if issues_file.exists():
            with open(issues_file, 'r', encoding='utf-8') as f:
                issues = json.load(f)
                
            for issue in issues:
                assignees = issue.get("assignees", [])
                for assignee in assignees:
                    if assignee in member_loads:
                        member_loads[assignee] += 1
                        
        print("\n📊 当前成员工作负载:")
        for team_slug, team_info in self.teams.items():
            print(f"\n🏢 {team_info['name']}:")
            team_members = [member['username'] for member in team_info['members']]
            for member in team_members:
                load = member_loads.get(member, 0)
                print(f"   {member}: {load} 个issues")
                
        # 基于负载调整AI建议
        balanced_suggestions = {}
        for issue_num, suggestion in ai_suggestions.items():
            team_slug = suggestion['suggested_team']
            team_members = get_team_usernames(team_slug)
            
            # 按负载排序选择成员
            sorted_members = sorted(team_members, key=lambda x: member_loads.get(x, 0))
            
            # 选择负载最轻的1-2个成员
            balanced_assignees = sorted_members[:2]
            
            balanced_suggestions[issue_num] = {
                **suggestion,
                "suggested_assignees": balanced_assignees,
                "reasoning": f"{suggestion['reasoning']} + 负载均衡优化"
            }
            
        print(f"\n✅ 生成了 {len(balanced_suggestions)} 个负载均衡的分配建议")
        
        return balanced_suggestions
        

if __name__ == "__main__":
    manager = TeamBasedIssuesManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "analyze":
            # 仅分析，不生成报告
            stats = manager.analyze_issues_by_team()
            if stats:
                print("\\n📊 团队分布分析完成")
        elif command == "suggest":
            # 加载AI分配建议
            ai_suggestions = manager.load_ai_team_assignments()
            if ai_suggestions:
                print(f"\\n🤖 加载了 {len(ai_suggestions)} 个AI分配建议")
                for issue_num, suggestion in list(ai_suggestions.items())[:5]:
                    print(f"  Issue #{issue_num}: {suggestion['suggested_team']}")
            else:
                print("\\n⚠️ 没有AI分配建议，请先运行: python3 4_ai_unified_manager.py team-assignment")
        elif command == "labels":
            # 创建团队标签
            manager.create_team_labels()
        elif command == "report":
            # 生成完整报告
            manager.generate_team_assignment_report()
        elif command == "apply":
            # 应用AI分配建议
            dry_run = "--dry-run" in sys.argv
            manager.apply_ai_assignments(dry_run=dry_run)
        elif command == "balance":
            # 负载均衡分配
            manager.smart_assignment_with_load_balancing()
        else:
            print("用法: python3 team_issues_manager.py [analyze|suggest|labels|report|apply|balance]")
            print("      --dry-run: 与apply命令配合使用，预览模式不实际执行")
    else:
        # 默认：生成完整报告
        print("🚀 开始团队Issues分配分析...")
        manager.generate_team_assignment_report()
