"""记忆检索模块 - 负责从短期记忆服务中检索对话历史"""

from sage.common.core import MapFunction


class MemoryRetrieval(MapFunction):
    """从短期记忆服务检索对话历史
    
    职责：
    1. 调用 ShortTermMemoryService 检索所有对话
    2. 将对话转换为文本格式（供 LLM 使用）
    3. 返回对话历史文本
    """

    def __init__(self):
        super().__init__()

    def execute(self, data):
        """执行记忆检索
        
        Args:
            data: PipelineRequest 对象或字典
        
        Returns:
            在原始数据基础上添加 "history_text" 字段
        """
        if not data:
            return None

        # 提取 payload（如果是 PipelineRequest）
        payload = data.payload if hasattr(data, "payload") else data

        # 调用短期记忆服务检索所有对话
        # 注意：retrieve() 方法不接受参数，直接调用即可
        memory_data = self.call_service(
            "short_term_memory",
            method="retrieve",
            timeout=10.0
        )

        # 将检索到的对话转换为文本格式
        history_lines = []
        for entry in memory_data:
            dialog = entry.get("dialog", [])
            for msg in dialog:
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                history_lines.append(f"{speaker}: {text}")

        history_text = "\n".join(history_lines)

        # 将历史文本添加到 payload 中
        payload["history_text"] = history_text

        return data
