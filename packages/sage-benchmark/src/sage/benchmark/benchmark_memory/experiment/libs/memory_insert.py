"""记忆插入模块 - 负责将对话存储到记忆服务中"""

from sage.benchmark.benchmark_memory.experiment.utils.data_parser import DataParser
from sage.common.core import MapFunction


class MemoryInsert(MapFunction):
    """将对话插入记忆服务

    职责：
    1. 接收 PreInsert 输出的列表格式数据
    2. 逐条处理记忆条目
    3. 调用配置的记忆服务存储
    4. 透传数据给下游
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

        # 初始化数据解析器
        self.parser = DataParser(config)

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
        # None 或空数据，直接返回
        if not data:
            return None

        # 提取记忆条目队列
        entries = data.get("memory_entries", [])
        if not entries:
            return data

        # 逐个处理记忆条目
        for entry_dict in entries:
            self._insert_single_entry(entry_dict)

        # 透传数据给下一个算子（不修改队列）
        return data

    def _insert_single_entry(self, entry_dict: dict):
        """插入单条记忆条目（统一调用格式）

        Args:
            entry_dict: 记忆条目字典，由 PreInsert 生成：
                - 传统模式: {"data": {...}}
                - 三元组模式: {"dialogs": [...], "triple": ..., "refactor": ..., "embedding": ...}

        调用服务的统一格式：
            call_service(service_name, entry, vector, metadata, method="insert")
            
        根据 DataParser 配置的 adapter 决定如何处理 entry_dict：
            - "to_dialogs": 返回 str（多条对话已合并）
            - "to_refactor": 返回 str
        """
        # 使用 parser 统一提取 entry（根据配置的 adapter 决定）
        entry = self.parser.extract(entry_dict)
        
        # 如果 entry 为空字符串，跳过插入
        if not entry:
            return
        
        # 提取 vector 和 metadata
        vector = entry_dict.get("embedding", None)
        metadata = entry_dict.get("metadata", None)

        # 统一插入字符串（to_dialogs 和 to_refactor 都是 str）
        self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            method="insert",
            timeout=10.0,
        )
