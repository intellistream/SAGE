#!/usr/bin/env python3
"""演示新增模板的使用方法

@test:allow-demo
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from sage.cli.templates.catalog import get_template, list_templates

console = Console()


def demo_template_usage():
    """演示模板使用"""

    console.print(
        Panel.fit(
            "🎨 新增模板使用演示\n展示如何使用 6 个新增的应用模板",
            title="演示开始",
            border_style="bold blue",
        )
    )

    # 新增的模板 ID
    new_template_ids = [
        "rag-dense-milvus",
        "rag-rerank",
        "rag-bm25-sparse",
        "agent-workflow",
        "rag-memory-enhanced",
        "multimodal-cross-search",
    ]

    for template_id in new_template_ids:
        template = get_template(template_id)

        console.print(f"\n{'=' * 80}", style="bold cyan")
        console.print(f"模板: {template.title}", style="bold yellow")
        console.print(f"ID: {template.id}", style="dim")
        console.print(f"{'=' * 80}", style="bold cyan")

        # 基本信息
        console.print("\n📝 描述:", style="bold green")
        console.print(f"  {template.description}")

        console.print("\n🏷️  标签:", style="bold blue")
        console.print(f"  {', '.join(template.tags[:8])}")

        console.print("\n📂 示例路径:", style="bold magenta")
        console.print(f"  {template.example_path}")

        # 显示 Pipeline 结构
        console.print("\n🔧 Pipeline 结构:", style="bold cyan")
        plan = template.pipeline_plan()
        source_class = plan.get("source", {}).get("class", "N/A")
        console.print(f"  Source: {source_class}", style="green")

        stages = plan.get("stages", [])
        for i, stage in enumerate(stages, 1):
            console.print(
                f"  Stage {i}: {stage.get('id', 'N/A')} → {stage.get('class', 'N/A')}",
                style="yellow",
            )
            if stage.get("summary"):
                console.print(f"           {stage.get('summary')}", style="dim")

        sink_class = plan.get("sink", {}).get("class", "N/A")
        console.print(f"  Sink: {sink_class}", style="red")

        # 显示使用指南
        console.print("\n💡 使用指南:", style="bold green")
        console.print(f"  {template.guidance.strip()}")

        # 显示注意事项
        if template.notes:
            console.print("\n⚠️  注意事项:", style="bold yellow")
            for note in template.notes:
                console.print(f"  • {note}")

        console.print("\n" + "─" * 80)

    # 使用示例
    console.print(f"\n\n{'=' * 80}", style="bold blue")
    console.print("📚 使用示例", style="bold blue")
    console.print(f"{'=' * 80}", style="bold blue")

    usage_examples = """
## 方式一: 在代码中使用

```python
from sage.cli.templates.catalog import get_template

# 获取模板
template = get_template("rag-dense-milvus")

# 获取 Pipeline 配置
config = template.pipeline_plan()

# 查看配置
print(config)
```

## 方式二: 通过 sage chat 命令使用

```bash
# 启动交互式 chat 界面
sage chat

# 输入需求，系统会自动匹配合适的模板
"我想使用 Milvus 向量数据库构建一个语义检索系统"
```

## 方式三: 匹配最佳模板

```python
from sage.cli.templates.catalog import match_templates

requirements = {
    "name": "智能问答系统",
    "goal": "使用向量检索和重排序构建高精度问答",
    "data_sources": ["文档库"],
    "constraints": "需要高精度"
}

# 获取最匹配的模板
matches = match_templates(requirements, top_k=3)
for match in matches:
    print(f"{match.template.title}: {match.score:.3f}")
```

## 推荐的使用场景

### 1. Milvus 向量检索 (`rag-dense-milvus`)
- 适合: 大规模文档库、生产环境部署
- 需要: Milvus 服务、嵌入模型
- 优势: 高性能、可扩展

### 2. 重排序检索 (`rag-rerank`)
- 适合: 高精度要求场景（法律、医疗、金融）
- 需要: 向量库 + BGE Reranker
- 优势: 精确度高

### 3. BM25 检索 (`rag-bm25-sparse`)
- 适合: 关键词匹配、资源受限环境
- 需要: 文本语料库
- 优势: 无需 GPU、计算成本低

### 4. 智能体工作流 (`agent-workflow`)
- 适合: 复杂任务自动化、多步骤推理
- 需要: LLM API、MCP 工具
- 优势: 自主规划、工具调用

### 5. 记忆对话 (`rag-memory-enhanced`)
- 适合: 多轮对话、客服机器人
- 需要: 记忆服务、对话历史存储
- 优势: 上下文连贯

### 6. 跨模态搜索 (`multimodal-cross-search`)
- 适合: 图文混合检索、电商、媒体
- 需要: 多模态向量库、图像编码器
- 优势: 支持文本、图像、融合检索
"""

    console.print(Markdown(usage_examples))

    # 总结
    console.print(f"\n\n{'=' * 80}", style="bold blue")
    console.print("✅ 总结", style="bold blue")
    console.print(f"{'=' * 80}", style="bold blue")

    console.print(f"\n已展示 {len(new_template_ids)} 个新增模板", style="bold green")
    console.print(f"总计 {len(list_templates())} 个可用模板", style="bold cyan")
    console.print(
        "\n💡 提示: 使用 'sage chat' 命令可以自动匹配最合适的模板！",
        style="bold yellow",
    )


if __name__ == "__main__":
    demo_template_usage()
