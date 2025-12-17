"""
Template Loading Utilities

Common functions for loading Jinja2 templates across planners.
"""

import logging
from pathlib import Path
from typing import Optional

from jinja2 import Template

logger = logging.getLogger(__name__)


def load_template(
    template_name: str,
    fallback_template: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> Template:
    """
    Load a Jinja2 template from the prompt_templates directory.

    Args:
        template_name: Name of the template file (e.g., 'planner_v2.j2')
        fallback_template: Fallback template string if loading fails
        base_path: Base path for templates (defaults to planning/prompt_templates)

    Returns:
        Loaded Jinja2 Template

    Example:
        >>> template = load_template(
        ...     'planner_v2.j2',
        ...     fallback_template='Generate a plan for: {{ goal }}'
        ... )
    """
    if base_path is None:
        # Default to the prompt_templates directory under planning
        base_path = Path(__file__).parent.parent / "prompt_templates"

    template_path = base_path / template_name

    try:
        with open(template_path, encoding="utf-8") as f:
            template_str = f.read()
        return Template(template_str)
    except Exception as e:
        logger.warning(f"Failed to load template from {template_path}: {e}")
        if fallback_template:
            return Template(fallback_template)
        # Return a minimal default template
        return Template("{{ goal }}")


def render_template(
    template: Template,
    **kwargs,
) -> str:
    """
    Safely render a Jinja2 template with error handling.

    Args:
        template: Jinja2 Template object
        **kwargs: Template variables

    Returns:
        Rendered template string, or fallback on error
    """
    try:
        return template.render(**kwargs)
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        # Return a simple fallback
        goal = kwargs.get("goal", "")
        return f"Process request: {goal}"
