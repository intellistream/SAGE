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
        # 控制调试输出：当为 True 时，仅输出 LLM 调用汇总行（其余调试行静默）
        self.debug_summary_only = bool(self._get_config("debug_summary_only", False))
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
        # 入口级调试：打印是否有 LLM 以及待处理条目数（summary_only 时静默）
        if not self.debug_summary_only:
            try:
                entries_preview = input_data.insert_stats.get("entries", [])
                print(
                    f"[DEBUG CRUD] start processed_candidate_entries={len(entries_preview)} has_llm={bool(llm is not None)} top_k={self.top_k}"
                )
            except Exception:
                pass

        if llm is None:
            if not self.debug_summary_only:
                try:
                    print("[DEBUG CRUD] llm_required but missing; skipping CRUD decision")
                except Exception:
                    pass
            return PostInsertOutput(
                success=False,
                action="crud",
                details={"error": "LLM client required for CRUD decision"},
            )

        # Extract complete entries from insert stats (includes embedding)
        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="crud",
                details={"message": "No entries to process"},
            )

        operations = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NOOP": 0}

        # Process each newly inserted memory
        for new_memory in entries:
            try:
                # 预调试：打印条目基本信息（summary_only 时静默）
                if not self.debug_summary_only:
                    try:
                        nm_id = new_memory.get("id", "unknown")
                        has_emb = (
                            "embedding" in new_memory and new_memory.get("embedding") is not None
                        )
                        text_len = len(new_memory.get("text", ""))
                        print(
                            f"[DEBUG CRUD] entry id={nm_id} has_embedding={has_emb} text_len={text_len} retrieving_similar top_k={self.top_k}"
                        )
                    except Exception:
                        pass

                # new_memory already contains: id, text, embedding, metadata
                # No need to query service.get_entry()

                # Retrieve similar existing memories
                import time

                _t0 = time.time()
                similar_memories = self._retrieve_similar_memories(service, new_memory, self.top_k)
                _elapsed = (time.time() - _t0) * 1000.0
                if not self.debug_summary_only:
                    try:
                        print(
                            f"[DEBUG CRUD] retrieved_similar count={len(similar_memories)} elapsed={_elapsed:.1f}ms id={new_memory.get('id', 'unknown')}"
                        )
                    except Exception:
                        pass

                # Use LLM to decide CRUD operation
                if not self.debug_summary_only:
                    try:
                        print(
                            f"[DEBUG CRUD] calling_llm_for_decision id={new_memory.get('id', 'unknown')} similar={len(similar_memories)}"
                        )
                    except Exception:
                        pass
                decision = self._make_crud_decision(llm, new_memory, similar_memories)

                # Execute the decision
                self._execute_crud_operation(service, decision, new_memory)
                operations[decision["action"]] += 1

                if not self.debug_summary_only:
                    try:
                        print(
                            f"[DEBUG CRUD] executed action={decision.get('action', '-')} id={new_memory.get('id', 'unknown')}"
                        )
                    except Exception:
                        pass

            except Exception as e:
                # 显式打印失败原因，避免静默（summary_only 时静默）
                if not self.debug_summary_only:
                    try:
                        print(
                            f"[DEBUG CRUD] decision_failed id={new_memory.get('id', 'unknown')} error={type(e).__name__}: {e}"
                        )
                    except Exception:
                        pass
                details = input_data.data.setdefault("errors", [])
                details.append(
                    {
                        "entry_id": new_memory.get("id", "unknown"),
                        "action": "crud",
                        "error": str(e),
                    }
                )

        return PostInsertOutput(
            success=True,
            action="crud",
            details={
                "operations": operations,
                "processed_entries": len(entries),
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

        # 与 SAGE 现有服务接口保持一致：使用 retrieve(vector=..., top_k=...)
        results = service.retrieve(
            vector=new_memory["embedding"],
            top_k=top_k,
        )

        # 规范化返回的 id 字段：兼容不同服务键名（id|entry_id|node_id）
        normalized = []
        for r in results:
            rid = r.get("id") or r.get("entry_id") or r.get("node_id")
            if rid is not None:
                r["id"] = rid
            normalized.append(r)

        # 过滤掉新插入的自身 id（若服务未支持 exclude_ids）
        new_id = new_memory.get("id")
        if new_id is not None:
            normalized = [r for r in normalized if r.get("id") != new_id]
        return normalized

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

        # Generate decision prompt (safe fill to avoid str.format interpreting JSON braces)
        prompt_tmpl = self.decision_prompt or ""
        prompt = prompt_tmpl.replace("{new_memory}", new_memory.get("text", "")).replace(
            "{existing_memories}", existing_text
        )

        # Call LLM (prefer JSON mode if available)
        llm_model = None
        llm_base_url = None
        try:
            try:
                llm_model = getattr(llm, "model_name", None)
            except Exception:
                llm_model = None
            try:
                llm_base_url = getattr(getattr(llm, "client", object()), "base_url", None)
            except Exception:
                llm_base_url = None

            if hasattr(llm, "generate_json"):
                response = llm.generate_json(
                    prompt,
                    default={
                        "action": "ADD",
                        "to_delete": [],
                        "reason": "insufficient evidence",
                    },
                )
            else:
                response = llm.generate(prompt)
        except Exception as e:
            # Debug: surface LLM call failure but keep original error propagation
            try:
                print(
                    f"[DEBUG CRUD] LLM called=False error={type(e).__name__}: {e} model={llm_model or '-'} base={llm_base_url or '-'} similar={len(similar_memories)}"
                )
            except Exception:
                pass
            raise

        # Parse JSON response
        try:
            # 兼容 response 为 dict/list 的情况
            if isinstance(response, dict):
                decision = response
            else:
                # 若不是字符串，尽量转为字符串；失败则走解析失败兜底
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                decision = json.loads(response)
            # 兼容不同字段：支持 target_id 或 to_delete 列表
            action = decision.get("action")
            if action not in ["ADD", "UPDATE", "DELETE", "NOOP"]:
                action = "ADD"
            decision["action"] = action

            # 规范化字段
            if "to_delete" in decision and isinstance(decision["to_delete"], list):
                # 保留原有列表
                pass
            elif decision.get("target_id"):
                decision["to_delete"] = [decision["target_id"]]
            else:
                decision["to_delete"] = []

            # 约束 to_delete 必须来自相似集的有效 ID；否则降级
            valid_ids = {m.get("id") for m in similar_memories if m.get("id")}
            decision["to_delete"] = [tid for tid in decision["to_delete"] if tid in valid_ids]
            if decision["action"] in ["UPDATE", "DELETE"] and not decision["to_delete"]:
                # 无有效目标则不执行破坏性操作，转为 NOOP
                decision["action"] = "NOOP"

            # Debug: successful LLM call
            try:
                print(
                    f"[DEBUG CRUD] LLM called=True action={decision.get('action', '-')} model={llm_model or '-'} base={llm_base_url or '-'} similar={len(similar_memories)}"
                )
            except Exception:
                pass
            return decision
        except json.JSONDecodeError:
            # Fallback decision
            fallback = {"action": "ADD", "to_delete": [], "reason": "Failed to parse LLM response"}
            try:
                print(
                    f"[DEBUG CRUD] LLM called=True action=ADD reason=parse_error model={llm_model or '-'} base={llm_base_url or '-'} similar={len(similar_memories)}"
                )
            except Exception:
                pass
            return fallback
        except Exception as e:
            # 更通用的解析异常兜底（例如 TypeError）
            fallback = {
                "action": "ADD",
                "to_delete": [],
                "reason": f"Exception while parsing: {type(e).__name__}: {e}",
            }
            try:
                print(
                    f"[DEBUG CRUD] LLM called=True action=ADD reason=parse_exception model={llm_model or '-'} base={llm_base_url or '-'} similar={len(similar_memories)}"
                )
            except Exception:
                pass
            return fallback

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
            # 新记忆保留，已有不变（成功静默）
            return

        elif action == "UPDATE":
            # 删除旧的（to_delete），保留新记忆
            for tid in decision.get("to_delete", []):
                try:
                    ok = bool(service.delete(tid))
                    if not ok:
                        try:
                            print(
                                f"[WARN CRUD] delete_failed action=UPDATE id={tid}: service returned False"
                            )
                        except Exception:
                            pass
                except Exception as e:
                    # 失败时输出一条告警，但不中断流程
                    try:
                        print(
                            f"[WARN CRUD] delete_failed action=UPDATE id={tid} error={type(e).__name__}: {e}"
                        )
                    except Exception:
                        pass
            return

        elif action == "DELETE":
            # 删除旧的（to_delete），保留新记忆（按 Mem0ᵍ 提示）
            for tid in decision.get("to_delete", []):
                try:
                    ok = bool(service.delete(tid))
                    if not ok:
                        try:
                            print(
                                f"[WARN CRUD] delete_failed action=DELETE id={tid}: service returned False"
                            )
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        print(
                            f"[WARN CRUD] delete_failed action=DELETE id={tid} error={type(e).__name__}: {e}"
                        )
                    except Exception:
                        pass
            return

        elif action == "NOOP":
            # 冗余：删除新插入的这一条，避免重复
            try:
                ok = bool(service.delete(new_memory.get("id")))
                if not ok:
                    try:
                        print(
                            f"[WARN CRUD] delete_failed action=NOOP id={new_memory.get('id', 'unknown')}: service returned False"
                        )
                    except Exception:
                        pass
            except Exception as e:
                try:
                    print(
                        f"[WARN CRUD] delete_failed action=NOOP id={new_memory.get('id', 'unknown')} error={type(e).__name__}: {e}"
                    )
                except Exception:
                    pass
            return
