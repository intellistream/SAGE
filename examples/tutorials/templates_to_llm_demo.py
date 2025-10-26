#!/usr/bin/env python3
"""
详细演示：大模型如何参考 Templates

这个脚本展示了从 Template 匹配到传递给 LLM 的完整过程

@test:allow-demo
"""

import json

from rich.console import Console
from rich.panel import Panel
from sage.tools import templates
from sage.tools.cli.commands.pipeline import _template_contexts

console = Console()


def demonstrate_template_to_llm():
    """演示模板如何被传递给 LLM"""

    console.print("\n" + "=" * 80)
    console.print("[bold cyan]Templates → LLM 完整流程演示[/bold cyan]")
    console.print("=" * 80 + "\n")

    # Step 1: 用户需求
    console.print("[bold]步骤 1: 用户需求[/bold]")
    requirements = {
        "name": "智能问答助手",
        "goal": "构建基于文档检索的问答系统",
        "data_sources": ["文档知识库"],
        "latency_budget": "实时响应优先",
    }
    console.print(
        Panel(
            json.dumps(requirements, ensure_ascii=False, indent=2),
            title="用户需求",
            border_style="green",
        )
    )

    # Step 2: Template 匹配
    console.print("\n[bold]步骤 2: Template 自动匹配[/bold]")
    console.print("[dim]调用: templates.match_templates(requirements, top_k=3)[/dim]\n")

    matches = templates.match_templates(requirements, top_k=3)

    console.print(f"✓ 找到 {len(matches)} 个相关模板:\n")
    for idx, match in enumerate(matches, 1):
        console.print(
            f"[{idx}] {match.template.title} ([cyan]{match.template.id}[/cyan])"
        )
        console.print(f"    标签: [yellow]{', '.join(match.template.tags)}[/yellow]")
        console.print(f"    匹配度: [magenta]{match.score:.2f}[/magenta]")
        console.print()

    # Step 3: 转换为 LLM 可读的提示词
    console.print("\n[bold]步骤 3: 转换为 LLM 提示词[/bold]")
    console.print("[dim]调用: match.template.render_prompt(match.score)[/dim]\n")

    if matches:
        top_match = matches[0]
        template_prompt = top_match.template.render_prompt(top_match.score)

        console.print(
            Panel(
                template_prompt,
                title=f"模板提示词: {top_match.template.title}",
                border_style="blue",
            )
        )

    # Step 4: 所有模板上下文
    console.print("\n[bold]步骤 4: 组装所有模板上下文[/bold]")
    console.print("[dim]调用: _template_contexts(matches)[/dim]\n")

    template_contexts = _template_contexts(matches)
    console.print(f"✓ 生成了 {len(template_contexts)} 个模板上下文片段\n")

    # Step 5: 构建发送给 LLM 的完整提示词
    console.print("\n[bold]步骤 5: 构建完整的 User Prompt[/bold]")
    console.print("[dim]在 _build_prompt() 方法中组装[/dim]\n")

    # 模拟 _build_prompt 的逻辑
    blocks = [
        "请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：",
        json.dumps(requirements, ensure_ascii=False, indent=2),
    ]

    if template_contexts:
        blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
        for idx, snippet in enumerate(template_contexts, start=1):
            blocks.append(f"模板[{idx}]:\n{snippet.strip()}")

    blocks.append("严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。")

    user_prompt = "\n\n".join(blocks)

    # 只显示前 1500 字符
    preview = user_prompt[:1500]
    console.print(
        Panel(
            preview + "\n\n[dim]... (省略部分内容) ...[/dim]",
            title="发送给 LLM 的 User Prompt (预览)",
            border_style="magenta",
        )
    )

    # Step 6: 完整的 API 调用
    console.print("\n[bold]步骤 6: 完整的 LLM API 调用[/bold]\n")

    console.print("发送给 LLM 的完整 messages:")
    console.print(
        """
[cyan]messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT  # SAGE Pipeline 规范说明
    },
    {
        "role": "user",
        "content": user_prompt  # 包含模板、需求、知识库检索等
    }
][/cyan]

[yellow]# 调用 LLM[/yellow]
response = self._client.generate(
    messages,
    max_tokens=1200,
    temperature=0.2
)
    """
    )

    # 关键代码位置
    console.print("\n" + "=" * 80)
    console.print("[bold green]关键代码位置[/bold green]")
    console.print("=" * 80 + "\n")

    code_locations = """
1️⃣ Template 匹配 (pipeline.py:598-601)
   self._template_matches = tuple(
       templates.match_templates(requirements, top_k=3)
   )

2️⃣ 转换为上下文 (pipeline.py:600)
   self._last_template_contexts = _template_contexts(self._template_matches)

3️⃣ 传递给 _build_prompt (pipeline.py:625-631)
   user_prompt = self._build_prompt(
       requirements,
       previous_plan,
       feedback,
       knowledge_contexts,
       self._last_template_contexts,  # ← 这里！
       self._last_blueprint_contexts,
   )

4️⃣ 在 prompt 中注入模板 (pipeline.py:654-657)
   if template_contexts:
       blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
       for idx, snippet in enumerate(template_contexts, start=1):
           blocks.append(f"模板[{idx}]:\\n{snippet.strip()}")

5️⃣ 调用 LLM (pipeline.py:632-637)
   messages = [
       {"role": "system", "content": SYSTEM_PROMPT},
       {"role": "user", "content": user_prompt},
   ]
   response = self._client.generate(messages, max_tokens=1200, temperature=0.2)
    """

    console.print(Panel(code_locations, border_style="green"))

    # 测试环境说明
    console.print("\n" + "=" * 80)
    console.print("[bold yellow]关于测试环境[/bold yellow]")
    console.print("=" * 80 + "\n")

    test_info = """
[red]测试使用 Mock（不调用真实 LLM）[/red]

在测试中 (test_chat_pipeline.py):
  • 使用 DummyGenerator 替代 PipelinePlanGenerator
  • 不真正调用 OpenAI API
  • 返回预定义的配置

原因:
  1. 避免测试依赖外部 API
  2. 提高测试速度和稳定性
  3. 不需要 API Key

[green]生产环境使用真实 LLM[/green]

在实际使用时 (backend != "mock"):
  • 使用 OpenAIClient 调用真实 API
  • 需要配置 TEMP_GENERATOR_API_KEY
  • 支持 OpenAI / 兼容接口 (vLLM, Ollama 等)

示例:
  export TEMP_GENERATOR_API_KEY="sk-xxx"  # pragma: allowlist secret
  sage chat --backend openai --model qwen-max
    """

    console.print(Panel(test_info, border_style="yellow"))

    # 如何验证
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]如何验证 Templates 被使用[/bold cyan]")
    console.print("=" * 80 + "\n")

    verification = """
方法 1: 启用调试输出
  sage pipeline build \\
    --name "TestApp" \\
    --goal "构建问答应用" \\
    --show-knowledge  # ← 会显示匹配的模板！

方法 2: 查看日志
  在生成过程中，会调用 _render_template_panel() 显示匹配的模板

方法 3: 代码断点
  在 pipeline.py:625 设置断点，查看 self._last_template_contexts 的值

方法 4: 打印提示词（调试用）
  在 pipeline.py:638 之后添加:
    print("="*80)
    print("User Prompt:", user_prompt)
    print("="*80)
    """

    console.print(Panel(verification, border_style="cyan"))

    console.print("\n" + "=" * 80)
    console.print("[bold green]演示完成！[/bold green]")
    console.print("=" * 80 + "\n")


if __name__ == "__main__":
    demonstrate_template_to_llm()
