#!/usr/bin/env python3
"""
AI智能分析Issues工具 - 重新设计版本
支持两种模式：
1. 交互式Copilot模式 - 通过VS Code Copilot进行分析
2. API模式 - 使用配置的API密钥进行自动化分析

整合团队信息和GitHub工具进行智能分析
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 导入legacy工具
sys.path.append(os.path.join(os.path.dirname(__file__), 'legacy'))

# 尝试导入AI库
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class AIIssuesAnalyzer:
    def __init__(self):
        self.workspace_dir = Path(__file__).parent.parent / "issues_workspace"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.helpers_dir = Path(__file__).parent / "helpers"
        self.ensure_output_dir()
        
        # 检测分析模式
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.has_api = bool(self.anthropic_api_key or self.openai_api_key)
        
        # AI客户端初始化
        self.anthropic_client = None
        self.openai_client = None
        
        if self.has_api:
            self._init_api_clients()
        else:
            print("🤖 Copilot交互模式")
            print("💡 如需API自动化模式，请设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY")
        
        # 加载团队信息
        self.team_info = self._load_team_info()
    
    def _init_api_clients(self):
        """初始化API客户端"""
        if ANTHROPIC_AVAILABLE and self.anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                print("✅ Claude AI API 已连接")
            except Exception as e:
                print(f"⚠️ Claude AI 连接失败: {e}")
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                print("✅ OpenAI API 已连接")
            except Exception as e:
                print(f"⚠️ OpenAI 连接失败: {e}")
    
    def _load_team_info(self):
        """加载团队信息"""
        try:
            sys.path.append(str(self.output_dir))
            from team_config import TEAMS, get_all_usernames, get_team_usernames
            print(f"✅ 已加载团队信息: {len(get_all_usernames())} 位成员")
            return {
                'teams': TEAMS,
                'all_usernames': get_all_usernames(),
                'team_count': len(TEAMS)
            }
        except ImportError:
            print("⚠️ 团队信息未找到")
            print("💡 运行以下命令获取团队信息:")
            print("   python3 _scripts/helpers/get_team_members.py")
            return None
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(exist_ok=True)
    
    def analyze_duplicates(self):
        """分析重复Issues"""
        print("🤖 AI分析重复Issues...")
        
        # 加载Issues数据
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据，请先下载Issues")
            return False
        
        print(f"📊 分析 {len(issues)} 个Issues中的重复项...")
        
        if self.has_api and (self.anthropic_client or self.openai_client):
            # API模式：自动化分析
            duplicates = self._api_analyze_duplicates(issues)
        else:
            # Copilot交互模式：准备数据供用户分析
            duplicates = self._copilot_analyze_duplicates(issues)
        
        # 保存分析结果
        report_file = self.output_dir / f"duplicates_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_duplicates_report(duplicates, report_file)
        
        print(f"✅ 重复分析完成，报告保存到: {report_file}")
        return True
    
    def optimize_labels(self):
        """AI优化标签分类"""
        print("🤖 AI优化标签分类...")
        
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
            return False
        
        print(f"📊 分析 {len(issues)} 个Issues的标签优化建议...")
        
        if self.has_api and (self.anthropic_client or self.openai_client):
            label_suggestions = self._api_optimize_labels(issues)
        else:
            label_suggestions = self._copilot_optimize_labels(issues)
        
        # 保存建议
        report_file = self.output_dir / f"label_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_label_report(label_suggestions, report_file)
        
        print(f"✅ 标签优化分析完成，报告保存到: {report_file}")
        return True
    
    def evaluate_priority(self):
        """AI评估优先级"""
        print("🤖 AI评估Issues优先级...")
        
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
            return False
        
        print(f"📊 评估 {len(issues)} 个Issues的优先级...")
        
        if self.has_api and (self.anthropic_client or self.openai_client):
            priority_analysis = self._api_evaluate_priority(issues)
        else:
            priority_analysis = self._copilot_evaluate_priority(issues)
        
        # 保存评估结果
        report_file = self.output_dir / f"priority_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_priority_report(priority_analysis, report_file)
        
        print(f"✅ 优先级评估完成，报告保存到: {report_file}")
        return True
    
    def comprehensive_analysis(self):
        """AI综合分析"""
        print("🤖 AI综合分析Issues...")
        
        issues = self.load_issues()
        if not issues:
            print("❌ 未找到Issues数据")
            return False
        
        print(f"📊 对 {len(issues)} 个Issues进行综合分析...")
        
        # 收集所有分析数据
        context_data = self._prepare_analysis_context(issues)
        
        if self.has_api and (self.anthropic_client or self.openai_client):
            analysis_results = self._api_comprehensive_analysis(context_data)
        else:
            analysis_results = self._copilot_comprehensive_analysis(context_data)
        
        # 生成综合报告
        report_file = self.output_dir / f"comprehensive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_comprehensive_report(analysis_results, report_file)
        
        print(f"✅ 综合分析完成，报告保存到: {report_file}")
        return True
    
    def _prepare_analysis_context(self, issues):
        """准备分析上下文数据"""
        print("📋 准备分析上下文...")
        
        context = {
            'issues': issues,
            'statistics': self._get_issues_statistics(issues),
            'team_info': self.team_info,
            'github_stats': self._get_github_stats()
        }
        
        return context
    
    def _get_issues_statistics(self, issues):
        """获取Issues统计信息"""
        stats = {
            'total': len(issues),
            'open': len([i for i in issues if i.get('state') == 'open']),
            'closed': len([i for i in issues if i.get('state') == 'closed']),
            'labels': {},
            'assignees': {},
        }
        
        # 统计标签
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label if isinstance(label, str) else label.get('name', 'unknown')
                stats['labels'][label_name] = stats['labels'].get(label_name, 0) + 1
        
        # 统计分配给
        for issue in issues:
            assignee = issue.get('assignee')
            if assignee:
                assignee_name = assignee if isinstance(assignee, str) else assignee.get('login', 'unknown')
                stats['assignees'][assignee_name] = stats['assignees'].get(assignee_name, 0) + 1
        
        return stats
    
    def _get_github_stats(self):
        """获取GitHub仓库统计信息"""
        try:
            # 调用legacy工具获取更多信息
            from _github_operations import GitHubManager
            github_manager = GitHubManager()
            return github_manager.get_repo_stats()
        except:
            return {"message": "GitHub统计信息获取失败"}
    
    # Copilot交互模式实现
    def _copilot_analyze_duplicates(self, issues):
        """Copilot交互模式：重复分析"""
        print("\n" + "="*60)
        print("🤖 Copilot交互模式 - 重复Issues分析")
        print("="*60)
        
        # 准备供分析的数据摘要
        analysis_data = {
            'total_issues': len(issues),
            'sample_titles': [issue.get('title', 'No title')[:80] for issue in issues[:10]],
            'all_titles': [issue.get('title', 'No title') for issue in issues]
        }
        
        print(f"\n📊 数据概况:")
        print(f"   总Issues数: {analysis_data['total_issues']}")
        print(f"   样本标题预览:")
        for i, title in enumerate(analysis_data['sample_titles'], 1):
            print(f"   {i:2d}. {title}")
        
        # 🆕 直接进行重复分析
        print(f"\n� 正在分析重复项...")
        duplicates_found = self._find_potential_duplicates(issues)
        
        if duplicates_found:
            print(f"\n⚠️ 发现 {len(duplicates_found)} 组潜在重复Issues:")
            for dup in duplicates_found:
                print(f"   - #{dup['issue1']['number']}: {dup['issue1']['title'][:50]}...")
                print(f"     #{dup['issue2']['number']}: {dup['issue2']['title'][:50]}...")
                print(f"     相似度: {dup['similarity']}")
                print()
        else:
            print(f"\n✅ 未发现明显的重复Issues")
        
        # 保存完整数据供进一步分析
        data_file = self.output_dir / f"duplicates_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({**analysis_data, 'duplicates_found': duplicates_found}, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 完整数据已保存到: {data_file}")
        
        return {
            'mode': 'copilot_interactive',
            'data_file': str(data_file),
            'duplicates_found': duplicates_found,
            'analysis_complete': True
        }
    
    def _copilot_optimize_labels(self, issues):
        """Copilot交互模式：标签优化"""
        print("\n" + "="*60)
        print("🤖 Copilot交互模式 - 标签优化分析")
        print("="*60)
        
        # 分析现有标签
        all_labels = {}
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label if isinstance(label, str) else label.get('name', 'unknown')
                all_labels[label_name] = all_labels.get(label_name, 0) + 1
        
        # 🆕 直接分析标签优化建议
        print(f"\n📊 当前标签分析:")
        print(f"   标签总数: {len(all_labels)}")
        print(f"   使用最多的标签:")
        most_used = sorted(all_labels.items(), key=lambda x: x[1], reverse=True)[:10]
        for label, count in most_used:
            print(f"   - {label}: {count} 次")
        
        # 生成优化建议
        optimization_suggestions = self._generate_label_optimization_suggestions(all_labels, issues)
        
        print(f"\n💡 标签优化建议:")
        for suggestion in optimization_suggestions:
            print(f"   - {suggestion}")
        
        analysis_data = {
            'current_labels': all_labels,
            'label_count': len(all_labels),
            'most_used': most_used,
            'optimization_suggestions': optimization_suggestions,
            'issues_sample': [
                {
                    'title': issue.get('title', 'No title')[:80],
                    'labels': [l if isinstance(l, str) else l.get('name', 'unknown') 
                              for l in issue.get('labels', [])]
                }
                for issue in issues[:15]
            ]
        }
        
        # 保存数据
        data_file = self.output_dir / f"labels_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 完整数据已保存到: {data_file}")
        
        return {
            'mode': 'copilot_interactive',
            'data_file': str(data_file),
            'current_labels': all_labels,
            'optimization_suggestions': optimization_suggestions,
            'analysis_complete': True
        }
    
    def _copilot_evaluate_priority(self, issues):
        """Copilot交互模式：优先级评估"""
        print("\n" + "="*60)
        print("🤖 Copilot交互模式 - 优先级评估")
        print("="*60)
        
        # 🆕 直接进行优先级评估
        print(f"\n🔍 正在评估 {len(issues)} 个Issues的优先级...")
        
        priority_assessment = []
        for issue in issues:
            title = issue.get('title', 'No title')
            labels = [l if isinstance(l, str) else l.get('name', 'unknown') 
                     for l in issue.get('labels', [])]
            
            priority = self._assess_priority(title, labels)
            priority_assessment.append({
                'number': issue.get('number', 0),
                'title': title,
                'labels': labels,
                'priority': priority,
                'reasoning': self._get_priority_reasoning(title, labels, priority)
            })
        
        # 按优先级分组
        high_priority = [item for item in priority_assessment if item['priority'] == 'high']
        medium_priority = [item for item in priority_assessment if item['priority'] == 'medium']
        low_priority = [item for item in priority_assessment if item['priority'] == 'low']
        
        print(f"\n📊 优先级评估结果:")
        print(f"   高优先级: {len(high_priority)} 个")
        print(f"   中优先级: {len(medium_priority)} 个")
        print(f"   低优先级: {len(low_priority)} 个")
        
        if high_priority:
            print(f"\n🔥 高优先级Issues:")
            for item in high_priority:
                print(f"   - #{item['number']}: {item['title'][:60]}...")
                print(f"     理由: {item['reasoning']}")
        
        analysis_data = {
            'priority_assessment': priority_assessment,
            'summary': {
                'high': len(high_priority),
                'medium': len(medium_priority),
                'low': len(low_priority)
            },
            'priority_factors': [
                "标签中是否包含 'critical', 'urgent', 'high-priority'",
                "Issue创建时间（越久优先级可能越高）",
                "分配状态和负责人",
                "Issues描述的详细程度",
                "社区讨论热度（评论数）"
            ],
            'team_context': self.team_info
        }
        
        # 保存数据
        data_file = self.output_dir / f"priority_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 完整数据已保存到: {data_file}")
        
        return {
            'mode': 'copilot_interactive',
            'data_file': str(data_file),
            'priority_assessment': priority_assessment,
            'analysis_complete': True
        }
    
    def _copilot_comprehensive_analysis(self, context_data):
        """Copilot交互模式：综合分析"""
        print("\n" + "="*60)
        print("🤖 Copilot交互模式 - 综合Issues分析")
        print("="*60)
        
        print(f"\n📊 综合分析上下文:")
        print(f"   Issues总数: {context_data['statistics']['total']}")
        print(f"   开放Issues: {context_data['statistics']['open']}")
        print(f"   已关闭Issues: {context_data['statistics']['closed']}")
        if context_data['team_info']:
            print(f"   团队成员数: {len(context_data['team_info']['all_usernames'])}")
            print(f"   团队数量: {context_data['team_info']['team_count']}")
        
        # 保存完整分析上下文
        data_file = self.output_dir / f"comprehensive_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 综合分析数据已保存到: {data_file}")
        
        # 🆕 直接进行分析，而不是让用户手动操作
        print("\n🔍 正在直接分析数据...")
        analysis_results = self._analyze_data_directly(context_data)
        
        # 生成分析指导
        analysis_guide = {
            'analysis_areas': [
                "Issues分布和趋势分析",
                "团队工作负载分析", 
                "标签和分类优化建议",
                "优先级和紧急程度评估",
                "重复Issues识别和合并建议",
                "工作流程改进建议"
            ],
            'data_file': str(data_file),
            'mode': 'copilot_interactive',
            'direct_analysis': analysis_results  # 🆕 添加直接分析结果
        }
        
        return analysis_guide
    
    def _analyze_data_directly(self, context_data):
        """直接分析Issues数据，而不需要用户手动操作"""
        print("📈 开始直接分析Issues数据...")
        
        issues = context_data.get('issues', [])
        stats = context_data.get('statistics', {})
        team_info = context_data.get('team_info', {})
        
        analysis = {
            'summary': self._generate_summary(issues, stats),
            'issues_analysis': self._analyze_issues_content(issues),
            'team_analysis': self._analyze_team_distribution(issues, team_info),
            'recommendations': self._generate_recommendations(issues, stats, team_info)
        }
        
        # 打印分析结果
        self._print_analysis_results(analysis)
        
        return analysis
    
    def _generate_summary(self, issues, stats):
        """生成Issues概要分析"""
        total = stats.get('total', 0)
        open_count = stats.get('open', 0)
        closed_count = stats.get('closed', 0)
        
        completion_rate = (closed_count / total * 100) if total > 0 else 0
        
        return {
            'total_issues': total,
            'completion_rate': f"{completion_rate:.1f}%",
            'open_issues': open_count,
            'closed_issues': closed_count,
            'health_status': 'healthy' if completion_rate > 50 else 'needs_attention'
        }
    
    def _analyze_issues_content(self, issues):
        """分析Issues内容"""
        analysis = {
            'titles_analysis': [],
            'labels_distribution': {},
            'potential_duplicates': [],
            'priority_assessment': []
        }
        
        # 分析标题
        for issue in issues:
            title = issue.get('title', '')
            labels = [label.get('name', '') for label in issue.get('labels', [])]
            
            analysis['titles_analysis'].append({
                'issue_number': issue.get('number', 'unknown'),
                'title': title,
                'labels': labels,
                'type': self._classify_issue_type(title, labels),
                'priority': self._assess_priority(title, labels)
            })
        
        # 统计标签分布
        all_labels = {}
        for issue in issues:
            for label in issue.get('labels', []):
                label_name = label.get('name', 'unknown')
                all_labels[label_name] = all_labels.get(label_name, 0) + 1
        
        analysis['labels_distribution'] = all_labels
        
        # 查找潜在重复
        analysis['potential_duplicates'] = self._find_potential_duplicates(issues)
        
        return analysis
    
    def _classify_issue_type(self, title, labels):
        """分类Issue类型"""
        title_lower = title.lower()
        
        if any(label in ['bug', 'fix'] for label in labels) or any(word in title_lower for word in ['bug', '修复', 'fix', '错误']):
            return 'bug_fix'
        elif any(label in ['enhancement', 'feature'] for label in labels) or any(word in title_lower for word in ['添加', '新增', 'add', 'feature']):
            return 'feature_enhancement'
        elif any(label in ['documentation', 'docs'] for label in labels) or any(word in title_lower for word in ['文档', 'doc', 'documentation']):
            return 'documentation'
        else:
            return 'other'
    
    def _assess_priority(self, title, labels):
        """评估优先级"""
        title_lower = title.lower()
        
        # 高优先级关键词
        high_priority_keywords = ['critical', '紧急', 'urgent', '重要', 'crash', '崩溃']
        if any(keyword in title_lower for keyword in high_priority_keywords):
            return 'high'
        
        # 中优先级关键词
        medium_priority_keywords = ['improve', '优化', 'enhance', '改进']
        if any(keyword in title_lower for keyword in medium_priority_keywords):
            return 'medium'
        
        return 'low'
    
    def _find_potential_duplicates(self, issues):
        """查找潜在的重复Issues"""
        duplicates = []
        
        for i, issue1 in enumerate(issues):
            for j, issue2 in enumerate(issues[i+1:], i+1):
                similarity = self._calculate_title_similarity(
                    issue1.get('title', ''), 
                    issue2.get('title', '')
                )
                
                if similarity > 0.6:  # 相似度阈值
                    duplicates.append({
                        'issue1': {
                            'number': issue1.get('number', 'unknown'),
                            'title': issue1.get('title', '')
                        },
                        'issue2': {
                            'number': issue2.get('number', 'unknown'),
                            'title': issue2.get('title', '')
                        },
                        'similarity': f"{similarity:.2%}"
                    })
        
        return duplicates
    
    def _calculate_title_similarity(self, title1, title2):
        """计算标题相似度"""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _analyze_team_distribution(self, issues, team_info):
        """分析团队分配情况"""
        if not team_info:
            return {'message': '无团队信息'}
        
        teams = team_info.get('teams', {})
        all_usernames = set(team_info.get('all_usernames', []))
        
        analysis = {
            'team_workload': {},
            'unassigned_issues': 0,
            'external_assignees': []
        }
        
        for team_name, team_data in teams.items():
            team_members = {member['username'] for member in team_data.get('members', [])}
            analysis['team_workload'][team_name] = {
                'members': len(team_members),
                'assigned_issues': 0
            }
        
        # 分析Issues分配情况
        for issue in issues:
            assignee = issue.get('assignee')
            if assignee:
                assignee_name = assignee.get('login', '') if isinstance(assignee, dict) else str(assignee)
                if assignee_name in all_usernames:
                    # 找到该用户所属的团队
                    for team_name, team_data in teams.items():
                        team_members = {member['username'] for member in team_data.get('members', [])}
                        if assignee_name in team_members:
                            analysis['team_workload'][team_name]['assigned_issues'] += 1
                            break
                else:
                    analysis['external_assignees'].append(assignee_name)
            else:
                analysis['unassigned_issues'] += 1
        
        return analysis
    
    def _generate_recommendations(self, issues, stats, team_info):
        """生成改进建议"""
        recommendations = []
        
        # 基于完成率的建议
        total = stats.get('total', 0)
        closed = stats.get('closed', 0)
        completion_rate = (closed / total * 100) if total > 0 else 0
        
        if completion_rate < 50:
            recommendations.append("📈 Issues完成率较低，建议加强项目管理和任务分配")
        
        # 基于标签的建议
        labels = stats.get('labels', {})
        if 'bug' in labels and labels['bug'] > total * 0.3:
            recommendations.append("🐛 Bug类Issues较多，建议加强代码质量控制和测试")
        
        # 基于团队分配的建议
        if team_info:
            unassigned_count = sum(1 for issue in issues if not issue.get('assignee'))
            if unassigned_count > total * 0.2:
                recommendations.append("👥 未分配的Issues较多，建议明确责任人")
        
        # 基于重复Issues的建议
        duplicates = self._find_potential_duplicates(issues)
        if duplicates:
            recommendations.append(f"🔄 发现 {len(duplicates)} 组潜在重复Issues，建议合并处理")
        
        return recommendations
    
    def _generate_label_optimization_suggestions(self, all_labels, issues):
        """生成标签优化建议"""
        suggestions = []
        
        # 检查常见标签是否存在
        recommended_labels = ['bug', 'enhancement', 'documentation', 'question', 'help wanted']
        missing_labels = [label for label in recommended_labels if label not in all_labels]
        
        if missing_labels:
            suggestions.append(f"建议添加标准标签: {', '.join(missing_labels)}")
        
        # 检查是否有使用频率很低的标签
        low_usage_labels = [label for label, count in all_labels.items() if count == 1]
        if len(low_usage_labels) > 3:
            suggestions.append(f"有 {len(low_usage_labels)} 个标签仅使用一次，考虑是否需要合并")
        
        # 检查标签命名一致性
        similar_labels = self._find_similar_labels(all_labels.keys())
        if similar_labels:
            suggestions.append("发现相似标签，建议统一命名: " + str(similar_labels))
        
        return suggestions
    
    def _find_similar_labels(self, label_names):
        """查找相似的标签名称"""
        similar_pairs = []
        label_list = list(label_names)
        
        for i, label1 in enumerate(label_list):
            for label2 in label_list[i+1:]:
                if self._calculate_title_similarity(label1, label2) > 0.5:
                    similar_pairs.append((label1, label2))
        
        return similar_pairs
    
    def _get_priority_reasoning(self, title, labels, priority):
        """获取优先级评估理由"""
        reasons = []
        
        if priority == 'high':
            if any(word in title.lower() for word in ['critical', '紧急', 'urgent', '重要']):
                reasons.append("标题包含高优先级关键词")
            if 'bug' in labels:
                reasons.append("属于Bug类Issue")
        elif priority == 'medium':
            if any(word in title.lower() for word in ['improve', '优化', 'enhance']):
                reasons.append("属于改进类Issue")
        else:
            reasons.append("常规优先级Issue")
        
        return "; ".join(reasons) if reasons else "基于标题和标签的综合评估"
    
    def _print_analysis_results(self, analysis):
        """打印分析结果到控制台"""
        print("\n" + "="*60)
        print("📊 Issues数据分析结果")
        print("="*60)
        
        # 打印概要
        summary = analysis.get('summary', {})
        print(f"\n📈 概要统计:")
        print(f"   总Issues: {summary.get('total_issues', 0)}")
        print(f"   完成率: {summary.get('completion_rate', 'N/A')}")
        print(f"   健康状态: {summary.get('health_status', 'unknown')}")
        
        # 打印Issues分析
        issues_analysis = analysis.get('issues_analysis', {})
        
        # 标签分布
        labels_dist = issues_analysis.get('labels_distribution', {})
        if labels_dist:
            print(f"\n🏷️ 标签分布 (前5):")
            sorted_labels = sorted(labels_dist.items(), key=lambda x: x[1], reverse=True)[:5]
            for label, count in sorted_labels:
                print(f"   - {label}: {count}")
        
        # 重复Issues
        duplicates = issues_analysis.get('potential_duplicates', [])
        if duplicates:
            print(f"\n⚠️ 发现 {len(duplicates)} 组潜在重复Issues:")
            for dup in duplicates[:3]:  # 只显示前3组
                print(f"   - #{dup['issue1']['number']} vs #{dup['issue2']['number']} (相似度: {dup['similarity']})")
        
        # 团队分析
        team_analysis = analysis.get('team_analysis', {})
        if 'team_workload' in team_analysis:
            print(f"\n👥 团队工作负载:")
            for team, workload in team_analysis['team_workload'].items():
                print(f"   - {team}: {workload['assigned_issues']} issues ({workload['members']} 成员)")
        
        # 建议
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 改进建议:")
            for rec in recommendations:
                print(f"   {rec}")

    # API模式实现（留作扩展）
    def _api_analyze_duplicates(self, issues):
        """API模式：自动化重复分析"""
        print("🔄 API模式分析...")
        return self._copilot_analyze_duplicates(issues)
    
    def _api_optimize_labels(self, issues):
        """API模式：自动化标签优化"""
        print("🔄 API模式分析...")
        return self._copilot_optimize_labels(issues)
    
    def _api_evaluate_priority(self, issues):
        """API模式：自动化优先级评估"""
        print("🔄 API模式分析...")
        return self._copilot_evaluate_priority(issues)
    
    def _api_comprehensive_analysis(self, context_data):
        """API模式：自动化综合分析"""
        print("🔄 API模式分析...")
        return self._copilot_comprehensive_analysis(context_data)
    
    def load_issues(self):
        """加载Issues数据"""
        issues_dir = self.workspace_dir / "issues"
        if not issues_dir.exists():
            print("⚠️ Issues目录不存在，尝试查找其他位置...")
            # 尝试legacy目录中的数据
            legacy_file = Path(__file__).parent.parent / "downloaded_issues" / "github_issues.json"
            if legacy_file.exists():
                print(f"✅ 找到legacy数据: {legacy_file}")
                with open(legacy_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        
        issues = []
        for md_file in issues_dir.glob("*.md"):
            issue_data = self.parse_issue_markdown(md_file)
            if issue_data:
                issues.append(issue_data)
        
        return issues
    
    def parse_issue_markdown(self, md_file):
        """解析Markdown格式的Issue文件"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单解析Markdown格式
            lines = content.split('\n')
            title = lines[0].replace('# ', '') if lines else ""
            
            # 提取基本信息
            issue_data = {
                'title': title,
                'filename': md_file.name,
                'content': content,
                'state': 'open' if 'open_' in md_file.name else 'closed',
                'labels': [],
                'assignee': None
            }
            
            # 尝试解析更多信息
            for line in lines:
                if line.startswith('**编号**:'):
                    try:
                        issue_data['number'] = int(line.split('#')[1].strip())
                    except:
                        pass
                elif line.startswith('## 标签'):
                    # 下一行应该是标签
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        labels_line = lines[idx + 1].strip()
                        if labels_line:
                            issue_data['labels'] = [{'name': label.strip()} for label in labels_line.split(',')]
            
            return issue_data
        except Exception as e:
            print(f"❌ 解析文件失败 {md_file}: {e}")
            return None
    
    def save_duplicates_report(self, duplicates, report_file):
        """保存重复分析报告"""
        content = f"""# Issues重复分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析模式**: {duplicates.get('mode', 'unknown')}

## 分析结果

"""
        if duplicates.get('analysis_complete'):
            duplicates_found = duplicates.get('duplicates_found', [])
            if duplicates_found:
                content += f"### 发现的重复Issues ({len(duplicates_found)} 组)\n\n"
                for i, dup in enumerate(duplicates_found, 1):
                    content += f"#### {i}. 重复组\n"
                    content += f"- **Issue #{dup['issue1']['number']}**: {dup['issue1']['title']}\n"
                    content += f"- **Issue #{dup['issue2']['number']}**: {dup['issue2']['title']}\n"
                    content += f"- **相似度**: {dup['similarity']}\n\n"
            else:
                content += "✅ 未发现明显的重复Issues\n\n"
        
        content += f"""### 数据文件
{duplicates.get('data_file', 'N/A')}

### 建议行动
- 检查相似度高的Issues是否可以合并
- 建立Issue创建模板以减少重复
- 改进搜索功能帮助用户找到已有Issues

"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_label_report(self, suggestions, report_file):
        """保存标签优化报告"""
        content = f"""# 标签优化建议报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析模式**: {suggestions.get('mode', 'unknown')}

## 当前标签状态

"""
        if suggestions.get('current_labels'):
            content += "### 现有标签统计\n"
            sorted_labels = sorted(suggestions['current_labels'].items(), key=lambda x: x[1], reverse=True)
            for label, count in sorted_labels:
                content += f"- **{label}**: {count} 次使用\n"
        
        if suggestions.get('analysis_complete'):
            opt_suggestions = suggestions.get('optimization_suggestions', [])
            if opt_suggestions:
                content += f"\n## 优化建议\n\n"
                for suggestion in opt_suggestions:
                    content += f"- {suggestion}\n"
        
        content += f"""
### 数据文件
{suggestions.get('data_file', 'N/A')}

### 实施建议
1. 统一标签命名规范
2. 定期清理低使用频率的标签
3. 建立标签使用指南
4. 自动化标签建议系统

"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_priority_report(self, analysis, report_file):
        """保存优先级分析报告"""
        content = f"""# 优先级分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析模式**: {analysis.get('mode', 'unknown')}

## 优先级分布

"""
        if analysis.get('analysis_complete'):
            priority_assessment = analysis.get('priority_assessment', [])
            
            # 统计各优先级数量
            high_count = len([item for item in priority_assessment if item.get('priority') == 'high'])
            medium_count = len([item for item in priority_assessment if item.get('priority') == 'medium'])
            low_count = len([item for item in priority_assessment if item.get('priority') == 'low'])
            
            content += f"- **高优先级**: {high_count} 个\n"
            content += f"- **中优先级**: {medium_count} 个\n"
            content += f"- **低优先级**: {low_count} 个\n\n"
            
            # 详细列出高优先级Issues
            high_priority_issues = [item for item in priority_assessment if item.get('priority') == 'high']
            if high_priority_issues:
                content += "## 高优先级Issues详情\n\n"
                for item in high_priority_issues:
                    content += f"### Issue #{item['number']}\n"
                    content += f"- **标题**: {item['title']}\n"
                    content += f"- **标签**: {', '.join(item['labels'])}\n"
                    content += f"- **评估理由**: {item['reasoning']}\n\n"
        
        content += f"""
### 数据文件
{analysis.get('data_file', 'N/A')}

### 行动建议
1. 优先处理高优先级Issues
2. 建立优先级评估标准
3. 定期回顾和调整优先级
4. 平衡开发资源分配

"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_comprehensive_report(self, results, report_file):
        """保存综合分析报告"""
        content = f"""# Issues综合分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析模式**: {results.get('mode', 'unknown')}

## 执行摘要

"""
        
        if results.get('direct_analysis'):
            analysis = results['direct_analysis']
            summary = analysis.get('summary', {})
            
            content += f"- **总Issues数**: {summary.get('total_issues', 0)}\n"
            content += f"- **完成率**: {summary.get('completion_rate', 'N/A')}\n"
            content += f"- **健康状态**: {summary.get('health_status', 'unknown')}\n\n"
            
            # Issues类型分布
            issues_analysis = analysis.get('issues_analysis', {})
            if 'titles_analysis' in issues_analysis:
                type_counts = {}
                for item in issues_analysis['titles_analysis']:
                    issue_type = item.get('type', 'other')
                    type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
                
                content += "## Issues类型分布\n\n"
                for issue_type, count in type_counts.items():
                    content += f"- **{issue_type}**: {count} 个\n"
                content += "\n"
            
            # 重复Issues
            duplicates = issues_analysis.get('potential_duplicates', [])
            if duplicates:
                content += f"## 重复Issues检测\n\n发现 {len(duplicates)} 组潜在重复Issues:\n\n"
                for dup in duplicates:
                    content += f"- Issue #{dup['issue1']['number']} vs #{dup['issue2']['number']} (相似度: {dup['similarity']})\n"
                content += "\n"
            
            # 改进建议
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                content += "## 改进建议\n\n"
                for rec in recommendations:
                    content += f"- {rec}\n"
        
        content += f"""
### 数据文件
{results.get('data_file', 'N/A')}

### 详细分析领域
"""
        for area in results.get('analysis_areas', []):
            content += f"- {area}\n"
        
        content += """
## 下一步行动

1. **立即行动**: 处理高优先级Issues和重复Issues
2. **短期目标**: 改进标签体系和工作流程
3. **长期规划**: 建立Issues管理最佳实践

---
*本报告由SAGE Issues管理工具自动生成*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    parser = argparse.ArgumentParser(description="AI智能分析Issues")
    parser.add_argument("--mode", choices=["duplicates", "labels", "priority", "comprehensive"], 
                       required=True, help="分析模式")
    
    args = parser.parse_args()
    
    analyzer = AIIssuesAnalyzer()
    
    success = False
    if args.mode == "duplicates":
        success = analyzer.analyze_duplicates()
    elif args.mode == "labels":
        success = analyzer.optimize_labels()
    elif args.mode == "priority":
        success = analyzer.evaluate_priority()
    elif args.mode == "comprehensive":
        success = analyzer.comprehensive_analysis()
    
    if success:
        print("\n🎉 AI分析完成！")
        print("📝 查看生成的报告了解详细结果")
        print("💡 所有分析都已自动完成，无需手动操作")
    else:
        print("💥 AI分析失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
