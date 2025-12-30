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
        merge_summary_only (bool): If True, merge summaries from metadata.summary instead of text
                                   (for SeCom: preserves original conversations)
    """

    def _init_action(self) -> None:
        """Initialize distillation action configuration."""
        # 数据量驱动的蒸馏策略（TiM 核心思路）
        self.retrieve_count = self._get_config("retrieve_count", 10)  # 检索候选数量
        self.min_merge_count = self._get_config("min_merge_count", 3)  # 最少需要多少条才蒸馏
        self.merge_prompt = self._get_config(
            "merge_prompt", "请将以下多条相似记忆合并为一条简洁的记忆：\n{memories}\n合并后的记忆："
        )

        # SeCom 特性：仅合并摘要，保留原始对话
        self.merge_summary_only = self._get_config("merge_summary_only", False)

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

        # Extract complete entries from insert stats (includes embedding)
        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="distillation",
                details={"message": "No entries to process"},
            )

        merged_count = 0
        deleted_count = 0

        # Process each newly inserted memory
        for entry in entries:
            try:
                # Retrieve similar memories from service (数据量驱动，不用阈值过滤)
                similar_memories = self._retrieve_similar_memories(
                    service, entry, self.retrieve_count
                )

                # TiM 核心：数据量足够才蒸馏，否则跳过（避免小概率重复的过度处理）
                if len(similar_memories) >= self.min_merge_count:
                    # Use LLM to merge memories
                    merged_summary = self._merge_memories(llm, similar_memories)

                    # Delete old memories
                    for mem in similar_memories:
                        service.delete(mem["id"])
                        deleted_count += 1

                    # SeCom 模式：合并原始对话，将摘要存入 metadata
                    if self.merge_summary_only:
                        # 合并所有原始对话（text 字段）
                        merged_original_texts = []
                        for mem in similar_memories:
                            text = mem.get("text", "")
                            if text:
                                merged_original_texts.append(text)

                        merged_text = "\n\n---\n\n".join(merged_original_texts)

                        # 准备 metadata
                        merged_metadata = {
                            "merged_from": [m["id"] for m in similar_memories],
                            "summary": merged_summary,  # 合并后的摘要
                            "segment_count": len(similar_memories),
                        }
                    else:
                        # 默认模式：合并后的文本直接作为 entry
                        merged_text = merged_summary
                        merged_metadata = {"merged_from": [m["id"] for m in similar_memories]}

                    # Insert merged memory (need vector for VectorHashMemoryService)
                    # Use first memory's embedding as the merged embedding
                    merged_embedding = (
                        similar_memories[0].get("embedding") if similar_memories else None
                    )
                    service.insert(
                        entry=merged_text,
                        vector=merged_embedding,
                        metadata=merged_metadata,
                    )
                    merged_count += 1

            except Exception as e:
                # Log error but continue processing
                details = input_data.data.setdefault("errors", [])
                details.append(
                    {
                        "entry_id": entry.get("id", "unknown"),
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
                "processed_entries": len(entries),
            },
        )

    def _retrieve_similar_memories(
        self, service: Any, entry: dict[str, Any], retrieve_count: int
    ) -> list[dict[str, Any]]:
        """Retrieve memories similar to the given entry.

        Args:
            service: Memory service
            entry: Complete entry dict with id, text, embedding, metadata
            retrieve_count: Number of similar memories to retrieve

        Returns:
            List of similar memory entries (让服务返回 top-k，不做阈值过滤)
        """
        # Use embedding directly from entry (no need to query service)
        embedding = entry.get("embedding")
        if not embedding:
            return []

        # Search for similar memories (不用 threshold，让服务返回 top-k)
        results = service.retrieve(
            vector=embedding,
            top_k=retrieve_count,
            # 移除 threshold 参数，让服务返回所有 top-k 结果
        )

        return results

    def _merge_memories(self, llm: Any, memories: list[dict[str, Any]]) -> str:
        """Use LLM to merge multiple memories into one.

        Args:
            llm: LLM client
            memories: List of memory entries to merge

        Returns:
            Merged memory text (or summary if merge_summary_only=True)
        """
        # SeCom 模式：仅合并摘要，不合并原文
        if self.merge_summary_only:
            # 提取所有 metadata.summary（如果有）
            summaries = []
            for mem in memories:
                summary = mem.get("metadata", {}).get("summary")
                if summary:
                    summaries.append(summary)
                # 如果没有 summary，回退到使用 text
                elif mem.get("text"):
                    summaries.append(mem.get("text"))

            if summaries:
                # 合并摘要
                summaries_text = "\n".join([f"{i + 1}. {s}" for i, s in enumerate(summaries)])
                prompt = self.merge_prompt.format(memories=summaries_text)
                response = llm.generate(prompt)
                return response.strip()

        # 默认模式：合并完整的 text 字段
        memories_text = "\n".join(
            [f"{i + 1}. {mem.get('text', '')}" for i, mem in enumerate(memories)]
        )

        # Generate merge prompt
        prompt = self.merge_prompt.format(memories=memories_text)

        # Call LLM
        response = llm.generate(prompt)
        return response.strip()
