"""Core logic for the SAGE pipeline builder command."""

from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

from .templates import PipelineTemplate, TemplateParameter, get_pipeline_templates


@dataclass
class PipelineBuildResult:
    """Artifacts produced by the pipeline builder."""

    template: PipelineTemplate
    pipeline_name: str
    pipeline_description: str
    config: Dict
    code: str
    output_dir: Optional[Path] = None
    files: Dict[str, Path] = field(default_factory=dict)


class PipelineBuilder:
    """High level helper that orchestrates template selection and rendering."""

    def __init__(self, templates: Optional[Sequence[PipelineTemplate]] = None):
        self._templates = list(templates or get_pipeline_templates())

    # ------------------------------------------------------------------
    # Template utilities
    # ------------------------------------------------------------------
    def list_templates(self) -> List[PipelineTemplate]:
        return list(self._templates)

    def get_template(self, key: str) -> PipelineTemplate:
        for template in self._templates:
            if template.key == key:
                return template
        raise KeyError(f"Unknown pipeline template: {key}")

    def suggest_templates(self, intent: str) -> List[PipelineTemplate]:
        intent = intent.strip().lower()
        matches = [tpl for tpl in self._templates if tpl.matches_intent(intent)]
        return matches or list(self._templates)

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def initialize_config(self, template: PipelineTemplate) -> Dict:
        config = template.clone_config()
        pipeline_section = config.setdefault("pipeline", {})
        pipeline_section.setdefault("name", template.default_pipeline_name)
        pipeline_section.setdefault(
            "description", template.default_pipeline_description
        )
        pipeline_section.setdefault("version", "1.0.0")
        pipeline_section.setdefault("type", "local")
        return config

    @staticmethod
    def get_nested(config: Dict, path: Sequence[str]):
        current = config
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def set_nested(config: Dict, path: Sequence[str], value) -> None:
        if not path:
            raise ValueError("Path must contain at least one key")
        current = config
        for key in path[:-1]:
            current = current.setdefault(key, {})
            if not isinstance(current, dict):
                raise ValueError(f"Cannot set value at path {'/'.join(path)}")
        current[path[-1]] = value

    def apply_parameter_values(
        self,
        config: Dict,
        template: PipelineTemplate,
        answers: Optional[Dict[Tuple[str, ...], object]] = None,
    ) -> Dict:
        answers = answers or {}
        for param in template.parameters:
            existing_value = self.get_nested(config, param.path)
            default_value = (
                existing_value if existing_value is not None else param.default
            )
            value = answers.get(param.path, default_value)
            if param.value_type is not None and value is not None:
                try:
                    if param.value_type is bool and isinstance(value, str):
                        value = value.lower() in {"true", "1", "yes", "y"}
                    else:
                        value = param.value_type(value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid value '{value}' for parameter '{param.prompt}'"
                    )
            self.set_nested(config, param.path, value)
        return config

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _slugify(name: str) -> str:
        unsafe_chars = " _:/\\'\""
        slug = name
        for ch in unsafe_chars:
            slug = slug.replace(ch, "-")
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
        slug = "-".join(part for part in slug.split("-") if part)
        return slug.lower() or "pipeline"

    def build_result(
        self,
        template: PipelineTemplate,
        config: Dict,
        custom_code: Optional[str] = None,
    ) -> PipelineBuildResult:
        pipeline_section = config.get("pipeline", {})
        pipeline_name = pipeline_section.get(
            "name", template.default_pipeline_name
        )
        pipeline_description = pipeline_section.get(
            "description", template.default_pipeline_description
        )
        code = custom_code or template.code_template
        return PipelineBuildResult(
            template=template,
            pipeline_name=pipeline_name,
            pipeline_description=pipeline_description,
            config=config,
            code=code,
        )

    def write_result(
        self,
        result: PipelineBuildResult,
        base_output_dir: Path,
        include_readme: bool = True,
    ) -> PipelineBuildResult:
        timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(result.pipeline_name)
        output_dir = base_output_dir / f"{slug}-{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        config_path = output_dir / "pipeline_config.yaml"
        with config_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(result.config, fh, sort_keys=False, allow_unicode=True)

        script_path = output_dir / "pipeline_runner.py"
        with script_path.open("w", encoding="utf-8") as fh:
            fh.write(result.code)
            fh.write("\n")

        result.output_dir = output_dir
        files = {
            "config": config_path,
            "script": script_path,
        }
        result.files = files

        readme_path = None
        if include_readme:
            readme_path = output_dir / "README.md"
            readme_content = self._render_readme(result)
            with readme_path.open("w", encoding="utf-8") as fh:
                fh.write(readme_content)

        if readme_path:
            files["readme"] = readme_path
        result.files = files
        return result

    @staticmethod
    def _render_readme(result: PipelineBuildResult) -> str:
        lines = [
            f"# {result.pipeline_name}\n",
            f"\n{result.pipeline_description}\n\n",
            "## Quick start\n",
            "```bash\n",
            "python pipeline_runner.py\n",
            "```\n",
            "\n",
            "## Generated files\n",
        ]
        for label, path in result.files.items():
            lines.append(f"- `{label}` → `{path.name}`")
        lines.append("\n")
        lines.append("Generated with `sage pipeline build`. Customize the configuration before deploying to production.\n")
        return "".join(lines)


__all__ = ["PipelineBuilder", "PipelineBuildResult"]
