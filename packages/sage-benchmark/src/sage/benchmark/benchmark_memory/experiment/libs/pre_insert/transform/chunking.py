"""ChunkingAction - 文本分块策略

将长文本分割为多个小块，便于检索和管理。
适用于 MemGPT 等需要分块处理的记忆体。
"""

import re

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class ChunkingAction(BasePreInsertAction):
    """文本分块 Action

    使用场景：
    - MemGPT: 将长对话分块存储
    - 通用 RAG: 文档分块索引

    支持的分块策略：
    - fixed: 固定长度分块（按字符数）
    - sentence: 按句子边界分块
    - paragraph: 按段落分块
    """

    def _init_action(self) -> None:
        """初始化分块参数"""
        self.chunk_size = self.config.get("chunk_size", 512)
        self.chunk_overlap = self.config.get("chunk_overlap", 50)
        self.chunk_strategy = self.config.get("chunk_strategy", "fixed")

        # 句子分割模式（支持中英文）
        self.sentence_pattern = re.compile(r'[。.!?！？]+["\'»"]*\s*')
        # 段落分割模式
        self.paragraph_pattern = re.compile(r"\n\s*\n")

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行文本分块

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含多个分块条目的输出
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 分块
        chunks = self._split_text(text)

        # 创建记忆条目
        entries = []
        for i, chunk in enumerate(chunks):
            entry = {
                "text": chunk,
                "chunk_text": chunk,
                "metadata": {
                    "action": "transform.chunking",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_strategy": self.chunk_strategy,
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "chunk_insert"
            entries.append(entry)

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "total_chunks": len(chunks),
                "chunk_strategy": self.chunk_strategy,
            },
        )

    def _split_text(self, text: str) -> list[str]:
        """根据策略分块文本

        Args:
            text: 待分块的文本

        Returns:
            分块后的文本列表
        """
        if self.chunk_strategy == "sentence":
            return self._split_by_sentence(text)
        elif self.chunk_strategy == "paragraph":
            return self._split_by_paragraph(text)
        else:  # fixed
            return self._split_fixed(text)

    def _split_fixed(self, text: str) -> list[str]:
        """固定长度分块（带重叠）

        Args:
            text: 待分块的文本

        Returns:
            分块列表
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks.append(chunk)

            # 下一个块的起始位置（考虑重叠）
            start = end - self.chunk_overlap

            # 避免无限循环
            if start + self.chunk_size >= text_len:
                break

        return chunks

    def _split_by_sentence(self, text: str) -> list[str]:
        """按句子分块

        Args:
            text: 待分块的文本

        Returns:
            分块列表
        """
        # 按句子分割
        sentences = self.sentence_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 合并为不超过 chunk_size 的块
        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_len + sentence_len > self.chunk_size and current_chunk:
                # 当前块已满，保存并开始新块
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_len = sentence_len
            else:
                current_chunk.append(sentence)
                current_len += sentence_len

        # 保存最后一个块
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_by_paragraph(self, text: str) -> list[str]:
        """按段落分块

        Args:
            text: 待分块的文本

        Returns:
            分块列表
        """
        # 按段落分割
        paragraphs = self.paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # 如果段落太长，进一步使用句子分块
        chunks = []
        for para in paragraphs:
            if len(para) > self.chunk_size:
                # 段落过长，使用句子分块
                chunks.extend(self._split_by_sentence(para))
            else:
                chunks.append(para)

        return chunks
