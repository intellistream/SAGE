"""后插入处理模块 - 在记忆插入后的后处理（可选）

支持的 action:
- none: 无操作，直接透传
- log: 日志记录
- stats: 统计分析
- distillation: 记忆蒸馏（SCM4LLMs）- 算子级实现

服务级操作（委托给服务的 optimize() 方法）:
- reflection: 基于累积记忆生成高阶反思（Generative Agents, LoCoMo）
- link_evolution: 管理记忆节点间的链接关系（HippoRAG, A-mem）
- forgetting: 实现记忆遗忘/淘汰机制（MemoryBank, MemoryOS）
- summarize: 对累积记忆进行摘要压缩（MemGPT, MemoryBank, SCM4LLMs）
- migrate: 记忆在不同层级间迁移（MemoryOS, LD-Agent）

架构约束:
- 只与单一记忆服务交互（通过 service_name）
- 遵循"仅允许一次 检索→删除→插入"约束
- 将复杂逻辑委托给记忆服务的 optimize() 方法
"""

from __future__ import annotations

import json
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction

# 算子级操作列表（PostInsert 自己实现）
OPERATOR_LEVEL_ACTIONS = {"none", "log", "stats", "distillation"}

# 服务级操作列表（委托给服务的 optimize() 方法）
SERVICE_LEVEL_ACTIONS = {"reflection", "link_evolution", "forgetting", "summarize", "migrate"}


class PostInsert(MapFunction):
    """记忆插入后的后处理算子

    职责：
    - 触发记忆服务的优化操作（服务级操作）
    - 执行简单的算子级操作（log, stats, distillation）

    约束：
    - 只与单一记忆服务交互
    - 复杂优化逻辑委托给服务的 optimize() 方法
    - distillation 执行一次 检索→删除→插入（符合规范）
    """

    def __init__(self, config):
        """初始化 PostInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.post_insert.action
        """
        super().__init__()
        self.config = config
        self.action = get_required_config(self.config, "operators.post_insert.action")

        # 只引用单一服务
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 共通工具
        self._generator = LLMGenerator.from_config(self.config)
        self._embedding_generator = EmbeddingGenerator.from_config(self.config)

        # 根据 action 初始化配置
        self._init_for_action()

    def _init_for_action(self):
        """根据 action 类型初始化对应配置

        - 算子级操作: 需要加载完整配置
        - 服务级操作: 只需收集配置参数，委托给服务
        """
        cfg = "operators.post_insert"

        if self.action == "distillation":
            # distillation 是算子级操作，需要完整配置
            self.distillation_topk = self.config.get(f"{cfg}.distillation_topk", 10)
            self.distillation_threshold = self.config.get(f"{cfg}.distillation_threshold", None)
            self.distillation_prompt = self.config.get(f"{cfg}.distillation_prompt")
            if not self.distillation_prompt:
                raise ValueError("缺少必需的配置: operators.post_insert.distillation_prompt")

        elif self.action in SERVICE_LEVEL_ACTIONS:
            # 服务级操作：收集配置参数（将传递给服务的 optimize() 方法）
            self._action_config = self._collect_action_config()

    def _collect_action_config(self) -> dict[str, Any]:
        """收集当前 action 的所有配置参数

        Returns:
            配置参数字典，将传递给服务的 optimize() 方法
        """
        cfg = "operators.post_insert"

        # 通用配置收集器：定义每个 action 需要收集的配置键
        config_keys = {
            "reflection": [
                "trigger_mode",
                "importance_threshold",
                "importance_field",
                "reset_after_reflection",
                "interval_minutes",
                "memory_count",
                "reflection_prompt",
                "reflection_depth",
                "max_reflections",
                "reflection_type",
                "self_reflection_prompt",
                "other_reflection_prompt",
                "store_reflection",
                "reflection_importance",
            ],
            "link_evolution": [
                "link_policy",
                "knn_k",
                "similarity_threshold",
                "edge_weight",
                "strengthen_factor",
                "decay_factor",
                "max_weight",
                "activation_depth",
                "activation_decay",
                "auto_link_prompt",
                "max_auto_links",
            ],
            "forgetting": [
                "decay_type",
                "decay_rate",
                "decay_floor",
                "max_memories",
                "evict_count",
                "heat_threshold",
                "heat_decay",
                "initial_strength",
                "forgetting_curve",
                "review_boost",
                "factors",
                "retention_min",
                "archive_before_delete",
            ],
            "summarize": [
                "trigger_condition",
                "overflow_threshold",
                "periodic_interval",
                "summary_strategy",
                "hierarchy_levels",
                "incremental_prompt",
                "summarize_prompt",
                "replace_originals",
                "store_as_new",
                "summary_importance",
            ],
            "migrate": [
                "migrate_policy",
                "heat_upgrade_threshold",
                "cold_threshold",
                "session_gap",
                "tier_capacities",
                "upgrade_transform",
                "downgrade_transform",
            ],
        }

        # 根据 action 收集配置
        keys = config_keys.get(self.action, [])
        return {key: self.config.get(f"{cfg}.{key}") for key in keys}

    # ==================== 主执行方法 ====================

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行后处理

        Args:
            data: 由 MemoryInsert 输出的数据，格式：
                {
                    "memory_entries": [条目1, 条目2, ...],  # 已插入但未清空的队列
                    ...其他字段
                }

        Returns:
            处理后的数据
        """
        # 算子级操作处理器映射
        operator_handlers = {
            "none": self._execute_none,
            "log": self._execute_log,
            "stats": self._execute_stats,
            "distillation": self._execute_distillation,
        }

        if self.action in operator_handlers:
            operator_handlers[self.action](data)
        elif self.action in SERVICE_LEVEL_ACTIONS:
            # 服务级操作统一入口
            self._execute_service_optimize(data)
        else:
            print(f"[WARNING] Unknown action: {self.action}, skipping")

        return data

    # ==================== 算子级操作 ====================

    def _execute_none(self, data: dict[str, Any]) -> None:
        """无操作，直接透传"""
        pass

    def _execute_log(self, data: dict[str, Any]) -> None:
        """日志记录"""
        log_level = self.config.get("operators.post_insert.log_level", "INFO")
        entries = data.get("memory_entries", [])
        log_msg = f"PostInsert 处理了 {len(entries)} 条记忆条目"
        print(f"[{log_level}] {log_msg}")

    def _execute_stats(self, data: dict[str, Any]) -> None:
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

    # ==================== Distillation 实现（符合规范）====================

    def _execute_distillation(self, data: dict[str, Any]) -> None:
        """执行记忆蒸馏（符合"一次 检索→删除→插入"规范）

        流程（严格顺序，每步只执行一次）：
        1. 检索相似记忆（一次检索）
        2. LLM 判断需要合并/删除的记忆
        3. 删除旧记忆（一次删除，批量）
        4. 插入蒸馏后的新记忆（一次插入）

        Args:
            data: 包含 memory_entries 的数据字典
        """
        for entry_dict in data.get("memory_entries", []):
            # 获取当前条目的文本和向量
            text = entry_dict.get("refactor", "") or entry_dict.get("text", "")
            vector = entry_dict.get("embedding")

            if not text or vector is None:
                continue

            # ========== 第一步：检索（仅一次）==========
            similar_entries = self.call_service(
                self.service_name,
                method="retrieve",
                query=text,
                vector=vector,
                top_k=self.distillation_topk,
                threshold=self.distillation_threshold,
                timeout=10.0,
            )

            if not similar_entries:
                continue

            # ========== 第二步：LLM 分析 ==========
            distilled_text, to_delete = self._analyze_for_distillation(entry_dict, similar_entries)

            if not distilled_text and not to_delete:
                continue

            # ========== 第三步：删除（仅一次，批量）==========
            for entry_id in to_delete:
                self.call_service(
                    self.service_name,
                    method="delete",
                    entry_id=entry_id,
                    timeout=5.0,
                )

            # ========== 第四步：插入（仅一次）==========
            if distilled_text:
                distilled_vector = self._embedding_generator.embed(distilled_text)
                self.call_service(
                    self.service_name,
                    method="insert",
                    entry=distilled_text,
                    vector=distilled_vector,
                    metadata={"distilled": True, "source_count": len(to_delete) + 1},
                    timeout=10.0,
                )

    def _analyze_for_distillation(
        self, entry_dict: dict, similar_entries: list[dict]
    ) -> tuple[str | None, list[str]]:
        """分析需要蒸馏的内容（内联实现）

        Args:
            entry_dict: 当前条目
            similar_entries: 相似记忆列表

        Returns:
            (蒸馏后的文本, 需要删除的记忆ID列表)
        """
        memory_texts = [r.get("text", "") for r in similar_entries]
        memory_ids = [r.get("entry_id", "") for r in similar_entries]
        memory_list_str = "\n".join(f"[{i}] {t}" for i, t in enumerate(memory_texts))

        prompt = self.distillation_prompt.replace("{memory_list}", memory_list_str)
        response = self._generator.generate(prompt)

        result = self._parse_json_response(response)
        if not result:
            return None, []

        # 解析 to_delete（索引列表）
        to_delete_indices = result.get("to_delete", [])
        to_delete_ids = [memory_ids[i] for i in to_delete_indices if i < len(memory_ids)]

        # 解析 to_insert（合并后的文本）
        distilled_text = result.get("distilled_text", result.get("to_insert"))

        return distilled_text, to_delete_ids

    # ==================== 服务级操作（委托给服务）====================

    def _execute_service_optimize(self, data: dict[str, Any]) -> None:
        """执行服务级优化操作

        将 reflection, link_evolution, forgetting, summarize, migrate
        等复杂操作委托给记忆服务的 optimize() 方法

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])

        # 收集配置参数
        config = self._collect_action_config()

        # 调用服务的 optimize 方法
        try:
            result = self.call_service(
                self.service_name,
                trigger=self.action,
                config=config,
                entries=entries,
                method="optimize",
                timeout=30.0,
            )

            # 记录结果
            if result:
                data["optimize_result"] = result
                print(f"服务优化完成: {self.action}")

        except Exception as e:
            print(f"服务优化失败 ({self.action}): {e}")

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
        """获取当前状态（用于调试）

        Returns:
            状态字典
        """
        return {
            "action": self.action,
            "service_name": self.service_name,
            "is_operator_level": self.action in OPERATOR_LEVEL_ACTIONS,
            "is_service_level": self.action in SERVICE_LEVEL_ACTIONS,
        }
