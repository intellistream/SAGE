"""Interactive pipeline builder CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer

from ..core.output import print_info, print_success, print_warning
from ..pipeline_builder import (
    PipelineBuilder,
    PipelineTemplate,
    TemplateParameter,
    get_pipeline_templates,
)
from ..pipeline_builder.sql import sql_cli_app

app = typer.Typer(help="🛠️ Pipeline 构建助手 - 交互式生成管道配置和样板代码")


def _prompt_parameter(param: TemplateParameter, current_value: Any) -> Any:
    """Prompt the user for a parameter value with validation."""

    prompt_text = f"{param.prompt}"
    if param.help_text:
        prompt_text += f"\n{param.help_text}"

    default_value = current_value if current_value is not None else param.default

    if param.value_type is bool:
        bool_default = bool(default_value) if default_value is not None else False
        return typer.confirm(param.prompt, default=bool_default)

    if param.choices:
        choices_text = ", ".join(str(choice) for choice in param.choices)
        prompt_text += f"\n可选值: {choices_text}"

    default_str = str(default_value) if default_value is not None else None
    value = typer.prompt(prompt_text, default=default_str)
    return value


def _prompt_template(builder: PipelineBuilder, intent: Optional[str]) -> PipelineTemplate:
    templates = builder.list_templates()

    if intent:
        suggestions = builder.suggest_templates(intent)
    else:
        suggestions = templates

    print_info("可用模板：")
    for idx, template in enumerate(suggestions, start=1):
        print_info(f"  {idx}. {template.name} - {template.description}")

    default_index = 1
    selected_idx = int(
        typer.prompt(
            "请选择模板编号",
            default=str(default_index),
        )
    )

    template = suggestions[selected_idx - 1]
    print_success(f"已选择模板：{template.name}")
    return template


def _interactive_answers(
    builder: PipelineBuilder, template: PipelineTemplate, base_config: Dict[str, Any]
) -> Dict[Tuple[str, ...], Any]:
    answers: Dict[Tuple[str, ...], Any] = {}

    for param in template.parameters:
        current_value = builder.get_nested(base_config, param.path)
        answer = _prompt_parameter(param, current_value)
        answers[param.path] = answer

    return answers


@app.command()
def build(
    intent: Optional[str] = typer.Option(None, "--intent", "-i", help="描述你的需求，如 'RAG问答' 或 '文档摘要'"),
    template_key: Optional[str] = typer.Option(None, "--template", "-t", help="直接指定模板 key"),
    output_dir: Path = typer.Option(Path.cwd() / "generated_pipelines", "--output-dir", "-o", help="生成文件输出目录"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="使用默认参数直接生成"),
    dump_only: bool = typer.Option(False, "--dump", help="只打印结果，不写入文件"),
):
    """交互式构建新的 SAGE Pipeline。"""

    builder = PipelineBuilder()

    # Validate output directory when writing files
    if not dump_only:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise typer.BadParameter(
                f"无法创建输出目录 {output_dir}: {exc}"
            ) from exc

    if template_key:
        template = builder.get_template(template_key)
    else:
        template = _prompt_template(builder, intent)

    base_config = builder.initialize_config(template)

    if non_interactive:
        answers = {}
    else:
        answers = _interactive_answers(builder, template, base_config)

    config = builder.apply_parameter_values(base_config, template, answers)
    result = builder.build_result(template, config)

    if dump_only:
        typer.echo(
            json.dumps(
                {"config": result.config, "code": result.code},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    built = builder.write_result(result, output_dir)
    print_success("✅ Pipeline 构建完成！")
    print_info(f"输出目录: {built.output_dir}")
    for label, path in built.files.items():
        print_info(f"- {label}: {path}")

    print_warning("请根据自身环境更新API Key等敏感信息后再运行。")


@app.command()
def list_templates():
    """列出所有内置的 Pipeline 模板。"""

    templates = get_pipeline_templates()
    print_info("内置模板列表：")
    for template in templates:
        print_info(f"- {template.key}: {template.name} → {template.description}")


@app.command()
def show_template(key: str):
    """显示指定模板的详细信息。"""

    builder = PipelineBuilder()
    try:
        template = builder.get_template(key)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(json.dumps({
        "key": template.key,
        "name": template.name,
        "description": template.description,
        "config": template.config,
        "parameters": [
            {
                "path": list(param.path),
                "prompt": param.prompt,
                "default": param.default,
                "help": param.help_text,
            }
            for param in template.parameters
        ],
    }, ensure_ascii=False, indent=2))


# Add SQL-based pipeline commands as subcommand
app.add_typer(sql_cli_app, name="sql", help="📊 SQL-based pipeline definition and management")
