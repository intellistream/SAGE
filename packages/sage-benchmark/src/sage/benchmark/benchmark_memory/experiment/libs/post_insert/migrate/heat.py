"""
Migrate Action - Memory layer migration
========================================

Used by: MemoryOS

This action implements heat-based memory migration across layers
(STM → MTM → LTM) based on access patterns and importance scores.
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class MigrateAction(BasePostInsertAction):
    """Layer migration strategy for hierarchical memory systems.

    Implementation logic (based on MemoryOS):
    1. Evaluate memory heat/importance scores
    2. Promote high-heat memories to higher layers (STM → MTM → LTM)
    3. Demote low-heat memories to lower layers

    Config Parameters:
        promote_threshold (float): Heat threshold for promotion (default: 0.8)
        demote_threshold (float): Heat threshold for demotion (default: 0.2)
        layers (list): Layer names in order (default: ["stm", "mtm", "ltm"])
    """

    def _init_action(self) -> None:
        """Initialize migrate action configuration."""
        self.promote_threshold = self._get_config("promote_threshold", 0.8)
        self.demote_threshold = self._get_config("demote_threshold", 0.2)
        self.layers = self._get_config("layers", ["stm", "mtm", "ltm"])

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute layer migration action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service (must support layer operations)
            llm: LLM client (unused)

        Returns:
            PostInsertOutput with migration statistics
        """
        # Check if service supports layer operations
        if not hasattr(service, "migrate_memories"):
            return PostInsertOutput(
                success=False,
                action="migrate",
                details={
                    "error": "Service does not support layer operations (missing migrate_memories method)"
                },
            )

        try:
            # Call service's migrate_memories method
            result = service.migrate_memories(
                promote_threshold=self.promote_threshold,
                demote_threshold=self.demote_threshold,
                layers=self.layers,
            )

            return PostInsertOutput(
                success=True,
                action="migrate",
                details={
                    "promoted_count": result.get("promoted_count", 0),
                    "demoted_count": result.get("demoted_count", 0),
                    "total_migrated": result.get("total_migrated", 0),
                    "layer_distribution": result.get("layer_distribution", {}),
                },
            )

        except Exception as e:
            return PostInsertOutput(
                success=False,
                action="migrate",
                details={"error": str(e)},
            )
