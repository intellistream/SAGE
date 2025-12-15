"""SummarizeAction - 文本摘要策略

使用 LLM 生成对话摘要，减少存储和检索开销。
适用于 MemGPT, LD-Agent 等需要摘要的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class SummarizeAction(BasePreInsertAction):
    """文本摘要 Action

    使用场景：
    - MemGPT: 对长对话生成摘要
    - LD-Agent: 摘要重要对话
    - MemoryBank: 定期摘要历史记忆
    """

    def _init_action(self) -> None:
        """初始化摘要参数"""
        self.max_length = self.config.get("max_length", 200)
        self.style = self.config.get("style", "concise")  # concise, detailed

        # 摘要提示模板
        self.prompt_template = self.config.get(
            "prompt_template",
            "Summarize the following conversation in {max_length} words or less:\n\n{text}\n\nSummary:",
        )

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行文本摘要

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含摘要条目的输出
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 生成摘要
        summary = self._generate_summary(text)

        # 创建记忆条目（同时保存原文和摘要）
        entry = {
            "text": summary,
            "original_text": text,
            "summary": summary,
            "metadata": {
                "action": "transform.summarize",
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if text else 0,
                "style": self.style,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "summarize_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "summarized": True,
                "compression_ratio": entry["metadata"]["compression_ratio"],
            },
        )

    def _generate_summary(self, text: str) -> str:
        """生成摘要

        注意：这里使用简化的摘要逻辑。
        实际应用中应该调用 LLM（通过 UnifiedInferenceClient）。

        Args:
            text: 原始文本

        Returns:
            摘要文本
        """
        # TODO: 集成 LLM 调用
        # 当前实现：简单截断前 N 个字符作为摘要
        if len(text) <= self.max_length:
            return text

        # 按句子截断（尽量不破坏句子完整性）
        import re

        sentences = re.split(r'[。.!?！？]+["\'»"]*\s*', text)

        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) <= self.max_length:
                summary += sentence + "。"
            else:
                break

        if not summary:
            # 如果第一句话就超长，强制截断
            summary = text[: self.max_length] + "..."

        return summary.strip()
