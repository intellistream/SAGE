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

from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils import (
    EmbeddingGenerator,
    LLMGenerator,
    get_required_config,
)
from sage.common.core import MapFunction

# 算子级操作列表（PostInsert 自己实现）
OPERATOR_LEVEL_ACTIONS = {"none", "log", "stats", "distillation", "mem0_crud", "status_based"}

# 服务级操作列表（委托给服务的 optimize() 方法）
SERVICE_LEVEL_ACTIONS = {"reflection", "link_evolution", "forgetting", "summarize", "migrate"}


import time


class PostInsert(MapFunction):
    """记忆插入后的后处理算子

    职责：
    - 触发记忆服务的优化操作（服务级操作）
    - 执行简单的算子级操作（log, stats, distillation）

    约束：
    - 只与单一记忆服务交互
    - 复杂优化逻辑委托给服务的 optimize() 方法
    - distillation 执行一次 检索→删除→插入（符合规范）

    优化策略（HippoRAG 对齐）：
    - link_evolution 等服务级操作仅在 session_id 变化时执行（而非每次插入）
    - 这与 HippoRAG 的"索引完成后一次性优化"策略对齐
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

        # 用于追踪 session_id 变化（HippoRAG 优化策略）
        self._last_session_id: int | None = None

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

        elif self.action == "mem0_crud":
            # Mem0 CRUD 操作配置
            self.crud_topk = self.config.get(f"{cfg}.crud_topk", 10)
            self.crud_threshold = self.config.get(f"{cfg}.crud_threshold", None)
            self.crud_prompt = self.config.get(f"{cfg}.crud_prompt")
            if not self.crud_prompt:
                # 使用默认 prompt
                self.crud_prompt = """You are managing a fact database. Given a new fact and similar existing facts,
decide the appropriate action:

- ADD: The new fact is entirely new information
- UPDATE: The new fact updates/extends an existing fact (delete old, keep new)
- DELETE: The new fact contradicts an existing fact (delete old, keep new)
- NOOP: The new fact is redundant (already covered by existing facts)

New fact: {new_entry}

Existing facts:
{memory_list}

Respond with JSON:
{{"action": "ADD|UPDATE|DELETE|NOOP", "to_delete": [indices of facts to remove], "reason": "brief explanation"}}"""

        elif self.action in SERVICE_LEVEL_ACTIONS:
            # 服务级操作：收集配置参数（将传递给服务的 optimize() 方法）
            self._action_config = self._collect_action_config()

        elif self.action == "status_based":
            # 状态查询模式：从服务查询状态，根据状态执行操作
            # 配置 LLM prompts
            self.migrate_prompt = self.config.get(f"{cfg}.migrate_prompt")
            self.crud_prompt = self.config.get(f"{cfg}.crud_prompt")
            self.link_prompt = self.config.get(f"{cfg}.link_prompt")
            self.synonym_prompt = self.config.get(f"{cfg}.synonym_prompt")

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
                    "session_id": int,  # 当前会话 ID
                    "packet_idx": int,  # 当前数据包索引
                    "total_packets": int,  # 总数据包数
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
            "mem0_crud": self._execute_mem0_crud,
            "status_based": self._execute_status_based,
        }

        if self.action in operator_handlers:
            operator_handlers[self.action](data)
        elif self.action in SERVICE_LEVEL_ACTIONS:
            # 服务级操作：只在所有数据插入完成后执行一次优化
            # 原因：link_evolution 是 O(n²) 操作，每个 session 都执行太慢
            # HippoRAG 论文也是在所有 indexing 完成后才一次性执行 add_synonymy_edges
            packet_idx = data.get("packet_idx", 0)
            total_packets = data.get("total_packets", 1)
            is_last_packet = (packet_idx + 1) >= total_packets
            current_session_id = data.get("session_id")

            # 只在最后一个 packet 时执行一次优化（所有数据都插入完成）
            if is_last_packet:
                print(
                    f"[PostInsert] All data inserted (final packet in session {current_session_id}), "
                    f"triggering {self.action} optimization"
                )
                self._execute_service_optimize(data)

            # 更新追踪的 session_id（用于其他可能的用途）
            self._last_session_id = current_session_id
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
        start_time = time.time()
        print(
            f"[TIMING-POST] Distillation started for {len(data.get('memory_entries', []))} entries"
        )

        for entry_dict in data.get("memory_entries", []):
            # 获取当前条目的文本和向量
            text = entry_dict.get("refactor", "") or entry_dict.get("text", "")
            vector = entry_dict.get("embedding")

            if not text or vector is None:
                continue

            # ========== 第一步：检索（仅一次）==========
            retrieve_start = time.time()
            similar_entries = self.call_service(
                self.service_name,
                method="retrieve",
                query=text,
                vector=vector,
                top_k=self.distillation_topk,
                threshold=self.distillation_threshold,
                timeout=10.0,
            )
            retrieve_time = time.time() - retrieve_start
            print(
                f"[TIMING-POST]   Retrieve: {retrieve_time:.3f}s, found {len(similar_entries) if similar_entries else 0} similar entries"
            )

            # 只有相似记忆数量达到 topk 时才进行蒸馏（避免不必要的 LLM 调用）
            if not similar_entries or len(similar_entries) < self.distillation_topk:
                continue

            # ========== 第二步：LLM 分析 ==========
            llm_start = time.time()
            distilled_text, to_delete = self._analyze_for_distillation(entry_dict, similar_entries)
            llm_time = time.time() - llm_start
            print(f"[TIMING-POST]   LLM analysis: {llm_time:.3f}s, to_delete={len(to_delete)}")

            if not distilled_text and not to_delete:
                continue

            # ========== 第三步：删除（仅一次，批量）==========
            delete_start = time.time()
            for entry_id in to_delete:
                self.call_service(
                    self.service_name,
                    method="delete",
                    entry_id=entry_id,
                    timeout=5.0,
                )
            delete_time = time.time() - delete_start
            print(f"[TIMING-POST]   Delete: {delete_time:.3f}s, deleted {len(to_delete)} entries")

            # ========== 第四步：插入（仅一次）==========
            # 确保 distilled_text 是有效的字符串
            if distilled_text and isinstance(distilled_text, str) and distilled_text.strip():
                insert_start = time.time()
                distilled_vector = self._embedding_generator.embed(distilled_text)
                if distilled_vector is not None:  # 确保 embedding 成功
                    # DEBUG: 记录参数类型
                    self.logger.debug(
                        f"[DISTILLATION_INSERT] distilled_text type: {type(distilled_text)}, "
                        f"value: {distilled_text[:100] if isinstance(distilled_text, str) else distilled_text}"
                    )
                    self.logger.debug(
                        f"[DISTILLATION_INSERT] distilled_vector type: {type(distilled_vector)}, "
                        f"length: {len(distilled_vector) if hasattr(distilled_vector, '__len__') else 'N/A'}"
                    )
                    self.call_service(
                        self.service_name,
                        method="insert",
                        entry=distilled_text,
                        vector=distilled_vector,
                        metadata={"distilled": True, "source_count": len(to_delete) + 1},
                        timeout=10.0,
                    )
                    insert_time = time.time() - insert_start
                    print(f"[TIMING-POST]   Insert: {insert_time:.3f}s")
                else:
                    self.logger.warning(
                        f"Failed to generate embedding for distilled text: {distilled_text[:50]}..."
                    )

        total_time = time.time() - start_time
        print(f"[TIMING-POST] Distillation finished: {total_time:.3f}s")

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

        result = self._generator.generate_json(prompt)
        if not result:
            return None, []

        # 解析 to_delete（索引列表），确保转换为整数
        to_delete_indices_raw = result.get("to_delete", [])
        to_delete_indices = []
        for idx in to_delete_indices_raw:
            try:
                to_delete_indices.append(int(idx))
            except (ValueError, TypeError):
                pass  # 忽略无法转换为整数的值
        to_delete_ids = [memory_ids[i] for i in to_delete_indices if i < len(memory_ids)]

        # 解析 to_insert（合并后的文本）
        # 注意：LLM 返回的可能是字符串、列表或字典，需要规范化为字符串
        raw_distilled = result.get("distilled_text", result.get("to_insert"))
        distilled_text: str | None = None

        if raw_distilled is not None:
            if isinstance(raw_distilled, str):
                # 情况 1：已经是字符串
                distilled_text = raw_distilled.strip() if raw_distilled.strip() else None
            elif isinstance(raw_distilled, list) and raw_distilled:
                # 情况 2：是列表，提取其中的文本
                texts = []
                for item in raw_distilled:
                    if isinstance(item, str):
                        texts.append(item)
                    elif isinstance(item, dict):
                        text = item.get("new_entry") or item.get("text") or item.get("content")
                        if text and isinstance(text, str):
                            texts.append(text)
                distilled_text = " ".join(texts).strip() if texts else None
            elif isinstance(raw_distilled, dict):
                # 情况 3：是字典，尝试常见的键名
                text = (
                    raw_distilled.get("new_entry")
                    or raw_distilled.get("text")
                    or raw_distilled.get("content")
                )
                if text and isinstance(text, str):
                    distilled_text = text.strip()

        return distilled_text, to_delete_ids

    # ==================== Mem0 CRUD 实现 ====================

    def _execute_mem0_crud(self, data: dict[str, Any]) -> None:
        """执行 Mem0 风格的 CRUD 操作

        论文要求 (Mem0):
        对新记忆，LLM 决定：
        - ADD: 新信息，直接插入（已由 MemoryInsert 完成）
        - UPDATE: 更新已有事实（删旧）
        - DELETE: 矛盾信息（删旧）
        - NOOP: 冗余信息，删除刚插入的记忆

        流程（符合"一次 检索→删除→插入"规范）：
        1. 检索相似记忆
        2. LLM 判断 action
        3. 根据 action 执行删除操作

        Args:
            data: 包含 memory_entries 的数据字典
        """
        start_time = time.time()
        entries = data.get("memory_entries", [])
        print(f"[TIMING-POST] Mem0 CRUD started for {len(entries)} entries")

        crud_stats = {"add": 0, "update": 0, "delete": 0, "noop": 0}

        for entry_dict in entries:
            text = entry_dict.get("refactor", "") or entry_dict.get("text", "")
            vector = entry_dict.get("embedding")
            entry_id = entry_dict.get("entry_id")

            if not text or vector is None:
                continue

            # 第一步：检索相似记忆
            similar_entries = self.call_service(
                self.service_name,
                method="retrieve",
                query=text,
                vector=vector,
                top_k=self.crud_topk,
                threshold=self.crud_threshold,
                timeout=10.0,
            )

            # 如果没有相似记忆，默认 ADD（已完成）
            if not similar_entries:
                crud_stats["add"] += 1
                continue

            # 第二步：LLM 分析决定 action
            action, to_delete_ids = self._analyze_for_crud(entry_dict, similar_entries)

            # 第三步：根据 action 执行操作
            if action == "ADD":
                # 直接保留，无需额外操作
                crud_stats["add"] += 1

            elif action == "UPDATE":
                # 删除旧记忆，保留新记忆
                for old_id in to_delete_ids:
                    self.call_service(
                        self.service_name,
                        method="delete",
                        entry_id=old_id,
                        timeout=5.0,
                    )
                crud_stats["update"] += 1

            elif action == "DELETE":
                # 删除旧记忆，保留新记忆（矛盾替换）
                for old_id in to_delete_ids:
                    self.call_service(
                        self.service_name,
                        method="delete",
                        entry_id=old_id,
                        timeout=5.0,
                    )
                crud_stats["delete"] += 1

            elif action == "NOOP":
                # 删除刚插入的记忆（冗余）
                if entry_id:
                    self.call_service(
                        self.service_name,
                        method="delete",
                        entry_id=entry_id,
                        timeout=5.0,
                    )
                crud_stats["noop"] += 1

        total_time = time.time() - start_time
        print(f"[TIMING-POST] Mem0 CRUD finished: {total_time:.3f}s, stats={crud_stats}")
        data["crud_stats"] = crud_stats

    def _analyze_for_crud(
        self, entry_dict: dict, similar_entries: list[dict]
    ) -> tuple[str, list[str]]:
        """分析决定 CRUD 操作

        Args:
            entry_dict: 当前条目
            similar_entries: 相似记忆列表

        Returns:
            (action, to_delete_ids)
            action: "ADD" | "UPDATE" | "DELETE" | "NOOP"
            to_delete_ids: 需要删除的记忆 ID 列表
        """
        new_text = entry_dict.get("refactor", "") or entry_dict.get("text", "")
        memory_texts = [r.get("text", "") for r in similar_entries]
        memory_ids = [r.get("entry_id", "") for r in similar_entries]
        memory_list_str = "\n".join(f"[{i}] {t}" for i, t in enumerate(memory_texts))

        prompt = self.crud_prompt.replace("{new_entry}", new_text)
        prompt = prompt.replace("{memory_list}", memory_list_str)

        result = self._generator.generate_json(prompt)

        if not result:
            return "ADD", []

        action = result.get("action", "ADD").upper()
        if action not in ("ADD", "UPDATE", "DELETE", "NOOP"):
            action = "ADD"

        # 解析 to_delete
        to_delete_indices_raw = result.get("to_delete", [])
        to_delete_indices = []
        for idx in to_delete_indices_raw:
            try:
                to_delete_indices.append(int(idx))
            except (ValueError, TypeError):
                pass
        to_delete_ids = [memory_ids[i] for i in to_delete_indices if i < len(memory_ids)]

        return action, to_delete_ids

    # ==================== 状态查询模式实现 ====================

    def _execute_status_based(self, data: dict[str, Any]) -> None:
        """执行基于状态查询的后处理（被动插入模式核心方法）

        流程：
        1. 查询服务状态 (service.get_status())
        2. 根据 pending_action 类型调用对应的 LLM 决策
        3. 执行决策结果（迁移/删除/链接等）
        4. 清除服务的待处理状态

        支持的 pending_action 类型：
        - migrate: HierarchicalMemoryService 溢出迁移
        - forget: HierarchicalMemoryService 遗忘
        - crud: HybridMemoryService Mem0 CRUD 决策
        - link: GraphMemoryService A-Mem 链接建立
        - synonym: GraphMemoryService HippoRAG 同义边

        Args:
            data: 包含 memory_entries 的数据字典
        """
        start_time = time.time()
        print("[TIMING-POST] Status-based processing started")

        # 1. 查询服务状态
        try:
            status = self.call_service(
                self.service_name,
                method="get_status",
                timeout=10.0,
            )
        except Exception as e:
            print(f"[WARNING] Failed to get service status: {e}")
            return

        pending_action = status.get("pending_action")
        if not pending_action:
            print("[TIMING-POST] No pending action, skipping")
            return

        print(f"[TIMING-POST] Pending action: {pending_action}")

        # 2. 根据 pending_action 类型执行处理
        try:
            if pending_action == "migrate":
                self._handle_migrate_action(status, data)
            elif pending_action == "forget":
                self._handle_forget_action(status, data)
            elif pending_action == "crud":
                self._handle_crud_action(status, data)
            elif pending_action == "link":
                self._handle_link_action(status, data)
            elif pending_action == "synonym":
                self._handle_synonym_action(status, data)
            else:
                print(f"[WARNING] Unknown pending_action: {pending_action}")

        except Exception as e:
            print(f"[WARNING] Failed to handle {pending_action}: {e}")

        # 3. 清除服务的待处理状态
        try:
            self.call_service(
                self.service_name,
                method="clear_pending_status",
                timeout=5.0,
            )
        except Exception:
            pass  # 忽略清除失败

        total_time = time.time() - start_time
        print(f"[TIMING-POST] Status-based processing finished: {total_time:.3f}s")

    def _handle_migrate_action(self, status: dict, data: dict[str, Any]) -> None:
        """处理 HierarchicalMemoryService 的迁移操作

        Args:
            status: 服务状态
            data: 数据字典
        """
        pending_items = status.get("pending_items", [])
        target_tier = status.get("target_tier")

        if not pending_items or not target_tier:
            return

        print(f"[STATUS-BASED] Migrating {len(pending_items)} items to {target_tier}")

        # 可选：LLM 决策是否需要转换/摘要
        for item in pending_items:
            entry_id = item.get("entry_id")
            text = item.get("text", "")
            vector = item.get("vector")

            # 默认直接迁移，如果有 migrate_prompt 则可以进行 LLM 转换
            transformed_text = text
            if self.migrate_prompt and self._generator:
                try:
                    prompt = self.migrate_prompt.replace("{text}", text)
                    transformed_text = self._generator.generate(prompt)
                except Exception:
                    transformed_text = text  # 失败时使用原文本

            # 主动插入到目标层级
            try:
                self.call_service(
                    self.service_name,
                    method="insert",
                    entry=transformed_text,
                    vector=vector,
                    metadata={"migrated_from": item.get("tier")},
                    insert_mode="active",
                    insert_params={"target_tier": target_tier, "force": True},
                    timeout=10.0,
                )

                # 从源层删除原条目
                self.call_service(
                    self.service_name,
                    method="delete",
                    entry_id=entry_id,
                    timeout=5.0,
                )
                print(f"[STATUS-BASED] Migrated {entry_id[:16]}... to {target_tier}")

            except Exception as e:
                print(f"[WARNING] Migration failed for {entry_id[:16]}...: {e}")

    def _handle_forget_action(self, status: dict, data: dict[str, Any]) -> None:
        """处理 HierarchicalMemoryService 的遗忘操作

        Args:
            status: 服务状态
            data: 数据字典
        """
        pending_items = status.get("pending_items", [])

        if not pending_items:
            return

        print(f"[STATUS-BASED] Forgetting {len(pending_items)} items")

        for item in pending_items:
            entry_id = item.get("entry_id")
            try:
                self.call_service(
                    self.service_name,
                    method="delete",
                    entry_id=entry_id,
                    timeout=5.0,
                )
                print(f"[STATUS-BASED] Forgot {entry_id[:16]}...")
            except Exception as e:
                print(f"[WARNING] Forget failed for {entry_id[:16]}...: {e}")

    def _handle_crud_action(self, status: dict, data: dict[str, Any]) -> None:
        """处理 HybridMemoryService 的 Mem0 CRUD 操作

        Args:
            status: 服务状态
            data: 数据字典
        """
        pending_items = status.get("pending_items", [])
        pending_similar = status.get("pending_similar", [])

        if not pending_items:
            return

        new_item = pending_items[0]
        new_text = new_item.get("text", "")
        new_id = new_item.get("entry_id")

        print(f"[STATUS-BASED] CRUD decision for {new_id[:16]}..., similar={len(pending_similar)}")

        # 使用 LLM 决定 CRUD 操作
        action, to_delete_ids = self._analyze_for_crud_from_status(new_text, pending_similar)
        print(f"[STATUS-BASED] CRUD decision: {action}, to_delete={len(to_delete_ids)}")

        # 执行决策
        if action == "ADD":
            # 直接保留，无需额外操作
            pass
        elif action in ("UPDATE", "DELETE"):
            # 删除旧记忆
            for old_id in to_delete_ids:
                try:
                    self.call_service(
                        self.service_name,
                        method="delete",
                        entry_id=old_id,
                        timeout=5.0,
                    )
                except Exception as e:
                    print(f"[WARNING] Delete failed for {old_id[:16]}...: {e}")
        elif action == "NOOP":
            # 删除刚插入的记忆（冗余）
            if new_id:
                try:
                    self.call_service(
                        self.service_name,
                        method="delete",
                        entry_id=new_id,
                        timeout=5.0,
                    )
                except Exception as e:
                    print(f"[WARNING] Delete new item failed: {e}")

    def _analyze_for_crud_from_status(
        self, new_text: str, similar_entries: list[dict]
    ) -> tuple[str, list[str]]:
        """从状态分析 CRUD 操作

        Args:
            new_text: 新条目文本
            similar_entries: 相似条目列表

        Returns:
            (action, to_delete_ids)
        """
        if not similar_entries:
            return "ADD", []

        memory_texts = [r.get("text", "") for r in similar_entries]
        memory_ids = [r.get("entry_id", "") for r in similar_entries]
        memory_list_str = "\n".join(f"[{i}] {t}" for i, t in enumerate(memory_texts))

        # 使用配置的 prompt 或默认 prompt
        prompt_template = (
            self.crud_prompt
            or """Given a new fact and existing facts, decide:
- ADD: New information
- UPDATE: Updates existing (delete old)
- DELETE: Contradicts existing (delete old)
- NOOP: Redundant (delete new)

New: {new_entry}
Existing:
{memory_list}

Respond JSON: {{"action": "ADD|UPDATE|DELETE|NOOP", "to_delete": [indices]}}"""
        )

        prompt = prompt_template.replace("{new_entry}", new_text)
        prompt = prompt.replace("{memory_list}", memory_list_str)

        try:
            result = self._generator.generate_json(prompt)
        except Exception:
            return "ADD", []

        if not result:
            return "ADD", []

        action = result.get("action", "ADD").upper()
        if action not in ("ADD", "UPDATE", "DELETE", "NOOP"):
            action = "ADD"

        # 解析 to_delete
        to_delete_indices_raw = result.get("to_delete", [])
        to_delete_indices = []
        for idx in to_delete_indices_raw:
            try:
                to_delete_indices.append(int(idx))
            except (ValueError, TypeError):
                pass
        to_delete_ids = [memory_ids[i] for i in to_delete_indices if i < len(memory_ids)]

        return action, to_delete_ids

    def _handle_link_action(self, status: dict, data: dict[str, Any]) -> None:
        """处理 GraphMemoryService 的 A-Mem 链接建立操作

        Args:
            status: 服务状态
            data: 数据字典
        """
        pending_node = status.get("pending_node")
        pending_candidates = status.get("pending_candidates", [])

        if not pending_node or not pending_candidates:
            return

        node_id = pending_node.get("node_id")
        node_text = pending_node.get("text", "")

        print(
            f"[STATUS-BASED] Link decision for {node_id[:16]}..., candidates={len(pending_candidates)}"
        )

        # 使用 LLM 决定链接哪些节点
        links = self._analyze_for_links(node_text, pending_candidates)
        print(f"[STATUS-BASED] Link decision: {len(links)} links to create")

        # 建立链接
        for target_id in links:
            try:
                self.call_service(
                    self.service_name,
                    method="add_edge",
                    from_node=node_id,
                    to_node=target_id,
                    edge_type="related",
                    timeout=5.0,
                )
            except Exception as e:
                print(f"[WARNING] Add edge failed: {e}")

    def _analyze_for_links(self, node_text: str, candidates: list[dict]) -> list[str]:
        """分析需要建立的链接

        Args:
            node_text: 新节点文本
            candidates: 候选节点列表

        Returns:
            需要链接的节点 ID 列表
        """
        if not candidates:
            return []

        candidate_texts = [c.get("text", "") for c in candidates]
        candidate_ids = [c.get("node_id", "") for c in candidates]
        candidate_list_str = "\n".join(f"[{i}] {t}" for i, t in enumerate(candidate_texts))

        # 使用配置的 prompt 或默认 prompt
        prompt_template = (
            self.link_prompt
            or """Given a new memory and candidate memories, decide which ones should be linked.

New memory: {new_node}

Candidates:
{candidate_list}

Respond JSON: {{"links": [indices of candidates to link]}}"""
        )

        prompt = prompt_template.replace("{new_node}", node_text)
        prompt = prompt.replace("{candidate_list}", candidate_list_str)

        try:
            result = self._generator.generate_json(prompt)
        except Exception:
            return []

        if not result:
            return []

        # 解析 links
        link_indices_raw = result.get("links", [])
        link_indices = []
        for idx in link_indices_raw:
            try:
                link_indices.append(int(idx))
            except (ValueError, TypeError):
                pass

        return [candidate_ids[i] for i in link_indices if i < len(candidate_ids)]

    def _handle_synonym_action(self, status: dict, data: dict[str, Any]) -> None:
        """处理 GraphMemoryService 的 HippoRAG 同义边建立操作

        Args:
            status: 服务状态
            data: 数据字典
        """
        pending_node = status.get("pending_node")
        pending_candidates = status.get("pending_candidates", [])

        if not pending_node or not pending_candidates:
            return

        node_id = pending_node.get("node_id")
        node_text = pending_node.get("text", "")

        print(
            f"[STATUS-BASED] Synonym decision for {node_id[:16]}..., candidates={len(pending_candidates)}"
        )

        # 使用 LLM 决定哪些是同义词
        synonyms = self._analyze_for_synonyms(node_text, pending_candidates)
        print(f"[STATUS-BASED] Synonym decision: {len(synonyms)} synonyms to create")

        # 建立同义边
        for target_id in synonyms:
            try:
                self.call_service(
                    self.service_name,
                    method="add_edge",
                    from_node=node_id,
                    to_node=target_id,
                    edge_type="synonym",
                    timeout=5.0,
                )
            except Exception as e:
                print(f"[WARNING] Add synonym edge failed: {e}")

    def _analyze_for_synonyms(self, node_text: str, candidates: list[dict]) -> list[str]:
        """分析需要建立的同义边

        Args:
            node_text: 新节点文本
            candidates: 候选节点列表

        Returns:
            需要建立同义边的节点 ID 列表
        """
        if not candidates:
            return []

        candidate_texts = [c.get("text", "") for c in candidates]
        candidate_ids = [c.get("node_id", "") for c in candidates]
        candidate_list_str = "\n".join(f"[{i}] {t}" for i, t in enumerate(candidate_texts))

        # 使用配置的 prompt 或默认 prompt
        prompt_template = (
            self.synonym_prompt
            or """Given an entity and candidate entities, decide which ones are synonyms (same meaning, different expressions).

Entity: {new_node}

Candidates:
{candidate_list}

Respond JSON: {{"synonyms": [indices of synonym candidates]}}"""
        )

        prompt = prompt_template.replace("{new_node}", node_text)
        prompt = prompt.replace("{candidate_list}", candidate_list_str)

        try:
            result = self._generator.generate_json(prompt)
        except Exception:
            return []

        if not result:
            return []

        # 解析 synonyms
        synonym_indices_raw = result.get("synonyms", [])
        synonym_indices = []
        for idx in synonym_indices_raw:
            try:
                synonym_indices.append(int(idx))
            except (ValueError, TypeError):
                pass

        return [candidate_ids[i] for i in synonym_indices if i < len(candidate_ids)]

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
        # link_evolution 需要更长超时（O(n²) 复杂度，数据量大时可能需要10分钟以上）
        timeout = 600.0 if self.action == "link_evolution" else 30.0
        try:
            result = self.call_service(
                self.service_name,
                trigger=self.action,
                config=config,
                entries=entries,
                method="optimize",
                timeout=timeout,
            )

            # 记录结果
            if result:
                data["optimize_result"] = result
                print(f"服务优化完成: {self.action}")

        except Exception as e:
            print(f"服务优化失败 ({self.action}): {e}")

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
