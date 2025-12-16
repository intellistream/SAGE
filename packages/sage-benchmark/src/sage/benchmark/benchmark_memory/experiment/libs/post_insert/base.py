"""
PostInsert Action Base Classes
===============================

Provides unified interface for all PostInsert actions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PostInsertInput:
    """PostInsert unified input data structure.

    Attributes:
        data: Complete data from PreInsert + MemoryInsert stages
        insert_stats: Statistics from insertion (inserted count, entry_ids, etc.)
        service_name: Name of the memory service
        is_session_end: Whether this is the last packet in session
        config: Action-specific configuration
    """

    data: dict[str, Any]
    insert_stats: dict[str, Any]
    service_name: str
    is_session_end: bool = False
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PostInsertOutput:
    """PostInsert unified output data structure.

    Attributes:
        success: Whether action executed successfully
        action: Action name
        details: Action-specific execution details
    """

    success: bool
    action: str
    details: dict[str, Any] = field(default_factory=dict)


class BasePostInsertAction(ABC):
    """Base class for all PostInsert actions.

    PostInsert actions handle memory optimization and maintenance after insertion,
    including deduplication, CRUD decisions, link evolution, migration, and forgetting.

    Attributes:
        config: Action-specific configuration dictionary
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize PostInsert action.

        Args:
            config: Action configuration dictionary
        """
        self.config = config
        self._init_action()

    @abstractmethod
    def _init_action(self) -> None:
        """Initialize action-specific configuration and tools.

        This method should:
        1. Parse action-specific config parameters
        2. Initialize required tools (LLM client, embedding generator, etc.)
        3. Set up default values

        Subclasses must implement this method.
        """
        pass

    @abstractmethod
    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute PostInsert action logic.

        Args:
            input_data: Input data structure
            service: Memory service instance (provides retrieve, delete, insert capabilities)
            llm: Optional LLM client (for distillation, CRUD decision, etc.)

        Returns:
            PostInsertOutput with execution results

        Subclasses must implement this method.
        """
        pass

    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback.

        Args:
            key: Configuration key (supports nested keys with dots, e.g. "param.subkey")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
