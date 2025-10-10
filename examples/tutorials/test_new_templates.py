#!/usr/bin/env python3
"""
测试新增的应用模板功能

@test:skip - 需要真实 API Key，不在 CI 中运行
"""

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, project_root)

from sage.tools.cli.commands.pipeline import PipelinePlanGenerator
from sage.tools.templates.catalog import match_templates

console = Console()


def test_template_with_llm(scenario_name: str, requirements: dict):
    """使用 LLM 测试模板生成"""
    console.print(f"\n{'='*80}", style="bold blue")
    console.print(f"测试场景: {scenario_name}", style="bold yellow")
    console.print(f"{'='*80}", style="bold blue")

    # 显示需求
    console.print("\n📝 用户需求:", style="bold green")
    console.print(Panel(str(requirements), title="Requirements", border_style="green"))

    # 匹配模板
    console.print("\n🔍 匹配模板:", style="bold cyan")
    matches = match_templates(requirements, top_k=3)
    for i, match in enumerate(matches, 1):
        console.print(
            f"  {i}. {match.template.title} (匹配度: {match.score:.3f})",
            style="cyan",
        )

    # 创建生成器
    try:
        from sage.tools.cli.commands.pipeline import (
            PipelineBuilderConfig,
            load_domain_contexts,
        )

        # 加载领域上下文
        domain_contexts = list(load_domain_contexts(limit=3))
        console.print(f"\n✅ 加载了 {len(domain_contexts)} 个领域上下文", style="green")

        # 创建配置
        config = PipelineBuilderConfig(
            backend="openai",  # 使用真实 API
            domain_contexts=tuple(domain_contexts),
            knowledge_base=None,  # 简化测试
        )

        # 创建生成器
        generator = PipelinePlanGenerator(config)

        console.print("\n🤖 使用 LLM 生成配置...", style="bold magenta")

        # 生成配置
        result = generator.generate(requirements)

        if result.get("success"):
            console.print("\n✅ 配置生成成功！", style="bold green")
            config = result.get("config", {})

            # 显示生成的配置
            pipeline_info = config.get("pipeline", {})
            console.print(
                f"\n管道名称: {pipeline_info.get('name', 'N/A')}", style="yellow"
            )
            console.print(
                f"管道描述: {pipeline_info.get('description', 'N/A')}", style="yellow"
            )

            # 显示 stages
            stages = config.get("stages", [])
            console.print(f"\n处理阶段 ({len(stages)} 个):", style="bold cyan")
            for i, stage in enumerate(stages, 1):
                console.print(
                    f"  {i}. {stage.get('id', 'N/A')}: {stage.get('class', 'N/A')}"
                )
                console.print(f"     说明: {stage.get('summary', 'N/A')}", style="dim")

            return True
        else:
            error_msg = result.get("error", "Unknown error")
            console.print(f"\n❌ 生成失败: {error_msg}", style="bold red")
            return False

    except Exception as e:
        console.print(f"\n❌ 异常: {str(e)}", style="bold red")
        import traceback

        traceback.print_exc()
        return False


def main():
    console.print(
        Panel.fit(
            "🧪 新增模板功能测试\n测试 6 个新增的应用模板",
            title="测试开始",
            border_style="bold blue",
        )
    )

    # 测试场景
    test_cases = [
        (
            "Milvus 向量检索",
            {
                "name": "向量检索系统",
                "goal": "使用 Milvus 向量数据库构建大规模语义检索系统",
                "data_sources": ["文档库"],
                "constraints": "需要支持百万级文档",
            },
        ),
        (
            "重排序检索",
            {
                "name": "高精度问答",
                "goal": "构建高精度的问答系统，使用两阶段检索和重排序",
                "constraints": "对答案准确度要求高",
            },
        ),
        (
            "智能体系统",
            {
                "name": "AI助手",
                "goal": "创建可以自主规划和调用工具的智能体",
                "description": "支持复杂任务的多步骤执行",
            },
        ),
        (
            "记忆对话",
            {
                "name": "对话机器人",
                "goal": "构建支持多轮对话的客服机器人",
                "description": "需要记住历史对话上下文",
                "constraints": "多轮对话",
            },
        ),
    ]

    success_count = 0
    total_count = len(test_cases)

    for scenario_name, requirements in test_cases:
        if test_template_with_llm(scenario_name, requirements):
            success_count += 1
        console.print("\n" + "─" * 80 + "\n")

    # 总结
    console.print(
        Panel.fit(
            f"✅ 成功: {success_count}/{total_count}\n"
            f"{'❌ 失败: ' + str(total_count - success_count) if success_count < total_count else '🎉 全部通过！'}",
            title="测试总结",
            border_style=(
                "bold green" if success_count == total_count else "bold yellow"
            ),
        )
    )


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("SAGE_CHAT_API_KEY"):
        console.print("⚠️  警告: 未设置 SAGE_CHAT_API_KEY 环境变量", style="bold yellow")
        console.print("将尝试使用 .env 文件中的配置")

    main()
