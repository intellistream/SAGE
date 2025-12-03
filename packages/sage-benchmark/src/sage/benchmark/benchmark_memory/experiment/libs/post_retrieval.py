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

            # time_weighted 相关配置：仅在 rerank_type=time_weighted 时必需
            if self.rerank_type == "time_weighted":
                self.time_decay_rate: float = float(
                    get_required_config(
                        self.config, f"{cfg_prefix}.time_decay_rate", "rerank_type=time_weighted"
                    ),
                )
            else:
                self.time_decay_rate = self.config.get(f"{cfg_prefix}.time_decay_rate", 0.1)
            self.time_field: str = self.config.get(f"{cfg_prefix}.time_field", "timestamp")

            # PPR 相关配置：仅在 rerank_type=ppr 时使用
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

            # weighted 相关配置：仅在 rerank_type=weighted 时必需
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
            # 根据 filter_type 加载对应配置
            if self.filter_type == "token_budget":
                self.token_budget = get_required_config(
                    self.config, f"{cfg_prefix}.token_budget", "filter_type=token_budget"
                )
                self.token_counter = self.config.get(f"{cfg_prefix}.token_counter", "char")
                self.overflow_strategy = self.config.get(
                    f"{cfg_prefix}.overflow_strategy", "truncate"
                )
            elif self.filter_type == "threshold":
                self.score_threshold = get_required_config(
                    self.config, f"{cfg_prefix}.score_threshold", "filter_type=threshold"
                )
            elif self.filter_type == "top_k":
                self.top_k = get_required_config(
                    self.config, f"{cfg_prefix}.k", "filter_type=top_k"
                )

            # 为其他类型设置默认值（避免属性缺失）
            if not hasattr(self, "token_budget"):
                self.token_budget = 1000
            if not hasattr(self, "token_counter"):
                self.token_counter = "char"
            if not hasattr(self, "overflow_strategy"):
                self.overflow_strategy = "truncate"
            if not hasattr(self, "score_threshold"):
                self.score_threshold = 0.0
            if not hasattr(self, "top_k"):
                self.top_k = 10

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
            # 根据 format_type 加载对应配置
            if self.format_type == "template":
                self.format_template = self.config.get(f"{cfg_prefix}.template", "")
                self.memory_template = self.config.get(
                    f"{cfg_prefix}.memory_template", "- {{text}}"
                )
            elif self.format_type == "structured":
                self.format_structure = get_required_config(
                    self.config, f"{cfg_prefix}.structure", "format_type=structured"
                )
            elif self.format_type == "chat":
                self.role_mapping = self.config.get(f"{cfg_prefix}.role_mapping", {})
                self.include_timestamps = self.config.get(f"{cfg_prefix}.include_timestamps", False)
            elif self.format_type == "xml":
                self.xml_tags = self.config.get(f"{cfg_prefix}.xml_tags", {})

            # 为其他类型设置默认值（避免属性缺失）
            if not hasattr(self, "format_template"):
                self.format_template = ""
            if not hasattr(self, "memory_template"):
                self.memory_template = "- {text}"
            if not hasattr(self, "format_structure"):
                self.format_structure = []
            if not hasattr(self, "role_mapping"):
                self.role_mapping = {}
            if not hasattr(self, "include_timestamps"):
                self.include_timestamps = False
            if not hasattr(self, "xml_tags"):
                self.xml_tags = {}

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

        action_handlers = {
            "none": self._execute_none,
            "rerank": self._execute_rerank,
            "filter": self._execute_filter,
            "merge": self._execute_merge,
            "augment": self._execute_augment,
            "compress": self._execute_compress,
            "format": self._execute_format,
        }

        handler = action_handlers.get(self.action)
        if handler:
            data = handler(data)
        else:
            print(f"[WARNING] Unknown action: {self.action}, using default format")
            data = self._execute_none(data)

        # 最终格式化（如果还没有 history_text）
        if "history_text" not in data:
            data = self._format_dialog_history(data)

        return data

    # =============================================================
    # 大类操作方法 (Action Methods)
    # =============================================================

    def _execute_none(self, data: dict[str, Any]) -> dict[str, Any]:
        """无操作，仅做基础格式化（保持向后兼容）"""
        return data

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
            # 合并 metadata，同时保留顶层的 node_id/entry_id
            metadata = dict(entry.get("metadata") or {})
            # 将顶层字段复制到 metadata 中，方便后续访问
            for key in ("node_id", "entry_id", "depth"):
                if key in entry and key not in metadata:
                    metadata[key] = entry[key]
            items.append(MemoryItem(text=text, score=score, metadata=metadata, original_index=idx))
        return items

    def _convert_from_memory_items(self, items: list[MemoryItem]) -> list[dict[str, Any]]:
        """将 MemoryItem list 转换回 dict list。"""
        result: list[dict[str, Any]] = []
        for item in items:
            entry = {
                "text": item.text,
                "score": item.score,
                "metadata": item.metadata,
            }
            # 将 node_id/entry_id 同时放在顶层，保持与服务返回格式一致
            for key in ("node_id", "entry_id", "depth"):
                if key in item.metadata:
                    entry[key] = item.metadata[key]
            result.append(entry)
        return result

    def _format_dialog_history(self, data: dict[str, Any]) -> dict[str, Any]:
        """格式化对话历史为结构化文本（阶段一：Prompt 拼接）。

        HippoRAG 对齐：优先返回原始对话文本而非三元组描述。
        检索到的三元组用于 PPR 图遍历，但最终返回给 LLM 的应该是原始文本。
        """

        memory_data = data.get("memory_data", []) or []

        history_parts: list[str] = []
        if self.conversation_format_prompt:
            history_parts.append(self.conversation_format_prompt.strip())

        # 使用 set 去重，避免重复的原始文本
        seen_texts = set()

        for entry in memory_data:
            if not isinstance(entry, dict):
                continue

            # HippoRAG: 优先使用原始对话文本
            metadata = entry.get("metadata", {}) or {}
            original_text = metadata.get("original_text", "")

            if original_text and original_text not in seen_texts:
                history_parts.append(original_text)
                seen_texts.add(original_text)
            else:
                # 回退到三元组描述
                text = entry.get("text", "")
                if text and text not in seen_texts:
                    history_parts.append(text)
                    seen_texts.add(text)

        history_text = "\n".join(history_parts) if history_parts else ""
        data["history_text"] = history_text
        return data

    def _execute_rerank(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行结果重排序（rerank action）

        支持的 rerank_type:
        - semantic: 语义相似度重排
        - time_weighted: 时间衰减重排
        - ppr: Personalized PageRank（占位）
        - weighted: 多因子加权
        - cross_encoder: 交叉编码器重排（占位）
        """
        memory_data = data.get("memory_data", [])
        if not memory_data:
            return data

        items = self._convert_to_memory_items(memory_data)
        rerank_type = self.rerank_type

        # 根据 rerank_type 内联处理逻辑
        scored_items: list[tuple[MemoryItem, float]] = []

        if rerank_type == "semantic":
            # ---- semantic 重排内联 ----
            query_embedding = data.get("query_embedding")

            if query_embedding is None:
                # 注意：不自己计算 embedding，跳过语义重排
                print(
                    "[WARNING] Semantic rerank: query_embedding not provided, fallback to original score"
                )
                scored_items = [(item, item.score or 0.5) for item in items]
            else:
                # 使用已有的 query_embedding 计算相似度
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

                for item in items:
                    item_embedding = item.metadata.get("embedding")
                    if item_embedding is not None:
                        score = cosine(query_embedding, item_embedding)
                    else:
                        score = item.score or 0.5
                    scored_items.append((item, float(score)))

        elif rerank_type == "time_weighted":
            # ---- time_weighted 重排内联 ----
            now = datetime.now(UTC)
            decay_rate = float(self.time_decay_rate)
            time_field = self.time_field

            for item in items:
                ts = item.get_timestamp(time_field)
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
                final_score = float(recency * base_score)
                scored_items.append((item, final_score))

        elif rerank_type == "ppr":
            # ---- ppr 重排内联（调用 GraphMemoryService.ppr_retrieve）----
            # 从检索结果中提取种子节点 ID
            seed_nodes = []
            for item in items:
                node_id = item.metadata.get("node_id") or item.metadata.get("entry_id")
                if node_id:
                    seed_nodes.append(node_id)

            if not seed_nodes:
                # 如果没有节点 ID，回退到原始顺序
                print("[WARNING] PPR rerank: no node_id in memory_data, keep original order")
                scored_items = [(item, item.score or 0.5) for item in items]
            else:
                try:
                    # 调用服务的 ppr_retrieve 方法
                    # PPR 可能需要较长时间，增加超时到 60 秒
                    ppr_results = self.call_service(
                        self.service_name,
                        method="ppr_retrieve",
                        timeout=60.0,
                        seed_nodes=seed_nodes,
                        alpha=1.0 - self.ppr_damping_factor,  # HippoRAG: damping=0.5 -> alpha=0.5
                        max_iter=self.ppr_max_iterations,
                        top_k=self.rerank_top_k or len(items) * 2,  # 获取更多结果以扩展上下文
                    )

                    if ppr_results and isinstance(ppr_results, list):
                        # 构建 node_id -> PPR score 的映射
                        ppr_scores = {}
                        for r in ppr_results:
                            if isinstance(r, dict):
                                node_id = r.get("node_id") or r.get("entry_id")
                                score = r.get("score", 0.0)
                                if node_id:
                                    ppr_scores[node_id] = score

                        # 更新原有 items 的分数，并添加新发现的节点
                        seen_nodes = set()
                        for item in items:
                            node_id = item.metadata.get("node_id") or item.metadata.get("entry_id")
                            if node_id:
                                seen_nodes.add(node_id)
                                ppr_score = ppr_scores.get(node_id, 0.0)
                                # 组合原始分数和 PPR 分数
                                base_score = item.score if item.score is not None else 0.5
                                final_score = 0.5 * base_score + 0.5 * ppr_score
                                scored_items.append((item, final_score))
                            else:
                                scored_items.append((item, item.score or 0.5))

                        # 添加 PPR 发现的新节点（图遍历扩展）
                        for r in ppr_results:
                            if isinstance(r, dict):
                                node_id = r.get("node_id") or r.get("entry_id")
                                if node_id and node_id not in seen_nodes:
                                    text = r.get("text", "")
                                    if text:
                                        new_item = MemoryItem(
                                            text=text,
                                            score=r.get("score", 0.0),
                                            metadata={"node_id": node_id, **r.get("metadata", {})},
                                            original_index=-1,
                                        )
                                        scored_items.append((new_item, r.get("score", 0.0)))
                                        seen_nodes.add(node_id)

                        print(
                            f"[INFO] PPR rerank: {len(seed_nodes)} seeds -> {len(scored_items)} results"
                        )
                    else:
                        print(
                            "[WARNING] PPR rerank: ppr_retrieve returned empty, keep original order"
                        )
                        scored_items = [(item, item.score or 0.5) for item in items]

                except Exception as e:  # noqa: BLE001
                    print(f"[WARNING] PPR rerank failed: {e}, keep original order")
                    scored_items = [(item, item.score or 0.5) for item in items]

        elif rerank_type == "weighted":
            # ---- weighted 重排内联 ----
            now = datetime.now(UTC)

            if not self.weighted_factors:
                # 没有配置时退化为 time_weighted 行为
                print("[WARNING] No weighted_factors configured, fallback to time_weighted")
                for item in items:
                    ts = item.get_timestamp(self.time_field)
                    if ts is None:
                        recency = 1.0
                    else:
                        hours = max((now - ts).total_seconds() / 3600.0, 0.0)
                        recency = pow(0.995, hours)
                    base_score = item.score if item.score is not None else 1.0
                    scored_items.append((item, float(recency * base_score)))
            else:
                # 多因子加权
                for item in items:
                    total_score = 0.0

                    for factor in self.weighted_factors:
                        name = (factor.get("name") or "").lower()
                        weight = float(factor.get("weight", 0.0))

                        if weight == 0.0:
                            continue

                        # 计算因子分数
                        if name == "recency":
                            decay_type = factor.get("decay_type", "exponential")
                            decay_rate = float(factor.get("decay_rate", 0.995))
                            ts = item.get_timestamp(self.time_field)
                            if ts is None:
                                factor_score = 1.0
                            else:
                                hours = max((now - ts).total_seconds() / 3600.0, 0.0)
                                if decay_type == "exponential":
                                    factor_score = pow(decay_rate, hours)
                                else:
                                    factor_score = 1.0 / (1.0 + hours)

                        elif name == "importance":
                            field = factor.get("field", "importance_score")
                            raw = item.metadata.get(field)
                            try:
                                val = float(raw)
                                factor_score = max(min(val / 10.0, 1.0), 0.0)
                            except Exception:  # noqa: BLE001
                                factor_score = 0.0

                        elif name == "relevance":
                            # R3: 只使用已有 score，不计算 embedding
                            factor_score = float(item.score) if item.score is not None else 0.0

                        else:
                            # 未知因子默认 0
                            factor_score = 0.0

                        total_score += weight * factor_score

                    scored_items.append((item, float(total_score)))

        elif rerank_type == "cross_encoder":
            # ---- cross_encoder 重排内联（占位实现）----
            # 需要加载 cross-encoder 模型，这里使用原始分数
            print(
                "[INFO] cross_encoder rerank is not implemented in benchmark, keep original score"
            )
            scored_items = [(item, item.score or 0.5) for item in items]

        else:
            print(f"[WARNING] Unknown rerank_type: {rerank_type}, skip rerank")
            return data

        # 排序
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 应用 top_k
        if self.rerank_top_k:
            scored_items = scored_items[: self.rerank_top_k]

        # 更新分数并转换回字典格式
        result_items = []
        for item, score in scored_items:
            item.score = score
            item.metadata[self.rerank_score_field] = score
            result_items.append(item)

        data["memory_data"] = self._convert_from_memory_items(result_items)
        return data

    def _execute_filter(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行结果筛选（filter action）

        支持的 filter_type:
        - token_budget: 按 token 预算过滤
        - threshold: 按分数阈值过滤
        - top_k: 取 top-k
        - llm: 占位，由 LLM 判断相关性

        注意：dedup 已移除，应由服务返回去重结果。
        """
        memory_data = data.get("memory_data", [])
        if not memory_data:
            return data

        items = self._convert_to_memory_items(memory_data)
        filter_type = self.filter_type

        if filter_type == "token_budget":
            # ---- token_budget 过滤内联 ----
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
                elif self.overflow_strategy == "drop":
                    break

            items = result

        elif filter_type == "threshold":
            # ---- threshold 过滤内联 ----
            threshold = float(self.score_threshold)
            items = [item for item in items if (item.score or 0.0) >= threshold]

        elif filter_type == "top_k":
            # ---- top_k 过滤内联 ----
            k = int(self.top_k)
            items = items[:k]

        elif filter_type == "llm":
            # ---- llm 过滤内联（占位实现）----
            # 真实实现需要调用 LLMGenerator
            print("[INFO] LLM-based filter is not implemented in benchmark; keep all items")

        else:
            print(f"[WARNING] Unknown filter_type: {filter_type}, fallback to threshold")
            threshold = float(getattr(self, "score_threshold", 0.0))
            items = [item for item in items if (item.score or 0.0) >= threshold]

        data["memory_data"] = self._convert_from_memory_items(items)
        return data

    def _execute_merge(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行结果合并（merge action）

        通过多次查询服务实现合并，而非从 data 读取多源

        支持的 merge_type:
        - link_expand: 基于链接扩展
        - multi_query: 多次查询合并
        """
        memory_data = data.get("memory_data", [])
        items = self._convert_to_memory_items(memory_data)
        merge_type = self.merge_type

        if merge_type == "link_expand":
            # ---- link_expand 内联 ----
            expand_top_n = int(getattr(self, "expand_top_n", 5))
            max_depth = int(getattr(self, "max_depth", 1))

            # 收集已有的 text，用于去重
            seen_texts = {item.text for item in items}

            # 只扩展 top N 条记忆
            for item in items[:expand_top_n]:
                # 调用服务获取关联记忆
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
                                    items.append(
                                        MemoryItem(
                                            text=text,
                                            score=r.get("score"),
                                            metadata=r.get("metadata", {}),
                                            original_index=-1,
                                        )
                                    )
                                    seen_texts.add(text)
                except Exception as e:  # noqa: BLE001
                    print(f"[WARNING] link_expand: call_service failed: {e}")
                    continue

        elif merge_type == "multi_query":
            # ---- multi_query 内联 ----
            secondary_queries = getattr(self, "secondary_queries", []) or []

            # 收集已有的 text，用于去重
            seen_texts = {item.text for item in items}

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
                                    items.append(
                                        MemoryItem(
                                            text=text,
                                            score=r.get("score"),
                                            metadata=r.get("metadata", {}),
                                            original_index=-1,
                                        )
                                    )
                                    seen_texts.add(text)
                except Exception as e:  # noqa: BLE001
                    print(f"[WARNING] multi_query: call_service failed: {e}")
                    continue

        else:
            print(f"[WARNING] Unknown merge_type: {merge_type}, no merge applied")

        data["memory_data"] = self._convert_from_memory_items(items)
        return data

    def _execute_augment(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行结果增强（augment action）

        支持的 augment_type:
        - reflection: 占位，为记忆生成反思
        - context: 添加上下文信息
        - metadata: 将 metadata 转换为自然语言描述
        - temporal: 添加时间信息
        """
        memory_data = data.get("memory_data", [])
        items = self._convert_to_memory_items(memory_data)
        augment_type = self.augment_type

        if augment_type == "reflection":
            # ---- reflection 内联（占位实现）----
            # 真实实现需要调用 LLMGenerator
            print("[INFO] reflection augment is not implemented in benchmark; keep original items")

        elif augment_type == "context":
            # ---- context 内联 ----
            if self.augment_fields:
                context_parts = []
                for field in self.augment_fields:
                    value = data.get(field)
                    if value is not None:
                        context_parts.append(f"{field}: {value}")

                if context_parts:
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
                    items = result

        elif augment_type == "metadata":
            # ---- metadata 内联 ----
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
            items = result

        elif augment_type == "temporal":
            # ---- temporal 内联 ----
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
            items = result

        else:
            print(f"[WARNING] Unknown augment_type: {augment_type}, no augmentation")

        data["memory_data"] = self._convert_from_memory_items(items)
        return data

    def _execute_compress(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行结果压缩（compress action）

        支持的 compress_type:
        - llmlingua: 占位，基于 LLMLingua 的提示词压缩
        - extractive: 抽取式压缩（保留关键句子）
        - abstractive: 占位，生成式压缩
        """
        memory_data = data.get("memory_data", [])
        items = self._convert_to_memory_items(memory_data)
        compress_type = self.compress_type

        if compress_type == "llmlingua":
            # ---- llmlingua 内联（占位实现）----
            print("[INFO] llmlingua compress is not implemented in benchmark; keep original items")

        elif compress_type == "extractive":
            # ---- extractive 内联 ----
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

            items = result

        elif compress_type == "abstractive":
            # ---- abstractive 内联（占位实现）----
            print(
                "[INFO] abstractive compress is not implemented in benchmark; keep original items"
            )

        else:
            print(f"[WARNING] Unknown compress_type: {compress_type}, no compression")

        data["memory_data"] = self._convert_from_memory_items(items)
        return data

    def _execute_format(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行最终格式化（format action）

        支持的 format_type:
        - template: 模板格式化
        - structured: 结构化分区格式化
        - chat: 对话格式化
        - xml: XML 标签包装
        """
        memory_data = data.get("memory_data", [])
        items = self._convert_to_memory_items(memory_data)
        format_type = self.format_type
        history_text = ""

        if format_type == "template":
            # ---- template 内联 ----
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
                    print(f"[WARNING] Failed to format memory item with template: {e}")
                    memory_lines.append(f"- {item.text}")

            memories_str = "\n".join(memory_lines) if memory_lines else "(No memories)"

            # 如果没有配置 template，返回默认格式
            if not self.format_template:
                history_text = memories_str
            else:
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
                    history_text = self.format_template.format(**template_vars)
                except Exception as e:  # noqa: BLE001
                    print(f"[WARNING] Failed to format template: {e}")
                    history_text = memories_str

        elif format_type == "structured":
            # ---- structured 内联 ----
            if not self.format_structure:
                # 没有配置结构，返回默认格式
                history_text = "\n".join([item.text for item in items])
            else:
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

                history_text = "\n\n".join(sections) if sections else "(No content)"

        elif format_type == "chat":
            # ---- chat 内联 ----
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

            history_text = "\n".join(chat_lines) if chat_lines else "(No conversation)"

        elif format_type == "xml":
            # ---- xml 内联 ----
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

            history_text = "\n".join(xml_parts) if xml_parts else "<empty/>"

        else:
            print(f"[WARNING] Unknown format_type: {format_type}, fallback to template")
            # 默认模板格式
            memory_lines = [f"- {item.text}" for item in items]
            history_text = "\n".join(memory_lines) if memory_lines else "(No memories)"

        data["history_text"] = history_text
        return data
