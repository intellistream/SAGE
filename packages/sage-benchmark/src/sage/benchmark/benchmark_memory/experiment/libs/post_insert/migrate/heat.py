"""
Migrate Action - Memory layer migration
========================================

Used by: MemoryOS

This action implements heat-based memory migration across layers
(STM → MTM → LPM) following MemoryOS paper design:
- STM→MTM: Multi-summary generation with LLM
- MTM→LPM: Profile/Knowledge extraction when Heat ≥ threshold
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class MigrateAction(BasePostInsertAction):
    """Layer migration strategy for hierarchical memory systems (MemoryOS Paper).

    Implementation logic (MemoryOS Algorithm 1 & 2):
    1. STM→MTM: FIFO overflow, generate multi-summary, calculate Fscore
    2. MTM→LPM: Heat-based trigger (τ=5.0), extract Profile/Knowledge with LLM

    Config Parameters:
        migrate_policy (str): Migration policy (default: "heat")
        heat_threshold (float): Heat threshold for MTM→LPM (default: 5.0)
        cold_threshold (float): Unused in MemoryOS
        upgrade_transform (str): "multi_summary" or "none" (default: "none")
        enable_keywords (bool): Extract keywords for Fscore (default: true)
        enable_summary (bool): Generate segment summary (default: true)
        enable_profile_extraction (bool): Extract user profile (default: true)
        enable_knowledge_extraction (bool): Extract knowledge (default: true)
        reset_heat_after_extraction (bool): Reset heat after extraction (default: true)
    """

    def _init_action(self) -> None:
        """Initialize migrate action configuration."""
        self.migrate_policy = self._get_config("migrate_policy", "heat")
        self.heat_threshold = self._get_config("heat_threshold", 5.0)
        self.cold_threshold = self._get_config("cold_threshold", 0.3)
        self.upgrade_transform = self._get_config("upgrade_transform", "none")
        self.enable_keywords = self._get_config("enable_keywords", True)
        self.enable_summary = self._get_config("enable_summary", True)
        self.enable_profile_extraction = self._get_config("enable_profile_extraction", True)
        self.enable_knowledge_extraction = self._get_config("enable_knowledge_extraction", True)
        self.reset_heat_after_extraction = self._get_config("reset_heat_after_extraction", True)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute layer migration action (MemoryOS Algorithm 1 & 2).

        Args:
            input_data: Input data with newly inserted memories
            service: HierarchicalMemoryService (must support MemoryOS methods)
            llm: LLM client for multi-summary and profile extraction

        Returns:
            PostInsertOutput with migration statistics
        """
        # Check if service supports MemoryOS methods
        if not hasattr(service, "_migrate_stm_to_mtm_batch"):
            return PostInsertOutput(
                success=False,
                action="migrate",
                details={
                    "error": "Service does not support MemoryOS migration (missing _migrate_stm_to_mtm_batch)"
                },
            )

        try:
            total_migrated = 0
            details = {}

            # ===== Step 1: STM→MTM Migration (Algorithm 1) =====
            # Check if STM overflow triggers migration
            stm_capacity = self._get_config("tier_capacities", {}).get("stm", 20)
            stm_count = getattr(service, "_tier_counts", {}).get("stm", 0)

            if stm_count > stm_capacity:
                overflow_count = stm_count - stm_capacity

                # Prepare config for multi-summary generation
                stm_config = {
                    "enable_multi_summary": self.upgrade_transform == "multi_summary",
                    "llm_generator": llm,
                }

                migrated_stm = service._migrate_stm_to_mtm_batch(
                    count=overflow_count, config=stm_config
                )

                total_migrated += migrated_stm
                details["stm_to_mtm"] = {
                    "count": migrated_stm,
                    "multi_summary_enabled": self.upgrade_transform == "multi_summary",
                }

            # ===== Step 2: MTM→LPM Profile Extraction (Algorithm 2) =====
            # Extract profile/knowledge when Heat ≥ threshold
            if self.enable_profile_extraction or self.enable_knowledge_extraction:
                if not hasattr(service, "analyze_mtm_sessions_for_long_term"):
                    details["mtm_to_lpm"] = {
                        "error": "Service missing analyze_mtm_sessions_for_long_term method"
                    }
                else:
                    mtm_config = {
                        "llm_generator": llm,
                        "enable_heat_analysis": True,
                        "heat_threshold": self.heat_threshold,
                        "user_id": input_data.metadata.get("user_id", "default")
                        if input_data.metadata
                        else "default",
                    }

                    extracted_count = service.analyze_mtm_sessions_for_long_term(config=mtm_config)

                    details["mtm_to_lpm"] = {
                        "extracted_sessions": extracted_count,
                        "heat_threshold": self.heat_threshold,
                        "profile_extraction_enabled": self.enable_profile_extraction,
                        "knowledge_extraction_enabled": self.enable_knowledge_extraction,
                    }

            return PostInsertOutput(
                success=True,
                action="migrate",
                details={
                    "total_migrated": total_migrated,
                    "policy": self.migrate_policy,
                    **details,
                },
            )

        except Exception as e:
            import traceback

            return PostInsertOutput(
                success=False,
                action="migrate",
                details={"error": str(e), "traceback": traceback.format_exc()},
            )
