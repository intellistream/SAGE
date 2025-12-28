"""
SAGE Tools Loader - Loads tools from tool_catalog_complete.jsonl.

This module provides the SageToolsLoader class that loads tool definitions
from the SAGE benchmark's tool catalog and exposes them via a unified interface
compatible with the selector resources.

The complete catalog includes:
- 1,200 synthetic tools (original)
- 468 ToolAlpaca tools (real APIs)
- 85 BFCL tools (function calling)
- 10 API-Bank tools
- ~1,400 derived tools from dataset references
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

# Default path to tool catalog (use complete catalog with external benchmarks)
TOOL_CATALOG_PATH = (
    Path(__file__).parent.parent.parent
    / "data"
    / "sources"
    / "agent_tools"
    / "data"
    / "tool_catalog_complete.jsonl"
)

# Fallback to original catalog if complete doesn't exist
if not TOOL_CATALOG_PATH.exists():
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
        name = data.get("name", "")
        category = data.get("category", "")
        capabilities = data.get("capabilities", [])
        inputs = data.get("inputs", [])

        # Use existing description if available, otherwise generate
        description = data.get("description", "")
        if not description:
            # Check for NL documentation (from ToolAlpaca)
            nl_doc = data.get("nl_documentation", "")
            if nl_doc:
                description = nl_doc[:500]  # Truncate if too long
            else:
                # Generate description from available fields
                desc_parts = [name]
                if category:
                    desc_parts.append(f"Category: {category}")
                if capabilities:
                    desc_parts.append(f"Capabilities: {', '.join(capabilities)}")
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
        self._name_to_id: dict[str, str] = {}
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
                        # Build name-to-id mapping for lookup by name
                        self._name_to_id[tool.name.lower()] = tool.tool_id
                        self._name_to_id[tool.name] = tool.tool_id
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
            elif tid in self._name_to_id:
                tools.append(self._tools[self._name_to_id[tid]])
        return tools

    def get_tool_by_name(self, name: str) -> SageTool | None:
        """
        Get a tool by name (case-insensitive).

        Args:
            name: Tool name

        Returns:
            SageTool instance or None if not found
        """
        self._ensure_loaded()
        name_lower = name.lower()
        if name_lower in self._name_to_id:
            return self._tools[self._name_to_id[name_lower]]
        # Try exact match
        if name in self._name_to_id:
            return self._tools[self._name_to_id[name]]
        return None

    def __len__(self) -> int:
        """Return number of tools."""
        self._ensure_loaded()
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        """Check if tool exists by ID or name."""
        self._ensure_loaded()
        return tool_id in self._tools or tool_id.lower() in self._name_to_id


# Singleton instance for convenience
_default_loader: SageToolsLoader | None = None


def get_sage_tools_loader() -> SageToolsLoader:
    """Get the default SageToolsLoader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SageToolsLoader()
    return _default_loader
