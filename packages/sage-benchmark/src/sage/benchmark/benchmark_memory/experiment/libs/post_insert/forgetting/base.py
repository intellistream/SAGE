"""
Forgetting Action - Active memory forgetting
============================================

Used by: MemoryBank, MemoryOS, LD-Agent

This action implements active forgetting based on various strategies:
- Ebbinghaus forgetting curve (MemoryBank)
- Heat-based pruning (MemoryOS)
- Time-based decay (LD-Agent)
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class ForgettingAction(BasePostInsertAction):
    """Active forgetting strategy.

    Implementation logic:
    1. Calculate forgetting scores based on strategy
    2. Identify memories below forget threshold
    3. Delete low-score memories

    Config Parameters:
        strategy (str): Forgetting strategy - "ebbinghaus", "heat_based", "time_based" (default: "ebbinghaus")
        forget_threshold (float): Threshold below which memories are forgotten (default: 0.1)
        decay_factor (float): Time decay factor (default: 0.1)
        only_on_session_end (bool): Execute only at session end (default: True)
    """

    def _init_action(self) -> None:
        """Initialize forgetting action configuration."""
        self.strategy = self._get_config("strategy", "ebbinghaus")
        self.forget_threshold = self._get_config("forget_threshold", 0.1)
        self.decay_factor = self._get_config("decay_factor", 0.1)
        self.only_on_session_end = self._get_config("only_on_session_end", True)

        # Validate strategy
        valid_strategies = ["ebbinghaus", "heat_based", "time_based"]
        if self.strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy: {self.strategy}. Must be one of {valid_strategies}"
            )

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute forgetting action.

        Args:
            input_data: Input data with session context
            service: Memory service (must support forgetting operations)
            llm: LLM client (unused)

        Returns:
            PostInsertOutput with forgetting statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="forgetting",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                    "message": "Forgetting only runs at session end",
                },
            )

        # Check if service supports forgetting operations
        if not hasattr(service, "forget_memories"):
            return PostInsertOutput(
                success=False,
                action="forgetting",
                details={
                    "error": "Service does not support forgetting operations (missing forget_memories method)"
                },
            )

        try:
            # Call service's forget_memories method
            result = service.forget_memories(
                strategy=self.strategy,
                threshold=self.forget_threshold,
                decay_factor=self.decay_factor,
            )

            return PostInsertOutput(
                success=True,
                action="forgetting",
                details={
                    "forgotten_count": result.get("forgotten_count", 0),
                    "strategy": self.strategy,
                    "threshold": self.forget_threshold,
                    "remaining_count": result.get("remaining_count", 0),
                },
            )

        except Exception as e:
            return PostInsertOutput(
                success=False,
                action="forgetting",
                details={"error": str(e)},
            )
