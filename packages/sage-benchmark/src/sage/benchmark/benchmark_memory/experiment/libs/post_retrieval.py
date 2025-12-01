"""后检索处理模块 - 在记忆检索后的后处理（可选）

R3 重构：修正职责边界，确保不实现应属于记忆服务的功能。

职责边界（R3 规范）：
- 检索结果后处理（rerank, filter, augment, compress, format）
- 允许多次查询记忆服务以拼接完整 prompt
- 不自己计算 embedding（由服务完成）
- 不从 data 读取多个记忆源（只与单一服务交互）
- filter 不支持 dedup（应由服务返回去重结果）
- merge 通过多次调用服务实现，而非从 data 读取多源

当前支持的 action：
- none: 仅做基础格式化（保持向后兼容）
- rerank: 对检索结果进行重排序（语义 / 时间衰减 / PPR / 加权 / cross-encoder）
- filter: 结果筛选（token budget / 阈值 / top-k / llm）
- merge: 多次查询服务合并（link_expand / multi_query）
- augment: 结果增强（context / metadata / temporal）
- compress: 结果压缩（extractive）
- format: 最终格式化输出（template / structured / chat / xml）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.common.core import MapFunction


@dataclass
class MemoryItem:
    """标准化后的记忆条目结构

    统一封装 memory_service 返回的单条结果，方便后续在不同策略中重用。
    """

    text: str
    score: Optional[float]
    metadata: dict[str, Any]
    original_index: int

    def get_timestamp(self, field: str = "timestamp") -> Optional[datetime]:
        value = self.metadata.get(field)
        if value is None:
            return None

        # 已经是 datetime
        if isinstance(value, datetime):
            return value

        # 常见字符串格式
        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    return dt
                except Exception:  # noqa: BLE001
                    continue

        # 时间戳（秒）
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=UTC)
            except Exception:  # noqa: BLE001
                return None

        return None


class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子

    职责边界：
    - 检索结果后处理（rerank, filter, augment, compress, format）
    - 允许多次查询记忆服务以拼接完整 prompt
    - 构建最终 history_text

    约束（R3 重构）：
    - 不自己计算 embedding（由服务完成）
    - 不从 data 读取多个记忆源（只与单一服务交互）
    - filter 不再支持 dedup（应由服务返回去重结果）
    - merge 通过多次调用服务实现，而非从 data 读取多源

    当前实现：
    - 默认 `none` 行为不变，仅做基础 history_text 拼接
    - 在此基础上按 action 追加/改写 memory_data，并最终统一生成 history_text
    """

    def __init__(self, config):  # noqa: D401
        """初始化 PostRetrieval

        Args:
            config: RuntimeConfig 对象
        """

        super().__init__()
        self.config = config
        self.action = get_required_config(self.config, "operators.post_retrieval.action")

        # 对话格式化 Prompt（阶段一）
        self.conversation_format_prompt = config.get(
            "operators.post_retrieval.conversation_format_prompt",
            (
                "Below is a conversation between two people. "
                "The conversation takes place over multiple days and the date of each "
                "conversation is written at the beginning of the conversation."
            ),
        )

        # 服务名称（用于多次查询）
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 根据 action 初始化特定配置
        self._init_for_action()

    def _init_for_action(self) -> None:
        """根据 action 类型初始化对应配置"""
        cfg_prefix = "operators.post_retrieval"

        if self.action == "rerank":
            # rerank 配置
            self.rerank_type: str = get_required_config(
                self.config, f"{cfg_prefix}.rerank_type", "action=rerank"
            )
            self.semantic_model_name: str | None = self.config.get(f"{cfg_prefix}.rerank_model")
            self.cross_encoder_model: str | None = self.config.get(
                f"{cfg_prefix}.cross_encoder_model"
            )
            self.cross_encoder_batch_size: int = self.config.get(f"{cfg_prefix}.batch_size", 32)
            self.time_decay_rate: float = float(
                get_required_config(
                    self.config, f"{cfg_prefix}.time_decay_rate", "rerank_type=time_weighted"
                ),
            )
            self.time_field: str = self.config.get(f"{cfg_prefix}.time_field", "timestamp")
            self.ppr_damping_factor: float = float(
                self.config.get(f"{cfg_prefix}.damping_factor", 0.5)
            )
            self.ppr_max_iterations: int = int(self.config.get(f"{cfg_prefix}.max_iterations", 100))
            self.ppr_convergence_threshold: float = float(
                self.config.get(f"{cfg_prefix}.convergence_threshold", 1e-6)
            )
            self.ppr_personalization_nodes: str = self.config.get(
                f"{cfg_prefix}.personalization_nodes", "query_entities"
            )
            self.weighted_factors: list[dict[str, Any]] = self.config.get(f"{cfg_prefix}.factors")
            if self.rerank_type == "weighted" and not self.weighted_factors:
                raise ValueError(
                    "缺少必需配置: operators.post_retrieval.factors (rerank_type=weighted)"
                )
            self.rerank_top_k: int | None = self.config.get(f"{cfg_prefix}.top_k")
            self.rerank_score_field: str = self.config.get(
                f"{cfg_prefix}.score_field", "rerank_score"
            )

        elif self.action == "filter":
            # filter 配置（R3: 移除 dedup，由服务返回去重结果）
            self.filter_type = get_required_config(
                self.config, f"{cfg_prefix}.filter_type", "action=filter"
            )
            self.token_budget = get_required_config(
                self.config, f"{cfg_prefix}.token_budget", "filter_type=token_budget"
            )
            self.token_counter = self.config.get(f"{cfg_prefix}.token_counter", "char")
            self.overflow_strategy = self.config.get(f"{cfg_prefix}.overflow_strategy", "truncate")
            self.score_threshold = get_required_config(
                self.config, f"{cfg_prefix}.score_threshold", "filter_type=threshold"
            )
            self.top_k = get_required_config(self.config, f"{cfg_prefix}.k", "filter_type=top_k")

        elif self.action == "merge":
            # merge 配置（R3 重构：基于多次查询服务，而非从 data 读取多源）
            self.merge_type = get_required_config(
                self.config, f"{cfg_prefix}.merge_type", "action=merge"
            )
            # link_expand 专用配置
            self.expand_top_n = self.config.get(f"{cfg_prefix}.expand_top_n", 5)
            self.max_depth = self.config.get(f"{cfg_prefix}.max_depth", 1)
            # multi_query 专用配置
            self.secondary_queries = self.config.get(f"{cfg_prefix}.secondary_queries", [])

        elif self.action == "augment":
            # augment 配置
            self.augment_type = get_required_config(
                self.config, f"{cfg_prefix}.augment_type", "action=augment"
            )
            self.augment_template = self.config.get(f"{cfg_prefix}.augment_template", "")
            self.augment_fields = self.config.get(f"{cfg_prefix}.augment_fields", [])
            self.time_field = self.config.get(f"{cfg_prefix}.time_field", "timestamp")

        elif self.action == "compress":
            # compress 配置
            self.compress_type = get_required_config(
                self.config, f"{cfg_prefix}.compress_type", "action=compress"
            )
            self.compress_ratio = get_required_config(
                self.config, f"{cfg_prefix}.compress_ratio", "action=compress"
            )
            self.compress_max_length = self.config.get(f"{cfg_prefix}.compress_max_length", 512)

        elif self.action == "format":
            # format 配置
            self.format_type = get_required_config(
                self.config, f"{cfg_prefix}.format_type", "action=format"
            )
            self.format_template = get_required_config(
                self.config, f"{cfg_prefix}.template", "format_type=template"
            )
            self.memory_template = self.config.get(f"{cfg_prefix}.memory_template", "- {{text}}")
            self.format_structure = get_required_config(
                self.config, f"{cfg_prefix}.structure", "format_type=structured"
            )
            self.role_mapping = self.config.get(f"{cfg_prefix}.role_mapping", {})
            self.include_timestamps = self.config.get(f"{cfg_prefix}.include_timestamps", False)
            self.xml_tags = self.config.get(f"{cfg_prefix}.xml_tags", {})

    # =============================================================
    # 公共入口
    # =============================================================

    def execute(self, data):  # noqa: D401
        """执行后处理并生成 `history_text`。

        data 约定：
        - `memory_data`: List[{"text": str, "score"?: float, "metadata"?: dict}]
        - `question`, `query_embedding` 等字段由上游决定
        """

        if not data:
            return data

        action = self.action or "none"

        if action == "none":
            processed = data
        elif action == "rerank":
            processed = self._execute_rerank(data)
        elif action == "filter":
            processed = self._execute_filter_action(data)
        elif action == "merge":
            processed = self._execute_merge_action(data)
        elif action == "augment":
            processed = self._execute_augment_action(data)
        elif action == "compress":
            processed = self._execute_compress_action(data)
        elif action == "format":
            # format action 直接设置 history_text，不需要再调用 _format_dialog_history
            return self._execute_format_action(data)
        else:
            # 其他 action 尚未实现时，保持向后兼容：仅做基础格式化
            print("PostRetrieval action '%s' not implemented, fallback to 'none'", action)
            processed = data

        # 无论如何，最终都生成 history_text 供下游 LLM 使用
        return self._format_dialog_history(processed)

    # =============================================================
    # Action 包装方法：从 data 提取 memory_data，调用对应 _execute_*，再放回 data
    # =============================================================

    def _execute_filter_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """filter action 包装：提取、过滤、放回。"""
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)
        filtered_items = self._execute_filter(items, data)
        data["memory_data"] = self._convert_from_memory_items(filtered_items)
        return self._format_dialog_history(data)

    def _execute_merge_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """merge action 包装：提取、合并、放回。"""
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)
        merged_items = self._execute_merge(items, data)
        data["memory_data"] = self._convert_from_memory_items(merged_items)
        return self._format_dialog_history(data)

    def _execute_augment_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """augment action 包装：提取、增强、放回。"""
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)
        augmented_items = self._execute_augment(items, data)
        data["memory_data"] = self._convert_from_memory_items(augmented_items)
        return self._format_dialog_history(data)

    def _execute_compress_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """compress action 包装：提取、压缩、放回。"""
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)
        compressed_items = self._execute_compress(items, data)
        data["memory_data"] = self._convert_from_memory_items(compressed_items)
        return self._format_dialog_history(data)

    # =============================================================
    # 基础格式化：保持原有行为
    # =============================================================

    def _convert_to_memory_items(self, memory_data: list[dict[str, Any]]) -> list[MemoryItem]:
        """将 memory_data 标准化为 MemoryItem list。"""
        items: list[MemoryItem] = []
        for idx, entry in enumerate(memory_data):
            if not isinstance(entry, dict):
                continue
            text = entry.get("text", "")
            if not text:
                continue
            score = entry.get("score")
            metadata = entry.get("metadata") or {}
            items.append(MemoryItem(text=text, score=score, metadata=metadata, original_index=idx))
        return items

    def _convert_from_memory_items(self, items: list[MemoryItem]) -> list[dict[str, Any]]:
        """将 MemoryItem list 转换回 dict list。"""
        result: list[dict[str, Any]] = []
        for item in items:
            result.append(
                {
                    "text": item.text,
                    "score": item.score,
                    "metadata": item.metadata,
                }
            )
        return result

    def _format_dialog_history(self, data: dict[str, Any]) -> dict[str, Any]:
        """格式化对话历史为结构化文本（阶段一：Prompt 拼接）。"""

        memory_data = data.get("memory_data", []) or []

        history_parts: list[str] = []
        if self.conversation_format_prompt:
            history_parts.append(self.conversation_format_prompt.strip())

        for entry in memory_data:
            text = entry.get("text", "") if isinstance(entry, dict) else ""
            if text:
                history_parts.append(text)

        history_text = "\n".join(history_parts) if history_parts else ""
        data["history_text"] = history_text
        return data

    # =============================================================
    # rerank: 结果重排序
    # =============================================================

    def _execute_rerank(self, data: dict[str, Any]) -> dict[str, Any]:
        """根据 rerank_type 对 memory_data 进行重排序。"""

        memory_data_raw = data.get("memory_data", []) or []
        if not memory_data_raw:
            return data

        # 标准化为 MemoryItem
        items: list[MemoryItem] = []
        for idx, entry in enumerate(memory_data_raw):
            if not isinstance(entry, dict):
                continue
            text = entry.get("text", "")
            if not text:
                continue
            score = entry.get("score")
            metadata = entry.get("metadata") or {}
            items.append(MemoryItem(text=text, score=score, metadata=metadata, original_index=idx))

        if not items:
            return data

        rerank_type = (self.rerank_type or "weighted").lower()

        if rerank_type == "semantic":
            scored = self._rerank_semantic(items, data)
        elif rerank_type == "time_weighted":
            scored = self._rerank_time_weighted(items, data)
        elif rerank_type == "ppr":
            scored = self._rerank_ppr_placeholder(items, data)
        elif rerank_type == "weighted":
            scored = self._rerank_weighted(items, data)
        elif rerank_type == "cross_encoder":
            scored = self._rerank_cross_encoder_placeholder(items, data)
        else:
            print("Unknown rerank_type '%s', skip rerank", rerank_type)
            return data

        # 按分数排序
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)

        if self.rerank_top_k is not None and self.rerank_top_k > 0:
            scored_sorted = scored_sorted[: self.rerank_top_k]

        # 回写到 memory_data（保持原有结构）
        new_memory_data: list[dict[str, Any]] = []
        for item, score in scored_sorted:
            original = memory_data_raw[item.original_index]
            if isinstance(original, dict):
                original = dict(original)
                original.setdefault("metadata", {})[self.rerank_score_field] = float(score)
                new_memory_data.append(original)

        data["memory_data"] = new_memory_data
        return data

    # ---------------------- semantic ----------------------

    def _rerank_semantic(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[tuple[MemoryItem, float]]:
        """基于 embedding 相似度的语义重排。

        R3 重构：只使用上游已提供的 query_embedding 和 item.metadata 中的 embedding。
        如果上游未提供 embedding，则回退到使用已有 score。
        """

        query_vec = data.get("query_embedding")
        if query_vec is None:
            print(
                "Semantic rerank: query_embedding not provided by upstream, "
                "fallback to original score"
            )
            return [(item, item.score or 0.0) for item in items]

        import math

        def cosine(a: list[float], b: list[float]) -> float:
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            if na == 0.0 or nb == 0.0:
                return 0.0
            return dot / (na * nb)

        scored: list[tuple[MemoryItem, float]] = []
        for item in items:
            # 尝试从 metadata 中获取 embedding（服务应在 retrieve 时返回）
            item_emb = item.metadata.get("embedding")
            if item_emb is not None:
                sim = cosine(query_vec, item_emb)
                scored.append((item, float(sim)))
            else:
                # 没有 embedding，使用已有 score
                scored.append((item, item.score or 0.0))

        return scored

    # ------------------- time_weighted --------------------

    def _rerank_time_weighted(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[tuple[MemoryItem, float]]:
        """时间衰减 + 原相关性组合（受 LD-Agent 启发）。"""

        now = datetime.now(UTC)
        decay_rate = float(self.time_decay_rate)

        scored: list[tuple[MemoryItem, float]] = []
        for item in items:
            ts = item.get_timestamp(self.time_field)
            if ts is None:
                recency = 1.0
            else:
                hours = max((now - ts).total_seconds() / 3600.0, 0.0)
                recency = (
                    pow(0.995, hours)
                    if decay_rate <= 0
                    else pow(1.0 - min(decay_rate, 0.99), hours)
                )

            base_score = item.score if item.score is not None else 1.0
            scored.append((item, float(recency * base_score)))

        return scored

    # ------------------------ ppr ------------------------

    def _rerank_ppr_placeholder(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[tuple[MemoryItem, float]]:
        """PPR 占位实现。

        真实 PPR 需要图存储支持，这里仅保留接口并返回原顺序，
        方便未来与 HippoRAG 图后端集成时无缝替换。
        """

        print("PPR rerank is not wired to a graph backend yet, keep original order")
        return [(item, item.score or 0.0) for item in items]

    # ---------------------- weighted ----------------------

    def _rerank_weighted(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[tuple[MemoryItem, float]]:
        """多因子加权重排（参考 Generative Agents 的 recency/importance/relevance）。

        R3 重构：relevance 只使用已有 score，不自己计算 embedding。
        """

        now = datetime.now(UTC)

        def get_relevance(item: MemoryItem) -> float:
            # R3: 只使用已有 score，不计算 embedding
            if item.score is not None:
                return float(item.score)
            return 0.0

        def compute_factor_score(item: MemoryItem, factor_cfg: dict[str, Any]) -> float:
            name = (factor_cfg.get("name") or "").lower()

            if name == "recency":
                decay_type = factor_cfg.get("decay_type", "exponential")
                decay_rate = float(factor_cfg.get("decay_rate", 0.995))
                ts = item.get_timestamp(self.time_field)
                if ts is None:
                    return 1.0
                hours = max((now - ts).total_seconds() / 3600.0, 0.0)
                if decay_type == "exponential":
                    return pow(decay_rate, hours)
                return 1.0 / (1.0 + hours)

            if name == "importance":
                field = factor_cfg.get("field", "importance_score")
                raw = item.metadata.get(field)
                try:
                    val = float(raw)
                except Exception:  # noqa: BLE001
                    return 0.0
                return max(min(val / 10.0, 1.0), 0.0)

            if name == "relevance":
                return get_relevance(item)

            # 未知因子默认 0
            return 0.0
            return 0.0

        scored: list[tuple[MemoryItem, float]] = []

        if not self.weighted_factors:
            # 没有配置时退化为 time_weighted 行为
            return self._rerank_time_weighted(items, data)

        for item in items:
            total = 0.0
            for factor in self.weighted_factors:
                weight = float(factor.get("weight", 0.0))
                if weight == 0.0:
                    continue
                val = compute_factor_score(item, factor)
                total += weight * val
            scored.append((item, float(total)))

        return scored

    # ------------------- cross_encoder -------------------

    def _rerank_cross_encoder_placeholder(
        self,
        items: list[MemoryItem],
        data: dict[str, Any],
    ) -> list[tuple[MemoryItem, float]]:
        """cross-encoder 占位实现。

        真正的 cross-encoder 通常需要加载较大的 transformer 模型，
        这里仅保留接口以免引入沉重依赖，默认返回原 score。
        """

        print("cross_encoder rerank is not implemented in benchmark; keep original score")
        return [(item, item.score or 0.0) for item in items]

    # ========================================================================
    # FILTER ACTION
    # ========================================================================

    def _execute_filter(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """filter 执行分发。

        支持的子类型（R3 重构后）：
        - token_budget: 按 token 预算过滤（参考 SCM4LLMs）
        - threshold: 按分数阈值过滤
        - top_k: 取 top-k
        - llm: 占位，由 LLM 判断相关性

        注意：dedup 已移除，应由服务返回去重结果。
        """
        if self.filter_type == "token_budget":
            return self._filter_token_budget(items, data)
        if self.filter_type == "threshold":
            return self._filter_threshold(items, data)
        if self.filter_type == "top_k":
            return self._filter_top_k(items, data)
        if self.filter_type == "llm":
            return self._filter_llm_placeholder(items, data)

        print(f"Unknown filter_type: {self.filter_type}, fallback to threshold")
        return self._filter_threshold(items, data)

    def _filter_token_budget(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """按 token 预算过滤（参考 SCM4LLMs）。

        token_counter:
        - "char": len(text)
        - "word": len(text.split())
        - "tiktoken": (需要 tiktoken 库，暂不实现)

        overflow_strategy:
        - "truncate": 超出预算的 item 截断保留
        - "drop": 超出预算的 item 直接丢弃
        """

        def count_tokens(text: str) -> int:
            if self.token_counter == "char":
                return len(text)
            if self.token_counter == "word":
                return len(text.split())
            # tiktoken 等暂不实现
            return len(text)

        budget = int(self.token_budget)
        used = 0
        result: list[MemoryItem] = []

        for item in items:
            tokens = count_tokens(item.text)
            if used + tokens <= budget:
                result.append(item)
                used += tokens
            elif self.overflow_strategy == "truncate":
                # 截断 item.text
                remain = budget - used
                if remain <= 0:
                    break
                truncated_text = (
                    item.text[:remain]
                    if self.token_counter == "char"
                    else " ".join(item.text.split()[:remain])
                )
                truncated_item = MemoryItem(
                    text=truncated_text,
                    score=item.score,
                    metadata=item.metadata,
                    original_index=item.original_index,
                )
                result.append(truncated_item)
                break
            # overflow_strategy == "drop": 直接不加，继续尝试下一个
            # 但已经超预算就不再继续了
            elif self.overflow_strategy == "drop":
                break

        return result

    def _filter_threshold(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """按分数阈值过滤。"""
        threshold = float(self.score_threshold)
        return [item for item in items if (item.score or 0.0) >= threshold]

    def _filter_top_k(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """取 top-k（按当前顺序）。"""
        k = int(self.top_k)
        return items[:k]

    def _filter_llm_placeholder(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """LLM 判断相关性过滤（占位）。

        真实实现需要调用 LLMGenerator，构造 prompt 让 LLM 判断每条记忆是否相关。
        这里仅保留接口，默认返回所有 items。
        """
        print("LLM-based filter is not implemented in benchmark; keep all items")
        return items

    # ========================================================================
    # MERGE ACTION (R3 重构：基于多次查询服务，而非从 data 读取多源)
    # ========================================================================

    def _execute_merge(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """merge 执行分发。

        R3 重构：不再从 data 读取多个来源，而是通过多次查询记忆服务来合并。

        支持的子类型：
        - link_expand: 通过链接扩展获取关联记忆（参考 A-mem）
        - multi_query: 多次查询服务获取补充信息

        注意：旧的 concat/interleave/weighted/rrf 已移除，
        这些功能应由服务内部实现或通过 multi_query 实现。
        """
        if self.merge_type == "link_expand":
            return self._merge_by_link_expand(items, data)
        if self.merge_type == "multi_query":
            return self._merge_by_multi_query(items, data)

        # 默认：不合并，直接使用
        print(f"Unknown merge_type: {self.merge_type}, no merge applied")
        return items

    def _merge_by_link_expand(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """通过链接扩展获取关联记忆（参考 A-mem 的图扩展）。

        调用服务的 retrieve 方法获取关联记忆。
        服务负责实现扩展逻辑（如图遍历、链接追踪等）。

        配置：
        - expand_top_n: 只扩展 top N 条记忆（默认 5）
        - max_depth: 扩展深度（默认 1）
        """
        result = list(items)
        expand_top_n = int(getattr(self, "expand_top_n", 5))
        max_depth = int(getattr(self, "max_depth", 1))

        # 收集已有的 text，用于去重
        seen_texts = {item.text for item in result}

        # 只扩展 top N 条记忆
        for item in items[:expand_top_n]:
            # 调用服务获取关联记忆
            # 注意：这里使用 call_service 方法（MapFunction 提供）
            # 服务应根据 metadata 中的 expand_links=True 返回关联记忆
            try:
                related = self.call_service(
                    self.service_name,
                    method="retrieve",
                    query=item.text,
                    metadata={"expand_links": True, "max_depth": max_depth},
                )
                if related and isinstance(related, list):
                    for r in related:
                        if isinstance(r, dict):
                            text = r.get("text", "")
                            if text and text not in seen_texts:
                                result.append(
                                    MemoryItem(
                                        text=text,
                                        score=r.get("score"),
                                        metadata=r.get("metadata", {}),
                                        original_index=-1,
                                    )
                                )
                                seen_texts.add(text)
            except Exception as e:  # noqa: BLE001
                print(f"link_expand: call_service failed: {e}")
                continue

        return result

    def _merge_by_multi_query(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """多次查询服务获取补充信息。

        允许配置多个补充查询，每个查询可以指定不同的查询模板和元数据。

        配置：
        - secondary_queries: 补充查询列表
            - query_template: 查询模板（可使用 {user}, {question} 等变量）
            - metadata: 传递给服务的元数据
        """
        result = list(items)
        secondary_queries = getattr(self, "secondary_queries", []) or []

        # 收集已有的 text，用于去重
        seen_texts = {item.text for item in result}

        for query_cfg in secondary_queries:
            if not isinstance(query_cfg, dict):
                continue

            # 构造查询
            query_template = query_cfg.get("query_template", "")
            query_metadata = query_cfg.get("metadata", {})

            # 替换模板变量
            query = query_template
            for key in ["user", "question", "user_name"]:
                value = data.get(key, "")
                query = query.replace("{" + key + "}", str(value))

            if not query.strip():
                query = data.get("question", "")

            if not query:
                continue

            # 调用服务
            try:
                secondary_result = self.call_service(
                    self.service_name,
                    method="retrieve",
                    query=query,
                    metadata=query_metadata,
                )
                if secondary_result and isinstance(secondary_result, list):
                    for r in secondary_result:
                        if isinstance(r, dict):
                            text = r.get("text", "")
                            if text and text not in seen_texts:
                                result.append(
                                    MemoryItem(
                                        text=text,
                                        score=r.get("score"),
                                        metadata=r.get("metadata", {}),
                                        original_index=-1,
                                    )
                                )
                                seen_texts.add(text)
            except Exception as e:  # noqa: BLE001
                print(f"multi_query: call_service failed: {e}")
                continue

        return result

    # ========================================================================
    # AUGMENT ACTION
    # ========================================================================

    def _execute_augment(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """augment 执行分发。

        支持的子类型：
        - reflection: 占位，为记忆生成反思（参考 LoCoMo, Generative Agents）
        - context: 添加上下文信息（如对话历史、用户画像）
        - metadata: 将 metadata 转换为自然语言描述并添加到 text
        - temporal: 添加时间信息到 text
        """
        if self.augment_type == "reflection":
            return self._augment_reflection_placeholder(items, data)
        if self.augment_type == "context":
            return self._augment_context(items, data)
        if self.augment_type == "metadata":
            return self._augment_metadata(items, data)
        if self.augment_type == "temporal":
            return self._augment_temporal(items, data)

        print(f"Unknown augment_type: {self.augment_type}, no augmentation")
        return items

    def _augment_reflection_placeholder(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """reflection 占位实现。

        真实实现需要调用 LLMGenerator，为每条记忆生成高层次的反思摘要。
        这里仅保留接口，默认返回原 items。
        """
        print("reflection augment is not implemented in benchmark; keep original items")
        return items

    def _augment_context(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """添加上下文信息。

        从 data 中提取配置的 augment_fields，拼接到每个 item 的 text 前面。
        例如：augment_fields = ["user_name", "user_age"]
        结果：[User: John, Age: 30] original_text
        """
        if not self.augment_fields:
            return items

        context_parts = []
        for field in self.augment_fields:
            value = data.get(field)
            if value is not None:
                context_parts.append(f"{field}: {value}")

        if not context_parts:
            return items

        context_str = "[" + ", ".join(context_parts) + "] "

        result: list[MemoryItem] = []
        for item in items:
            augmented_item = MemoryItem(
                text=context_str + item.text,
                score=item.score,
                metadata=item.metadata,
                original_index=item.original_index,
            )
            result.append(augmented_item)
        return result

    def _augment_metadata(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """将 metadata 转换为自然语言描述并添加到 text。

        例如：metadata = {"importance": 8, "emotion": "happy"}
        结果：[importance: 8, emotion: happy] original_text
        """
        result: list[MemoryItem] = []
        for item in items:
            if not item.metadata:
                result.append(item)
                continue

            meta_parts = [f"{k}: {v}" for k, v in item.metadata.items()]
            meta_str = "[" + ", ".join(meta_parts) + "] "

            augmented_item = MemoryItem(
                text=meta_str + item.text,
                score=item.score,
                metadata=item.metadata,
                original_index=item.original_index,
            )
            result.append(augmented_item)
        return result

    def _augment_temporal(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """添加时间信息到 text。

        从 metadata 中提取 time_field 字段，转换为自然语言时间描述。
        例如：[2 hours ago] original_text
        """
        now = datetime.now(UTC)
        result: list[MemoryItem] = []

        for item in items:
            ts = item.get_timestamp(self.time_field)
            if ts is None:
                result.append(item)
                continue

            delta = now - ts
            if delta.total_seconds() < 60:
                time_str = "just now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(delta.total_seconds() / 86400)
                time_str = f"{days} day{'s' if days != 1 else ''} ago"

            augmented_item = MemoryItem(
                text=f"[{time_str}] {item.text}",
                score=item.score,
                metadata=item.metadata,
                original_index=item.original_index,
            )
            result.append(augmented_item)
        return result

    # ========================================================================
    # COMPRESS ACTION
    # ========================================================================

    def _execute_compress(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """compress 执行分发。

        支持的子类型：
        - llmlingua: 占位，基于 LLMLingua 的提示词压缩（参考 SeCom）
        - extractive: 抽取式压缩（保留关键句子）
        - abstractive: 占位，生成式压缩（用 LLM 改写摘要）
        """
        if self.compress_type == "llmlingua":
            return self._compress_llmlingua_placeholder(items, data)
        if self.compress_type == "extractive":
            return self._compress_extractive(items, data)
        if self.compress_type == "abstractive":
            return self._compress_abstractive_placeholder(items, data)

        print(f"Unknown compress_type: {self.compress_type}, no compression")
        return items

    def _compress_llmlingua_placeholder(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """llmlingua 占位实现（参考 SeCom）。

        真实实现需要调用 LLMLingua 库进行提示词压缩，去除冗余 tokens。
        这里仅保留接口，默认返回原 items。
        """
        print("llmlingua compress is not implemented in benchmark; keep original items")
        return items

    def _compress_extractive(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """抽取式压缩，保留每个 item 的关键句子。

        compress_ratio: 保留的比例（0-1）
        compress_max_length: 每个 item 压缩后的最大长度（字符数）
        """
        ratio = float(self.compress_ratio)
        max_len = int(self.compress_max_length)

        result: list[MemoryItem] = []
        for item in items:
            text = item.text
            if len(text) <= max_len:
                result.append(item)
                continue

            # 简单按句子切分（按 . ! ? 换行符）
            import re

            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                result.append(item)
                continue

            # 计算保留多少句子
            target_count = max(1, int(len(sentences) * ratio))
            # 简单策略：保留前 target_count 句
            kept_sentences = sentences[:target_count]
            compressed_text = " ".join(kept_sentences)

            # 如果还是超长，按字符截断
            if len(compressed_text) > max_len:
                compressed_text = compressed_text[:max_len] + "..."

            compressed_item = MemoryItem(
                text=compressed_text,
                score=item.score,
                metadata=item.metadata,
                original_index=item.original_index,
            )
            result.append(compressed_item)

        return result

    def _compress_abstractive_placeholder(
        self, items: list[MemoryItem], data: dict[str, Any]
    ) -> list[MemoryItem]:
        """abstractive 占位实现。

        真实实现需要调用 LLMGenerator，为每个 item 生成摘要。
        这里仅保留接口，默认返回原 items。
        """
        print("abstractive compress is not implemented in benchmark; keep original items")
        return items

    # ========================================================================
    # FORMAT ACTION
    # ========================================================================

    def _execute_format_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """format action 包装：提取、格式化、直接设置 history_text。"""
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)
        history_text = self._execute_format(items, data)
        data["history_text"] = history_text
        return data

    def _execute_format(self, items: list[MemoryItem], data: dict[str, Any]) -> str:
        """format 执行分发。

        支持的子类型：
        - template: 模板格式化（参考 MemGPT, MemoryBank）
        - structured: 结构化分区格式化
        - chat: 对话格式化
        - xml: XML 标签包装（Claude style）
        """
        if self.format_type == "template":
            return self._format_template(items, data)
        if self.format_type == "structured":
            return self._format_structured(items, data)
        if self.format_type == "chat":
            return self._format_chat(items, data)
        if self.format_type == "xml":
            return self._format_xml(items, data)

        print(f"Unknown format_type: {self.format_type}, fallback to template")
        return self._format_template(items, data)

    def _format_template(self, items: list[MemoryItem], data: dict[str, Any]) -> str:
        """模板格式化（参考 MemGPT, MemoryBank）。

        支持变量替换：
        - {memories}: 格式化后的记忆列表
        - {profile}: 用户画像（从 data 中提取）
        - {question}: 当前问题
        - 其他 data 中的字段
        """
        # 格式化记忆列表
        memory_lines: list[str] = []
        for item in items:
            # 使用 memory_template 格式化每条记忆
            try:
                # 准备格式化参数
                format_vars = {
                    "text": item.text,
                    "score": item.score or 0.0,
                }
                # 添加 metadata 中的字段
                format_vars.update(item.metadata)

                line = self.memory_template.format(**format_vars)
                memory_lines.append(line)
            except Exception as e:  # noqa: BLE001
                print(f"Failed to format memory item with template: {e}")
                memory_lines.append(f"- {item.text}")

        memories_str = "\n".join(memory_lines) if memory_lines else "(No memories)"

        # 如果没有配置 template，返回默认格式
        if not self.format_template:
            return memories_str

        # 准备变量替换
        template_vars = {
            "memories": memories_str,
            "profile": data.get("user_profile", ""),
            "question": data.get("question", ""),
        }
        # 添加 data 中的其他字段
        for key, value in data.items():
            if key not in template_vars and isinstance(value, (str, int, float, bool)):
                template_vars[key] = value

        # 模板替换
        try:
            return self.format_template.format(**template_vars)
        except Exception as e:  # noqa: BLE001
            print(f"Failed to format template: {e}")
            return memories_str

    def _format_structured(self, items: list[MemoryItem], data: dict[str, Any]) -> str:
        """结构化分区格式化。

        根据 structure 配置，将记忆分为多个 section。
        每个 section 可以指定 source、max_items。
        """
        if not self.format_structure:
            # 没有配置结构，返回默认格式
            return "\n".join([item.text for item in items])

        sections: list[str] = []

        for section_cfg in self.format_structure:
            section_name = section_cfg.get("section", "Memories")
            source = section_cfg.get("source", "memory_data")
            max_items = section_cfg.get("max_items", 10)

            # 从 data 中提取对应源的数据
            if source == "memory_data":
                section_items = items[:max_items]
            else:
                source_data = data.get(source, [])
                if isinstance(source_data, list):
                    section_items = self._convert_to_memory_items(source_data)[:max_items]
                elif isinstance(source_data, str):
                    # 如果是字符串（如 user_profile），直接使用
                    sections.append(f"## {section_name}\n{source_data}")
                    continue
                else:
                    section_items = []

            if not section_items:
                continue

            # 格式化 section
            section_lines = [f"## {section_name}"]
            for item in section_items:
                section_lines.append(f"- {item.text}")

            sections.append("\n".join(section_lines))

        return "\n\n".join(sections) if sections else "(No content)"

    def _format_chat(self, items: list[MemoryItem], data: dict[str, Any]) -> str:
        """对话格式化。

        将记忆格式化为对话形式，支持角色映射和时间戳。
        """
        chat_lines: list[str] = []

        for item in items:
            # 提取角色
            role = item.metadata.get("role", "user")
            # 应用角色映射
            display_role = self.role_mapping.get(role, role.capitalize())

            # 构建对话行
            if self.include_timestamps:
                timestamp = item.metadata.get("timestamp", "")
                if timestamp:
                    chat_lines.append(f"[{timestamp}] {display_role}: {item.text}")
                else:
                    chat_lines.append(f"{display_role}: {item.text}")
            else:
                chat_lines.append(f"{display_role}: {item.text}")

        return "\n".join(chat_lines) if chat_lines else "(No conversation)"

    def _format_xml(self, items: list[MemoryItem], data: dict[str, Any]) -> str:
        """XML 标签包装（Claude style）。

        将记忆和其他信息包装在 XML 标签中。
        """
        # 默认标签
        memories_tag = self.xml_tags.get("memories", "relevant_context")
        profile_tag = self.xml_tags.get("profile", "user_profile")

        xml_parts: list[str] = []

        # 记忆部分
        if items:
            xml_parts.append(f"<{memories_tag}>")
            for item in items:
                xml_parts.append("  <memory>")
                xml_parts.append(f"    <text>{item.text}</text>")
                if item.score is not None:
                    xml_parts.append(f"    <score>{item.score}</score>")
                if item.metadata:
                    xml_parts.append("    <metadata>")
                    for key, value in item.metadata.items():
                        xml_parts.append(f"      <{key}>{value}</{key}>")
                    xml_parts.append("    </metadata>")
                xml_parts.append("  </memory>")
            xml_parts.append(f"</{memories_tag}>")

        # 用户画像部分
        profile = data.get("user_profile")
        if profile:
            xml_parts.append(f"<{profile_tag}>")
            xml_parts.append(f"  {profile}")
            xml_parts.append(f"</{profile_tag}>")

        return "\n".join(xml_parts) if xml_parts else "<empty/>"
