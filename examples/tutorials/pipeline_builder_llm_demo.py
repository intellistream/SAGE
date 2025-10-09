#!/usr/bin/env python3
"""
演示 SAGE Pipeline Builder 中的大模型交互流程

这个脚本展示了用户请求如何通过 RAG 和 LLM 转换为完整的 Pipeline 配置

@test:allow-demo
"""

from sage.tools.cli.commands import pipeline as pipeline_builder
from sage.tools.cli.commands.pipeline_knowledge import get_default_knowledge_base
from sage.tools.cli.commands.pipeline_domain import load_domain_contexts
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

console = Console()


def demonstrate_llm_pipeline():
    """演示完整的 LLM Pipeline 构建流程"""
    
    console.print("\n" + "="*80)
    console.print("[bold cyan]SAGE Pipeline Builder - LLM 交互流程演示[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Step 1: 用户需求
    console.print("[bold]步骤 1: 用户需求[/bold]")
    user_request = "请帮我构建一个基于文档检索的智能问答系统"
    requirements = {
        "name": "智能问答助手",
        "goal": "构建基于文档检索的问答系统，支持向量检索和大模型生成",
        "data_sources": ["文档知识库", "向量数据库"],
        "latency_budget": "实时响应优先",
        "constraints": "支持流式输出",
    }
    console.print(f"用户输入: [yellow]{user_request}[/yellow]")
    console.print("\n收集到的需求:")
    console.print(Panel(
        json.dumps(requirements, ensure_ascii=False, indent=2),
        title="Requirements",
        border_style="green"
    ))
    
    # Step 2: 加载 Domain Contexts
    console.print("\n[bold]步骤 2: 加载 Domain Contexts (示例配置)[/bold]")
    try:
        domain_contexts = tuple(load_domain_contexts(limit=2))
        console.print(f"✓ 加载了 {len(domain_contexts)} 个示例配置片段")
        if domain_contexts:
            console.print("\n示例片段（前 200 字符）:")
            console.print(f"[dim]{domain_contexts[0][:200]}...[/dim]")
    except Exception as exc:
        console.print(f"[yellow]加载失败: {exc}[/yellow]")
        domain_contexts = ()
    
    # Step 3: 初始化知识库
    console.print("\n[bold]步骤 3: 初始化知识库 (RAG)[/bold]")
    try:
        kb = get_default_knowledge_base(max_chunks=500, allow_download=False)
        console.print(f"✓ 知识库初始化成功")
        console.print(f"  - 文档来源: docs-public/, examples/, packages/sage-libs/")
        console.print(f"  - 检索方法: 向量相似度匹配")
    except Exception as exc:
        console.print(f"[yellow]知识库初始化失败: {exc}[/yellow]")
        console.print("[dim]提示: 在实际使用中会自动下载或使用本地文档[/dim]")
        kb = None
    
    # Step 4: RAG 检索
    console.print("\n[bold]步骤 4: RAG 检索相关文档和代码[/bold]")
    if kb:
        from sage.tools.cli.commands.pipeline_knowledge import build_query_payload
        query = build_query_payload(requirements)
        console.print(f"\n检索查询: [cyan]{query[:150]}...[/cyan]")
        
        try:
            results = kb.search(query, top_k=3)
            console.print(f"\n✓ 检索到 {len(results)} 个相关片段:")
            for idx, chunk in enumerate(results, 1):
                console.print(f"\n[{idx}] 来源: [green]{chunk.source}[/green] (相关度: {chunk.score:.3f})")
                console.print(f"[dim]{chunk.text[:200]}...[/dim]")
        except Exception as exc:
            console.print(f"[yellow]检索失败: {exc}[/yellow]")
    else:
        console.print("[dim]知识库未初始化，跳过检索[/dim]")
    
    # Step 5: 模板匹配
    console.print("\n[bold]步骤 5: 匹配应用模板[/bold]")
    try:
        from sage.tools import templates
        matches = templates.match_templates(requirements, top_k=3)
        console.print(f"✓ 找到 {len(matches)} 个相关模板:")
        for match in matches[:3]:
            console.print(f"  - {match.template.title} ({match.template.id})")
            console.print(f"    标签: {', '.join(match.template.tags)}")
            console.print(f"    匹配度: {match.score:.2f}")
    except Exception as exc:
        console.print(f"[yellow]模板匹配失败: {exc}[/yellow]")
    
    # Step 6: 蓝图匹配
    console.print("\n[bold]步骤 6: 匹配配置蓝图[/bold]")
    try:
        from sage.tools.cli import pipeline_blueprints
        blueprint_matches = tuple(pipeline_blueprints.match_blueprints(requirements))
        console.print(f"✓ 找到 {len(blueprint_matches)} 个相关蓝图:")
        for blueprint, score in blueprint_matches[:3]:
            console.print(f"  - {blueprint.id}: {blueprint.title}")
            console.print(f"    匹配度: {score:.2f}")
    except Exception as exc:
        console.print(f"[yellow]蓝图匹配失败: {exc}[/yellow]")
    
    # Step 7: 构建提示词
    console.print("\n[bold]步骤 7: 构建 LLM 提示词[/bold]")
    console.print("""
提示词结构:
┌──────────────────────────────────────┐
│ System Prompt                        │
│  - SAGE Pipeline 规范说明            │
│  - JSON 结构定义                     │
│  - 生成规则                          │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ User Prompt                          │
│  1. 用户需求 (JSON)                  │
│  2. 应用模板 (top 3)                 │
│  3. 配置蓝图 (top 3)                 │
│  4. 知识库检索结果 (top 5)           │
│  5. Domain 上下文 (示例配置)         │
│  6. 上一版配置 (如有)                │
│  7. 用户反馈 (如有)                  │
└──────────────────────────────────────┘
    """)
    
    # Step 8: 模拟 LLM 调用
    console.print("\n[bold]步骤 8: 调用大模型生成配置[/bold]")
    console.print("""
[cyan]>>> 调用 LLM API...[/cyan]
模型: qwen-max (或用户指定模型)
参数: max_tokens=1200, temperature=0.2
    """)
    
    # 示例生成的配置
    example_config = {
        "pipeline": {
            "name": "智能问答助手",
            "description": "基于文档检索的问答系统，支持向量检索和大模型生成",
            "version": "1.0.0",
            "type": "local"
        },
        "source": {
            "class": "sage.libs.rag.source.TerminalInputSource",
            "params": {}
        },
        "stages": [
            {
                "id": "retriever",
                "kind": "map",
                "class": "sage.libs.rag.retriever.FAISSRetriever",
                "params": {
                    "index_path": "data/vector_index",
                    "top_k": 5
                },
                "summary": "向量检索相关文档"
            },
            {
                "id": "promptor",
                "kind": "map",
                "class": "sage.libs.rag.promptor.QAPromptor",
                "params": {},
                "summary": "构建问答提示词"
            },
            {
                "id": "generator",
                "kind": "map",
                "class": "sage.libs.rag.generator.OpenAIGenerator",
                "params": {
                    "model": "qwen-max",
                    "temperature": 0.7,
                    "stream": True
                },
                "summary": "大模型生成回答"
            }
        ],
        "sink": {
            "class": "sage.libs.rag.sink.ConsoleSink",
            "params": {}
        },
        "services": [],
        "monitors": [],
        "notes": [
            "使用 FAISS 进行向量检索",
            "支持流式输出",
            "可配置检索相关文档数量"
        ]
    }
    
    console.print("\n[bold green]✓ LLM 返回配置:[/bold green]")
    syntax = Syntax(
        json.dumps(example_config, ensure_ascii=False, indent=2),
        "json",
        theme="monokai",
        line_numbers=True
    )
    console.print(syntax)
    
    # Step 9: 验证配置
    console.print("\n[bold]步骤 9: 验证生成的配置[/bold]")
    from sage.tools.cli.commands.chat import _validate_pipeline_config
    is_valid, errors = _validate_pipeline_config(example_config)
    if is_valid:
        console.print("[green]✓ 配置验证通过[/green]")
    else:
        console.print(f"[red]✗ 配置验证失败: {errors}[/red]")
    
    # Step 10: 用户确认和保存
    console.print("\n[bold]步骤 10: 用户确认和保存[/bold]")
    console.print("""
用户可以:
  1. ✅ 确认配置 → 保存为 YAML 文件
  2. ✏️  提供反馈 → 重新生成（最多 6 轮）
  3. ▶️  立即运行 Pipeline
  4. ❌ 取消构建
    """)
    
    console.print("\n" + "="*80)
    console.print("[bold cyan]演示完成![/bold cyan]")
    console.print("="*80 + "\n")
    
    console.print(Panel(
        """
[bold]关键要点:[/bold]

1. 🤖 [cyan]大模型全程参与[/cyan]
   - 接收包含文档、模板、代码示例的丰富上下文
   - 基于 SAGE 规范生成配置

2. 📚 [cyan]RAG 检索增强[/cyan]
   - 自动从文档库检索相关内容
   - 匹配最相关的模板和蓝图
   - 提供代码示例参考

3. 🔄 [cyan]多轮迭代优化[/cyan]
   - 支持用户反馈
   - 基于上一版配置改进
   - 最多 6 轮优化

4. ✅ [cyan]自动验证[/cyan]
   - 检查配置结构
   - 验证必需字段
   - 检查类导入路径
        """,
        title="总结",
        border_style="green"
    ))


if __name__ == "__main__":
    demonstrate_llm_pipeline()
