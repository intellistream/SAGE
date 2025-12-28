"""
None Action - Passthrough without post-processing
==================================================

Used by: HippoRAG2, SCM
"""

from typing import Any, Optional

from .base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class NoneAction(BasePostInsertAction):
    """Passthrough action - no post-insert processing.

    This action is used by memory systems that don't require any post-insert
    optimization or maintenance (e.g., HippoRAG2, SCM).
    """

    def _init_action(self) -> None:
        """Initialize none action (no setup required)."""
        pass

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute passthrough action.

        Args:
            input_data: Input data (unused)
            service: Memory service (unused)
            llm: LLM client (unused)

        Returns:
            Success result with no modifications
        """
        return PostInsertOutput(
            success=True,
            action="none",
            details={"message": "No post-insert processing performed"},
        )
