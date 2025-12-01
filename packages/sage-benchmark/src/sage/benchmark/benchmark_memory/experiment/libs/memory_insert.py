"""记忆插入模块 - 负责将对话存储到记忆服务中

支持两种插入模式：
- passive: 被动插入，由服务内部决定如何存储（默认）
- active: 主动插入，根据 insert_params 指定存储方式
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import DialogueParser
from sage.common.core import MapFunction

if TYPE_CHECKING:
    pass


class MemoryInsert(MapFunction):
    """将对话插入记忆服务

    支持两种插入模式：
    - passive: 被动插入，由服务内部决定如何存储（默认）
    - active: 主动插入，根据 insert_params 指定存储方式

    职责：
    1. 接收 PreInsert 输出的列表格式数据
    2. 逐条处理记忆条目
    3. 根据 insert_mode 决定调用方式
    4. 调用配置的记忆服务存储
    5. 透传数据给下游
    """

    def __init__(self, config=None):
        """初始化 MemoryInsert

        Args:
            config: RuntimeConfig 对象
        """
        super().__init__()
        self.config = config

        # 明确服务后端
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 从配置读取提取模式
        self.adapter = (
            config.get("services.memory_insert_adapter", "to_dialogs") if config else "to_dialogs"
        )

        # 初始化对话解析器（仅 to_dialogs 模式需要）
        if self.adapter == "to_dialogs":
            self.dialogue_parser = DialogueParser()

    def execute(self, data):
        """执行记忆插入

        Args:
            data: 由 PreInsert 输出的数据，格式：
                {
                    "memory_entries": [条目1, 条目2, ...],  # 待插入的记忆条目队列
                    ...其他字段
                }

        Returns:
            原始数据（透传），队列保持不变
        """
        # 逐个处理记忆条目（空列表时自动跳过循环）
        for entry_dict in data.get("memory_entries", []):
            self._insert_single_entry(entry_dict)

        # 透传数据给下一个算子（不修改队列）
        return data

    def _insert_single_entry(self, entry_dict: dict[str, Any]) -> None:
        """插入单条记忆条目

        根据 insert_mode 决定调用方式：
        - passive: 简单调用，由服务决定如何存储（默认）
        - active: 传递 insert_params，服务按参数存储

        Args:
            entry_dict: 记忆条目字典，由 PreInsert 生成：
                - to_dialogs 模式: {"dialogs": [...], ...}
                - to_refactor 模式: {"refactor": "...", "embedding": ..., ...}
                - insert_mode: "active" | "passive"（可选，默认 passive）
                - insert_params: 主动插入参数（可选）
                    - target_tier: 目标层级 (分层服务)
                    - node_type: 节点类型 (图服务)
                    - priority: 优先级
                    - force: 是否强制插入

        调用服务的统一格式：
            call_service(service_name, entry, vector, metadata, insert_mode, insert_params, method="insert")
        """
        # 根据 adapter 模式提取 entry
        if self.adapter == "to_dialogs":
            # 使用 DialogueParser 格式化对话
            dialogs = entry_dict.get("dialogs", [])
            entry = self.dialogue_parser.format(dialogs)
        elif self.adapter == "to_refactor":
            # 直接提取 refactor 字段
            entry = entry_dict.get("refactor", "")
        else:
            # 未知模式，尝试提取 refactor 或返回空
            entry = entry_dict.get("refactor", "")

        # 如果 entry 为空字符串，跳过插入
        if not entry:
            return

        # 提取 vector 和 metadata
        vector = entry_dict.get("embedding", None)
        metadata = entry_dict.get("metadata", None)

        # 获取插入模式配置
        insert_mode: Literal["active", "passive"] = entry_dict.get("insert_mode", "passive")
        insert_params: dict[str, Any] | None = entry_dict.get("insert_params", None)

        # 统一插入字符串
        self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            insert_mode=insert_mode,
            insert_params=insert_params,
            method="insert",
            timeout=10.0,
        )
