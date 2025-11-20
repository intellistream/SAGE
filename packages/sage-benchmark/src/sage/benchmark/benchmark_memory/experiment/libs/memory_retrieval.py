"""记忆检索模块 - 负责从短期记忆服务中检索对话历史"""

from sage.common.core import MapFunction


class MemoryRetrieval(MapFunction):
    """从短期记忆服务检索对话历史

    职责：
    1. 调用 ShortTermMemoryService 检索所有对话
    2. 将对话转换为文本格式（供 LLM 使用）
    3. 返回对话历史文本
    """

    def __init__(self, config=None):
        """初始化 MemoryRetrieval
        
        Args:
            config: RuntimeConfig 对象（可选，当前不使用）
        """
        super().__init__()

    def execute(self, data):
        """执行记忆检索

        Args:
            data: PipelineRequest 对象或字典，可包含 'question' 字段用于基于查询的检索

        Returns:
            在原始数据基础上添加 "history_text" 字段
        """
        if not data:
            return None

        # 提取 payload（如果是 PipelineRequest）
        payload = data.payload if hasattr(data, "payload") else data

        # 获取问题（如果有）
        # question = payload.get("question", "")  # Reserved for future question-based retrieval

        try:
            # 调用短期记忆服务检索所有对话
            # 注意：当前 STM 的 retrieve() 方法不接受参数，未来可扩展为基于问题的检索
            # 例如：对于向量数据库，可以根据 question 检索相关对话
            memory_data = self.call_service("short_term_memory", method="retrieve", timeout=10.0)

            # 检查返回结果
            if memory_data is None:
                print("⚠️  记忆检索失败：服务未返回数据")
                payload["history_text"] = ""
                return data

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

        except Exception as e:
            import traceback

            print(f"❌ 记忆检索异常：{str(e)}")
            traceback.print_exc()
            # 出错时返回空历史
            payload["history_text"] = ""

        return data
