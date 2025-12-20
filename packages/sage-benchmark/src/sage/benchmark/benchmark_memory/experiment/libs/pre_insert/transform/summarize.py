"""SummarizeAction - 文本摘要策略

使用 LLM 生成对话摘要，减少存储和检索开销。
适用于 MemGPT, LD-Agent 等需要摘要的记忆体。
"""

import logging

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput

logger = logging.getLogger(__name__)


class SummarizeAction(BasePreInsertAction):
    """文本摘要 Action

    使用场景：
    - MemGPT: 对长对话生成摘要
    - LD-Agent: 摘要重要对话
    - MemoryBank: 定期摘要历史记忆
    """

    def _init_action(self) -> None:
        """初始化摘要参数和 LLM 客户端"""
        self.max_length = self.config.get("max_length", 200)
        self.style = self.config.get("style", "concise")  # concise, detailed

        # 摘要提示模板
        self.prompt_template = self.config.get(
            "summarize_prompt",
            "Summarize the following conversation in {max_length} words or less:\n\n{text}\n\nSummary:",
        )

        # 初始化 LLM 生成器 (将由 operator 注入)
        self._llm_generator: LLMGenerator | None = None
        self._use_llm = self.config.get("use_llm", True)  # 默认使用 LLM

        # 是否仅在 session 结束时生成摘要
        self.only_on_session_end = self.config.get("only_on_session_end", False)

    def set_llm_generator(self, llm_generator: LLMGenerator) -> None:
        """设置 LLM 生成器（由 PreInsert operator 调用）"""
        self._llm_generator = llm_generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行文本摘要

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含摘要条目的输出
        """
        # 检查是否仅在 session 结束时生成摘要
        is_session_end = input_data.data.get("is_session_end", False)
        session_id = input_data.data.get("session_id", "unknown")

        if self.only_on_session_end and not is_session_end:
            # 不是 session 结束,跳过摘要生成,直接返回原始对话
            dialogs = input_data.data.get("dialogs", [])
            text = self._format_dialogue(dialogs)

            entry = {
                "text": text,
                "original_text": text,
                "metadata": {
                    "action": "transform.summarize",
                    "skipped": True,
                    "reason": "not_session_end",
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "direct_insert"

            return PreInsertOutput(
                memory_entries=[entry],
                metadata={"summarized": False, "skipped": True},
            )

        # Session 结束,生成摘要
        print(f"\n{'=' * 60}")
        print(f"[MemoryBank] Session {session_id} 结束 - 生成摘要")
        print(f"{'=' * 60}")

        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 生成摘要
        summary = self._generate_summary(text)

        print(f"  原文长度: {len(text)} 字符")
        print(f"  摘要长度: {len(summary)} 字符")
        print(f"  压缩率: {len(summary) / len(text) * 100:.1f}%")

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

        使用 LLM 生成摘要（MemoryBank 风格）。
        如果 LLM 不可用或禁用，降级为简单截断。

        Args:
            text: 原始文本

        Returns:
            摘要文本
        """
        # 如果启用 LLM 且生成器已注入，使用 LLM 生成摘要
        if self._use_llm and self._llm_generator is not None:
            try:
                # 格式化 prompt
                prompt = self.prompt_template.replace("{dialogue}", text).replace("{text}", text)
                if "{max_length}" in prompt:
                    prompt = prompt.replace("{max_length}", str(self.max_length))

                # 调用 LLM 生成摘要
                # 注意：max_length 是字符数，max_tokens 是 token 数
                # 中文: 1字符 ≈ 2-3 tokens，英文: 1词 ≈ 1-2 tokens
                # 保守估计：使用 max_length * 3 来确保足够空间
                summary = self._llm_generator.generate(
                    prompt=prompt,
                    max_tokens=self.max_length * 3,  # 字符到token的安全转换
                    temperature=0.3,  # 较低温度保证一致性
                )

                if summary.strip():
                    logger.debug(f"[LLM 摘要] 原文长度: {len(text)}, 摘要长度: {len(summary)}")
                    return summary.strip()
                else:
                    logger.warning("[LLM 摘要] LLM 返回空字符串，降级为截断策略")
            except Exception as e:
                logger.warning(f"[LLM 摘要] 调用失败: {e}，降级为截断策略")

        # 降级策略：简单截断（保持句子完整性）
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
