"""后插入处理模块 - 在记忆插入后的后处理（可选）

支持的 action:
- none: 无操作，直接透传
- distillation: 记忆蒸馏（SCM4LLMs）
- log: 日志记录
- stats: 统计分析
- reflection: 基于累积记忆生成高阶反思（Generative Agents, LoCoMo）
- link_evolution: 管理记忆节点间的链接关系（HippoRAG, A-mem）
- forgetting: 实现记忆遗忘/淘汰机制（MemoryBank, MemoryOS）
- summarize: 对累积记忆进行摘要压缩（MemGPT, MemoryBank, SCM4LLMs）
- migrate: 记忆在不同层级间迁移（MemoryOS, LD-Agent）
"""

from __future__ import annotations

import json
import math
import random
import time
from collections import defaultdict
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction


class PostInsert(MapFunction):
    """记忆插入后的后处理算子

    职责：
    - 触发后续操作
    - 记忆蒸馏（distillation）
    - 反思生成（reflection）
    - 链接演化（link_evolution）
    - 遗忘机制（forgetting）
    - 摘要压缩（summarize）
    - 层级迁移（migrate）
    """

    def __init__(self, config):
        """初始化 PostInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.post_insert.action
        """
        super().__init__()
        self.config = config
        self.action = get_required_config(self.config, "operators.post_insert.action")

        # 服务后端配置
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 图服务名称（用于 link_evolution）
        self.graph_service_name = config.get("services.graph_memory_service", "graph_memory")

        # 分层记忆服务名称（用于 migrate）
        self.hierarchical_service_names = {
            "stm": config.get("services.stm_service", "short_term_memory"),
            "mtm": config.get("services.mtm_service", "mid_term_memory"),
            "ltm": config.get("services.ltm_service", "long_term_memory"),
        }

        # 默认初始化共通工具（LLM 和 Embedding）
        # 这些工具依赖外部模型部署，持有句柄没有问题
        self._generator = LLMGenerator.from_config(self.config)
        self._embedding_generator = EmbeddingGenerator.from_config(self.config)

        # 初始化状态追踪器（用于各种触发机制）
        self._init_state_trackers()

        # 根据 action 初始化特定配置
        self._init_for_action()

    def _init_state_trackers(self):
        """初始化状态追踪器"""
        # 反思触发追踪
        self._importance_accumulator = 0.0
        self._memory_count = 0
        self._last_reflection_time = time.time()
        self._last_session_time = time.time()

        # 遗忘追踪
        self._memory_access_times: dict[str, float] = {}
        self._memory_access_counts: dict[str, int] = defaultdict(int)
        self._memory_strengths: dict[str, float] = defaultdict(lambda: 1.0)

        # 热度追踪（migrate）
        self._memory_heat: dict[str, float] = defaultdict(lambda: 1.0)

        # 摘要追踪
        self._pending_memories: list[dict] = []
        self._last_summarize_time = time.time()
        self._existing_summary = ""

        # 层次摘要
        self._daily_memories: list[dict] = []
        self._weekly_summaries: list[str] = []
        self._global_summary = ""

    def _init_for_action(self):
        """根据 action 类型初始化对应配置"""
        cfg = "operators.post_insert"

        if self.action == "distillation":
            # distillation 配置
            self.distillation_topk = self.config.get(f"{cfg}.distillation_topk", 10)
            self.distillation_threshold = self.config.get(f"{cfg}.distillation_threshold", None)
            self.distillation_prompt = self.config.get(f"{cfg}.distillation_prompt")
            if not self.distillation_prompt:
                raise ValueError("缺少必需的配置: operators.post_insert.distillation_prompt")

        elif self.action == "reflection":
            # reflection 配置
            self.trigger_mode = get_required_config(
                self.config, f"{cfg}.trigger_mode", "action=reflection"
            )
            self.importance_threshold = get_required_config(
                self.config, f"{cfg}.importance_threshold", "trigger_mode=threshold"
            )
            self.importance_field = self.config.get(f"{cfg}.importance_field", "importance_score")
            self.reset_after_reflection = self.config.get(f"{cfg}.reset_after_reflection", True)
            self.interval_minutes = self.config.get(f"{cfg}.interval_minutes", 60)
            self.memory_count_trigger = self.config.get(f"{cfg}.memory_count", 50)
            self.reflection_prompt = get_required_config(
                self.config, f"{cfg}.reflection_prompt", "action=reflection"
            )
            self.reflection_depth = self.config.get(f"{cfg}.reflection_depth", 1)
            self.max_reflections = get_required_config(
                self.config, f"{cfg}.max_reflections", "action=reflection"
            )
            self.reflection_type = self.config.get(f"{cfg}.reflection_type", "general")
            self.self_reflection_prompt = self.config.get(f"{cfg}.self_reflection_prompt")
            self.other_reflection_prompt = self.config.get(f"{cfg}.other_reflection_prompt")
            if self.reflection_type == "self" and not self.self_reflection_prompt:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.self_reflection_prompt (reflection_type=self)"
                )
            if self.reflection_type == "other" and not self.other_reflection_prompt:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.other_reflection_prompt (reflection_type=other)"
                )
            self.store_reflection = self.config.get(f"{cfg}.store_reflection", True)
            self.reflection_importance = self.config.get(f"{cfg}.reflection_importance", 8)

        elif self.action == "link_evolution":
            # link_evolution 配置
            self.link_policy = get_required_config(
                self.config, f"{cfg}.link_policy", "action=link_evolution"
            )
            self.knn_k = get_required_config(
                self.config, f"{cfg}.knn_k", "link_policy=synonym_edge"
            )
            self.similarity_threshold = get_required_config(
                self.config, f"{cfg}.similarity_threshold", "link_policy=synonym_edge"
            )
            self.edge_weight = self.config.get(f"{cfg}.edge_weight", 1.0)
            self.strengthen_factor = self.config.get(f"{cfg}.strengthen_factor", 0.1)
            self.decay_factor = self.config.get(f"{cfg}.decay_factor", 0.01)
            self.max_weight = self.config.get(f"{cfg}.max_weight", 10.0)
            self.activation_depth = self.config.get(f"{cfg}.activation_depth", 2)
            self.activation_decay = self.config.get(f"{cfg}.activation_decay", 0.5)
            self.auto_link_prompt = self.config.get(f"{cfg}.auto_link_prompt")
            self.max_auto_links = self.config.get(f"{cfg}.max_auto_links", 5)
            if self.link_policy == "auto_link" and not self.auto_link_prompt:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.auto_link_prompt (link_policy=auto_link)"
                )

        elif self.action == "forgetting":
            # forgetting 配置
            self.decay_type = get_required_config(
                self.config, f"{cfg}.decay_type", "action=forgetting"
            )
            self.decay_rate = get_required_config(
                self.config, f"{cfg}.decay_rate", "decay_type=time_decay"
            )
            self.decay_floor = self.config.get(f"{cfg}.decay_floor", 0.1)
            self.max_memories = get_required_config(
                self.config, f"{cfg}.max_memories", "decay_type=lru/lfu"
            )
            self.evict_count = self.config.get(f"{cfg}.evict_count", 100)
            self.heat_threshold = self.config.get(f"{cfg}.heat_threshold", 0.3)
            self.heat_decay = self.config.get(f"{cfg}.heat_decay", 0.1)
            self.initial_strength = self.config.get(f"{cfg}.initial_strength", 1.0)
            self.forgetting_curve = self.config.get(f"{cfg}.forgetting_curve", "exponential")
            self.review_boost = self.config.get(f"{cfg}.review_boost", 0.5)
            self.hybrid_factors = self.config.get(f"{cfg}.factors")
            if self.decay_type == "hybrid" and not self.hybrid_factors:
                raise ValueError("缺少必需配置: operators.post_insert.factors (decay_type=hybrid)")
            self.retention_min = self.config.get(f"{cfg}.retention_min", 50)
            self.archive_before_delete = self.config.get(f"{cfg}.archive_before_delete", True)

        elif self.action == "summarize":
            # summarize 配置
            self.trigger_condition = get_required_config(
                self.config, f"{cfg}.trigger_condition", "action=summarize"
            )
            self.overflow_threshold = get_required_config(
                self.config, f"{cfg}.overflow_threshold", "trigger_condition=overflow"
            )
            self.periodic_interval = self.config.get(f"{cfg}.periodic_interval", 3600)
            self.summary_strategy = get_required_config(
                self.config, f"{cfg}.summary_strategy", "action=summarize"
            )
            self.hierarchy_levels = self.config.get(f"{cfg}.hierarchy_levels")
            if self.summary_strategy == "hierarchical" and not self.hierarchy_levels:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.hierarchy_levels (summary_strategy=hierarchical)"
                )
            self.incremental_prompt = self.config.get(f"{cfg}.incremental_prompt")
            if self.summary_strategy == "incremental" and not self.incremental_prompt:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.incremental_prompt (summary_strategy=incremental)"
                )
            self.summarize_prompt = self.config.get(f"{cfg}.summarize_prompt")
            if self.summary_strategy == "single" and not self.summarize_prompt:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.summarize_prompt (summary_strategy=single)"
                )
            self.replace_originals = self.config.get(f"{cfg}.replace_originals", False)
            self.store_as_new = self.config.get(f"{cfg}.store_as_new", True)
            self.summary_importance = self.config.get(f"{cfg}.summary_importance", 7)

        elif self.action == "migrate":
            # migrate 配置
            self.migrate_policy = get_required_config(
                self.config, f"{cfg}.migrate_policy", "action=migrate"
            )
            self.heat_upgrade_threshold = get_required_config(
                self.config, f"{cfg}.heat_upgrade_threshold", "migrate_policy=heat"
            )
            self.cold_threshold = get_required_config(
                self.config, f"{cfg}.cold_threshold", "migrate_policy=heat"
            )
            self.session_gap = get_required_config(
                self.config, f"{cfg}.session_gap", "migrate_policy=time"
            )
            self.tier_capacities = self.config.get(f"{cfg}.tier_capacities")
            if self.migrate_policy == "overflow" and not self.tier_capacities:
                raise ValueError(
                    "缺少必需配置: operators.post_insert.tier_capacities (migrate_policy=overflow)"
                )
            self.upgrade_transform = self.config.get(f"{cfg}.upgrade_transform", "none")
            self.downgrade_transform = self.config.get(f"{cfg}.downgrade_transform", "summarize")

    # ==================== 主执行方法 ====================

    def execute(self, data):
        """执行后处理

        Args:
            data: 由 MemoryInsert 输出的数据，格式：
                {
                    "memory_entries": [条目1, 条目2, ...],  # 已插入但未清空的队列
                    ...其他字段
                }

        Returns:
            处理后的数据（清空队列后透传）
        """
        # 根据 action 模式执行不同操作
        if self.action == "none":
            pass
        elif self.action == "distillation":
            self._distill_memory(data)
        elif self.action == "log":
            self._log_data(data)
        elif self.action == "stats":
            self._analyze_stats(data)
        elif self.action == "reflection":
            self._reflection_process(data)
        elif self.action == "link_evolution":
            self._link_evolution_process(data)
        elif self.action == "forgetting":
            self._forgetting_process(data)
        elif self.action == "summarize":
            self._summarize_process(data)
        elif self.action == "migrate":
            self._migrate_process(data)
        else:
            print(f"未知的 action: {self.action}，跳过处理")

        return data

    def _log_data(self, data):
        """日志记录"""
        log_level = self.config.get("operators.post_insert.log_level", "INFO")
        entries = data.get("memory_entries", [])
        log_msg = f"PostInsert 处理了 {len(entries)} 条记忆条目"
        print(f"[{log_level}] {log_msg}")

    def _analyze_stats(self, data):
        """统计分析"""
        stats_fields = self.config.get("operators.post_insert.stats_fields", ["count", "avg_len"])
        entries = data.get("memory_entries", [])

        stats = {}
        if "count" in stats_fields:
            stats["count"] = len(entries)
        if "avg_len" in stats_fields and entries:
            texts = [e.get("refactor", "") or e.get("text", "") for e in entries]
            stats["avg_len"] = sum(len(t) for t in texts) / len(texts) if texts else 0

        data["post_insert_stats"] = stats
        print(f"PostInsert 统计: {stats}")

    # ==================== Distillation 实现 ====================

    def _distill_memory(self, data):
        """执行记忆蒸馏

        对于每个已插入的三元组，检索相似记忆并进行蒸馏：
        1. 调用搜索服务，检索 Top10，如果结果个数不满足 10 个，跳过
        2. 个数满足 10 个，调用大模型进行蒸馏
        3. 调用删除服务，删除蒸馏过程中被移除的数据
        4. 调用插入服务，依次 embedding 并插入新的数据

        Args:
            data: 包含 memory_entries 的数据字典
        """
        for entry_dict in data.get("memory_entries", []):
            query_vector = entry_dict.get("embedding")

            # Step 1: 检索 Top-K 相似记忆
            results = self._retrieve_memories(query_vector)

            if not results or len(results) < self.distillation_topk:
                continue

            # Step 2: 调用 LLM 进行蒸馏
            memory_texts = [r.get("text", "") for r in results]
            memory_list_str = "\n".join(memory_texts)

            prompt = self.distillation_prompt.replace("{memory_list}", memory_list_str)
            distillation_result = self._generator.generate(prompt)

            # 解析 JSON 格式的蒸馏结果
            result = self._parse_json_response(distillation_result)
            if not result:
                continue

            to_delete_raw = result.get("to_delete", [])
            to_insert_raw = result.get("to_insert", [])

            memory_texts_set = set(memory_texts)

            # 处理 to_delete
            to_delete_set = set()
            for t in to_delete_raw:
                if isinstance(t, str) and t.strip() in memory_texts_set:
                    to_delete_set.add(t.strip())

            # 处理 to_insert
            seen = set()
            new_texts = []
            for t in to_insert_raw:
                if not isinstance(t, str):
                    continue
                t = t.strip()
                if "(" in t or ")" in t:
                    continue
                if t in memory_texts_set:
                    continue
                if t and t not in seen and t not in to_delete_set:
                    seen.add(t)
                    new_texts.append(t)

            # Step 3: 删除记忆
            for text_to_delete in to_delete_set:
                self._delete_memory(text_to_delete)

            # Step 4: 插入新记忆
            if new_texts:
                embeddings = self._embedding_generator.embed_batch(new_texts)
                for i, text in enumerate(new_texts):
                    vector = embeddings[i] if embeddings is not None else None
                    self._insert_memory(text, vector)

    # ==================== Reflection 实现 ====================

    def _reflection_process(self, data):
        """反思处理主流程

        基于累积记忆生成高阶反思/洞察，写回记忆库。
        参考: Generative Agents, LoCoMo

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])

        # 更新状态
        for entry in entries:
            self._memory_count += 1
            importance = entry.get(self.importance_field, 1.0)
            self._importance_accumulator += importance

        # 检查是否触发反思
        should_reflect = self._check_reflection_trigger()

        if should_reflect:
            self._generate_reflections(data)

    def _check_reflection_trigger(self) -> bool:
        """检查是否应该触发反思"""
        if self.trigger_mode == "threshold":
            # 累计重要性阈值触发 (Generative Agents)
            return self._importance_accumulator >= self.importance_threshold

        elif self.trigger_mode == "periodic":
            # 时间间隔触发
            elapsed = (time.time() - self._last_reflection_time) / 60
            return elapsed >= self.interval_minutes

        elif self.trigger_mode == "count":
            # 记忆数量触发 (LoCoMo)
            return self._memory_count >= self.memory_count_trigger

        elif self.trigger_mode == "manual":
            # 手动触发模式，总是返回 False
            return False

        return False

    def _generate_reflections(self, data):
        """生成反思

        Args:
            data: 数据字典
        """
        # 获取最近记忆
        recent_memories = self._get_recent_memories(limit=100)

        if not recent_memories:
            print("没有可用于反思的记忆")
            return

        memory_list_str = "\n".join([f"- {m.get('text', '')}" for m in recent_memories])

        reflections = []

        if self.reflection_type == "general":
            # 通用反思
            reflections = self._generate_general_reflections(memory_list_str)

        elif self.reflection_type == "self":
            # 自我反思 (LoCoMo)
            reflections = self._generate_typed_reflections(
                memory_list_str, self.self_reflection_prompt, "self"
            )

        elif self.reflection_type == "other":
            # 对他人的反思 (LoCoMo)
            reflections = self._generate_typed_reflections(
                memory_list_str, self.other_reflection_prompt, "other"
            )

        # 存储反思
        if self.store_reflection and reflections:
            self._store_reflections(reflections)

        # 重置累计
        if self.reset_after_reflection:
            self._importance_accumulator = 0.0
            self._memory_count = 0
            self._last_reflection_time = time.time()

        # 二阶反思
        if self.reflection_depth >= 2 and reflections:
            self._generate_higher_order_reflections(reflections)

    def _generate_general_reflections(self, memory_list_str: str) -> list[str]:
        """生成通用反思"""
        prompt = self.reflection_prompt.format(
            memory_list=memory_list_str,
            max_reflections=self.max_reflections,
        )

        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        if result and "reflections" in result:
            return result["reflections"][: self.max_reflections]

        # 尝试按行解析
        lines = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return lines[: self.max_reflections]

    def _generate_typed_reflections(
        self, memory_list_str: str, prompt_template: str, reflection_type: str
    ) -> list[str]:
        """生成特定类型的反思"""
        prompt = prompt_template.format(
            memory_list=memory_list_str,
            max_reflections=self.max_reflections,
        )

        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        if result and "reflections" in result:
            return result["reflections"][: self.max_reflections]

        lines = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return lines[: self.max_reflections]

    def _generate_higher_order_reflections(self, base_reflections: list[str]):
        """生成更高阶的反思（二阶反思）"""
        reflection_str = "\n".join([f"- {r}" for r in base_reflections])

        prompt = f"""Based on these insights, what are even higher-level patterns or conclusions?

Insights:
{reflection_str}

Output JSON: {{"higher_reflections": ["...", "..."]}}
"""
        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        if result and "higher_reflections" in result:
            higher_reflections = result["higher_reflections"]
            if self.store_reflection:
                self._store_reflections(higher_reflections, metadata={"reflection_level": 2})

    def _store_reflections(self, reflections: list[str], metadata: dict | None = None):
        """存储反思到记忆库"""
        base_metadata = {
            "type": "reflection",
            "importance_score": self.reflection_importance,
            "timestamp": time.time(),
        }
        if metadata:
            base_metadata.update(metadata)

        for reflection in reflections:
            vector = self._embedding_generator.embed(reflection)
            self._insert_memory(reflection, vector, base_metadata)

    def _get_recent_memories(self, limit: int = 100) -> list[dict]:
        """获取最近的记忆（从服务获取）"""
        try:
            # 尝试调用服务获取最近记忆
            return (
                self.call_service(
                    self.service_name,
                    method="get_recent",
                    limit=limit,
                    timeout=10.0,
                )
                or []
            )
        except Exception:
            # 服务不支持 get_recent，返回空
            return []

    # ==================== Link Evolution 实现 ====================

    def _link_evolution_process(self, data):
        """链接演化处理主流程

        管理记忆节点间的链接关系，包括创建、强化、激活。
        参考: HippoRAG (synonym_edge), A-mem (strengthen, activate)

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])

        for entry in entries:
            if self.link_policy == "synonym_edge":
                self._create_synonym_edges(entry)

            elif self.link_policy == "strengthen":
                self._strengthen_links(entry)

            elif self.link_policy == "activate":
                self._activate_links(entry)

            elif self.link_policy == "auto_link":
                self._create_auto_links(entry)

    def _create_synonym_edges(self, entry: dict):
        """创建同义边 (HippoRAG)

        基于 embedding 相似度，为新实体创建同义边。

        Args:
            entry: 记忆条目
        """
        vector = entry.get("embedding")
        if vector is None:
            return

        # 获取 KNN 近邻
        try:
            similar_entries = self._retrieve_memories(vector, topk=self.knn_k)
        except Exception as e:
            print(f"检索相似记忆失败: {e}")
            return

        if not similar_entries:
            return

        entry_id = entry.get("id") or entry.get("refactor", "")[:32]

        # 为相似度超过阈值的条目创建同义边
        for sim_entry in similar_entries:
            score = sim_entry.get("score", 0)
            if score >= self.similarity_threshold:
                target_id = sim_entry.get("id") or sim_entry.get("text", "")[:32]

                # 调用图服务创建边
                self._create_graph_edge(
                    source=entry_id,
                    target=target_id,
                    edge_type="synonym",
                    weight=score * self.edge_weight,
                )

    def _strengthen_links(self, entry: dict):
        """强化链接 (A-mem)

        访问时增加链接权重，未访问时衰减。

        Args:
            entry: 记忆条目
        """
        entry_id = entry.get("id") or entry.get("refactor", "")[:32]

        # 获取相关记忆
        vector = entry.get("embedding")
        if vector is None:
            return

        try:
            related = self._retrieve_memories(vector, topk=5)
        except Exception:
            return

        for rel in related:
            target_id = rel.get("id") or rel.get("text", "")[:32]

            # 增强链接
            try:
                self.call_service(
                    self.graph_service_name,
                    method="strengthen_link",
                    src_id=entry_id,
                    dst_id=target_id,
                    delta=self.strengthen_factor,
                    timeout=5.0,
                )
            except Exception:
                pass

    def _activate_links(self, entry: dict):
        """激活传播 (A-mem)

        新记忆插入后激活相关记忆，传播激活到邻居。

        Args:
            entry: 记忆条目
        """
        entry_id = entry.get("id") or entry.get("refactor", "")[:32]

        # 递归激活
        self._propagate_activation(entry_id, depth=self.activation_depth, decay=1.0)

    def _propagate_activation(self, node_id: str, depth: int, decay: float):
        """递归传播激活"""
        if depth <= 0 or decay < 0.01:
            return

        # 更新节点激活值
        try:
            self.call_service(
                self.graph_service_name,
                method="update_activation",
                node_id=node_id,
                activation_delta=decay,
                timeout=5.0,
            )

            # 获取邻居
            neighbors = (
                self.call_service(
                    self.graph_service_name,
                    method="get_neighbors",
                    node_id=node_id,
                    timeout=5.0,
                )
                or []
            )

            # 递归激活邻居
            new_decay = decay * self.activation_decay
            for neighbor_id in neighbors:
                self._propagate_activation(neighbor_id, depth - 1, new_decay)

        except Exception as e:
            print(f"激活传播失败: {e}")

    def _create_auto_links(self, entry: dict):
        """自动链接 (A-mem)

        使用 LLM 推荐应该链接的记忆。

        Args:
            entry: 记忆条目
        """
        new_memory_text = entry.get("refactor", "") or entry.get("text", "")
        vector = entry.get("embedding")

        if not new_memory_text:
            return

        # 获取候选记忆
        try:
            candidates = self._retrieve_memories(vector, topk=self.max_auto_links * 2)
        except Exception:
            return

        if not candidates:
            return

        # 格式化候选记忆
        existing_memories = "\n".join(
            [f"{i}. {c.get('text', '')}" for i, c in enumerate(candidates)]
        )

        prompt = self.auto_link_prompt.format(
            new_memory=new_memory_text,
            existing_memories=existing_memories,
        )

        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        if result and "links" in result:
            entry_id = entry.get("id") or new_memory_text[:32]
            link_indices = result["links"][: self.max_auto_links]

            for idx in link_indices:
                if 0 <= idx < len(candidates):
                    target = candidates[idx]
                    target_id = target.get("id") or target.get("text", "")[:32]
                    self._create_graph_edge(
                        source=entry_id,
                        target=target_id,
                        edge_type="auto_link",
                        weight=self.edge_weight,
                    )

    def _create_graph_edge(self, source: str, target: str, edge_type: str, weight: float):
        """创建图边"""
        try:
            self.call_service(
                self.graph_service_name,
                method="add_edge",
                source=source,
                target=target,
                edge_type=edge_type,
                weight=weight,
                timeout=5.0,
            )
        except Exception as e:
            print(f"创建图边失败: {e}")

    # ==================== Forgetting 实现 ====================

    def _forgetting_process(self, data):
        """遗忘处理主流程

        实现记忆遗忘/淘汰机制。
        参考: MemoryBank (ebbinghaus), MemoryOS (lfu)

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])

        # 更新访问记录
        current_time = time.time()
        for entry in entries:
            entry_id = entry.get("id") or entry.get("refactor", "")[:32]
            self._memory_access_times[entry_id] = current_time
            self._memory_access_counts[entry_id] += 1

        # 根据遗忘类型执行
        if self.decay_type == "time_decay":
            self._apply_time_decay()

        elif self.decay_type == "lru":
            self._apply_lru_eviction()

        elif self.decay_type == "lfu":
            self._apply_lfu_eviction()

        elif self.decay_type == "ebbinghaus":
            self._apply_ebbinghaus_forgetting()

        elif self.decay_type == "hybrid":
            self._apply_hybrid_forgetting()

    def _apply_time_decay(self):
        """应用时间衰减"""
        current_time = time.time()
        to_forget = []

        for entry_id, last_access in self._memory_access_times.items():
            # 计算时间差（小时）
            hours_elapsed = (current_time - last_access) / 3600

            # 指数衰减
            retention = math.exp(-self.decay_rate * hours_elapsed)

            if retention < self.decay_floor:
                to_forget.append(entry_id)

        # 保留最小数量
        if len(self._memory_access_times) - len(to_forget) < self.retention_min:
            # 按衰减程度排序，只删除最低的
            sorted_entries = sorted(
                to_forget,
                key=lambda x: self._memory_access_times.get(x, 0),
            )
            to_forget = sorted_entries[: len(self._memory_access_times) - self.retention_min]

        self._forget_memories(to_forget)

    def _apply_lru_eviction(self):
        """应用 LRU 淘汰"""
        if len(self._memory_access_times) <= self.max_memories:
            return

        # 按最后访问时间排序
        sorted_entries = sorted(
            self._memory_access_times.items(),
            key=lambda x: x[1],
        )

        # 淘汰最旧的
        to_evict = self.evict_count
        to_evict = min(to_evict, len(sorted_entries) - self.retention_min)

        to_forget = [entry_id for entry_id, _ in sorted_entries[:to_evict]]
        self._forget_memories(to_forget)

    def _apply_lfu_eviction(self):
        """应用 LFU 淘汰 (MemoryOS)"""
        if len(self._memory_access_counts) <= self.max_memories:
            return

        current_time = time.time()

        # 计算热度: 访问次数 + 时间衰减
        heat_scores = {}
        for entry_id, count in self._memory_access_counts.items():
            last_access = self._memory_access_times.get(entry_id, current_time)
            time_decay = math.exp(-self.heat_decay * (current_time - last_access) / 3600)
            heat_scores[entry_id] = count * time_decay

        # 找出低热度记忆
        sorted_by_heat = sorted(heat_scores.items(), key=lambda x: x[1])

        to_forget = []
        for entry_id, heat in sorted_by_heat:
            if heat < self.heat_threshold:
                to_forget.append(entry_id)
            if len(self._memory_access_counts) - len(to_forget) <= self.retention_min:
                break

        self._forget_memories(to_forget)

    def _apply_ebbinghaus_forgetting(self):
        """应用艾宾浩斯遗忘曲线 (MemoryBank)

        遗忘曲线: R(t) = e^(-t/(5*S))
        其中 t 是时间（天），S 是记忆强度
        """
        current_time = time.time()
        to_forget = []

        for entry_id, last_access in self._memory_access_times.items():
            # 计算时间差（天）
            days_elapsed = (current_time - last_access) / 86400

            # 获取记忆强度
            strength = self._memory_strengths.get(entry_id, self.initial_strength)

            # 艾宾浩斯遗忘曲线
            if self.forgetting_curve == "exponential":
                retention = math.exp(-days_elapsed / (5 * strength))
            else:  # power
                retention = 1 / (1 + days_elapsed / strength)

            # 概率遗忘
            if random.random() > retention:
                to_forget.append(entry_id)

        # 保留最小数量
        if len(self._memory_access_times) - len(to_forget) < self.retention_min:
            to_forget = to_forget[: len(self._memory_access_times) - self.retention_min]

        self._forget_memories(to_forget)

    def _apply_hybrid_forgetting(self):
        """应用混合遗忘策略"""
        current_time = time.time()
        composite_scores = {}

        for entry_id in self._memory_access_times:
            score = 0.0

            for factor in self.hybrid_factors:
                factor_type = factor.get("type", "time")
                factor_weight = factor.get("weight", 0.33)

                if factor_type == "time":
                    last_access = self._memory_access_times.get(entry_id, current_time)
                    days = (current_time - last_access) / 86400
                    time_score = 1 / (1 + days)
                    score += factor_weight * time_score

                elif factor_type == "frequency":
                    count = self._memory_access_counts.get(entry_id, 1)
                    freq_score = min(count / 10, 1.0)
                    score += factor_weight * freq_score

                elif factor_type == "importance":
                    # 默认重要性为 0.5
                    importance = 0.5
                    score += factor_weight * importance

            composite_scores[entry_id] = score

        # 按分数排序，淘汰最低的
        sorted_entries = sorted(composite_scores.items(), key=lambda x: x[1])

        to_forget = []
        threshold = 0.3  # 可配置

        for entry_id, score in sorted_entries:
            if score < threshold:
                to_forget.append(entry_id)
            if len(self._memory_access_times) - len(to_forget) <= self.retention_min:
                break

        self._forget_memories(to_forget)

    def _forget_memories(self, entry_ids: list[str]):
        """执行遗忘（删除记忆）"""
        for entry_id in entry_ids:
            # 归档
            if self.archive_before_delete:
                try:
                    self.call_service(
                        "archive_memory",
                        method="archive",
                        entry_id=entry_id,
                        timeout=5.0,
                    )
                except Exception:
                    pass  # 归档服务可能不存在

            # 删除
            try:
                self._delete_memory(entry_id)
            except Exception as e:
                print(f"删除记忆失败 {entry_id}: {e}")

            # 清理追踪器
            self._memory_access_times.pop(entry_id, None)
            self._memory_access_counts.pop(entry_id, None)
            self._memory_strengths.pop(entry_id, None)

    def update_memory_on_recall(self, entry_id: str):
        """当记忆被召回时更新强度 (供外部调用)"""
        self._memory_access_times[entry_id] = time.time()
        self._memory_access_counts[entry_id] += 1
        self._memory_strengths[entry_id] = (
            self._memory_strengths.get(entry_id, self.initial_strength) + self.review_boost
        )

    # ==================== Summarize 实现 ====================

    def _summarize_process(self, data):
        """摘要处理主流程

        对累积记忆进行摘要压缩。
        参考: MemGPT (overflow), MemoryBank (hierarchical), SCM4LLMs (incremental)

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])
        self._pending_memories.extend(entries)

        # 检查触发条件
        should_summarize = self._check_summarize_trigger()

        if should_summarize:
            if self.summary_strategy == "single":
                self._single_summarize()

            elif self.summary_strategy == "hierarchical":
                self._hierarchical_summarize()

            elif self.summary_strategy == "incremental":
                self._incremental_summarize()

    def _check_summarize_trigger(self) -> bool:
        """检查是否应该触发摘要"""
        if self.trigger_condition == "overflow":
            return len(self._pending_memories) >= self.overflow_threshold

        elif self.trigger_condition == "periodic":
            elapsed = time.time() - self._last_summarize_time
            return elapsed >= self.periodic_interval

        elif self.trigger_condition == "manual":
            return False

        return False

    def _single_summarize(self):
        """单次摘要"""
        if not self._pending_memories:
            return

        memory_list_str = "\n".join(
            [f"- {m.get('refactor', '') or m.get('text', '')}" for m in self._pending_memories]
        )

        prompt = self.summarize_prompt.format(memory_list=memory_list_str)
        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        summary = result.get("summary", response) if result else response

        # 存储摘要
        if self.store_as_new:
            vector = self._embedding_generator.embed(summary)
            metadata = {
                "type": "summary",
                "importance_score": self.summary_importance,
                "source_count": len(self._pending_memories),
                "timestamp": time.time(),
            }
            self._insert_memory(summary, vector, metadata)

        # 替换原始记忆
        if self.replace_originals:
            for mem in self._pending_memories:
                entry_text = mem.get("refactor", "") or mem.get("text", "")
                if entry_text:
                    self._delete_memory(entry_text)

        self._pending_memories.clear()
        self._last_summarize_time = time.time()

    def _hierarchical_summarize(self):
        """层次摘要 (MemoryBank)

        日/周/全局多层次摘要
        """
        current_time = time.time()

        for level_config in self.hierarchy_levels:
            level_name = level_config.get("name", "daily")
            window = level_config.get("window", 86400)
            prompt_template = level_config.get("prompt")
            if not prompt_template:
                raise ValueError(f"缺少必需配置: hierarchy_levels[{level_name}].prompt")

            # 根据时间窗口筛选记忆
            if window > 0:
                relevant_memories = [
                    m
                    for m in self._pending_memories
                    if current_time - m.get("timestamp", current_time) <= window
                ]
            else:
                relevant_memories = self._pending_memories[:]

            if not relevant_memories:
                continue

            memory_list_str = "\n".join(
                [f"- {m.get('refactor', '') or m.get('text', '')}" for m in relevant_memories]
            )

            prompt = prompt_template.format(memory_list=memory_list_str)
            response = self._generator.generate(prompt)
            result = self._parse_json_response(response)

            summary = result.get("summary", response) if result else response

            # 存储摘要
            if self.store_as_new:
                vector = self._embedding_generator.embed(summary)
                metadata = {
                    "type": f"{level_name}_summary",
                    "importance_score": self.summary_importance,
                    "level": level_name,
                    "timestamp": current_time,
                }
                self._insert_memory(summary, vector, metadata)

            # 更新层级状态
            if level_name == "daily":
                self._daily_memories.clear()
            elif level_name == "weekly":
                self._weekly_summaries.append(summary)
            elif level_name == "global":
                self._global_summary = summary

        # 清空 pending
        if self.replace_originals:
            for mem in self._pending_memories:
                entry_text = mem.get("refactor", "") or mem.get("text", "")
                if entry_text:
                    self._delete_memory(entry_text)

        self._pending_memories.clear()
        self._last_summarize_time = time.time()

    def _incremental_summarize(self):
        """增量摘要 (SCM4LLMs)"""
        if not self._pending_memories:
            return

        new_memories_str = "\n".join(
            [f"- {m.get('refactor', '') or m.get('text', '')}" for m in self._pending_memories]
        )

        prompt = self.incremental_prompt.format(
            existing_summary=self._existing_summary or "No existing summary.",
            new_memories=new_memories_str,
        )

        response = self._generator.generate(prompt)
        result = self._parse_json_response(response)

        summary = result.get("summary", response) if result else response
        self._existing_summary = summary

        # 存储更新的摘要
        if self.store_as_new:
            vector = self._embedding_generator.embed(summary)
            metadata = {
                "type": "incremental_summary",
                "importance_score": self.summary_importance,
                "timestamp": time.time(),
            }
            self._insert_memory(summary, vector, metadata)

        self._pending_memories.clear()
        self._last_summarize_time = time.time()

    # ==================== Migrate 实现 ====================

    def _migrate_process(self, data):
        """迁移处理主流程

        记忆在不同层级间迁移。
        参考: MemoryOS (heat), LD-Agent (time)

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])
        current_time = time.time()

        # 更新热度
        for entry in entries:
            entry_id = entry.get("id") or entry.get("refactor", "")[:32]
            self._memory_heat[entry_id] = 1.0  # 新记忆热度为 1

        if self.migrate_policy == "heat":
            self._heat_based_migration()

        elif self.migrate_policy == "time":
            self._time_based_migration(current_time)

        elif self.migrate_policy == "overflow":
            self._overflow_based_migration()

    def _heat_based_migration(self):
        """基于热度的迁移 (MemoryOS)"""
        to_upgrade = []
        to_downgrade = []

        for entry_id, heat in self._memory_heat.items():
            if heat >= self.heat_upgrade_threshold:
                to_upgrade.append((entry_id, heat))
            elif heat <= self.cold_threshold:
                to_downgrade.append((entry_id, heat))

        # 升级: STM → MTM 或 MTM → LTM
        for entry_id, _ in to_upgrade:
            self._migrate_memory(entry_id, direction="upgrade")

        # 降级: MTM → LTM (压缩后)
        for entry_id, _ in to_downgrade:
            self._migrate_memory(entry_id, direction="downgrade")

    def _time_based_migration(self, current_time: float):
        """基于时间间隔的迁移 (LD-Agent)

        会话间隔超过阈值时，将 STM 摘要后转入 LTM
        """
        time_gap = current_time - self._last_session_time

        if time_gap >= self.session_gap:
            # 获取当前 STM 中的所有记忆
            try:
                stm_memories = (
                    self.call_service(
                        self.hierarchical_service_names["stm"],
                        method="get_all",
                        timeout=10.0,
                    )
                    or []
                )
            except Exception:
                stm_memories = []

            if stm_memories:
                # 摘要 STM 内容
                memory_texts = [m.get("text", "") for m in stm_memories]
                summary = self._generate_session_summary(memory_texts)

                # 存入 LTM
                if summary:
                    vector = self._embedding_generator.embed(summary)
                    metadata = {
                        "type": "session_summary",
                        "session_time": self._last_session_time,
                        "memory_count": len(stm_memories),
                    }
                    try:
                        self.call_service(
                            self.hierarchical_service_names["ltm"],
                            method="insert",
                            entry=summary,
                            vector=vector,
                            metadata=metadata,
                            timeout=10.0,
                        )
                    except Exception as e:
                        print(f"存入 LTM 失败: {e}")

                # 清空 STM
                for mem in stm_memories:
                    try:
                        self.call_service(
                            self.hierarchical_service_names["stm"],
                            method="delete",
                            entry=mem.get("text", ""),
                            timeout=5.0,
                        )
                    except Exception:
                        pass

            self._last_session_time = current_time

    def _overflow_based_migration(self):
        """基于溢出的迁移"""
        # 检查 STM 容量
        stm_capacity = self.tier_capacities.get("stm", 100)

        try:
            stm_count = (
                self.call_service(
                    self.hierarchical_service_names["stm"],
                    method="count",
                    timeout=5.0,
                )
                or 0
            )
        except Exception:
            return

        if stm_count > stm_capacity:
            # 计算需要迁移的数量
            overflow_count = stm_count - stm_capacity

            # 获取最旧的记忆
            try:
                oldest_memories = (
                    self.call_service(
                        self.hierarchical_service_names["stm"],
                        method="get_oldest",
                        limit=overflow_count,
                        timeout=10.0,
                    )
                    or []
                )
            except Exception:
                oldest_memories = []

            for mem in oldest_memories:
                entry_id = mem.get("id") or mem.get("text", "")[:32]
                self._migrate_memory(entry_id, direction="downgrade")

    def _migrate_memory(self, entry_id: str, direction: str):
        """执行单条记忆的迁移"""
        try:
            # 获取原始记忆内容
            # 假设使用 entry_id 作为文本或从服务获取
            memory_content = entry_id  # 简化处理

            if direction == "upgrade":
                transform = self.upgrade_transform
                target_service = self.hierarchical_service_names["mtm"]
            else:
                transform = self.downgrade_transform
                target_service = self.hierarchical_service_names["ltm"]

            # 应用转换
            if transform == "summarize":
                prompt = f"Summarize this memory concisely:\n{memory_content}"
                response = self._generator.generate(prompt)
                final_content = response.strip()
            elif transform == "compress":
                final_content = memory_content[:100]  # 简单截断
            else:
                final_content = memory_content

            # 生成 embedding
            vector = self._embedding_generator.embed(final_content)

            # 插入目标层
            self.call_service(
                target_service,
                method="insert",
                entry=final_content,
                vector=vector,
                metadata={"migrated_from": entry_id, "timestamp": time.time()},
                timeout=10.0,
            )

            # 从源层删除
            self._delete_memory(entry_id)

            print(f"记忆 {entry_id} 已迁移 ({direction})")

        except Exception as e:
            print(f"迁移记忆失败 {entry_id}: {e}")

    def _generate_session_summary(self, memory_texts: list[str]) -> str:
        """生成会话摘要"""
        if not memory_texts:
            return ""

        memory_list_str = "\n".join([f"- {t}" for t in memory_texts])
        prompt = f"""Summarize the following conversation/memories in brief sentences (within 50 words):

{memory_list_str}

Summary:"""

        return self._generator.generate(prompt).strip()

    # ==================== 服务调用方法 ====================

    def _retrieve_memories(
        self, vector, topk: int | None = None, threshold: int | None = None
    ) -> list:
        """检索相似记忆

        Args:
            vector: 查询向量
            topk: 返回数量
            threshold: 汉明距离阈值

        Returns:
            检索结果列表，每个元素包含 text 和 metadata
        """
        default_topk = getattr(self, "distillation_topk", 10)
        default_threshold = getattr(self, "distillation_threshold", None)

        return self.call_service(
            self.service_name,
            vector=vector,
            topk=topk or default_topk,
            threshold=threshold if threshold is not None else default_threshold,
            method="retrieve",
            timeout=10.0,
        )

    def _delete_memory(self, entry: str) -> bool:
        """删除记忆条目

        Args:
            entry: 要删除的文本

        Returns:
            是否删除成功
        """
        return self.call_service(
            self.service_name,
            entry=entry,
            method="delete",
            timeout=10.0,
        )

    def _insert_memory(self, entry: str, vector=None, metadata: dict | None = None) -> bool:
        """插入记忆条目

        Args:
            entry: 文本内容
            vector: embedding 向量
            metadata: 元数据

        Returns:
            是否插入成功
        """
        return self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            method="insert",
            timeout=10.0,
        )

    # ==================== 辅助方法 ====================

    def _parse_json_response(self, response: str) -> dict | None:
        """解析 JSON 格式的响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，失败返回 None
        """
        try:
            result_text = response.strip()
            start_idx = result_text.find("{")
            end_idx = result_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                return None

            json_str = result_text[start_idx:end_idx]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def get_state(self) -> dict[str, Any]:
        """获取当前状态（用于调试和持久化）"""
        return {
            "importance_accumulator": self._importance_accumulator,
            "memory_count": self._memory_count,
            "last_reflection_time": self._last_reflection_time,
            "pending_memories_count": len(self._pending_memories),
            "tracked_memories_count": len(self._memory_access_times),
            "existing_summary_length": len(self._existing_summary),
        }

    def reset_state(self):
        """重置状态"""
        self._init_state_trackers()

    def trigger_reflection(self, data: dict | None = None) -> list[str]:
        """手动触发反思（用于 manual 模式）

        Args:
            data: 可选的数据字典

        Returns:
            生成的反思列表
        """
        original_mode = self.trigger_mode
        self.trigger_mode = "threshold"
        self._importance_accumulator = self.importance_threshold

        self._generate_reflections(data or {})

        self.trigger_mode = original_mode
        return []  # 反思已存储，返回空

    def trigger_summarize(self):
        """手动触发摘要"""
        original_condition = self.trigger_condition
        self.trigger_condition = "overflow"
        self._pending_memories = self._pending_memories or [{"text": "placeholder"}]

        original_threshold = self.overflow_threshold
        self.overflow_threshold = 0

        self._summarize_process({})

        self.trigger_condition = original_condition
        self.overflow_threshold = original_threshold
