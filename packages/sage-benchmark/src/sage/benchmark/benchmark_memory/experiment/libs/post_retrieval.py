"""后检索处理模块 - 在记忆检索后的后处理（可选）

当前支持的 action：
- none: 仅做基础格式化（保持向后兼容）
- rerank: 对检索结果进行重排序（语义 / 时间衰减 / PPR / 加权 / cross-encoder）

后续将扩展：
- filter: 结果筛选（token budget / 阈值 / top-k / 去重等）
- merge: 多源结果融合
- augment: 结果增强（反思 / 上下文 / 元数据 / 时间）
- compress: 结果压缩（LLMLingua / 抽取式 / 生成式）
- format: 最终格式化输出（模板 / 结构化 / chat / xml）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, List, Optional

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
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
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:  # noqa: BLE001
                    continue

        # 时间戳（秒）
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except Exception:  # noqa: BLE001
                return None

        return None


class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子

    职责：
    - 结果重排序（rerank）
    - 结果过滤（filter, TODO）
    - 多源融合（merge, TODO）
    - 结果增强（augment, TODO）
    - 内容压缩（compress, TODO）
    - 格式化输出（format, TODO）

    当前实现优先保证：
    - 默认 `none` 行为不变，仅做基础 history_text 拼接
    - 在此基础上按 action 追加 /改写 memory_data，并最终统一生成 history_text
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

        # 默认初始化共通工具（Embedding）
        # 这些工具依赖外部模型部署，持有句柄没有问题
        self._embedding_generator: EmbeddingGenerator = EmbeddingGenerator.from_config(self.config)

        # 根据 action 初始化特定配置
        self._init_for_action()

    def _init_for_action(self) -> None:
        """根据 action 类型初始化对应配置"""
        cfg_prefix = "operators.post_retrieval"

        if self.action == "rerank":
            # rerank 配置
            self.rerank_type: str = get_required_config(self.config, 
                f"{cfg_prefix}.rerank_type", "action=rerank"
            )
            self.semantic_model_name: str | None = self.config.get(f"{cfg_prefix}.rerank_model")
            self.cross_encoder_model: str | None = self.config.get(f"{cfg_prefix}.cross_encoder_model")
            self.cross_encoder_batch_size: int = self.config.get(f"{cfg_prefix}.batch_size", 32)
            self.time_decay_rate: float = float(
                get_required_config(self.config, f"{cfg_prefix}.time_decay_rate", "rerank_type=time_weighted"),
            )
            self.time_field: str = self.config.get(f"{cfg_prefix}.time_field", "timestamp")
            self.ppr_damping_factor: float = float(self.config.get(f"{cfg_prefix}.damping_factor", 0.5))
            self.ppr_max_iterations: int = int(self.config.get(f"{cfg_prefix}.max_iterations", 100))
            self.ppr_convergence_threshold: float = float(self.config.get(f"{cfg_prefix}.convergence_threshold", 1e-6))
            self.ppr_personalization_nodes: str = self.config.get(f"{cfg_prefix}.personalization_nodes", "query_entities")
            self.weighted_factors: list[dict[str, Any]] = self.config.get(f"{cfg_prefix}.factors")
            if self.rerank_type == "weighted" and not self.weighted_factors:
                raise ValueError("缺少必需配置: operators.post_retrieval.factors (rerank_type=weighted)")
            self.rerank_top_k: int | None = self.config.get(f"{cfg_prefix}.top_k")
            self.rerank_score_field: str = self.config.get(f"{cfg_prefix}.score_field", "rerank_score")

        elif self.action == "filter":
            # filter 配置
            self.filter_type = get_required_config(self.config, f"{cfg_prefix}.filter_type", "action=filter")
            self.token_budget = get_required_config(self.config, f"{cfg_prefix}.token_budget", "filter_type=token_budget")
            self.token_counter = self.config.get(f"{cfg_prefix}.token_counter", "char")
            self.overflow_strategy = self.config.get(f"{cfg_prefix}.overflow_strategy", "truncate")
            self.score_threshold = get_required_config(self.config, f"{cfg_prefix}.score_threshold", "filter_type=threshold")
            self.top_k = get_required_config(self.config, f"{cfg_prefix}.k", "filter_type=top_k")
            self.dedup_threshold = self.config.get(f"{cfg_prefix}.dedup_threshold", 0.9)
            self.dedup_strategy = self.config.get(f"{cfg_prefix}.dedup_strategy", "keep_first")

        elif self.action == "merge":
            # merge 配置
            self.merge_type = get_required_config(self.config, f"{cfg_prefix}.merge_type", "action=merge")
            self.merge_sources = self.config.get(f"{cfg_prefix}.merge_sources", ["memory_data", "context_data"])
            self.rrf_k = self.config.get(f"{cfg_prefix}.rrf_k", 60)
            self.merge_weights = self.config.get(f"{cfg_prefix}.merge_weights", None)
            if self.merge_type == "weighted" and not self.merge_weights:
                raise ValueError("缺少必需配置: operators.post_retrieval.merge_weights (merge_type=weighted)")

        elif self.action == "augment":
            # augment 配置
            self.augment_type = get_required_config(self.config, f"{cfg_prefix}.augment_type", "action=augment")
            self.augment_template = self.config.get(f"{cfg_prefix}.augment_template", "")
            self.augment_fields = self.config.get(f"{cfg_prefix}.augment_fields", [])
            self.time_field = self.config.get(f"{cfg_prefix}.time_field", "timestamp")

        elif self.action == "compress":
            # compress 配置
            self.compress_type = get_required_config(self.config, f"{cfg_prefix}.compress_type", "action=compress")
            self.compress_ratio = get_required_config(self.config, f"{cfg_prefix}.compress_ratio", "action=compress")
            self.compress_max_length = self.config.get(f"{cfg_prefix}.compress_max_length", 512)

        elif self.action == "format":
            # format 配置
            self.format_type = get_required_config(self.config, f"{cfg_prefix}.format_type", "action=format")
            self.format_template = get_required_config(self.config, f"{cfg_prefix}.template", "format_type=template")
            self.memory_template = self.config.get(f"{cfg_prefix}.memory_template", "- {{text}}")
            self.format_structure = get_required_config(self.config, f"{cfg_prefix}.structure", "format_type=structured")
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

    def _rerank_semantic(self, items: list[MemoryItem], data: dict[str, Any]) -> list[tuple[MemoryItem, float]]:
        """基于 embedding 相似度的语义重排。

        - 如果上游已经提供 `query_embedding`，优先使用
        - 否则使用 EmbeddingGenerator 对 `question` 做一次 embedding（如果可用）
        """

        if not self._embedding_generator.is_available():
            print("Semantic rerank requires embedding service, but none is available")
            return [(item, item.score or 0.0) for item in items]

        query_vec = data.get("query_embedding")
        if query_vec is None:
            question = data.get("question")
            if not isinstance(question, str) or not question.strip():
                print("Semantic rerank: missing question/query_embedding, fallback to original score")
                return [(item, item.score or 0.0) for item in items]
            query_vec = self._embedding_generator.embed(question)

        if not query_vec:
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

        item_embeddings = self._embedding_generator.embed_batch([i.text for i in items]) or []
        if len(item_embeddings) != len(items):
            print("Semantic rerank: embedding_batch length mismatch, fallback to original score")
            return [(item, item.score or 0.0) for item in items]

        scored: list[tuple[MemoryItem, float]] = []
        for item, emb in zip(items, item_embeddings):
            sim = cosine(query_vec, emb)
            scored.append((item, float(sim)))
        return scored

    # ------------------- time_weighted --------------------

    def _rerank_time_weighted(self, items: list[MemoryItem], data: dict[str, Any]) -> list[tuple[MemoryItem, float]]:
        """时间衰减 + 原相关性组合（受 LD-Agent 启发）。"""

        now = datetime.now(timezone.utc)
        decay_rate = float(self.time_decay_rate)

        scored: list[tuple[MemoryItem, float]] = []
        for item in items:
            ts = item.get_timestamp(self.time_field)
            if ts is None:
                recency = 1.0
            else:
                hours = max((now - ts).total_seconds() / 3600.0, 0.0)
                recency = pow(0.995, hours) if decay_rate <= 0 else pow(1.0 - min(decay_rate, 0.99), hours)

            base_score = item.score if item.score is not None else 1.0
            scored.append((item, float(recency * base_score)))

        return scored

    # ------------------------ ppr ------------------------

    def _rerank_ppr_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[tuple[MemoryItem, float]]:
        """PPR 占位实现。

        真实 PPR 需要图存储支持，这里仅保留接口并返回原顺序，
        方便未来与 HippoRAG 图后端集成时无缝替换。
        """

        print("PPR rerank is not wired to a graph backend yet, keep original order")
        return [(item, item.score or 0.0) for item in items]

    # ---------------------- weighted ----------------------

    def _rerank_weighted(self, items: list[MemoryItem], data: dict[str, Any]) -> list[tuple[MemoryItem, float]]:
        """多因子加权重排（参考 Generative Agents 的 recency/importance/relevance）。"""

        now = datetime.now(timezone.utc)

        def get_relevance(item: MemoryItem) -> float:
            # 优先使用已有 score，其次使用 embedding 相似度（如果可用），否则为 0
            if item.score is not None:
                return float(item.score)
            if not self._embedding_generator.is_available():
                return 0.0
            query_vec = data.get("query_embedding")
            question = data.get("question")
            if query_vec is None and isinstance(question, str) and question.strip():
                query_vec = self._embedding_generator.embed(question)
            if not query_vec:
                return 0.0
            emb = self._embedding_generator.embed(item.text)
            if not emb:
                return 0.0

            import math

            dot = sum(x * y for x, y in zip(query_vec, emb))
            na = math.sqrt(sum(x * x for x in query_vec))
            nb = math.sqrt(sum(y * y for y in emb))
            if na == 0.0 or nb == 0.0:
                return 0.0
            return float(dot / (na * nb))

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

        支持的子类型：
        - token_budget: 按 token 预算过滤（参考 SCM4LLMs）
        - threshold: 按分数阈值过滤
        - top_k: 取 top-k
        - llm: 占位，由 LLM 判断相关性
        - dedup: 去重
        """
        if self.filter_type == "token_budget":
            return self._filter_token_budget(items, data)
        if self.filter_type == "threshold":
            return self._filter_threshold(items, data)
        if self.filter_type == "top_k":
            return self._filter_top_k(items, data)
        if self.filter_type == "llm":
            return self._filter_llm_placeholder(items, data)
        if self.filter_type == "dedup":
            return self._filter_dedup(items, data)

        print(f"Unknown filter_type: {self.filter_type}, fallback to threshold")
        return self._filter_threshold(items, data)

    def _filter_token_budget(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
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
                truncated_text = item.text[:remain] if self.token_counter == "char" else " ".join(item.text.split()[:remain])
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

    def _filter_llm_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """LLM 判断相关性过滤（占位）。

        真实实现需要调用 LLMGenerator，构造 prompt 让 LLM 判断每条记忆是否相关。
        这里仅保留接口，默认返回所有 items。
        """
        print("LLM-based filter is not implemented in benchmark; keep all items")
        return items

    def _filter_dedup(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """去重过滤。

        dedup_strategy:
        - "keep_first": 重复时保留第一次出现的
        - "keep_last": 重复时保留最后一次出现的
        - "keep_highest_score": 重复时保留得分最高的
        """
        if not items:
            return []

        threshold = float(self.dedup_threshold)
        strategy = self.dedup_strategy

        # 使用 embedding 计算相似度进行去重
        if not self._embedding_generator.is_available():
            print("Dedup filter requires embedding service, but none is available; fallback to text equality")
            # 退化为严格文本去重
            seen: set[str] = set()
            result: list[MemoryItem] = []
            for item in items:
                if item.text not in seen:
                    result.append(item)
                    seen.add(item.text)
            return result

        # 使用 embedding 去重
        embeddings = self._embedding_generator.embed_batch([i.text for i in items]) or []
        if len(embeddings) != len(items):
            print("Dedup: embedding_batch length mismatch, fallback to text equality")
            seen = set()
            result = []
            for item in items:
                if item.text not in seen:
                    result.append(item)
                    seen.add(item.text)
            return result

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

        # 策略实现
        clusters: list[tuple[MemoryItem, list[float]]] = []  # (representative_item, embedding)
        result = []

        for item, emb in zip(items, embeddings):
            # 检查与已有 cluster 的相似度
            matched_cluster_idx = None
            for idx, (rep_item, rep_emb) in enumerate(clusters):
                sim = cosine(emb, rep_emb)
                if sim >= threshold:
                    matched_cluster_idx = idx
                    break

            if matched_cluster_idx is None:
                # 新 cluster
                clusters.append((item, emb))
                result.append(item)
            else:
                # 已有 cluster，根据策略决定是否替换
                rep_item, rep_emb = clusters[matched_cluster_idx]
                if strategy == "keep_first":
                    pass  # 保留原有代表
                elif strategy == "keep_last":
                    # 替换代表
                    clusters[matched_cluster_idx] = (item, emb)
                    result[matched_cluster_idx] = item
                elif strategy == "keep_highest_score":
                    # 比较得分
                    if (item.score or 0.0) > (rep_item.score or 0.0):
                        clusters[matched_cluster_idx] = (item, emb)
                        result[matched_cluster_idx] = item

        return result

    # ========================================================================
    # MERGE ACTION
    # ========================================================================

    def _execute_merge(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """merge 执行分发。

        支持的子类型：
        - concat: 简单拼接多个来源（参考 MemoryOS 的 multi-tier）
        - interleave: 交错合并
        - weighted: 加权合并（按来源权重）
        - rrf: Reciprocal Rank Fusion
        - link_expand: 占位，扩展图链接（参考 A-mem）
        - multi_aspect: 占位，多维度记忆合并（参考 EmotionalRAG）
        """
        if self.merge_type == "concat":
            return self._merge_concat(items, data)
        if self.merge_type == "interleave":
            return self._merge_interleave(items, data)
        if self.merge_type == "weighted":
            return self._merge_weighted(items, data)
        if self.merge_type == "rrf":
            return self._merge_rrf(items, data)
        if self.merge_type == "link_expand":
            return self._merge_link_expand_placeholder(items, data)
        if self.merge_type == "multi_aspect":
            return self._merge_multi_aspect_placeholder(items, data)

        print(f"Unknown merge_type: {self.merge_type}, fallback to concat")
        return self._merge_concat(items, data)

    def _merge_concat(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """简单拼接多个来源。

        merge_sources: ["memory_data", "context_data", ...]
        从 data 中取各来源的 memory item list，依次拼接。
        如果 items 已有内容，也会被保留在最前面。
        """
        result = list(items)
        for src in self.merge_sources:
            src_items = data.get(src)
            if isinstance(src_items, list):
                for obj in src_items:
                    if isinstance(obj, dict):
                        result.append(
                            MemoryItem(
                                text=obj.get("text", ""),
                                score=obj.get("score"),
                                metadata=obj.get("metadata", {}),
                                original_index=obj.get("original_index", -1),
                            )
                        )
                    elif isinstance(obj, MemoryItem):
                        result.append(obj)
        return result

    def _merge_interleave(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """交错合并多个来源。

        例如：source1[0], source2[0], source1[1], source2[1], ...
        """
        sources: list[list[MemoryItem]] = [list(items)]
        for src in self.merge_sources:
            src_items = data.get(src)
            if isinstance(src_items, list):
                converted: list[MemoryItem] = []
                for obj in src_items:
                    if isinstance(obj, dict):
                        converted.append(
                            MemoryItem(
                                text=obj.get("text", ""),
                                score=obj.get("score"),
                                metadata=obj.get("metadata", {}),
                                original_index=obj.get("original_index", -1),
                            )
                        )
                    elif isinstance(obj, MemoryItem):
                        converted.append(obj)
                sources.append(converted)

        # 交错合并
        result: list[MemoryItem] = []
        max_len = max((len(s) for s in sources), default=0)
        for i in range(max_len):
            for s in sources:
                if i < len(s):
                    result.append(s[i])
        return result

    def _merge_weighted(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """加权合并多个来源，对 score 进行加权平均。

        merge_weights: {"memory_data": 0.7, "context_data": 0.3, ...}
        如果 merge_weights 未配置，则退化为 concat。
        """
        if not self.merge_weights:
            return self._merge_concat(items, data)

        # 收集所有来源的 items 并标记来源
        all_items: list[tuple[MemoryItem, str]] = [(item, "items") for item in items]
        for src in self.merge_sources:
            src_items = data.get(src)
            if isinstance(src_items, list):
                for obj in src_items:
                    if isinstance(obj, dict):
                        all_items.append(
                            (
                                MemoryItem(
                                    text=obj.get("text", ""),
                                    score=obj.get("score"),
                                    metadata=obj.get("metadata", {}),
                                    original_index=obj.get("original_index", -1),
                                ),
                                src,
                            )
                        )
                    elif isinstance(obj, MemoryItem):
                        all_items.append((obj, src))

        # 按 text 合并相同的 item，对 score 进行加权平均
        text_to_items: dict[str, list[tuple[MemoryItem, str]]] = {}
        for item, src in all_items:
            text_to_items.setdefault(item.text, []).append((item, src))

        result: list[MemoryItem] = []
        for text, group in text_to_items.items():
            # 计算加权平均得分
            total_weight = 0.0
            weighted_score = 0.0
            representative_item = group[0][0]
            for item, src in group:
                weight = float(self.merge_weights.get(src, 1.0))
                total_weight += weight
                weighted_score += weight * (item.score or 0.0)

            avg_score = weighted_score / total_weight if total_weight > 0 else 0.0
            merged_item = MemoryItem(
                text=representative_item.text,
                score=avg_score,
                metadata=representative_item.metadata,
                original_index=representative_item.original_index,
            )
            result.append(merged_item)

        # 按 score 降序
        result.sort(key=lambda x: x.score or 0.0, reverse=True)
        return result

    def _merge_rrf(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """Reciprocal Rank Fusion 合并多个来源。

        RRF score = sum(1 / (k + rank_in_source_i))
        其中 k 默认为 60。
        """
        k = int(self.rrf_k)

        # 收集所有来源的 ranked lists
        sources: list[list[MemoryItem]] = [list(items)]
        for src in self.merge_sources:
            src_items = data.get(src)
            if isinstance(src_items, list):
                converted: list[MemoryItem] = []
                for obj in src_items:
                    if isinstance(obj, dict):
                        converted.append(
                            MemoryItem(
                                text=obj.get("text", ""),
                                score=obj.get("score"),
                                metadata=obj.get("metadata", {}),
                                original_index=obj.get("original_index", -1),
                            )
                        )
                    elif isinstance(obj, MemoryItem):
                        converted.append(obj)
                sources.append(converted)

        # 为每个 item (by text) 计算 RRF score
        text_to_rrf: dict[str, float] = {}
        text_to_item: dict[str, MemoryItem] = {}

        for src_list in sources:
            for rank, item in enumerate(src_list, start=1):
                rrf_contribution = 1.0 / (k + rank)
                text_to_rrf[item.text] = text_to_rrf.get(item.text, 0.0) + rrf_contribution
                if item.text not in text_to_item:
                    text_to_item[item.text] = item

        # 构建结果
        result: list[MemoryItem] = []
        for text, rrf_score in text_to_rrf.items():
            item = text_to_item[text]
            merged_item = MemoryItem(
                text=item.text,
                score=rrf_score,
                metadata=item.metadata,
                original_index=item.original_index,
            )
            result.append(merged_item)

        # 按 RRF score 降序
        result.sort(key=lambda x: x.score or 0.0, reverse=True)
        return result

    def _merge_link_expand_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """link_expand 占位实现（参考 A-mem 的图扩展）。

        真实实现需要图存储支持，从 items 中的节点扩展出关联节点。
        这里仅保留接口，默认返回原 items。
        """
        print("link_expand merge is not wired to a graph backend; keep original items")
        return items

    def _merge_multi_aspect_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """multi_aspect 占位实现（参考 EmotionalRAG 的多维度记忆）。

        真实实现需要从多个维度（事实、情感、社会等）的记忆存储中检索并合并。
        这里仅保留接口，默认返回原 items。
        """
        print("multi_aspect merge is not implemented in benchmark; keep original items")
        return items

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

    def _augment_reflection_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
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
        now = datetime.now(timezone.utc)
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

    def _compress_llmlingua_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
        """llmlingua 占位实现（参考 SeCom）。

        真实实现需要调用 LLMLingua 库进行提示词压缩，去除冗余 tokens。
        这里仅保留接口，默认返回原 items。
        """
        print("llmlingua compress is not implemented in benchmark; keep original items")
        return items

    def _compress_extractive(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
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

    def _compress_abstractive_placeholder(self, items: list[MemoryItem], data: dict[str, Any]) -> list[MemoryItem]:
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
                xml_parts.append(f"  <memory>")
                xml_parts.append(f"    <text>{item.text}</text>")
                if item.score is not None:
                    xml_parts.append(f"    <score>{item.score}</score>")
                if item.metadata:
                    xml_parts.append(f"    <metadata>")
                    for key, value in item.metadata.items():
                        xml_parts.append(f"      <{key}>{value}</{key}>")
                    xml_parts.append(f"    </metadata>")
                xml_parts.append(f"  </memory>")
            xml_parts.append(f"</{memories_tag}>")

        # 用户画像部分
        profile = data.get("user_profile")
        if profile:
            xml_parts.append(f"<{profile_tag}>")
            xml_parts.append(f"  {profile}")
            xml_parts.append(f"</{profile_tag}>")

        return "\n".join(xml_parts) if xml_parts else "<empty/>"

