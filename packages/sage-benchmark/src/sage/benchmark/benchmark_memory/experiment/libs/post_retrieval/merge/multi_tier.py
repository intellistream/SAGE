"""PostRetrieval Multi-Tier Merge 实现

MemGPT 风格的多层记忆融合：
1. Core memory: 直接作为上下文（不需要排序）
2. Archival + Recall: RRF 融合后返回 Top-K
3. 最终输出: Core（完整） + Top-K(Archival+Recall)

论文原文: Figure 3 - MemGPT System Architecture
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, MemoryItem, PostRetrievalInput, PostRetrievalOutput


class MemoryPressureMonitor:
    """Memory Pressure 监控器

    论文原文 Section 2.2:
    "When the prompt tokens exceed the 'warning token count' of the underlying LLM's
    context window (e.g. 70% of the context window), the queue manager inserts a
    system message into the queue warning the LLM of an impending queue eviction."

    功能：
    1. 监控当前 context 的 token 使用率
    2. 超过阈值时生成 Memory Pressure Warning
    3. 允许 Agent 主动保存重要信息
    """

    def __init__(self, config: dict):
        """初始化监控器

        Args:
            config: 配置字典，包含：
                - context_window_size: LLM 的 context window 大小（tokens）
                - memory_pressure_threshold: 触发警告的阈值（0-1）
                - queue_flush_threshold: 强制 flush 的阈值（0-1）
        """
        self.context_window_size = config.get("runtime.context_window_size", 8192)
        self.memory_pressure_threshold = config.get("runtime.memory_pressure_threshold", 0.7)
        self.queue_flush_threshold = config.get("runtime.queue_flush_threshold", 1.0)
        self.pressure_warning_sent = False

    def estimate_token_count(self, text: str) -> int:
        """估算文本的 token 数量（简单估算：1 token ≈ 4 characters）"""
        return len(text) // 4

    def check_memory_pressure(
        self,
        core_memory_text: str,
        retrieved_memories: list[dict],
        conversation_history: list[dict] = None,
    ) -> dict[str, Any]:
        """检查 memory pressure 并生成警告"""
        # 估算当前 context 的 token 使用量
        core_tokens = self.estimate_token_count(core_memory_text)
        retrieved_tokens = sum(
            self.estimate_token_count(mem.get("text", "")) for mem in retrieved_memories
        )
        history_tokens = 0
        if conversation_history:
            for msg in conversation_history:
                history_tokens += self.estimate_token_count(msg.get("content", ""))

        total_tokens = core_tokens + retrieved_tokens + history_tokens
        usage_ratio = total_tokens / self.context_window_size

        result = {
            "has_pressure": False,
            "usage_ratio": usage_ratio,
            "estimated_tokens": total_tokens,
            "warning_message": None,
        }

        # 检查是否超过警告阈值
        if usage_ratio >= self.memory_pressure_threshold and not self.pressure_warning_sent:
            result["has_pressure"] = True
            result["warning_message"] = self._generate_pressure_warning(usage_ratio, total_tokens)
            self.pressure_warning_sent = True

        # 检查是否超过 flush 阈值
        if usage_ratio >= self.queue_flush_threshold:
            result["should_flush"] = True
            result["flush_message"] = (
                f"WARNING: Context window is {usage_ratio * 100:.1f}% full "
                f"({total_tokens}/{self.context_window_size} tokens). "
                f"FIFO queue will be flushed to Recall Storage."
            )
        else:
            result["should_flush"] = False

        return result

    def _generate_pressure_warning(self, usage_ratio: float, total_tokens: int) -> str:
        """生成 Memory Pressure Warning 消息"""
        warning = f"""
================================================================
                  MEMORY PRESSURE WARNING
================================================================
  Context window usage: {usage_ratio * 100:.1f}%
  Current tokens: {total_tokens}/{self.context_window_size}

  The context window is approaching capacity.
  Consider using the following functions to preserve
  important information:

  - core_memory_append(label, content)
    Save critical facts to core memory

  - archival_memory_insert(content, tags)
    Archive detailed information for later retrieval

  If no action is taken, older messages in the conversation
  queue will be automatically moved to Recall Storage.
================================================================
"""
        return warning.strip()

    def reset(self):
        """重置警告状态"""
        self.pressure_warning_sent = False


class MultiTierMerge:
    """多层记忆融合器（MemGPT 风格）

    执行流程：
    1. 从 memory_data 中分离三层结果
    2. Core memory 直接作为上下文
    3. Archival + Recall 使用 RRF 融合
    4. 检查 Memory Pressure 并生成警告（论文核心特性）
    5. 组合最终结果
    """

    def __init__(self, config=None):
        """初始化

        Args:
            config: RuntimeConfig 对象
        """
        self.config = config or {}

        # 从配置读取参数
        post_retrieval_config = config.get("operators.post_retrieval", {})
        self.top_k = post_retrieval_config.get("top_k", 10)
        self.rrf_k = post_retrieval_config.get("rrf_k", 60)
        self.vector_weight = post_retrieval_config.get("vector_weight", 0.5)
        self.fts_weight = post_retrieval_config.get("fts_weight", 0.5)

        # Memory Pressure 监控（MemGPT 核心特性）
        self.enable_pressure_warning = post_retrieval_config.get(
            "enable_memory_pressure_warning", True
        )
        if self.enable_pressure_warning:
            self.pressure_monitor = MemoryPressureMonitor(config)
        else:
            self.pressure_monitor = None

        # 详细日志开关
        self.verbose = config.get("runtime.memory_test_verbose", False)

        # 读取层级映射配置（支持动态层级名称）
        tier_mapping_config = config.get("operators.post_retrieval.tier_mapping")
        if tier_mapping_config and isinstance(tier_mapping_config, dict):
            self.tier_mapping = tier_mapping_config
        else:
            # 默认映射（MemGPT 风格）
            self.tier_mapping = {"first": "core", "second": "archival", "third": "recall"}

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行多层融合

        Args:
            data: 包含 memory_data 的字典

        Returns:
            data + enhanced_context
        """
        memory_data = data.get("memory_data", [])

        if not memory_data:
            data["enhanced_context"] = {
                "core_memory": "",
                "retrieved_memories": [],
                "stats": {"core_count": 0, "retrieved_count": 0},
            }
            return data

        # 1. 按 tier 分组（动态检测层级名称）
        core_memories = []
        archival_memories = []
        recall_memories = []

        # 从数据中推断实际层级名称
        all_tiers = {item.get("tier", "") for item in memory_data if item.get("tier")}

        # 尝试从配置的 tier_mapping 反向查找，或使用默认值
        core_tier_names = [self.tier_mapping.get("first", "core")]
        archival_tier_names = [self.tier_mapping.get("second", "archival")]
        recall_tier_names = [self.tier_mapping.get("third", "recall")]

        # 如果数据中没有配置的名称，尝试按顺序映射
        if all_tiers and not any(
            t in all_tiers for t in core_tier_names + archival_tier_names + recall_tier_names
        ):
            sorted_tiers = sorted(all_tiers)
            if len(sorted_tiers) >= 1:
                core_tier_names = [sorted_tiers[0]]
            if len(sorted_tiers) >= 2:
                archival_tier_names = [sorted_tiers[1]]
            if len(sorted_tiers) >= 3:
                recall_tier_names = [sorted_tiers[2]]

        for item in memory_data:
            tier = item.get("tier", "")
            if item.get("is_core_memory", False) or tier in core_tier_names:
                core_memories.append(item)
            elif tier in archival_tier_names:
                archival_memories.append(item)
            elif tier in recall_tier_names:
                recall_memories.append(item)

        if self.verbose:
            print("\n" + "=" * 80)
            print("🔄 [PostRetrieval] Multi-Tier Merge")
            print("=" * 80)
            print(f"Core memories: {len(core_memories)}")
            print(f"Archival memories: {len(archival_memories)}")
            print(f"Recall memories: {len(recall_memories)}")

        # 2. 格式化 Core Memory
        core_text = self._format_core_memory(core_memories)

        # 3. RRF 融合 Archival + Recall
        fused_memories = self._rrf_fusion(archival_memories, recall_memories)

        # 4. 检查 Memory Pressure（MemGPT 核心特性）
        pressure_info = None
        if self.pressure_monitor:
            pressure_info = self.pressure_monitor.check_memory_pressure(
                core_memory_text=core_text,
                retrieved_memories=fused_memories[: self.top_k],
                conversation_history=None,  # TODO: 从 data 中获取对话历史
            )

            # 如果有压力，输出警告
            if pressure_info.get("has_pressure") and self.verbose:
                print("\n" + pressure_info["warning_message"] + "\n")

        # 5. 组合最终上下文
        enhanced_context = {
            "core_memory": core_text,
            "retrieved_memories": fused_memories[: self.top_k],
            "stats": {
                "core_count": len(core_memories),
                "archival_count": len(archival_memories),
                "recall_count": len(recall_memories),
                "fused_count": len(fused_memories),
                "final_count": min(len(fused_memories), self.top_k),
            },
        }

        # 添加 Memory Pressure 信息
        if pressure_info:
            enhanced_context["memory_pressure"] = {
                "has_pressure": pressure_info.get("has_pressure", False),
                "usage_ratio": pressure_info.get("usage_ratio", 0.0),
                "estimated_tokens": pressure_info.get("estimated_tokens", 0),
                "should_flush": pressure_info.get("should_flush", False),
            }

        if self.verbose:
            print("\n✅ Fusion complete:")
            print(f"   Core memory: {len(core_text)} chars")
            print(f"   Retrieved: {len(fused_memories)} → Top-{self.top_k}")
            print("=" * 80 + "\n")

        data["enhanced_context"] = enhanced_context
        return data

    def _format_core_memory(self, core_memories: list[dict]) -> str:
        """格式化 Core Memory 为文本

        MemGPT 的 Core Memory 包含多个 blocks（persona, human 等）

        Args:
            core_memories: Core memory 列表

        Returns:
            格式化的文本
        """
        if not core_memories:
            return ""

        # 按 label 分组
        blocks = {}
        for mem in core_memories:
            label = mem.get("metadata", {}).get("label", "unknown")
            text = mem.get("text", "")
            if label not in blocks:
                blocks[label] = []
            blocks[label].append(text)

        # 格式化输出
        lines = []
        lines.append("<core_memory>")
        for label, texts in blocks.items():
            lines.append(f"<{label}>")
            lines.extend(texts)
            lines.append(f"</{label}>")
        lines.append("</core_memory>")

        return "\n".join(lines)

    def _rrf_fusion(self, archival_results: list[dict], recall_results: list[dict]) -> list[dict]:
        """RRF (Reciprocal Rank Fusion) 融合

        与 Letta 和 HierarchicalMemoryService 的实现一致。

        Args:
            archival_results: Archival memory 检索结果
            recall_results: Recall memory 检索结果

        Returns:
            融合后的结果列表
        """
        # 构建排名映射
        archival_ranks = {
            r.get("entry_id", r.get("id")): rank + 1 for rank, r in enumerate(archival_results)
        }
        recall_ranks = {
            r.get("entry_id", r.get("id")): rank + 1 for rank, r in enumerate(recall_results)
        }

        # 合并所有唯一项
        all_items = {}
        for r in archival_results:
            item_id = r.get("entry_id", r.get("id"))
            all_items[item_id] = r
        for r in recall_results:
            item_id = r.get("entry_id", r.get("id"))
            if item_id not in all_items:
                all_items[item_id] = r

        # 计算 RRF 分数
        rrf_scores = {}
        for item_id in all_items:
            score = 0.0
            if item_id in archival_ranks:
                score += self.vector_weight / (self.rrf_k + archival_ranks[item_id])
            if item_id in recall_ranks:
                score += self.fts_weight / (self.rrf_k + recall_ranks[item_id])
            rrf_scores[item_id] = score

        # 排序
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        result = []
        for item_id, score in sorted_ids:
            item = all_items[item_id].copy()
            item["score"] = score
            item["metadata"] = item.get("metadata", {})
            item["metadata"]["rrf_score"] = score
            item["metadata"]["archival_rank"] = archival_ranks.get(item_id)
            item["metadata"]["recall_rank"] = recall_ranks.get(item_id)
            item["metadata"]["fusion_method"] = "rrf"
            result.append(item)

        return result


class MultiTierMergeAction(BasePostRetrievalAction):
    """Multi-Tier Merge Action（符合 Action 规范的包装类）

    将 MultiTierMerge 包装为标准的 PostRetrievalAction
    """

    def _init_action(self) -> None:
        """初始化 Action"""
        # 创建内部 MultiTierMerge 实例
        self.merger = MultiTierMerge(self.config)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """执行多层融合

        Args:
            input_data: 输入数据
            service: 记忆服务代理（未使用）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 融合后的结果
        """
        # 调用内部 MultiTierMerge
        result_data = self.merger.execute(input_data.data)

        # 从 enhanced_context 提取结果
        enhanced_context = result_data.get("enhanced_context", {})
        retrieved_memories = enhanced_context.get("retrieved_memories", [])

        # 转换为 MemoryItem 列表
        memory_items = []
        for mem in retrieved_memories:
            memory_items.append(
                MemoryItem(
                    text=mem.get("text", ""),
                    score=mem.get("score", 0.0),
                    metadata=mem.get("metadata", {}),
                )
            )

        # 构建 metadata
        metadata = {
            "action": "merge.multi_tier",
            "stats": enhanced_context.get("stats", {}),
        }

        # 添加 core_memory 到 metadata
        if enhanced_context.get("core_memory"):
            metadata["core_memory"] = enhanced_context["core_memory"]

        # 添加 memory_pressure 信息
        if enhanced_context.get("memory_pressure"):
            metadata["memory_pressure"] = enhanced_context["memory_pressure"]

        return PostRetrievalOutput(
            memory_items=memory_items,
            metadata=metadata,
        )
