"""Time-Based Migrate Action - Time-interval-triggered memory tier migration

Used by: LD-Agent

Implements LD-Agent's session-gap-triggered migration strategy:
- Detects time interval (current_time - last_memory_time)
- If interval exceeds threshold (e.g., 1 hour), triggers STM -> LTM migration
- Clears STM after migration

Note: This implementation relies on HierarchicalMemoryService's actual service object.
Currently accessed through _ServiceProxy with limited access, actual migration handled
by service layer's automatic mechanism.
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class TimeBasedMigrateAction(BasePostInsertAction):
    """Time-interval-based tier migration strategy

    Implementation logic (based on LD-Agent):
    1. Check if session has ended (is_session_end)
    2. If yes, mark for migration
    3. Actual migration automatically handled by HierarchicalMemoryService's insert()

    Config Parameters:
        time_gap_threshold (int): Time interval threshold (seconds), default 3600 (1 hour)
        source_tier (str): Source tier name (default "stm")
        target_tier (str): Target tier name (default "ltm")
        clear_source (bool): Whether to clear source tier after migration (default True)
        only_on_session_end (bool): Execute only at session end (default True)

    Note:
        Current implementation is simplified to marking mode, actual time interval
        detection and migration automatically triggered by HierarchicalMemoryService
        on capacity overflow
    """

    def _init_action(self) -> None:
        """Initialize time-based migrate action configuration."""
        self.time_gap_threshold = self._get_config("time_gap_threshold", 3600)
        self.source_tier = self._get_config("source_tier", "stm")
        self.target_tier = self._get_config("target_tier", "ltm")
        self.clear_source = self._get_config("clear_source", True)
        self.only_on_session_end = self._get_config("only_on_session_end", True)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute time-based migration check

        Args:
            input_data: Input data containing inserted memory and metadata
            service: Memory service proxy
            llm: LLM generator (unused)

        Returns:
            PostInsertOutput: Processing result with migration metadata
        """
        # Check if session end condition is met
        is_session_end = input_data.data.get("is_session_end", False)

        details = {
            "time_gap_threshold": self.time_gap_threshold,
            "is_session_end": is_session_end,
        }

        # Only check migration at session end if configured
        if self.only_on_session_end and not is_session_end:
            details["migration_triggered"] = False
            return PostInsertOutput(success=True, action="migrate.time_based", details=details)

        # Mark migration needed
        # Note: Actual migration is handled by HierarchicalMemoryService
        # when STM capacity overflows (triggered by session summary insertion)
        details.update(
            {
                "migration_triggered": True,
                "source_tier": self.source_tier,
                "target_tier": self.target_tier,
                "clear_source": self.clear_source,
            }
        )

        return PostInsertOutput(success=True, action="migrate.time_based", details=details)
