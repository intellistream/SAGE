"""
Link Evolution Action - Graph edge creation and evolution
==========================================================

Used by: A-Mem, HippoRAG

This action creates and updates edges (links) between memory nodes,
building a knowledge graph structure.

改造说明（A-Mem 对齐）：
- 原先依赖 service.evolve_links 的占位实现，现按 A-Mem 正确实现改为在动作中完成“自动建链”策略（auto_link），并支持 LLM 判定。
- 会读取 YAML 的 `operators.post_insert` 配置：
    - link_policy: "auto_link"
    - knn_k: KNN 检索邻居数
    - similarity_threshold: 过滤阈值（基于服务返回的相似度/距离字段）
    - max_auto_links: 每条新记忆最多自动建立的链接数
    - auto_link_prompt: 决策提示词（直接复用 A-Mem 提示词，要求返回 JSON/数组索引）
- 增加“大模型调用检测”与简洁日志输出，不修改 LLM 调用封装文件。
"""

from typing import Any, Optional

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class LinkEvolutionAction(BasePostInsertAction):
    """Link evolution strategy for graph-based memory systems.

    Implementation logic (based on HippoRAG, A-Mem):
    1. For newly inserted memories, retrieve KNN neighbors
    2. Use LLM to decide which neighbors should be linked (auto_link)
    3. Create bidirectional links via graph memory service

    Config Parameters (YAML operators.post_insert):
        only_on_session_end (bool): Whether to run only at session end (default: False for A-Mem)
        link_policy (str): Link strategy, expects "auto_link" for A-Mem
        knn_k (int): Number of nearest neighbors to consider (default: 10)
        similarity_threshold (float): Threshold to filter neighbors (default: 0.7)
        max_auto_links (int): Max number of links to create per new memory (default: 5)
        auto_link_prompt (str): LLM prompt template with placeholders {new_memory}, {existing_memories}
    """

    def _init_action(self) -> None:
        """Initialize link evolution action configuration."""
        # A-Mem 默认不强制仅在会话结束运行
        self.only_on_session_end = self._get_config("only_on_session_end", False)

        # A-Mem 相关配置
        self.link_policy = self._get_config("link_policy", "auto_link")
        self.knn_k = int(self._get_config("knn_k", 10) or 10)
        self.similarity_threshold = float(self._get_config("similarity_threshold", 0.7) or 0.7)
        self.max_auto_links = int(self._get_config("max_auto_links", 5) or 5)
        self.auto_link_prompt = self._get_config("auto_link_prompt", "")

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostInsertOutput:
        """Execute link evolution action (A-Mem style auto_link).

        Args:
            input_data: Input data with session context
            service: Memory service (must support graph operations)
            llm: LLM client (optional, required for auto_link prompt)

        Returns:
            PostInsertOutput with edge creation statistics
        """
        # 0) 进入动作的即时日志
        try:
            print(
                f"[DEBUG link_evolution] start policy={self.link_policy} only_on_session_end={self.only_on_session_end} is_session_end={input_data.is_session_end}"
            )
        except Exception:
            pass

        # 1) 是否跳过执行（仅在会话结束时运行）
        if self.only_on_session_end and not input_data.is_session_end:
            print("[DEBUG link_evolution] skipped reason=not_session_end only_on_session_end=True")
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                    "message": "Link evolution only runs at session end",
                },
            )

        # 2) 策略检查（仅实现 A-Mem 的 auto_link）
        if self.link_policy != "auto_link":
            print(
                f"[DEBUG link_evolution] skipped reason=unsupported_policy link_policy={self.link_policy}"
            )
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "unsupported_policy",
                    "message": f"link_policy '{self.link_policy}' not implemented in this action",
                },
            )

        # 3) 输入校验与准备：获取刚插入的 entries
        entries: list[dict[str, Any]] = (
            input_data.insert_stats.get("entries", [])
            if isinstance(input_data.insert_stats, dict)
            else []
        )
        try:
            print(f"[DEBUG link_evolution] entries_count={len(entries)}")
        except Exception:
            pass
        if not entries:
            print("[DEBUG link_evolution] skipped reason=no_entries insert_stats.entries=0")
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "no_entries",
                    "message": "No inserted entries found for link evolution",
                },
            )

        edges_created_total = 0
        nodes_affected = 0
        llm_called = False
        llm_model = getattr(llm, "model_name", None) if llm is not None else None
        # 更稳妥地获取 LLM 基础地址：优先从 llm.client.base_url，其次回退到 llm.base_url
        if llm is not None:
            try:
                llm_base_url = getattr(getattr(llm, "client", object()), "base_url", None)
            except Exception:
                llm_base_url = getattr(llm, "base_url", None)
        else:
            llm_base_url = None
        llm_error = None

        # 4) 对每个新插入的条目执行 auto_link
        for entry in entries:
            try:
                new_id = entry.get("id")
                new_text = entry.get("text", "")
                new_vec = entry.get("embedding")

                # 4.1 KNN 检索邻居（优先使用向量）
                neighbors = []
                try:
                    if hasattr(service, "retrieve"):
                        # 优先使用向量检索的 vector-only 路径（GraphMemoryService 支持）
                        if new_vec is not None:
                            retrieve_result = service.retrieve(
                                query=None,
                                vector=new_vec,
                                metadata={"method": "vector_only"},
                                top_k=self.knn_k,
                                threshold=self.similarity_threshold,
                            )
                        else:
                            # 回退到文本检索（匹配起始节点的文本）
                            retrieve_result = service.retrieve(
                                query=new_text,
                                vector=None,
                                metadata=None,
                                top_k=self.knn_k,
                            )
                        neighbors = (
                            retrieve_result[: self.knn_k]
                            if isinstance(retrieve_result, list)
                            else []
                        )
                    else:
                        neighbors = []
                except Exception:
                    # 检索失败则跳过此条目
                    continue

                # 检索到的候选为空时打印调试信息并跳过
                if not neighbors:
                    mode = "vector" if new_vec is not None else "text"
                    print(
                        f"[DEBUG link_evolution] no_candidates new_id={new_id} mode={mode} knn_k={self.knn_k} threshold={self.similarity_threshold}"
                    )
                    continue

                # 4.2 相似度阈值过滤（如果服务返回了距离/评分，可在 metadata/score 字段中）
                filtered_neighbors = []
                for idx, item in enumerate(neighbors):
                    meta = item.get("metadata", {}) if isinstance(item, dict) else {}
                    score = item.get("score") or meta.get("score")
                    # 约定：若 score 是相似度（越大越相似），则使用 >= 阈值；若是距离（越小越近），则尝试进行简单判断
                    if score is None:
                        filtered_neighbors.append((idx, item))
                    else:
                        try:
                            score_val = float(score)
                            # 粗略判断：score 大于阈值视为相似度，否则尝试当作距离
                            if score_val >= self.similarity_threshold or score_val <= (
                                1.0 - self.similarity_threshold
                            ):
                                filtered_neighbors.append((idx, item))
                        except Exception:
                            filtered_neighbors.append((idx, item))

                # 4.3 构造 LLM 决策输入
                if llm is None or not self.auto_link_prompt:
                    # 无 LLM 或无提示词：退化为前 max_auto_links 的直接链接
                    print(
                        f"[DEBUG link_evolution] llm_skipped new_id={new_id} cause={'no_llm' if llm is None else 'no_prompt'}"
                    )
                    selected = [idx for idx, _ in filtered_neighbors[: self.max_auto_links]]
                else:
                    try:
                        existing_memories_str = ""
                        for i, (_, nb) in enumerate(filtered_neighbors):
                            nb_text = nb.get("text", "") if isinstance(nb, dict) else str(nb)
                            nb_meta = nb.get("metadata", {}) if isinstance(nb, dict) else {}
                            ctx = nb_meta.get("context", "")
                            kws = nb_meta.get("keywords", [])
                            tags = nb_meta.get("tags", [])
                            existing_memories_str += (
                                f"[{i}] context:{ctx} keywords:{kws} tags:{tags} text:{nb_text}\n"
                            )

                        # 使用安全填充，避免模板中的 JSON 花括号触发 str.format 的 KeyError
                        prompt = self._fill_prompt_safe(
                            self.auto_link_prompt,
                            new_text,
                            existing_memories_str,
                            max_links=self.max_auto_links,
                        )
                        # 要求返回 JSON（优先）或纯数组，例如 {"links": [0,2]} 或 [0,2]
                        result_obj = llm.generate_json(prompt, default={})
                        llm_called = True

                        # 解析输出
                        import json

                        selected: list[int] = []
                        try:
                            parsed = result_obj
                            if isinstance(parsed, str):
                                parsed = json.loads(parsed)
                            if (
                                isinstance(parsed, dict)
                                and "links" in parsed
                                and isinstance(parsed["links"], list)
                            ):
                                selected = [int(x) for x in parsed["links"]][: self.max_auto_links]
                            elif isinstance(parsed, list):
                                selected = [int(x) for x in parsed][: self.max_auto_links]
                            else:
                                # 回退：尝试从字符串中抓取索引
                                import re

                                nums = re.findall(r"\d+", str(result_obj))
                                selected = [int(x) for x in nums][: self.max_auto_links]
                        except Exception:
                            # 回退：尝试从字符串中抓取索引
                            import re

                            nums = re.findall(r"\d+", str(result_obj))
                            selected = [int(x) for x in nums][: self.max_auto_links]

                        # 简洁日志
                        print(
                            f"[LinkEvolution] LLM called={llm_called} model={llm_model} base={llm_base_url} new_id={new_id} selected={selected}"
                        )
                    except Exception as e:
                        # 记录并打印 LLM 错误，随后回退为 Top-N 直接建链
                        llm_error = str(e)
                        try:
                            print(
                                f"[DEBUG link_evolution] llm_error new_id={new_id} error={llm_error} fallback_topN={self.max_auto_links}"
                            )
                        except Exception:
                            pass
                        selected = [idx for idx, _ in filtered_neighbors[: self.max_auto_links]]

                # 4.4 建立链接（严格使用 GraphMemoryService 的 add_edge）
                created_links = 0
                for sel in selected:
                    if sel < 0 or sel >= len(filtered_neighbors):
                        continue
                    nb_item = filtered_neighbors[sel][1]
                    nb_meta = nb_item.get("metadata", {}) if isinstance(nb_item, dict) else {}
                    # GraphMemoryService 返回的统一字段包含 node_id/entry_id
                    nb_id = (
                        nb_item.get("node_id")
                        or nb_item.get("entry_id")
                        or nb_meta.get("node_id")
                        or nb_meta.get("id")
                    )
                    if not nb_id or not new_id:
                        continue

                    # 使用 GraphMemoryService 提供的 add_edge（其内部根据 link_policy 决定是否双向）
                    try:
                        if hasattr(service, "add_edge"):
                            service.add_edge(new_id, nb_id, weight=1.0)
                            created_links += 1
                    except Exception:
                        # 单条失败不影响其他链接
                        continue

                if created_links > 0:
                    try:
                        print(
                            f"[DEBUG link_evolution] edges_created new_id={new_id} count={created_links}"
                        )
                    except Exception:
                        pass
                    edges_created_total += created_links
                    nodes_affected += 1

            except Exception:
                # 单条失败不影响总体
                continue

        # 5) 汇总结果
        details = {
            "edges_created": edges_created_total,
            "edges_updated": 0,
            "nodes_affected": nodes_affected,
            "link_policy": self.link_policy,
            "knn_k": self.knn_k,
            "similarity_threshold": self.similarity_threshold,
            "max_auto_links": self.max_auto_links,
            "llm_called": llm_called,
            "llm_model": llm_model,
            "llm_base_url": llm_base_url,
        }
        if llm_error:
            details["llm_error"] = llm_error

        return PostInsertOutput(
            success=True,
            action="link_evolution",
            details=details,
        )

    def _fill_prompt_safe(
        self,
        template: str,
        new_memory_text: str,
        existing_memories_block: str,
        *,
        max_links: int | None = None,
    ) -> str:
        """安全地填充 auto_link_prompt，避免 JSON 花括号被 str.format 误解析。

        仅替换已知占位符：{new_memory}、{existing_memories}、{max_auto_links}。
        其他花括号（例如示例 JSON）保持原样。
        """
        p = template or ""
        if "{new_memory}" in p:
            p = p.replace("{new_memory}", new_memory_text)
        if "{existing_memories}" in p:
            p = p.replace("{existing_memories}", existing_memories_block)
        if max_links is not None and "{max_auto_links}" in p:
            p = p.replace("{max_auto_links}", str(int(max_links)))
        return p
