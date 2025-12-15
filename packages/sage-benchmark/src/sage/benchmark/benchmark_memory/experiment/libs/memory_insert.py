"""
================================================================================
MemoryInsert - 记忆插入算子
================================================================================

[架构定位]
Pipeline: PreInsert → MemoryInsert(当前) → PostInsert → PreRetrieval → PostRetrieval
前驱: PreInsert（负责数据预处理，设置 text/embedding/metadata）
后继: PostInsert（插入后处理，如摘要生成、时间衰减）

[核心职责]
纯透传模式：遍历 PreInsert 输出的 memory_entries，调用记忆服务的 insert 方法

[输入数据结构] (由 PreInsert 生成)
data = {
    "memory_entries": [
        {
            "text": str,                    # 必须：要存储的文本内容
            "embedding": list[float],       # 可选：预计算的向量
            "metadata": {                   # 可选：元数据
                "timestamp": str,           # 时间戳
                "source": str,              # 来源
                "triples": list,            # 知识三元组（tri_embed）
                "vectors": list,            # 多向量（multi_embed）
                "is_summary": bool,         # 是否为摘要（summarize）
                "chunk_index": int,         # 分块索引（chunk_insert）
                ...
            },
            "insert_mode": str,             # 插入模式: "passive" | "active" | ...
            "insert_params": dict,          # 插入参数（服务特定）
        },
        ...
    ],
    ...其他透传字段...
}

[输出数据结构]
data（原样透传）+ insert_stats = {
    "inserted": int,                        # 成功插入数量
    "failed": int,                          # 失败数量
    "entry_ids": list[str],                 # 插入的条目 ID 列表
}

[设计原则]
1. 单一职责：只负责调用服务的 insert 方法，不做数据转换
2. 纯透传：PreInsert 已统一设置 text 字段，MemoryInsert 直接使用
3. 错误容忍：单条插入失败不影响其他条目
4. 可追溯：返回插入统计信息供 PostInsert 使用

[PreInsert Action 与条目数量关系]
不同的 PreInsert action 会产生不同数量的 memory_entries：

┌─────────────────┬──────────────────┬───────────────────────────────────────┐
│ Action          │ 条目数量         │ 说明                                  │
├─────────────────┼──────────────────┼───────────────────────────────────────┤
│ none            │ 1 条             │ 透传原始对话                          │
│ transform       │ 1 条             │ 文本转换后的单条记录                  │
│ extract         │ N 条             │ 提取多个事实/实体，每个一条           │
│ score           │ 1 条             │ 带重要性评分的单条记录                │
│ multi_embed     │ 1 条             │ 单条文本 + 多向量存于 metadata        │
│ scm_embed       │ 1 条             │ SCM 语义压缩后的单条记录              │
│ tri_embed       │ N 条             │ 每个三元组独立成一条                  │
└─────────────────┴──────────────────┴───────────────────────────────────────┘

示例场景：
- 单条插入 (none/transform/score):
  用户说 "我喜欢吃苹果" → 1 条 memory_entry

- 多条插入 (extract):
  用户说 "我叫张三，今年25岁，住在北京"
  → 3 条: ["用户名字是张三", "用户年龄25岁", "用户住在北京"]

- 多条插入 (tri_embed):
  提取三元组 [(张三, 年龄, 25), (张三, 居住地, 北京)]
  → 2 条，每条 metadata 含对应 triple
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from sage.common.core import MapFunction

# ==============================================================================
# 数据模型
# ==============================================================================


@dataclass
class InsertStats:
    """插入统计数据模型

    Attributes:
        inserted: 成功插入的数量
        failed: 插入失败的数量
        entry_ids: 成功插入的条目 ID 列表
        errors: 失败条目的详细错误信息列表
    """

    inserted: int
    failed: int
    entry_ids: list[str]
    errors: list[dict[str, Any]]


# ==============================================================================
# MemoryInsert 类
# ==============================================================================


class MemoryInsert(MapFunction):
    """记忆插入算子 - 纯透传模式（重构版）

    职责：
    1. 遍历 PreInsert 输出的 memory_entries
    2. 调用记忆服务的 insert 方法
    3. 统计插入结果，透传给 PostInsert

    重构改进：
    - 引入 InsertStats 数据类，统一统计格式
    - 增强错误处理，记录详细错误信息（entry 文本 + 异常消息）
    - 支持 verbose 日志模式，方便调试
    - 代码精简至 < 100 行（主类）
    """

    # --------------------------------------------------------------------------
    # 初始化
    # --------------------------------------------------------------------------

    def __init__(self, config=None):
        """初始化 MemoryInsert

        Args:
            config: RuntimeConfig 对象，用于获取服务名称和配置项
        """
        super().__init__()
        self.config = config
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        self.verbose = config.get("runtime.memory_insert_verbose", False)

    # --------------------------------------------------------------------------
    # 主执行流程
    # --------------------------------------------------------------------------

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行记忆插入

        流程：
        1. 遍历 memory_entries
        2. 逐条调用 _insert_entry
        3. 统计结果并返回

        Args:
            data: 由 PreInsert 输出的数据，包含 memory_entries

        Returns:
            原始数据 + insert_stats 统计信息
        """
        memory_entries = data.get("memory_entries", [])
        stats = InsertStats(inserted=0, failed=0, entry_ids=[], errors=[])

        # 记录批次总耗时
        batch_start = time.perf_counter()

        for entry in memory_entries:
            try:
                entry_id = self._insert_entry(entry)
                stats.inserted += 1
                stats.entry_ids.append(entry_id)

                if self.verbose:
                    self._log_insert(entry, entry_id)

            except Exception as e:
                stats.failed += 1
                stats.errors.append(
                    {
                        "entry": entry.get("text", "")[:100],
                        "error": str(e),
                    }
                )
                self.logger.warning(f"Insert failed: {e}")

        # 计算批次总耗时
        batch_elapsed_ms = (time.perf_counter() - batch_start) * 1000

        # 将统计信息转为字典并添加到数据中
        data["insert_stats"] = asdict(stats)

        # 使用输入的 dialogs 数量平均分配时间
        dialog_count = len(data.dialogs) if hasattr(data, "dialogs") else 1
        if dialog_count > 0:
            per_dialog_ms = batch_elapsed_ms / dialog_count
            data.setdefault("stage_timings", {})["memory_insert_ms"] = [
                per_dialog_ms
            ] * dialog_count
        else:
            data.setdefault("stage_timings", {})["memory_insert_ms"] = []

        return data

    # --------------------------------------------------------------------------
    # 单条插入
    # --------------------------------------------------------------------------

    def _insert_entry(self, entry: dict[str, Any]) -> str:
        """插入单条记忆到服务

        字段说明：
        - text: 必须，要存储的文本（由 PreInsert 统一设置）
        - embedding: 可选，预计算的向量
        - metadata: 可选，包含时间戳、来源、三元组等
        - insert_mode: 插入模式，默认 "passive"
        - insert_params: 服务特定的插入参数

        Args:
            entry: 记忆条目字典

        Returns:
            插入成功返回条目 ID

        Raises:
            ValueError: 如果 text 字段为空
            Exception: 服务调用失败时的各种异常
        """
        # 1. 验证必填字段
        text = entry.get("text", "")
        if not text:
            raise ValueError("Entry text is empty")

        # 2. 调用记忆服务
        return self.call_service(
            self.service_name,
            method="insert",
            entry=text,
            vector=entry.get("embedding"),
            metadata=entry.get("metadata", {}),
            insert_mode=entry.get("insert_mode", "passive"),
            insert_params=entry.get("insert_params"),
            timeout=10.0,
        )

    # --------------------------------------------------------------------------
    # 日志辅助方法
    # --------------------------------------------------------------------------

    def _log_insert(self, entry: dict[str, Any], entry_id: str) -> None:
        """记录插入详情（仅在 verbose 模式下）

        Args:
            entry: 插入的条目字典
            entry_id: 插入后的条目 ID
        """
        text = entry.get("text", "")[:50]  # 截断显示
        mode = entry.get("insert_mode", "passive")
        self.logger.info(f"Inserted [{entry_id}] (mode={mode}): {text}...")


# ==============================================================================
# 附录：特殊插入模式说明
# ==============================================================================
#
# [insert_mode 取值]
# ┌──────────┬──────────────────────────────────────────────────────────────────┐
# │ 模式     │ 说明                                                             │
# ├──────────┼──────────────────────────────────────────────────────────────────┤
# │ passive  │ 被动插入（默认），由记忆服务自行决定存储层级                     │
# │ active   │ 主动插入，明确指定目标层级（如 LTM），通常用于高价值信息         │
# └──────────┴──────────────────────────────────────────────────────────────────┘
#
# [insert_params 示例]
# ┌─────────────────────────────────────┬───────────────────────────────────────┐
# │ 参数组合                            │ 使用场景                              │
# ├─────────────────────────────────────┼───────────────────────────────────────┤
# │ {"target_tier": "ltm"}              │ 摘要插入，直接存入长期记忆            │
# │ {"target_tier": "ltm", "priority":8}│ 高分记忆(≥8)，优先级插入 LTM          │
# │ {"target_tier": "mtm"}              │ 中等分数(5-7)，插入中期记忆           │
# │ None (无参数)                       │ 普通插入，由服务决定层级              │
# └─────────────────────────────────────┴───────────────────────────────────────┘
#
# [PreInsert Action 与特殊插入的对应关系]
#
# 1. transform (summarize) → active + {"target_tier": "ltm"}
#    摘要是高度浓缩的信息，通常主动插入 LTM
#
# 2. score (importance) → 根据评分动态决定：
#    - score ≥ 8: active + {"target_tier": "ltm", "priority": score}
#    - score 5-7: passive + {"target_tier": "mtm"}
#    - score < 5: passive + 无特殊参数（STM）
#
# 3. 其他 action (none, extract, multi_embed, scm_embed, tri_embed):
#    - 默认: passive + 无特殊参数
#
# [记忆服务如何使用这些参数]
# 记忆服务的 insert 方法接收 insert_mode 和 insert_params，根据这些参数
# 决定将记忆存入 STM (短期) / MTM (中期) / LTM (长期) 哪个层级。
# 具体实现取决于各个记忆服务的策略。
#
