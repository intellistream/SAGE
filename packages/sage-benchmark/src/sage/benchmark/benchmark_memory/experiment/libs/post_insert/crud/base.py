"""
CRUD Action - Memory CRUD decision making
==========================================

Used by: Mem0, Mem0ᵍ

This action analyzes new memories against existing ones and decides
whether to ADD, UPDATE, DELETE, or do NOOP (no operation).
"""

import json
from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class CRUDAction(BasePostInsertAction):
    """CRUD decision-making strategy.

    Implementation logic (based on Mem0):
    1. Retrieve similar existing memories
    2. Use LLM to decide operation: ADD/UPDATE/DELETE/NOOP
    3. Execute the decided operation

    Config Parameters:
        decision_prompt (str): LLM prompt template for CRUD decision
        top_k (int): Number of similar memories to retrieve (default: 5)
    """

    def _init_action(self) -> None:
        """Initialize CRUD action configuration."""
        self.top_k = self._get_config("top_k", 5)
        self.decision_prompt = self._get_config(
            "decision_prompt",
            """分析新记忆与现有记忆的关系，决定操作类型。
新记忆：{new_memory}
现有相似记忆：{existing_memories}
请输出 JSON：{{"action": "ADD|UPDATE|DELETE|NOOP", "target_id": "...", "reason": "..."}}""",
        )

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute CRUD decision action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service for retrieval and CRUD operations
            llm: LLM client for decision making

        Returns:
            PostInsertOutput with CRUD operation statistics
        """
        if llm is None:
            return PostInsertOutput(
                success=False,
                action="crud",
                details={"error": "LLM client required for CRUD decision"},
            )

        # Extract entry IDs
        entry_ids = input_data.insert_stats.get("entry_ids", [])
        if not entry_ids:
            return PostInsertOutput(
                success=True,
                action="crud",
                details={"message": "No entries to process"},
            )

        operations = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NOOP": 0}

        # Process each newly inserted memory
        for entry_id in entry_ids:
            try:
                # Get the new memory
                new_memory = service.get_entry(entry_id)
                if not new_memory:
                    continue

                # Retrieve similar existing memories
                similar_memories = self._retrieve_similar_memories(service, new_memory, self.top_k)

                # Use LLM to decide CRUD operation
                decision = self._make_crud_decision(llm, new_memory, similar_memories)

                # Execute the decision
                self._execute_crud_operation(service, decision, new_memory)
                operations[decision["action"]] += 1

            except Exception as e:
                details = input_data.data.setdefault("errors", [])
                details.append(
                    {
                        "entry_id": entry_id,
                        "action": "crud",
                        "error": str(e),
                    }
                )

        return PostInsertOutput(
            success=True,
            action="crud",
            details={
                "operations": operations,
                "processed_entries": len(entry_ids),
            },
        )

    def _retrieve_similar_memories(
        self, service: Any, new_memory: dict[str, Any], top_k: int
    ) -> list[dict[str, Any]]:
        """Retrieve similar existing memories.

        Args:
            service: Memory service
            new_memory: New memory entry
            top_k: Number of results to retrieve

        Returns:
            List of similar memory entries
        """
        if "embedding" not in new_memory:
            return []

        results = service.search(
            query_embedding=new_memory["embedding"],
            top_k=top_k,
            exclude_ids=[new_memory.get("id")],
        )

        return results

    def _make_crud_decision(
        self, llm: Any, new_memory: dict[str, Any], similar_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Use LLM to make CRUD decision.

        Args:
            llm: LLM client
            new_memory: New memory entry
            similar_memories: List of similar existing memories

        Returns:
            Decision dict with keys: action, target_id, reason
        """
        # Format existing memories
        existing_text = (
            "\n".join(
                [
                    f"{i + 1}. [{mem.get('id', 'unknown')}] {mem.get('text', '')}"
                    for i, mem in enumerate(similar_memories)
                ]
            )
            if similar_memories
            else "无"
        )

        # Generate decision prompt
        prompt = self.decision_prompt.format(
            new_memory=new_memory.get("text", ""), existing_memories=existing_text
        )

        # Call LLM
        response = llm.generate(prompt)

        # Parse JSON response
        try:
            decision = json.loads(response)
            # Validate action
            if decision.get("action") not in ["ADD", "UPDATE", "DELETE", "NOOP"]:
                decision["action"] = "ADD"  # Fallback to ADD
            return decision
        except json.JSONDecodeError:
            # Fallback decision
            return {"action": "ADD", "target_id": None, "reason": "Failed to parse LLM response"}

    def _execute_crud_operation(
        self, service: Any, decision: dict[str, Any], new_memory: dict[str, Any]
    ) -> None:
        """Execute the CRUD operation based on decision.

        Args:
            service: Memory service
            decision: CRUD decision
            new_memory: New memory entry
        """
        action = decision["action"]

        if action == "ADD":
            # Already inserted, do nothing
            pass
        elif action == "UPDATE":
            # Update existing memory with new content
            target_id = decision.get("target_id")
            if target_id:
                service.update_entry(target_id, text=new_memory.get("text"))
                # Delete the newly inserted one (it was a duplicate)
                service.delete_entry(new_memory.get("id"))
        elif action == "DELETE":
            # Delete the newly inserted memory (it's redundant or incorrect)
            service.delete_entry(new_memory.get("id"))
        elif action == "NOOP":
            # Do nothing
            pass
