"""
Link Evolution Action - Graph edge creation and evolution
==========================================================

Used by: A-Mem, HippoRAG

This action creates and updates edges (links) between memory nodes,
building a knowledge graph structure.
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class LinkEvolutionAction(BasePostInsertAction):
    """Link evolution strategy for graph-based memory systems.

    Implementation logic (based on HippoRAG, A-Mem):
    1. Analyze relationships between newly inserted and existing memories
    2. Create edges (semantic, temporal, causal, synonym, etc.)
    3. Update edge weights based on co-occurrence or similarity

    Config Parameters:
        only_on_session_end (bool): Execute only at session end to avoid O(n²) (default: True)
        edge_types (list): Types of edges to create (default: ["semantic"])
        edge_threshold (float): Similarity threshold for edge creation (default: 0.7)
    """

    def _init_action(self) -> None:
        """Initialize link evolution action configuration."""
        self.only_on_session_end = self._get_config("only_on_session_end", True)
        self.edge_types = self._get_config("edge_types", ["semantic"])
        self.edge_threshold = self._get_config("edge_threshold", 0.7)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute link evolution action.

        Args:
            input_data: Input data with session context
            service: Memory service (must support graph operations)
            llm: LLM client (optional, for advanced edge type detection)

        Returns:
            PostInsertOutput with edge creation statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                    "message": "Link evolution only runs at session end",
                },
            )

        # Check if service supports graph operations
        if not hasattr(service, "evolve_links"):
            return PostInsertOutput(
                success=False,
                action="link_evolution",
                details={
                    "error": "Service does not support graph operations (missing evolve_links method)"
                },
            )

        try:
            # Call service's evolve_links method
            result = service.evolve_links(
                edge_types=self.edge_types,
                threshold=self.edge_threshold,
            )

            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "edges_created": result.get("edges_created", 0),
                    "edges_updated": result.get("edges_updated", 0),
                    "nodes_affected": result.get("nodes_affected", 0),
                    "edge_types": self.edge_types,
                },
            )

        except Exception as e:
            return PostInsertOutput(
                success=False,
                action="link_evolution",
                details={"error": str(e)},
            )
