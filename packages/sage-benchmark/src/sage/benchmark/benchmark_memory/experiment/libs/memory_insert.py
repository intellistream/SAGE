"""记忆插入模块 - 负责将对话存储到短期记忆服务中"""

from sage.common.core import MapFunction


class MemoryInsert(MapFunction):
    """将对话插入短期记忆服务

    职责：
    1. 接收对话数据
    2. 调用 ShortTermMemoryService 存储对话
    3. 返回存储状态
    """

    def __init__(self):
        super().__init__()

    def execute(self, data):
        """执行记忆插入

        Args:
            data: PipelineRequest 对象或字典

        Returns:
            原始数据（透传，供后续处理使用）
        """
        if not data:
            return None

        # 提取 payload（如果是 PipelineRequest）
        payload = data.payload if hasattr(data, "payload") else data

        dialogs = payload.get("dialogs", [])

        # 调用短期记忆服务存储对话
        # 注意：insert() 方法直接接收 dialog 列表，不需要包装在字典中
        self.call_service(
            "short_term_memory",
            dialogs,  # 直接传递列表
            method="insert",
            timeout=10.0,
        )

        # 透传数据给下一个算子（保持原始格式）
        return data
