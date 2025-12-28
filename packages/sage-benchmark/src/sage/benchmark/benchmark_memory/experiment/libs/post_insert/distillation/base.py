"""
Distillation Action - Memory deduplication and merging
=======================================================

Used by: TiM, MemGPT, SeCom

This action retrieves similar memories and uses LLM to merge them into
a consolidated memory, reducing redundancy while preserving information.
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class DistillationAction(BasePostInsertAction):
    """Distillation/merging strategy for memory deduplication.

    Implementation logic (based on TiM, SCM4LLMs):
    1. Retrieve memories similar to newly inserted ones
    2. If similarity exceeds threshold, use LLM to merge
    3. Delete old memories and insert merged result

    Config Parameters:
        similarity_threshold (float): Similarity threshold for merging (default: 0.85)
        max_merge_count (int): Maximum number of memories to merge (default: 5)
        merge_prompt (str): LLM prompt template for merging
    """

    def _init_action(self) -> None:
        """Initialize distillation action configuration."""
        self.similarity_threshold = self._get_config("similarity_threshold", 0.85)
        self.max_merge_count = self._get_config("max_merge_count", 5)
        self.merge_prompt = self._get_config(
            "merge_prompt", "请将以下多条相似记忆合并为一条简洁的记忆：\n{memories}\n合并后的记忆："
        )

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute distillation/merging action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service for retrieval and CRUD operations
            llm: LLM client for memory merging

        Returns:
            PostInsertOutput with merge statistics
        """
        if llm is None:
            return PostInsertOutput(
                success=False,
                action="distillation",
                details={"error": "LLM client required for distillation"},
            )

        # Extract entry IDs from insert stats
        entry_ids = input_data.insert_stats.get("entry_ids", [])
        if not entry_ids:
            return PostInsertOutput(
                success=True,
                action="distillation",
                details={"message": "No entries to process"},
            )

        merged_count = 0
        deleted_count = 0

        # Process each newly inserted memory
        for entry_id in entry_ids:
            try:
                # Retrieve similar memories from service
                similar_memories = self._retrieve_similar_memories(
                    service, entry_id, self.similarity_threshold, self.max_merge_count
                )

                if len(similar_memories) > 1:  # Found duplicates
                    # Use LLM to merge memories
                    merged_text = self._merge_memories(llm, similar_memories)

                    # Delete old memories
                    for mem in similar_memories:
                        service.delete_entry(mem["id"])
                        deleted_count += 1

                    # Insert merged memory
                    service.insert_entry(
                        text=merged_text,
                        metadata={"merged_from": [m["id"] for m in similar_memories]},
                    )
                    merged_count += 1

            except Exception as e:
                # Log error but continue processing
                details = input_data.data.setdefault("errors", [])
                details.append(
                    {
                        "entry_id": entry_id,
                        "action": "distillation",
                        "error": str(e),
                    }
                )

        return PostInsertOutput(
            success=True,
            action="distillation",
            details={
                "merged_count": merged_count,
                "deleted_count": deleted_count,
                "processed_entries": len(entry_ids),
            },
        )

    def _retrieve_similar_memories(
        self, service: Any, entry_id: str, threshold: float, max_count: int
    ) -> list[dict[str, Any]]:
        """Retrieve memories similar to the given entry.

        Args:
            service: Memory service
            entry_id: Target entry ID
            threshold: Similarity threshold
            max_count: Maximum number of results

        Returns:
            List of similar memory entries
        """
        # Get entry embedding
        entry = service.get_entry(entry_id)
        if not entry or "embedding" not in entry:
            return []

        # Search for similar memories
        results = service.search(
            query_embedding=entry["embedding"],
            top_k=max_count,
            threshold=threshold,
        )

        return results

    def _merge_memories(self, llm: Any, memories: list[dict[str, Any]]) -> str:
        """Use LLM to merge multiple memories into one.

        Args:
            llm: LLM client
            memories: List of memory entries to merge

        Returns:
            Merged memory text
        """
        # Format memories for prompt
        memories_text = "\n".join(
            [f"{i + 1}. {mem.get('text', '')}" for i, mem in enumerate(memories)]
        )

        # Generate merge prompt
        prompt = self.merge_prompt.format(memories=memories_text)

        # Call LLM
        response = llm.generate(prompt)
        return response.strip()
