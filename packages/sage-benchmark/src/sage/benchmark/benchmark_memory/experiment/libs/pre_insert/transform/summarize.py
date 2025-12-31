"""SummarizeAction - 文本摘要策略

使用 LLM 生成对话摘要，减少存储和检索开销。
适用于 MemGPT, LD-Agent、SCM 等需要摘要的记忆体。

对齐 SCM pre_insert 的关键点：
- 同时保存原文(original_text)与摘要(summary)
- 支持 summary_threshold（超过阈值才生成摘要，否则摘要=原文）
- 支持 embed_summary（是否对摘要做向量化；为 False 时改为对原文向量化）
- 兼容 only_on_session_end（仅在会话结束时生成摘要）

注意：
- 为不影响其他算子/默认行为，提供合理默认值：
    - embed_summary: True（默认沿用“摘要即存储文本、为其生成 embedding”的常见做法）
    - summary_threshold: None（默认禁用阈值；SCM 场景可显式设为 300；length_mode=char 近似）
    - only_on_session_end: False（默认每轮即可生成摘要）
"""

import logging
from typing import Optional

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
        self._llm_generator: Optional[LLMGenerator] = None
        self._use_llm = self.config.get("use_llm", True)  # 默认使用 LLM

        # 兼容 SCM 的可配置项（设置默认值以避免影响其他算子）
        # - 是否仅在会话结束时生成摘要（默认 False：每轮都可摘要）
        self.only_on_session_end = self.config.get("only_on_session_end", False)
        # - 是否对摘要做 embedding（默认 True：与以往 summarize 行为兼容；SCM 期望 False）
        self.embed_summary = self.config.get("embed_summary", True)
        # - 超过阈值才生成摘要（默认 None=禁用；SCM 可在配置中设为 300）。
        #   此处按字符长度近似，元数据标注 length_mode=char
        self.summary_threshold = self.config.get("summary_threshold", None)

        # 可选的 Embedding 生成器（由 operator 注入）。若存在且 embed_summary=False，则在本 Action 内直接生成
        # 对“原文”的 embedding，避免 operator 的批量逻辑默认对 summary 进行 embedding
        self._embedding_generator = None

    def set_llm_generator(self, llm_generator: LLMGenerator) -> None:
        """设置 LLM 生成器（由 PreInsert operator 调用）"""
        self._llm_generator = llm_generator

    # 供 operator 注入，可选
    def set_embedding_generator(self, embedding_generator) -> None:
        self._embedding_generator = embedding_generator

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
            # 不是 session 结束，跳过摘要生成，直接返回原始对话
            dialogs = input_data.data.get("dialogs", [])
            text = self._format_dialogue(dialogs)

            entry = {
                "text": text,  # 兼容：此分支直接存原文
                "original_text": text,
                "metadata": {
                    "action": "transform.summarize",
                    "skipped": True,
                    "reason": "not_session_end",
                },
            }
            # 如需与 SCM 对齐向量化（embed_summary=False），这里直接对原文生成 embedding
            if not self.embed_summary and self._embedding_generator is not None:
                try:
                    entry["embedding"] = self._embedding_generator.embed(text)
                except Exception as e:
                    logger.warning(f"[Embedding] generate on original_text failed: {e}")

            entry = self._set_default_fields(entry)
            entry["insert_method"] = "direct_insert"

            return PreInsertOutput(
                memory_entries=[entry],
                metadata={"summarized": False, "skipped": True},
            )

        # Session 结束,生成摘要
        print(f"\n{'=' * 60}")
        print(f"[Summarize] Session {session_id} - 生成摘要（SCM 对齐可选）")
        print(f"{'=' * 60}")

        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 阈值判断：当 summary_threshold 未配置(None) 时，总是生成摘要；
        # 显式配置了阈值时（如 SCM=300），只有超阈值才生成摘要，否则摘要=原文
        should_summarize = self._exceed_threshold(text)
        # 收集大模型调用信息（用于调试）
        llm_called = False
        llm_error = None
        try:
            llm_model = getattr(self._llm_generator, "model_name", None)
        except Exception:
            llm_model = None
        try:
            llm_base_url = (
                str(getattr(getattr(self._llm_generator, "client", object()), "base_url", ""))
                or None
            )
        except Exception:
            llm_base_url = None

        if should_summarize:
            llm_called = bool(self._use_llm and self._llm_generator is not None)
            summary = self._generate_summary(text)
        else:
            summary = text

        print(f"  原文长度: {len(text)} 字符")
        print(f"  摘要长度: {len(summary)} 字符")
        print(f"  压缩率: {len(summary) / len(text) * 100:.1f}%")

        # turn_index/session_id 作为时间戳替代（如果没有真实时间戳）
        dialogs = input_data.data.get("dialogs", [])
        turn_index = input_data.data.get("turn_index")
        if turn_index is None:
            # 退化近似：当前对话条目数（非严格意义）
            turn_index = len(dialogs)

        # 创建记忆条目（同时保存原文和摘要）
        # 为兼容不同使用场景：
        # - 若 embed_summary=True（默认），则沿用“摘要为主要文本”的习惯；
        # - 若 embed_summary=False（SCM 对齐），则以原文为主要文本，摘要存 metadata/summary 字段，且优先对原文做 embedding。
        text_for_store = summary if self.embed_summary else text

        entry = {
            "text": text_for_store,
            "original_text": text,
            "summary": summary,
            "metadata": {
                "action": "transform.summarize",
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if text else 0,
                "style": self.style,
                "has_summary": should_summarize,
                "embed_summary": self.embed_summary,
                "length_mode": "char",  # 此处使用字符近似
                "summary_threshold": self.summary_threshold
                if self.summary_threshold is not None
                else "none",
                "session_id": session_id,
                "turn_index": turn_index,
                # LLM 调试信息（参考 extract.keyword 风格）
                "llm_called": llm_called,
                "llm_model": llm_model if "llm_model" in locals() else None,
                "llm_base_url": llm_base_url if "llm_base_url" in locals() else None,
                "llm_error": llm_error,
            },
        }

        # 当 embed_summary=False 时，在本 Action 内直接对“原文”生成 embedding，避免 operator 对 summary 进行 embedding
        embedding_source = None
        if not self.embed_summary and self._embedding_generator is not None:
            try:
                entry["embedding"] = self._embedding_generator.embed(text)
                embedding_source = "original"
            except Exception as e:
                logger.warning(f"[Embedding] generate on original_text failed: {e}")
                embedding_source = "error"
        else:
            # 留给 operator 的批量 embedding（通常针对 entry.text）
            embedding_source = "summary" if self.embed_summary else "none"
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "summarize_insert"

        # 控制台调试输出
        try:
            print(
                f"[DEBUG Summarize] threshold={self.summary_threshold or 'none'} "
                f"should_summarize={should_summarize} embed_summary={self.embed_summary} "
                f"text_for_store={'summary' if self.embed_summary else 'original'} "
                f"embedding_source={embedding_source} llm_called={llm_called} "
                f"model={(llm_model if 'llm_model' in locals() and llm_model else '-')} "
                f"base={(llm_base_url if 'llm_base_url' in locals() and llm_base_url else '-')}"
            )
        except Exception:
            pass

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "summarized": True,
                "compression_ratio": entry["metadata"]["compression_ratio"],
            },
        )

    def _exceed_threshold(self, text: str) -> bool:
        """判断是否超过摘要阈值。

        当前实现采用字符长度近似，以保证在无 tokenizer 依赖时也可用；
        若后续接入 tiktoken，可在此扩展为真实 token 计数。
        """
        # 未配置阈值：保持原 summarize 行为（需要就生成）
        if self.summary_threshold is None:
            return True
        try:
            length = len(text) if text else 0
            return length > int(self.summary_threshold)
        except Exception:
            # 配置异常时，回退为“总是生成摘要”，以保证鲁棒性
            return True

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
                prompt = self.prompt_template
                # 兼容多变量名：{dialogue}/{text}/{input}
                if "{dialogue}" in prompt:
                    prompt = prompt.replace("{dialogue}", text)
                if "{text}" in prompt:
                    prompt = prompt.replace("{text}", text)
                if "{input}" in prompt:
                    prompt = prompt.replace("{input}", text)
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
