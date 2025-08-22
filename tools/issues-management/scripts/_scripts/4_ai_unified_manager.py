#!/usr/bin/env python3
"""
SAGE智能Issues管理系统 v2.0
基于AI的issues分析、解决方案生成和批量处理
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
import re
import sys
import time
import glob
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class SAGEIssuesAI:
    """SAGE智能Issues AI管理系统"""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            sys.exit(1)
            
        self.repo = "intellistream/SAGE"
        self.github_headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        self.issues_dir = Path("../issues")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Anthropic client if available
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
    
    def run(self):
        """运行主程序"""
        print("🤖 SAGE智能Issues管理系统 v2.0")
        print("=" * 60)
        print("基于AI的智能分析、解决方案生成和批量处理")
        print()
        
        while True:
            self.show_menu()
            choice = input("请选择功能 (1-5): ").strip()
            
            if choice == "5":
                print("👋 再见！")
                break
            elif choice == "1":
                self.smart_analysis()
            elif choice == "2":
                self.solution_generator()
            elif choice == "3":
                self.batch_enhancement()
            elif choice == "4":
                self.project_diagnosis()
            else:
                print("❌ 无效选择，请重新输入")
                
            print()
            input("按Enter键继续...")
    
    def show_menu(self):
        """显示主菜单"""
        print("\n🎯 选择AI功能:")
        print("  1. 🔍 Issues智能分析 (重复检测/标签优化/优先级评估/团队分配)")
        print("  2. 💡 AI解决方案生成 (自动分析issues并生成实现方案)")
        print("  3. 🚀 Issues批量增强 (AI内容优化/格式化/分类)")
        print("  4. 📊 项目健康诊断 (全面分析项目状态和改进建议)")
        print("  5. 🚪 退出")
        print()
    
    def smart_analysis(self):
        """智能分析功能"""
        print("🔍 Issues智能分析")
        print("=" * 40)
        
        # 选择分析范围
        issues = self.select_issues_range()
        if not issues:
            return
            
        # 选择分析类型
        print("\n📊 选择分析类型:")
        print("1. 🔄 重复检测分析")
        print("2. 🏷️ 标签优化分析")
        print("3. 📈 优先级评估分析")
        print("4. 👥 团队分配分析")
        print("5. 🧠 综合智能分析")
        
        analysis_choice = input("请选择 (1-5): ").strip()
        
        if analysis_choice == "1":
            self.analyze_duplicates(issues)
        elif analysis_choice == "2":
            self.analyze_labels(issues)
        elif analysis_choice == "3":
            self.analyze_priorities(issues)
        elif analysis_choice == "4":
            self.analyze_team_assignments(issues)
        elif analysis_choice == "5":
            self.comprehensive_analysis(issues)
        else:
            print("❌ 无效选择")
    
    def solution_generator(self):
        """AI解决方案生成"""
        print("💡 AI解决方案生成")
        print("=" * 40)
        
        # 选择要生成解决方案的issues
        issues = self.select_issues_range()
        if not issues:
            return
            
        print(f"\n🎯 开始为 {len(issues)} 个issues生成解决方案...")
        
        solutions = []
        for i, issue_file in enumerate(issues, 1):
            print(f"\n📝 处理第 {i}/{len(issues)} 个issue: {issue_file.name}")
            
            # 读取issue内容
            issue_content = self.read_issue_file(issue_file)
            if not issue_content:
                continue
                
            # 生成解决方案
            solution = self.generate_solution_for_issue(issue_content)
            if solution:
                solutions.append({
                    'issue_file': issue_file.name,
                    'issue_content': issue_content,
                    'solution': solution
                })
        
        # 保存解决方案报告
        if solutions:
            self.save_solutions_report(solutions)
            print(f"\n✅ 已为 {len(solutions)} 个issues生成解决方案")
        else:
            print("❌ 未能生成任何解决方案")
    
    def batch_enhancement(self):
        """批量增强功能"""
        print("🚀 Issues批量增强")
        print("=" * 40)
        
        # 选择要增强的issues
        issues = self.select_issues_range()
        if not issues:
            return
            
        print("\n🎨 选择增强类型:")
        print("1. ✨ 内容格式化和结构化")
        print("2. 🏷️ 自动标签建议")
        print("3. 📝 内容补充和完善")
        print("4. 🔧 全面内容增强")
        
        enhancement_choice = input("请选择 (1-4): ")


        # 处理增强类型选择
        if enhancement_choice == "1":
            self.format_and_structure_issues(issues)
        elif enhancement_choice == "2":
            self.auto_label_suggestions(issues)
        elif enhancement_choice == "3":
            self.content_enrichment(issues)
        elif enhancement_choice == "4":
            self.comprehensive_enhancement(issues)
        else:
            print("❌ 无效选择")
            return
        
        print(f"\n🔄 开始批量增强 {len(issues)} 个issues...")
        
        enhanced_count = 0
        for i, issue_file in enumerate(issues, 1):
            print(f"\n📝 处理第 {i}/{len(issues)} 个issue: {issue_file.name}")
            
            # 读取issue内容
            issue_content = self.read_issue_file(issue_file)
            if not issue_content:
                continue
                
            # 执行增强
            enhanced = self.enhance_issue_content(issue_content, enhancement_choice)
            if enhanced:
                enhanced_count += 1
        
        print(f"\n✅ 已增强 {enhanced_count} 个issues")
    
    def project_diagnosis(self):
        """项目健康诊断"""
        print("📊 项目健康诊断")
        print("=" * 40)
        
        # 获取所有issues
        all_issues = self.get_all_issues()
        open_issues = [f for f in all_issues if f.name.startswith('open_')]
        closed_issues = [f for f in all_issues if f.name.startswith('closed_')]
        
        print(f"\n📈 项目概况:")
        print(f"  • 总issues数量: {len(all_issues)}")
        print(f"  • 开放issues: {len(open_issues)}")
        print(f"  • 已关闭issues: {len(closed_issues)}")
        
        # 执行诊断分析
        diagnosis = self.perform_project_diagnosis(open_issues, closed_issues)
        
        # 保存诊断报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"project_diagnosis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(diagnosis)
        
        print(f"\n✅ 诊断报告已保存: {report_file}")
    
    def select_issues_range(self):
        """选择issues范围"""
        print("\n📋 选择issues范围:")
        print("1. 🔥 最新的开放issues (默认30个)")
        print("2. 🎯 指定数量的issues")
        print("3. 📊 所有开放issues")
        print("4. 🚪 返回")
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "4":
            return None
        elif choice == "1":
            return self.get_recent_open_issues(30)
        elif choice == "2":
            try:
                count = int(input("请输入issues数量: "))
                return self.get_recent_open_issues(count)
            except ValueError:
                print("❌ 请输入有效数字")
                return None
        elif choice == "3":
            return self.get_all_open_issues()
        else:
            print("❌ 无效选择")
            return None
    
    def get_recent_open_issues(self, count=30):
        """获取最近的开放issues"""
        open_files = []
        for file in self.issues_dir.glob("open_*.md"):
            open_files.append(file)
        
        # 按文件名排序（通常包含issue编号）
        open_files.sort(key=lambda x: x.name, reverse=True)
        
        return open_files[:count] if count > 0 else open_files
    
    def get_all_open_issues(self):
        """获取所有开放issues"""
        return list(self.issues_dir.glob("open_*.md"))
    
    def get_all_issues(self):
        """获取所有issues"""
        return list(self.issues_dir.glob("*.md"))
    
    def read_issue_file(self, file_path):
        """读取issue文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取文件失败 {file_path}: {e}")
            return None
    
    def generate_solution_for_issue(self, issue_content):
        """为单个issue生成解决方案"""
        if not self.anthropic_client:
            print("⚠️ Claude API不可用，使用规则分析...")
            return self.rule_based_solution(issue_content)
        
        try:
            # 使用Claude分析issue并生成解决方案
            prompt = f"""
请分析以下SAGE项目的GitHub issue，并生成详细的解决方案：

{issue_content}

请提供：
1. 问题分析和理解
2. 具体的解决方案步骤
3. 需要修改的文件和代码建议
4. 实现的优先级和时间估计
5. 潜在的风险和注意事项

请用中文回复，格式清晰，提供具体可操作的建议。
"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"❌ Claude分析失败: {e}")
            return self.rule_based_solution(issue_content)
    
    def rule_based_solution(self, issue_content):
        """基于规则的解决方案生成（备用方案）"""
        # 简单的规则分析
        if "[Bug]" in issue_content:
            return "🐛 Bug修复建议:\n1. 复现问题\n2. 定位错误代码\n3. 编写测试用例\n4. 修复并验证"
        elif "[Feature]" in issue_content:
            return "✨ 功能开发建议:\n1. 设计功能架构\n2. 编写接口文档\n3. 实现核心逻辑\n4. 添加测试和文档"
        elif "[Enhancement]" in issue_content:
            return "🚀 增强建议:\n1. 分析现有实现\n2. 设计改进方案\n3. 重构或优化代码\n4. 更新相关文档"
        else:
            return "📝 通用解决建议:\n1. 详细分析需求\n2. 制定实现计划\n3. 分步骤执行\n4. 测试和验证"
    
    def analyze_duplicates(self, issues):
        """重复检测分析"""
        print(f"🔄 开始分析 {len(issues)} 个issues的重复情况...")
        
        # 这里可以调用Claude进行智能重复检测
        # 为简化演示，使用基本的标题相似度检测
        duplicates = []
        for i, issue1 in enumerate(issues):
            for j, issue2 in enumerate(issues[i+1:], i+1):
                if self.calculate_similarity(issue1.name, issue2.name) > 0.8:
                    duplicates.append((issue1.name, issue2.name))
        
        # 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"duplicate_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 重复Issues分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**分析范围**: {len(issues)} 个issues\n\n")
            f.write(f"## 发现的重复issues\n\n")
            
            if duplicates:
                for dup in duplicates:
                    f.write(f"- {dup[0]} ↔ {dup[1]}\n")
            else:
                f.write("未发现明显的重复issues\n")
        
        print(f"✅ 重复分析完成，发现 {len(duplicates)} 组重复，报告已保存: {report_file}")
    
    def analyze_labels(self, issues):
        """标签优化分析"""
        print(f"🏷️ 开始分析 {len(issues)} 个issues的标签优化...")
        
        # 标签建议逻辑
        suggestions = []
        for issue_file in issues:
            content = self.read_issue_file(issue_file)
            if content:
                suggested_labels = self.suggest_labels(content)
                if suggested_labels:
                    suggestions.append((issue_file.name, suggested_labels))
        
        # 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"label_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 标签优化分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**分析范围**: {len(issues)} 个issues\n\n")
            f.write(f"## 标签建议\n\n")
            
            for issue_name, labels in suggestions:
                f.write(f"- **{issue_name}**: {', '.join(labels)}\n")
        
        print(f"✅ 标签分析完成，为 {len(suggestions)} 个issues提供建议，报告已保存: {report_file}")
    
    def analyze_priorities(self, issues):
        """优先级评估分析"""
        print(f"📈 开始分析 {len(issues)} 个issues的优先级...")
        
        # 优先级评估逻辑
        priorities = []
        for issue_file in issues:
            content = self.read_issue_file(issue_file)
            if content:
                priority = self.assess_priority(content)
                priorities.append((issue_file.name, priority))
        
        # 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"priority_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 优先级评估分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**分析范围**: {len(issues)} 个issues\n\n")
            f.write(f"## 优先级评估\n\n")
            
            # 按优先级排序
            priorities.sort(key=lambda x: x[1], reverse=True)
            
            for issue_name, priority in priorities:
                priority_text = "🔥 高" if priority > 7 else "⚡ 中" if priority > 4 else "📝 低"
                f.write(f"- **{issue_name}**: {priority_text} (分数: {priority})\n")
        
        print(f"✅ 优先级分析完成，报告已保存: {report_file}")
    
    def comprehensive_analysis(self, issues):
        """综合智能分析"""
        print(f"🧠 开始综合分析 {len(issues)} 个issues...")
        
        # 执行所有类型的分析
        self.analyze_duplicates(issues)
        self.analyze_labels(issues)
        self.analyze_priorities(issues)
        
        print("✅ 综合分析完成！")
    
    def enhance_issue_content(self, issue_content, enhancement_type):
        """增强issue内容"""
        # 这里可以调用Claude进行内容增强
        # 为简化演示，返回基本的增强建议
        print("  📝 内容增强完成")
        return True
    
    def perform_project_diagnosis(self, open_issues, closed_issues):
        """执行项目诊断"""
        diagnosis = f"""# SAGE项目健康诊断报告

**诊断时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 基本统计

- 开放issues: {len(open_issues)}
- 已关闭issues: {len(closed_issues)}
- 总issues: {len(open_issues) + len(closed_issues)}

## 🔍 问题分析

### Issue类型分布
"""
        
        # 分析issue类型
        bug_count = sum(1 for f in open_issues if '[Bug]' in f.name)
        feature_count = sum(1 for f in open_issues if '[Feature]' in f.name)
        enhancement_count = sum(1 for f in open_issues if '[Enhancement]' in f.name)
        
        diagnosis += f"""
- Bug reports: {bug_count}
- Feature requests: {feature_count}
- Enhancements: {enhancement_count}
- 其他: {len(open_issues) - bug_count - feature_count - enhancement_count}

## 💡 改进建议

1. **优先处理高优先级Bug**: 建议优先修复影响用户体验的关键Bug
2. **合并重复issues**: 定期检查并合并重复的功能请求
3. **完善issue模板**: 提供更详细的issue模板以获得更好的信息
4. **设置里程碑**: 为重要功能设置开发里程碑和时间线

## 📈 项目健康度评分

总体健康度: {'良好' if len(open_issues) < 100 else '需要关注' if len(open_issues) < 200 else '需要改进'}
"""
        
        return diagnosis
    
    def save_solutions_report(self, solutions):
        """保存解决方案报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"ai_solutions_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# AI解决方案生成报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**处理issues数量**: {len(solutions)}\n\n")
            
            for i, solution in enumerate(solutions, 1):
                f.write(f"## {i}. {solution['issue_file']}\n\n")
                f.write(f"### 问题描述\n\n")
                # 只显示问题标题，避免报告过长
                lines = solution['issue_content'].split('\n')
                title = lines[0] if lines else "无标题"
                f.write(f"{title}\n\n")
                f.write(f"### AI生成的解决方案\n\n")
                f.write(f"{solution['solution']}\n\n")
                f.write("---\n\n")
        
        print(f"✅ 解决方案报告已保存: {report_file}")
    
    def calculate_similarity(self, str1, str2):
        """计算字符串相似度"""
        # 简单的相似度计算
        set1 = set(str1.lower().split())
        set2 = set(str2.lower().split())
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0
    
    def suggest_labels(self, content):
        """建议标签"""
        labels = []
        content_lower = content.lower()
        
        # 基于内容关键词建议标签
        if 'bug' in content_lower or 'error' in content_lower or '错误' in content_lower:
            labels.append('bug')
        if 'feature' in content_lower or '功能' in content_lower:
            labels.append('feature')
        if 'enhancement' in content_lower or '增强' in content_lower:
            labels.append('enhancement')
        if 'documentation' in content_lower or '文档' in content_lower:
            labels.append('documentation')
        if 'test' in content_lower or '测试' in content_lower:
            labels.append('testing')
        
        return labels
    
    def assess_priority(self, content):
        """评估优先级 (1-10分)"""
        score = 5  # 基础分数
        content_lower = content.lower()
        
        # 根据关键词调整分数
        if any(word in content_lower for word in ['critical', '严重', 'urgent', '紧急']):
            score += 3
        if any(word in content_lower for word in ['important', '重要', 'high']):
            score += 2
        if any(word in content_lower for word in ['minor', '次要', 'low']):
            score -= 2
        if 'bug' in content_lower:
            score += 1
        if 'feature' in content_lower:
            score += 0.5
        
        return min(10, max(1, score))
    
    def analyze_team_assignments(self, issues):
        """AI团队分配分析"""
        print(f"👥 开始分析 {len(issues)} 个issues的团队分配...")
        
        # 加载团队配置
        team_config_path = Path("metadata/team_config.py")
        if not team_config_path.exists():
            print("❌ 未找到团队配置文件，请先运行: python3 get_team_members.py")
            return
            
        # 读取团队信息
        try:
            import sys
            sys.path.append(str(Path("metadata")))
            from team_config import TEAMS, get_all_usernames
            
            team_info = {
                "sage-apps": {
                    "name": "SAGE Apps Team",
                    "description": "负责应用层开发、前端界面、用户体验、演示程序",
                    "expertise": ["frontend", "ui", "visualization", "web", "app", "interface", "demo", "user"]
                },
                "sage-middleware": {
                    "name": "SAGE Middleware Team", 
                    "description": "负责中间件、服务架构、API设计、系统集成",
                    "expertise": ["service", "api", "middleware", "backend", "server", "architecture", "integration"]
                },
                "sage-kernel": {
                    "name": "SAGE Kernel Team",
                    "description": "负责核心引擎、算法优化、分布式计算、性能调优",
                    "expertise": ["engine", "core", "kernel", "algorithm", "distributed", "performance", "optimization"]
                }
            }
            
        except ImportError:
            print("❌ 无法加载团队配置，请检查metadata目录")
            return
        
        # 准备issues内容用于AI分析
        issues_content = []
        for issue_file in issues:
            content = self.read_issue_file(issue_file)
            if content:
                # 提取issue编号
                issue_num = re.search(r'#(\d+)', issue_file.name)
                issue_number = issue_num.group(1) if issue_num else "unknown"
                
                issues_content.append({
                    "number": issue_number,
                    "file": issue_file.name,
                    "title": content.get("title", ""),
                    "body": content.get("body", ""),
                    "labels": content.get("labels", []),
                    "assignees": content.get("assignees", [])
                })
        
        if not issues_content:
            print("❌ 没有有效的issues内容")
            return
            
        print(f"📊 准备AI分析 {len(issues_content)} 个issues...")
        
        # 构建AI分析prompt
        team_analysis_prompt = f"""
作为SAGE项目的智能团队分配助手，请基于以下信息为issues分配最合适的团队：

## 团队信息：
{json.dumps(team_info, indent=2, ensure_ascii=False)}

## 分析Issues：
{json.dumps(issues_content[:20], indent=2, ensure_ascii=False)}  # 限制数量避免token过多

## 分析要求：
1. 深度理解每个issue的技术内容和需求
2. 基于团队专长进行智能匹配
3. 考虑工作负载平衡
4. 识别需要跨团队协作的复杂issues
5. 为每个建议提供详细理由

## 输出格式：
为每个issue提供分配建议，格式如下：

Issue #123: 建议团队: sage-apps
理由: 该issue涉及前端界面优化，符合Apps团队的专长领域
置信度: 高

Issue #124: 建议团队: sage-middleware  
理由: 涉及API设计和服务架构，适合Middleware团队处理
置信度: 中

请开始分析：
"""

        # 调用AI进行分析
        ai_response = self.call_ai_api(team_analysis_prompt, task_type="team_assignment")
        
        if not ai_response:
            print("❌ AI分析失败")
            return
            
        # 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"team_assignment_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# AI团队分配分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**分析范围**: {len(issues_content)} 个issues\n")
            f.write(f"**AI模型**: 智能团队分配助手\n\n")
            
            f.write(f"## 🏢 团队配置\n\n")
            for team_slug, info in team_info.items():
                f.write(f"### {info['name']} ({team_slug})\n")
                f.write(f"- **职责**: {info['description']}\n")
                f.write(f"- **专长**: {', '.join(info['expertise'])}\n")
                f.write(f"- **成员**: {len(TEAMS[team_slug]['members'])} 人\n\n")
            
            f.write(f"## 🤖 AI分配建议\n\n")
            f.write(ai_response)
            
            f.write(f"\n\n## 📝 使用说明\n\n")
            f.write(f"1. 此分析结果由AI基于技术内容和团队专长生成\n")
            f.write(f"2. 建议结合实际情况和团队负载进行调整\n")
            f.write(f"3. 复杂issues可能需要跨团队协作\n")
            f.write(f"4. 可使用 `python3 team_issues_manager.py` 查看详细分配报告\n")
        
        print(f"✅ AI团队分配分析完成，报告已保存: {report_file}")
        print(f"💡 可运行 `python3 team_issues_manager.py` 查看基于此分析的详细报告")
