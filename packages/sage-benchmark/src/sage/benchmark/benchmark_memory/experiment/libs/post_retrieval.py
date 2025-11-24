"""后检索处理模块 - 在记忆检索后的后处理（可选）

对于短期记忆（STM），通常不需要后处理。
此模块保留用于未来扩展（如结果过滤、格式化、排序等）。
"""

from sage.common.core import MapFunction


class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子

    职责：
    - 结果过滤
    - 格式化对话历史为结构化文本（阶段一）
    - 排序和去重

    注：短期记忆通常不需要此步骤
    """

    def __init__(self, config):
        """初始化 PostRetrieval

        Args:
            config: RuntimeConfig 对象，从中获取 operators.post_retrieval.action
        """
        super().__init__()
        self.action = config.get("operators.post_retrieval.action", "none")
        # 读取对话格式化Prompt（阶段一）- 从operators.post_retrieval读取
        self.conversation_format_prompt = config.get(
            "operators.post_retrieval.conversation_format_prompt",
            "Below is a conversation between two people. The conversation takes place over multiple days and the date of each conversation is written at the beginning of the conversation."
        )

    def execute(self, data):
        """执行后处理

        Args:
            data: PipelineRequest 对象或检索到的记忆数据

        Returns:
            处理后的数据（添加了history_text字段）
        """
        # 始终格式化对话历史为结构化文本（阶段一）
        # action配置用于未来扩展其他后处理逻辑
        return self._format_dialog_history(data)

    def _format_dialog_history(self, data):
        """格式化对话历史为结构化文本（阶段一：Prompt拼接）

        从 memory_data 中提取对话，格式化为：
        
        Below is a conversation...
        
        DATE: 2023-08-01
        CONVERSATION:
        Alice said, "..."
        Bob said, "..."
        
        Args:
            data: 包含 memory_data 的字典
                 memory_data 格式: [{"dialog": [{"speaker": "...", "text": "..."}, ...]}, ...]

        Returns:
            添加了 history_text 字段的 data
        """
        if not data:
            return data

        memory_data = data.get("memory_data", [])

        # 构建对话历史文本
        history_parts = []
        
        # 添加Prompt前缀（阶段一）
        if self.conversation_format_prompt:
            history_parts.append(self.conversation_format_prompt.strip())
        
        # 格式化对话内容
        # STM返回格式: [{"dialog": [{"speaker": "...", "text": "...", "date_time": "..."}, ...]}, ...]
        # 按日期分组对话
        current_date = None
        conversation_lines = []
        
        for entry in memory_data:
            dialog = entry.get("dialog", [])
            for msg in dialog:
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                date_time = msg.get("date_time", "")
                
                # 检查日期是否变化
                if date_time and date_time != current_date:
                    # 输出上一个日期的对话
                    if conversation_lines:
                        history_parts.append("CONVERSATION:")
                        history_parts.extend(conversation_lines)
                        conversation_lines = []
                    
                    # 开始新日期
                    current_date = date_time
                    history_parts.append(f"\nDATE: {date_time}")
                
                # 添加对话行
                conversation_lines.append(f'{speaker} said, "{text}"')
        
        # 输出最后一组对话
        if conversation_lines:
            history_parts.append("CONVERSATION:")
            history_parts.extend(conversation_lines)
        
        # 合并为最终文本
        history_text = "\n".join(history_parts) if history_parts else ""
        
        # 添加到data中
        data["history_text"] = history_text
        
        return data
