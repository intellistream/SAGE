"""
Report builders for generating JSON and Markdown evaluation reports.
"""

import json
from pathlib import Path
from typing import Any

from . import EvaluationReport


class JsonReportBuilder:
    """Build JSON format evaluation reports."""

    def build(self, report: EvaluationReport, output_path: Path) -> Path:
        """
        Build and save JSON report.

        Args:
            report: EvaluationReport to format
            output_path: Path to save report

        Returns:
            Path to saved report file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert report to dict and handle Path objects
        report_dict = report.model_dump()
        report_dict["artifacts"] = {k: str(v) for k, v in report.artifacts.items()}

        # Write JSON with pretty formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return output_path


class MarkdownReportBuilder:
    """Build Markdown format evaluation reports."""

    def __init__(self, template: str = None):
        """
        Initialize builder.

        Args:
            template: Optional custom template string
        """
        self.template = template or self._default_template()

    def build(self, report: EvaluationReport, output_path: Path) -> Path:
        """
        Build and save Markdown report.

        Args:
            report: EvaluationReport to format
            output_path: Path to save report

        Returns:
            Path to saved report file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        content = self._generate_markdown(report)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _generate_markdown(self, report: EvaluationReport) -> str:
        """Generate markdown content from report."""
        lines = []

        # Header
        lines.append(f"# Evaluation Report: {report.task.replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"**Experiment ID**: `{report.experiment_id}`  ")
        lines.append(f"**Timestamp**: {report.timestamp}  ")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Metrics section
        lines.append("## 📊 Metrics")
        lines.append("")

        if report.metrics:
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            for metric_name, value in sorted(report.metrics.items()):
                formatted_value = f"{value:.4f}" if isinstance(value, float) else str(value)
                lines.append(f"| {metric_name} | {formatted_value} |")
            lines.append("")
        else:
            lines.append("*No metrics computed*")
            lines.append("")

        # Breakdowns section
        if report.breakdowns:
            lines.append("---")
            lines.append("")
            lines.append("## 🔍 Detailed Analysis")
            lines.append("")

            for section_name, section_data in report.breakdowns.items():
                lines.append(f"### {section_name.replace('_', ' ').title()}")
                lines.append("")
                lines.append(self._format_section(section_data))
                lines.append("")

        # Artifacts section
        if report.artifacts:
            lines.append("---")
            lines.append("")
            lines.append("## 📁 Artifacts")
            lines.append("")
            for name, path in report.artifacts.items():
                lines.append(f"- **{name}**: `{path}`")
            lines.append("")

        return "\n".join(lines)

    def _format_section(self, data: Any, indent: int = 0) -> str:
        """Recursively format section data."""
        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)) and len(str(value)) > 50:
                    lines.append(f"{prefix}- **{key}**:")
                    lines.append(self._format_section(value, indent + 1))
                else:
                    formatted_value = self._format_value(value)
                    lines.append(f"{prefix}- **{key}**: {formatted_value}")
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                # Format as table if list of dicts
                lines.append(self._format_table(data, indent))
            else:
                for item in data[:10]:  # Limit display
                    lines.append(f"{prefix}- {self._format_value(item)}")
                if len(data) > 10:
                    lines.append(f"{prefix}  *(... and {len(data) - 10} more)*")
        else:
            lines.append(f"{prefix}{self._format_value(data)}")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format individual value."""
        if isinstance(value, float):
            return f"{value:.4f}"
        elif isinstance(value, (list, tuple)) and len(value) <= 5:
            return ", ".join(str(v) for v in value)
        else:
            return str(value)

    def _format_table(self, data: list, indent: int = 0) -> str:
        """Format list of dicts as markdown table."""
        if not data:
            return ""

        prefix = "  " * indent
        lines = []

        # Get all keys
        keys = list(data[0].keys())

        # Header
        lines.append(prefix + "| " + " | ".join(keys) + " |")
        lines.append(prefix + "|" + "|".join([" --- "] * len(keys)) + "|")

        # Rows (limit to 10)
        for row in data[:10]:
            values = [self._format_value(row.get(k, "")) for k in keys]
            lines.append(prefix + "| " + " | ".join(values) + " |")

        if len(data) > 10:
            lines.append(prefix + f"*... and {len(data) - 10} more rows*")

        return "\n".join(lines)

    @staticmethod
    def _default_template() -> str:
        """Return default markdown template."""
        return ""  # We use programmatic generation instead


def create_report_builders(formats: list) -> dict[str, Any]:
    """
    Create report builders for specified formats.

    Args:
        formats: List of format names ("json", "markdown")

    Returns:
        Dictionary mapping format to builder instance
    """
    builders = {}

    for fmt in formats:
        if fmt == "json":
            builders["json"] = JsonReportBuilder()
        elif fmt == "markdown":
            builders["markdown"] = MarkdownReportBuilder()
        else:
            raise ValueError(f"Unknown report format: {fmt}")

    return builders
