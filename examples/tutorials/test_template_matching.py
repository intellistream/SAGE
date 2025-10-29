#!/usr/bin/env python3
"""简化的模板功能测试"""

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, project_root)

from sage.cli.templates.catalog import list_templates, match_templates  # noqa: E402

console = Console()


def test_template_matching():
    """测试模板匹配功能"""
    console.print(
        Panel.fit(
            "🧪 新增模板功能测试\n验证 6 个新增的应用模板",
            title="测试开始",
            border_style="bold blue",
        )
    )

    # 测试场景
    test_cases = [
        {
            "name": "Milvus 向量检索",
            "requirements": {
                "name": "向量检索系统",
                "goal": "使用 Milvus 向量数据库构建大规模语义检索系统",
                "data_sources": ["文档库"],
                "constraints": "需要支持百万级文档",
            },
            "expected": "rag-dense-milvus",
        },
        {
            "name": "重排序检索",
            "requirements": {
                "name": "高精度问答",
                "goal": "构建高精度的问答系统，使用两阶段检索和重排序",
                "constraints": "对答案准确度要求高",
            },
            "expected": "rag-rerank",
        },
        {
            "name": "BM25 关键词检索",
            "requirements": {
                "name": "关键词搜索",
                "goal": "使用 BM25 算法进行传统关键词检索",
                "description": "不需要向量化",
            },
            "expected": "rag-bm25-sparse",
        },
        {
            "name": "智能体系统",
            "requirements": {
                "name": "AI助手",
                "goal": "创建可以自主规划和调用工具的智能体",
                "description": "支持复杂任务的多步骤执行",
            },
            "expected": "agent-workflow",
        },
        {
            "name": "记忆对话",
            "requirements": {
                "name": "对话机器人",
                "goal": "构建支持多轮对话的客服机器人",
                "description": "需要记住历史对话上下文",
                "constraints": "多轮对话",
            },
            "expected": "rag-memory-enhanced",
        },
        {
            "name": "跨模态搜索",
            "requirements": {
                "name": "图文搜索",
                "goal": "构建可以同时搜索文本和图片的跨模态搜索引擎",
                "data_sources": ["图片库", "文本描述"],
            },
            "expected": "multimodal-cross-search",
        },
    ]

    results = []
    for test_case in test_cases:
        console.print(f"\n{'=' * 80}", style="bold blue")
        console.print(f"测试场景: {test_case['name']}", style="bold yellow")
        console.print(f"{'=' * 80}", style="bold blue")

        requirements = test_case["requirements"]
        expected = test_case["expected"]

        # 显示需求
        console.print(f"\n📝 目标: {requirements.get('goal', 'N/A')}", style="cyan")

        # 匹配模板
        matches = match_templates(requirements, top_k=5)

        # 创建匹配结果表格
        table = Table(title="匹配结果", show_header=True, header_style="bold magenta")
        table.add_column("排名", style="dim", width=6)
        table.add_column("模板 ID", style="cyan")
        table.add_column("标题", style="green")
        table.add_column("匹配度", justify="right", style="yellow")
        table.add_column("状态", justify="center")

        top_match = matches[0].template.id
        for i, match in enumerate(matches, 1):
            status = "✅" if match.template.id == expected else ""
            if i == 1 and match.template.id == expected:
                status = "🎯"
            table.add_row(
                str(i),
                match.template.id,
                match.template.title,
                f"{match.score:.3f}",
                status,
            )

        console.print(table)

        # 检查是否匹配预期
        success = top_match == expected
        results.append(
            {
                "name": test_case["name"],
                "success": success,
                "expected": expected,
                "actual": top_match,
            }
        )

        if success:
            console.print(f"\n✅ 成功: 顶部匹配为预期模板 '{expected}'", style="bold green")
        else:
            console.print(
                f"\n⚠️  警告: 预期 '{expected}' 但得到 '{top_match}'",
                style="bold yellow",
            )

    # 总结
    console.print(f"\n\n{'=' * 80}", style="bold blue")
    console.print("测试总结", style="bold blue")
    console.print(f"{'=' * 80}", style="bold blue")

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("场景", style="cyan")
    summary_table.add_column("预期模板", style="yellow")
    summary_table.add_column("实际匹配", style="green")
    summary_table.add_column("结果", justify="center")

    for result in results:
        status = "✅" if result["success"] else "❌"
        summary_table.add_row(result["name"], result["expected"], result["actual"], status)

    console.print(summary_table)

    console.print(
        f"\n\n总体结果: {success_count}/{total_count} 通过",
        style="bold green" if success_count == total_count else "bold yellow",
    )

    # 显示所有可用模板
    console.print(f"\n\n{'=' * 80}", style="bold blue")
    console.print("所有可用模板", style="bold blue")
    console.print(f"{'=' * 80}", style="bold blue")

    all_templates = list_templates()
    template_table = Table(show_header=True, header_style="bold magenta")
    template_table.add_column("#", style="dim", width=4)
    template_table.add_column("模板 ID", style="cyan")
    template_table.add_column("标题", style="green")
    template_table.add_column("主要标签", style="yellow")

    for i, template in enumerate(all_templates, 1):
        tags = ", ".join(template.tags[:4]) + ("..." if len(template.tags) > 4 else "")
        is_new = template.id in [
            "rag-dense-milvus",
            "rag-rerank",
            "rag-bm25-sparse",
            "agent-workflow",
            "rag-memory-enhanced",
            "multimodal-cross-search",
        ]
        prefix = "🆕 " if is_new else "   "
        template_table.add_row(prefix + str(i), template.id, template.title, tags)

    console.print(template_table)
    console.print(f"\n总计: {len(all_templates)} 个模板 (包含 6 个新增)", style="bold cyan")


if __name__ == "__main__":
    test_template_matching()
