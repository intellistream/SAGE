"""
SAGE Tools Loader - Loads 1,200 real tools from tool_catalog.jsonl.

This module provides the SageToolsLoader class that loads tool definitions
from the SAGE benchmark's tool catalog and exposes them via a unified interface
compatible with the selector resources.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

# Default path to tool catalog
TOOL_CATALOG_PATH = (
    Path(__file__).parent.parent.parent
    / "data"
    / "sources"
    / "agent_tools"
    / "data"
    / "tool_catalog.jsonl"
)


@dataclass
class SageTool:
    """
    Represents a tool from the SAGE tool catalog.

    Attributes:
        tool_id: Unique identifier (e.g., 'environment_weather_001')
        name: Human-readable name (e.g., 'Weather Fetch 1')
        description: Tool description (generated from name/category/capabilities)
        category: Tool category (e.g., 'environment/weather')
        capabilities: List of capabilities (e.g., ['forecast', 'radar'])
        inputs: List of input parameter definitions
        outputs: List of output field definitions
        metadata: Additional metadata (owner, version, etc.)
    """

    tool_id: str
    name: str
    description: str
    category: str
    capabilities: list[str] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SageTool:
        """Create SageTool from JSON data."""
        # Generate description from available fields
        name = data.get("name", "")
        category = data.get("category", "")
        capabilities = data.get("capabilities", [])

        # Build description
        desc_parts = [name]
        if category:
            desc_parts.append(f"Category: {category}")
        if capabilities:
            desc_parts.append(f"Capabilities: {', '.join(capabilities)}")

        # Add input info
        inputs = data.get("inputs", [])
        if inputs:
            input_names = [inp.get("name", "") for inp in inputs if inp.get("name")]
            if input_names:
                desc_parts.append(f"Inputs: {', '.join(input_names[:5])}")

        description = ". ".join(desc_parts)

        return cls(
            tool_id=data.get("tool_id", ""),
            name=name,
            description=description,
            category=category,
            capabilities=capabilities,
            inputs=inputs,
            outputs=data.get("outputs", []),
            metadata=data.get("metadata", {}),
        )


class SageToolsLoader:
    """
    Loads tools from the SAGE benchmark tool catalog.

    This loader reads the tool_catalog.jsonl file and provides methods
    to iterate over tools and retrieve tools by ID.

    Usage:
        loader = SageToolsLoader()
        for tool in loader.iter_all():
            print(tool.tool_id, tool.name)

        tool = loader.get_tool('environment_weather_001')
    """

    def __init__(self, catalog_path: str | Path | None = None):
        """
        Initialize the loader.

        Args:
            catalog_path: Path to tool_catalog.jsonl. If None, uses default path.
        """
        self.catalog_path = Path(catalog_path) if catalog_path else TOOL_CATALOG_PATH
        self._tools: dict[str, SageTool] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load tools if not already loaded."""
        if self._loaded:
            return

        if not self.catalog_path.exists():
            logger.warning(f"Tool catalog not found: {self.catalog_path}")
            self._loaded = True
            return

        try:
            with open(self.catalog_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        tool = SageTool.from_json(data)
                        self._tools[tool.tool_id] = tool
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse tool JSON: {e}")
                        continue

            logger.info(f"Loaded {len(self._tools)} tools from {self.catalog_path}")
        except Exception as e:
            logger.error(f"Failed to load tool catalog: {e}")

        self._loaded = True

    def iter_all(self) -> Iterator[SageTool]:
        """
        Iterate over all tools.

        Yields:
            SageTool instances
        """
        self._ensure_loaded()
        yield from self._tools.values()

    def get_tool(self, tool_id: str) -> SageTool:
        """
        Get a tool by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            SageTool instance

        Raises:
            KeyError: If tool not found
        """
        self._ensure_loaded()
        if tool_id not in self._tools:
            raise KeyError(f"Tool not found: {tool_id}")
        return self._tools[tool_id]

    def get_tools(self, tool_ids: list[str]) -> list[SageTool]:
        """
        Get multiple tools by IDs.

        Args:
            tool_ids: List of tool identifiers

        Returns:
            List of SageTool instances (skips missing tools)
        """
        self._ensure_loaded()
        tools = []
        for tid in tool_ids:
            if tid in self._tools:
                tools.append(self._tools[tid])
        return tools

    def __len__(self) -> int:
        """Return number of tools."""
        self._ensure_loaded()
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        """Check if tool exists."""
        self._ensure_loaded()
        return tool_id in self._tools


# Singleton instance for convenience
_default_loader: SageToolsLoader | None = None


def get_sage_tools_loader() -> SageToolsLoader:
    """Get the default SageToolsLoader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SageToolsLoader()
    return _default_loader
