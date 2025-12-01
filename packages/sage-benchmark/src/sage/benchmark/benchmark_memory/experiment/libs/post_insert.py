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
        action_config: dict[str, Any] = {}

        if self.action == "reflection":
            action_config = {
                "trigger_mode": self.config.get(f"{cfg}.trigger_mode", "threshold"),
                "importance_threshold": self.config.get(f"{cfg}.importance_threshold", 100),
                "importance_field": self.config.get(f"{cfg}.importance_field", "importance_score"),
                "reset_after_reflection": self.config.get(f"{cfg}.reset_after_reflection", True),
                "interval_minutes": self.config.get(f"{cfg}.interval_minutes", 60),
                "memory_count_trigger": self.config.get(f"{cfg}.memory_count", 50),
                "reflection_prompt": self.config.get(f"{cfg}.reflection_prompt"),
                "reflection_depth": self.config.get(f"{cfg}.reflection_depth", 1),
                "max_reflections": self.config.get(f"{cfg}.max_reflections", 5),
                "reflection_type": self.config.get(f"{cfg}.reflection_type", "general"),
                "self_reflection_prompt": self.config.get(f"{cfg}.self_reflection_prompt"),
                "other_reflection_prompt": self.config.get(f"{cfg}.other_reflection_prompt"),
                "store_reflection": self.config.get(f"{cfg}.store_reflection", True),
                "reflection_importance": self.config.get(f"{cfg}.reflection_importance", 8),
            }

        elif self.action == "link_evolution":
            action_config = {
                "link_policy": self.config.get(f"{cfg}.link_policy", "synonym_edge"),
                "knn_k": self.config.get(f"{cfg}.knn_k", 10),
                "similarity_threshold": self.config.get(f"{cfg}.similarity_threshold", 0.8),
                "edge_weight": self.config.get(f"{cfg}.edge_weight", 1.0),
                "strengthen_factor": self.config.get(f"{cfg}.strengthen_factor", 0.1),
                "decay_factor": self.config.get(f"{cfg}.decay_factor", 0.01),
                "max_weight": self.config.get(f"{cfg}.max_weight", 10.0),
                "activation_depth": self.config.get(f"{cfg}.activation_depth", 2),
                "activation_decay": self.config.get(f"{cfg}.activation_decay", 0.5),
                "auto_link_prompt": self.config.get(f"{cfg}.auto_link_prompt"),
                "max_auto_links": self.config.get(f"{cfg}.max_auto_links", 5),
            }

        elif self.action == "forgetting":
            action_config = {
                "decay_type": self.config.get(f"{cfg}.decay_type", "time_decay"),
                "decay_rate": self.config.get(f"{cfg}.decay_rate", 0.1),
                "decay_floor": self.config.get(f"{cfg}.decay_floor", 0.1),
                "max_memories": self.config.get(f"{cfg}.max_memories", 1000),
                "evict_count": self.config.get(f"{cfg}.evict_count", 100),
                "heat_threshold": self.config.get(f"{cfg}.heat_threshold", 0.3),
                "heat_decay": self.config.get(f"{cfg}.heat_decay", 0.1),
                "initial_strength": self.config.get(f"{cfg}.initial_strength", 1.0),
                "forgetting_curve": self.config.get(f"{cfg}.forgetting_curve", "exponential"),
                "review_boost": self.config.get(f"{cfg}.review_boost", 0.5),
                "hybrid_factors": self.config.get(f"{cfg}.factors"),
                "retention_min": self.config.get(f"{cfg}.retention_min", 50),
                "archive_before_delete": self.config.get(f"{cfg}.archive_before_delete", True),
            }

        elif self.action == "summarize":
            action_config = {
                "trigger_condition": self.config.get(f"{cfg}.trigger_condition", "overflow"),
                "overflow_threshold": self.config.get(f"{cfg}.overflow_threshold", 100),
                "periodic_interval": self.config.get(f"{cfg}.periodic_interval", 3600),
                "summary_strategy": self.config.get(f"{cfg}.summary_strategy", "single"),
                "hierarchy_levels": self.config.get(f"{cfg}.hierarchy_levels"),
                "incremental_prompt": self.config.get(f"{cfg}.incremental_prompt"),
                "summarize_prompt": self.config.get(f"{cfg}.summarize_prompt"),
                "replace_originals": self.config.get(f"{cfg}.replace_originals", False),
                "store_as_new": self.config.get(f"{cfg}.store_as_new", True),
                "summary_importance": self.config.get(f"{cfg}.summary_importance", 7),
            }

        elif self.action == "migrate":
            action_config = {
                "migrate_policy": self.config.get(f"{cfg}.migrate_policy", "heat"),
                "heat_upgrade_threshold": self.config.get(f"{cfg}.heat_upgrade_threshold", 5.0),
                "cold_threshold": self.config.get(f"{cfg}.cold_threshold", 0.1),
                "session_gap": self.config.get(f"{cfg}.session_gap", 1800),
                "tier_capacities": self.config.get(f"{cfg}.tier_capacities"),
                "upgrade_transform": self.config.get(f"{cfg}.upgrade_transform", "none"),
                "downgrade_transform": self.config.get(f"{cfg}.downgrade_transform", "summarize"),
            }

        return action_config

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
            处理后的数据
        """
        if self.action == "none":
            # 透传
            pass
        elif self.action == "log":
            self._log_data(data)
        elif self.action == "stats":
            self._analyze_stats(data)
        elif self.action == "distillation":
            self._distill_memory(data)
        elif self.action in SERVICE_LEVEL_ACTIONS:
            # 服务级操作：委托给服务
            self._trigger_service_optimize(data)
        else:
            print(f"未知的 action: {self.action}，跳过处理")

        return data

    # ==================== 算子级操作 ====================

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

    # ==================== Distillation 实现（符合规范）====================

    def _distill_memory(self, data):
        """执行记忆蒸馏（符合"一次 检索->删除->插入"规范）

        流程：
        1. 检索相似记忆（一次检索）
        2. LLM 判断需要合并/删除的记忆
        3. 删除旧记忆（一次删除，批量）
        4. 插入蒸馏后的新记忆（一次插入）

        Args:
            data: 包含 memory_entries 的数据字典
        """
        for entry_dict in data.get("memory_entries", []):
            vector = entry_dict.get("embedding")
            if vector is None:
                continue

            # Step 1: 检索（一次）
            similar_entries = self.call_service(
                self.service_name,
                method="retrieve",
                vector=vector,
                topk=self.distillation_topk,
                threshold=self.distillation_threshold,
                timeout=10.0,
            )

            if not similar_entries or len(similar_entries) < self.distillation_topk:
                continue

            # Step 2: LLM 蒸馏
            distilled_text, to_delete = self._llm_distill(entry_dict, similar_entries)

            if not distilled_text or not to_delete:
                continue

            # Step 3: 删除（一次，批量）
            for entry_text in to_delete:
                self.call_service(
                    self.service_name,
                    method="delete",
                    entry=entry_text,
                    timeout=10.0,
                )

            # Step 4: 插入（一次）
            new_vector = self._embedding_generator.embed(distilled_text)
            self.call_service(
                self.service_name,
                method="insert",
                entry=distilled_text,
                vector=new_vector,
                metadata={"type": "distilled"},
                timeout=10.0,
            )

    def _llm_distill(
        self, entry_dict: dict, similar_entries: list[dict]
    ) -> tuple[str | None, list[str]]:
        """调用 LLM 进行蒸馏

        Args:
            entry_dict: 当前条目
            similar_entries: 相似记忆列表

        Returns:
            (蒸馏后的文本, 需要删除的文本列表)
        """
        memory_texts = [r.get("text", "") for r in similar_entries]
        memory_texts_set = set(memory_texts)
        memory_list_str = "\n".join(memory_texts)

        prompt = self.distillation_prompt.replace("{memory_list}", memory_list_str)
        response = self._generator.generate(prompt)

        result = self._parse_json_response(response)
        if not result:
            return None, []

        to_delete_raw = result.get("to_delete", [])
        to_insert_raw = result.get("to_insert", [])

        # 处理 to_delete: 只保留存在于原始记忆中的文本
        to_delete_set = set()
        for t in to_delete_raw:
            if isinstance(t, str) and t.strip() in memory_texts_set:
                to_delete_set.add(t.strip())

        # 处理 to_insert: 过滤无效文本
        new_texts = []
        seen = set()
        for t in to_insert_raw:
            if not isinstance(t, str):
                continue
            t = t.strip()
            # 过滤包含括号的文本（可能是无效格式）
            if "(" in t or ")" in t:
                continue
            # 过滤已存在的文本
            if t in memory_texts_set:
                continue
            # 去重
            if t and t not in seen and t not in to_delete_set:
                seen.add(t)
                new_texts.append(t)

        # 返回第一个蒸馏文本和需要删除的列表
        distilled_text = new_texts[0] if new_texts else None
        return distilled_text, list(to_delete_set)

    # ==================== 服务级操作（委托给服务）====================

    def _trigger_service_optimize(self, data):
        """触发服务优化（服务级操作统一入口）

        将 reflection, link_evolution, forgetting, summarize, migrate
        等复杂操作委托给记忆服务的 optimize() 方法

        Args:
            data: 包含 memory_entries 的数据字典
        """
        entries = data.get("memory_entries", [])

        # 构造优化参数
        optimize_params = {
            "trigger": self.action,
            "entries": entries,
            "config": getattr(self, "_action_config", {}),
        }

        # 调用服务的 optimize 方法
        try:
            result = self.call_service(
                self.service_name,
                method="optimize",
                params=optimize_params,
                timeout=30.0,
            )

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
