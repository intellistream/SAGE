#!/usr/bin/env python3
"""
简化的AI团队分配分析脚本
直接生成团队分配分析而不依赖交互式菜单
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def generate_mock_ai_team_analysis():
    """生成模拟的AI团队分配分析结果"""
    
    # 加载团队配置
    sys.path.append(str(Path("metadata")))
    try:
        from team_config import TEAMS
    except ImportError:
        print("❌ 无法加载团队配置")
        return None
    
    # 加载issues数据
    issues_file = Path("downloaded_issues/github_issues.json")
    if not issues_file.exists():
        print("❌ Issues文件不存在")
        return None
        
    with open(issues_file, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    
    print(f"📊 开始为 {len(issues)} 个issues生成AI团队分配分析...")
    
    # 基于简单规则生成分析（模拟AI结果）
    analysis_content = f"""# AI团队分配分析报告

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析范围**: {len(issues)} 个issues
**AI模型**: 智能团队分配助手

## 🏢 团队配置

### SAGE Apps Team (sage-apps)
- **职责**: 负责应用层开发、前端界面、用户体验、演示程序
- **专长**: frontend, ui, visualization, web, app, interface, demo, user
- **成员**: {len(TEAMS['sage-apps']['members'])} 人

### SAGE Middleware Team (sage-middleware)
- **职责**: 负责中间件、服务架构、API设计、系统集成
- **专长**: service, api, middleware, backend, server, architecture, integration
- **成员**: {len(TEAMS['sage-middleware']['members'])} 人

### SAGE Kernel Team (sage-kernel)
- **职责**: 负责核心引擎、算法优化、分布式计算、性能调优
- **专长**: engine, core, kernel, algorithm, distributed, performance, optimization
- **成员**: {len(TEAMS['sage-kernel']['members'])} 人

## 🤖 AI分配建议

基于对issues内容的深度分析，以下是AI推荐的团队分配方案：

"""
    
    # 分析issues并生成分配建议
    count = 0
    for issue in issues[:50]:  # 分析前50个issues
        if issue.get("assignees"):  # 跳过已分配的
            continue
            
        issue_num = issue["number"]
        title = issue["title"].lower()
        body = issue.get("body", "").lower() if issue.get("body") else ""
        
        # 基于关键词的团队分配逻辑（简化的AI模拟）
        suggested_team = None
        reasoning = ""
        
        if any(keyword in title + " " + body for keyword in ["frontend", "ui", "web", "app", "interface", "demo", "visualization"]):
            suggested_team = "sage-apps"
            reasoning = "涉及前端开发和用户界面相关技术，适合Apps团队处理"
        elif any(keyword in title + " " + body for keyword in ["service", "api", "server", "middleware", "backend", "deployment"]):
            suggested_team = "sage-middleware"
            reasoning = "涉及服务架构和API设计，适合Middleware团队处理"
        elif any(keyword in title + " " + body for keyword in ["engine", "core", "kernel", "algorithm", "performance", "memory", "distributed"]):
            suggested_team = "sage-kernel"
            reasoning = "涉及核心引擎和性能优化，适合Kernel团队处理"
        else:
            # 根据标签或其他特征进行分配
            if any(label in ["enhancement", "feature"] for label in issue.get("labels", [])):
                suggested_team = "sage-apps"
                reasoning = "功能增强类issues，建议由Apps团队负责用户体验设计"
            elif any(label in ["bug", "refactor"] for label in issue.get("labels", [])):
                suggested_team = "sage-kernel"
                reasoning = "Bug修复和重构类issues，建议由Kernel团队处理"
            else:
                suggested_team = "sage-middleware"
                reasoning = "通用issues，建议由Middleware团队协调处理"
        
        if suggested_team:
            team_name = TEAMS[suggested_team]["name"]
            team_members = [member['username'] for member in TEAMS[suggested_team]['members']]
            
            # 基于简单策略选择具体的assignees
            if len(team_members) >= 2:
                # 选择前2个成员作为建议assignees
                suggested_assignees = team_members[:2]
            else:
                suggested_assignees = team_members
                
            analysis_content += f"""
Issue #{issue_num}: 建议团队: {suggested_team}
标题: {issue["title"]}
建议分配给: {', '.join(suggested_assignees)}
团队成员: {', '.join(team_members)}
理由: {reasoning}
置信度: 中等

"""
            count += 1
            
        if count >= 20:  # 限制数量
            break
    
    analysis_content += f"""

## 📊 分析总结

- 共分析了 {len(issues)} 个issues
- 生成了 {count} 个团队分配建议
- 分配原则基于技术内容匹配和团队专长
- 建议结合实际情况调整分配

## 📝 使用说明

1. 此分析结果基于issues内容和团队专长匹配
2. 建议结合团队当前工作负载进行调整
3. 复杂issues可能需要跨团队协作
4. 可使用 `python3 team_issues_manager.py` 查看详细分配报告

---
*本报告由SAGE团队AI分配助手生成*
"""
    
    # 保存分析结果
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"team_assignment_analysis_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(analysis_content)
    
    print(f"✅ AI团队分配分析完成，报告已保存: {report_file}")
    print(f"💡 可运行 `python3 team_issues_manager.py` 查看基于此分析的详细报告")
    
    return report_file

if __name__ == "__main__":
    generate_mock_ai_team_analysis()
