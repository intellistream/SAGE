"""PreInsert - 记忆插入前预处理算子

================================================================================
模块定位
================================================================================
本模块是 SAGE Pipeline 四层算子之一，负责记忆插入前的预处理操作。

Pipeline 架构：
┌─────────────┐    ┌─────────────┐    ┌───────────────┐    ┌──────────────┐
│  PreInsert  │ -> │  PostInsert │ -> │ PreRetrieval  │ -> │ PostRetrieval│
│  (插入前)    │    │  (插入后)    │    │  (检索前)      │    │  (检索后)     │
└─────────────┘    └─────────────┘    └───────────────┘    └──────────────┘
      ↑                  ↑                   ↑                    ↑
   预处理数据         优化存储            预处理查询            处理结果

本模块职责：
- 预处理记忆数据（格式转换、信息抽取、评分等）
- 决定插入方式（通过 memory_entries 返回 insert_method）
- 过程中仅允许对记忆服务进行检索（通过 service_name 访问）

================================================================================
Action 分类体系
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ 类别 A: 透传类                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ • none        - 直接透传，不做任何处理                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 类别 B: 文本转换类 (transform)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ transform_type:                                                              │
│   • chunking      - 文本分块 (MemGPT, RAG)                                   │
│   • topic_segment - 话题分段 (LoCoMo, LD-Agent)                              │
│   • fact_extract  - 事实抽取 (LoCoMo, SeCom)                                 │
│   • summarize     - 文本摘要 (MemGPT, MemoryBank)                            │
│   • compress      - 文本压缩 (LLMLingua)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 类别 C: 信息抽取类 (extract)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ extract_type:                                                                │
│   • keyword  - 关键词抽取 (RAKE/TextRank)                                    │
│   • entity   - 实体抽取 (spaCy NER)                                          │
│   • noun     - 名词抽取 (spaCy POS)                                          │
│   • persona  - 人物画像抽取 (LLM) - 参考 LAPS, LD-Agent                       │
│   • all      - 以上全部                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 类别 D: 评分类 (score)                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ score_type:                                                                  │
│   • importance - 重要性评分 (Generative Agents)                              │
│   • emotion    - 情感评分 (EmotionalRAG)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 类别 E: 向量编码类                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ • multi_embed - 多维向量编码 (EmotionalRAG 情感向量)                          │
│ • scm_embed   - SCM 样式: 摘要+原文+Embedding 同时保存 (SCM4LLMs)             │
│ • tri_embed   - 三元组提取+重构+Embedding (HippoRAG)                          │
└─────────────────────────────────────────────────────────────────────────────┘

================================================================================
类结构
================================================================================
PreInsert
├── __init__(config)           # 初始化
├── _init_for_action()         # 按 action 初始化特定工具
├── execute(data)              # 执行入口
│
├── [A] _execute_none          # 透传
│
├── [B] _execute_transform     # 文本转换（5 种子类型内联）
│   ├── chunking               # 分块
│   ├── topic_segment          # 话题分段
│   ├── fact_extract           # 事实抽取
│   ├── summarize              # 摘要
│   └── compress               # 压缩
│
├── [C] _execute_extract       # 信息抽取（4 种子类型内联）
│   ├── keyword                # 关键词
│   ├── entity                 # 实体
│   ├── noun                   # 名词
│   └── persona                # 人物画像
│
├── [D] _execute_score         # 评分（2 种子类型内联）
│   ├── importance             # 重要性
│   └── emotion                # 情感
│
├── [E-1] _execute_multi_embed # 多维向量 (EmotionalRAG)
├── [E-2] _execute_scm_embed   # SCM 编码 (SCM4LLMs)
└── [E-3] _execute_tri_embed   # 三元组编码 (HippoRAG)

================================================================================
论文对应
================================================================================
| Action        | 论文                                       |
|---------------|-------------------------------------------|
| none          | 短期记忆场景                                |
| transform     | MemGPT, SeCom, LoCoMo, LD-Agent           |
| extract       | A-mem, LD-Agent, LAPS                     |
| score         | Generative Agents, EmotionalRAG           |
| multi_embed   | EmotionalRAG                              |
| scm_embed     | SCM4LLMs                                  |
| tri_embed     | HippoRAG                                  |
"""

from __future__ import annotations

import re
import time
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils import (
    EmbeddingGenerator,
    LLMGenerator,
    format_dialogue,
    get_required_config,
)
from sage.common.core import MapFunction


class PreInsert(MapFunction):
    """记忆插入前的预处理算子

    Pipeline 位置: 第 1 层（插入前）
    访问权限: 仅允许检索记忆服务（不允许插入/删除）

    Action 分类:
        [A] none        - 透传
        [B] transform   - 文本转换 (chunking/topic_segment/fact_extract/summarize/compress)
        [C] extract     - 信息抽取 (keyword/entity/noun/persona/all)
        [D] score       - 评分 (importance/emotion)
        [E] multi_embed / scm_embed / tri_embed - 向量编码

    Attributes:
        config: 运行时配置对象
        action: 当前执行的 action 类型
        service_name: 关联的记忆服务名称（用于检索）
    """

    def __init__(self, config):
        """初始化 PreInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.pre_insert.* 配置
        """
        super().__init__()
        self.config = config

        # 注册要访问的记忆服务名称（插入前操作允许对记忆数据结构进行检索）
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 初始化共通工具（LLM 和 Embedding 生成器）
        self._generator: LLMGenerator = LLMGenerator.from_config(self.config)
        self._embedding_generator: EmbeddingGenerator = EmbeddingGenerator.from_config(self.config)

        # 根据 action 初始化特定配置和工具
        self.action = get_required_config(self.config, "operators.pre_insert.action")
        self._init_for_action()

    def _init_for_action(self):
        """根据 action 类型初始化特定配置和工具"""
        if self.action == "tri_embed":
            self._triple_extraction_prompt = get_required_config(
                self.config,
                "operators.pre_insert.triple_extraction_prompt",
                "action=tri_embed",
            )

        elif self.action == "transform":
            get_required_config(
                self.config,
                "operators.pre_insert.transform_type",
                "action=transform",
            )

        elif self.action == "extract":
            extract_type = get_required_config(
                self.config,
                "operators.pre_insert.extract_type",
                "action=extract",
            )
            if extract_type in ["entity", "noun", "all"]:
                import spacy

                model_name = get_required_config(
                    self.config,
                    "operators.pre_insert.spacy_model",
                    "entity/noun extraction",
                )
                self._spacy_nlp = spacy.load(model_name)

        elif self.action == "scm_embed":
            # SCM 样式：同时生成摘要和 embedding，保留原文
            # summarize prompt
            self._scm_summarize_prompt = get_required_config(
                self.config,
                "operators.pre_insert.summarize_prompt",
                "action=scm_embed",
            )
            # 是否对摘要做 embedding（默认对原文）
            self._scm_embed_summary = self.config.get("operators.pre_insert.embed_summary", False)
            # 原文 token 阈值，超过才生成摘要
            self._scm_summary_threshold = self.config.get(
                "operators.pre_insert.summary_threshold", 300
            )

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行预处理

        Args:
            data: 原始对话数据（字典格式）

        Returns:
            处理后的数据（字典格式），包含 memory_entries 队列
        """
        # 根据 action 调用对应的大类方法
        action_handlers = {
            "none": self._execute_none,
            "tri_embed": self._execute_tri_embed,
            "transform": self._execute_transform,
            "extract": self._execute_extract,
            "score": self._execute_score,
            "multi_embed": self._execute_multi_embed,
            "scm_embed": self._execute_scm_embed,
        }

        handler = action_handlers.get(self.action)
        if handler:
            entries = handler(data)
        else:
            print("[WARNING] " + str(f"Unknown action: {self.action}, passing through"))
            entries = [data]

        # 确保每个 entry 都有 insert_method
        for entry in entries:
            if "insert_method" not in entry:
                entry["insert_method"] = "default"
            if "insert_mode" not in entry:
                entry["insert_mode"] = "passive"

        # 为所有 entry 生成 embedding（如果还没有）
        # 按优先级选择文本字段用于 embedding
        if self._embedding_generator and self._embedding_generator.is_available():
            for entry in entries:
                if "embedding" not in entry or entry["embedding"] is None:
                    # 按优先级选择文本字段
                    text_for_embed = (
                        entry.get("summary", "")
                        or entry.get("compressed_text", "")
                        or entry.get("chunk_text", "")
                        or entry.get("segment_text", "")
                        or entry.get("fact", "")
                        or entry.get("refactor", "")
                        or entry.get("text", "")
                    )
                    # 如果还是没有文本，尝试从 dialogs 格式化
                    if not text_for_embed and "dialogs" in entry:
                        text_for_embed = format_dialogue(entry.get("dialogs", []))

                    if text_for_embed:
                        try:
                            embedding = self._embedding_generator.embed(text_for_embed)
                            if embedding:
                                entry["embedding"] = embedding
                        except Exception as e:
                            print("[WARNING] " + str(f"Embedding generation failed: {e}"))

        # 统一设置 text 字段（供 MemoryInsert 使用）
        # 按优先级选择：已有 text > 各种转换字段 > dialogs
        for entry in entries:
            if "text" not in entry or not entry["text"]:
                entry["text"] = (
                    entry.get("refactor", "")
                    or entry.get("summary", "")
                    or entry.get("compressed_text", "")
                    or entry.get("chunk_text", "")
                    or entry.get("segment_text", "")
                    or entry.get("fact", "")
                )
                # 如果还是没有，从 dialogs 格式化
                if not entry["text"] and "dialogs" in entry:
                    entry["text"] = format_dialogue(entry.get("dialogs", []))

        # 在原字典基础上添加 memory_entries 队列
        data["memory_entries"] = entries
        return data

    # ==========================================================================
    # [A] 透传类: none
    # ==========================================================================

    def _execute_none(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """直接透传数据，不做任何处理

        适用场景: 短期记忆、简单存储
        """
        entry = data.copy()
        entry["insert_method"] = "default"
        entry["insert_mode"] = "passive"
        return [entry]

    # ==========================================================================
    # [B] 文本转换类: transform
    # 子类型: chunking | topic_segment | fact_extract | summarize | compress
    # 论文: MemGPT, SeCom, LoCoMo, LD-Agent, LLMLingua
    # ==========================================================================

    def _execute_transform(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行内容转换

        transform_type:
        - chunking:      文本分块 (MemGPT, RAG)
        - topic_segment: 话题分段 (LoCoMo, LD-Agent)
        - fact_extract:  事实抽取 (LoCoMo, SeCom)
        - summarize:     文本摘要 (MemGPT, MemoryBank)
        - compress:      文本压缩 (LLMLingua)
        - summarize: 摘要
        - compress: 压缩

        Args:
            data: 原始数据

        Returns:
            转换后的记忆条目列表
        """
        transform_type = get_required_config(
            self.config, "operators.pre_insert.transform_type", "action=transform"
        )

        # 获取文本内容
        dialogs = data.get("dialogs", [])
        text = format_dialogue(dialogs)

        if not text:
            entry = data.copy()
            entry["insert_method"] = "default"
            entry["insert_mode"] = "passive"
            return [entry]

        # 根据 transform_type 处理
        if transform_type == "chunking":
            # ==== Chunking 逻辑内联 ====
            chunk_size = get_required_config(
                self.config, "operators.pre_insert.chunk_size", "transform_type=chunking"
            )
            chunk_overlap = get_required_config(
                self.config, "operators.pre_insert.chunk_overlap", "transform_type=chunking"
            )
            chunk_strategy = self.config.get("operators.pre_insert.chunk_strategy", "fixed")

            # 根据策略分块
            chunks = []
            if chunk_strategy == "sentence":
                # 按句子边界分块
                sentence_endings = re.compile(r"[.!?。！？]+[\s]*")
                sentences = sentence_endings.split(text)
                sentences = [s.strip() for s in sentences if s.strip()]

                current_chunk = []
                current_size = 0

                for sentence in sentences:
                    sentence_len = len(sentence)
                    if current_size + sentence_len > chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        # 保留部分句子作为重叠
                        overlap_sentences = []
                        overlap_size = 0
                        for s in reversed(current_chunk):
                            if overlap_size + len(s) <= chunk_overlap:
                                overlap_sentences.insert(0, s)
                                overlap_size += len(s)
                            else:
                                break
                        current_chunk = overlap_sentences
                        current_size = overlap_size

                    current_chunk.append(sentence)
                    current_size += sentence_len

                if current_chunk:
                    chunks.append(" ".join(current_chunk))

            elif chunk_strategy == "paragraph":
                # 按段落边界分块
                paragraphs = text.split("\n\n")
                paragraphs = [p.strip() for p in paragraphs if p.strip()]

                current_chunk = []
                current_size = 0

                for para in paragraphs:
                    para_len = len(para)
                    if current_size + para_len > chunk_size and current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                        current_chunk = []
                        current_size = 0

                    current_chunk.append(para)
                    current_size += para_len

                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))

            else:  # fixed
                # 固定大小分块
                start = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk = text[start:end]
                    if chunk.strip():
                        chunks.append(chunk)
                    start = end - chunk_overlap

            # 构建条目
            entries = []
            for i, chunk in enumerate(chunks):
                entry = data.copy()
                entry["chunk_text"] = chunk
                entry.setdefault("metadata", {})
                entry["metadata"]["chunk_index"] = i
                entry["metadata"]["total_chunks"] = len(chunks)
                entry["insert_method"] = "chunk_insert"
                entry["insert_mode"] = "passive"
                entries.append(entry)

            return entries if entries else [data]

        elif transform_type == "topic_segment":
            # ==== Topic Segment 逻辑内联 ====
            if not dialogs:
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            # 格式化对话（带索引）
            formatted_dialogs = []
            for i, dialog in enumerate(dialogs):
                speaker = dialog.get("speaker", "Unknown")
                dialog_text = dialog.get("text", dialog.get("clean_text", ""))
                formatted_dialogs.append(f"[Exchange {i}]: {speaker}: {dialog_text}")
            dialogue_text = "\n".join(formatted_dialogs)

            # 使用 LLM 识别话题边界
            prompt_template = get_required_config(
                self.config, "operators.pre_insert.segment_prompt", "transform_type=topic_segment"
            )
            prompt = prompt_template.replace("{dialogue}", dialogue_text)

            try:
                segments = self._generator.generate_json(prompt, default=[])
            except Exception as e:
                print(
                    "[WARNING] "
                    + str(f"Topic segmentation failed: {e}, falling back to single segment")
                )
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            if not segments:
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            # 构建分段条目
            min_size = self.config.get("operators.pre_insert.min_segment_size", 100)
            max_size = self.config.get("operators.pre_insert.max_segment_size", 500)

            entries = []
            for i, segment in enumerate(segments):
                exchange_indices = segment.get("exchanges", [])
                topic = segment.get("topic", f"segment_{i}")

                # 提取该段的对话
                segment_dialogs = [dialogs[idx] for idx in exchange_indices if idx < len(dialogs)]
                segment_text = format_dialogue(segment_dialogs)

                # 检查大小约束
                if len(segment_text) < min_size:
                    continue
                if len(segment_text) > max_size:
                    # 递归使用 chunking（通过修改配置临时调用）
                    # 为避免递归问题，这里简化为直接创建条目
                    entry = data.copy()
                    entry["segment_dialogs"] = segment_dialogs
                    entry["segment_text"] = segment_text
                    entry["topic"] = topic
                    entry["segment_index"] = i
                    entry["total_segments"] = len(segments)
                    entry["insert_method"] = "segment_insert"
                    entry["insert_mode"] = "passive"
                    entries.append(entry)
                else:
                    entry = data.copy()
                    entry["segment_dialogs"] = segment_dialogs
                    entry["segment_text"] = segment_text
                    entry["topic"] = topic
                    entry["segment_index"] = i
                    entry["total_segments"] = len(segments)
                    entry["insert_method"] = "segment_insert"
                    entry["insert_mode"] = "passive"
                    entries.append(entry)

            return entries if entries else [data]

        elif transform_type == "fact_extract":
            # ==== Fact Extract 逻辑内联 ====
            if not dialogs:
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            # 格式化对话（带 dialog_id）
            formatted_dialogs = []
            for i, dialog in enumerate(dialogs):
                speaker = dialog.get("speaker", "Unknown")
                dialog_text = dialog.get("text", dialog.get("clean_text", ""))
                dia_id = dialog.get("dia_id", i)
                formatted_dialogs.append(f"[{dia_id}] {speaker}: {dialog_text}")
            dialogue_text = "\n".join(formatted_dialogs)

            # 使用 LLM 提取事实
            prompt_template = get_required_config(
                self.config, "operators.pre_insert.fact_prompt", "transform_type=fact_extract"
            )
            prompt = prompt_template.replace("{dialogue}", dialogue_text)

            try:
                facts = self._generator.generate_json(prompt, default=[])
            except Exception as e:
                print("[WARNING] " + str(f"Fact extraction failed: {e}"))
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            if not facts:
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            # 根据格式构建条目
            fact_format = self.config.get("operators.pre_insert.fact_format", "statement")
            entries = []

            for fact_item in facts:
                if isinstance(fact_item, str):
                    fact_text = fact_item
                    speaker = "general"
                    dialog_id = None
                else:
                    fact_text = fact_item.get("fact", str(fact_item))
                    speaker = fact_item.get("speaker", "general")
                    dialog_id = fact_item.get("dialog_id")

                entry = data.copy()
                entry["fact"] = fact_text
                entry["fact_speaker"] = speaker
                entry["fact_dialog_id"] = dialog_id
                entry["fact_format"] = fact_format
                entry["insert_method"] = "fact_insert"
                entry["insert_mode"] = "passive"
                entries.append(entry)

            return entries if entries else [data]

        elif transform_type == "summarize":
            # ==== Summarize 逻辑内联 ====
            # 使用 LLM 生成摘要
            prompt_template = get_required_config(
                self.config, "operators.pre_insert.summarize_prompt", "transform_type=summarize"
            )
            prompt = prompt_template.replace("{dialogue}", text)

            try:
                max_tokens = self.config.get("operators.pre_insert.summary_max_tokens", 200)
                summary = self._generator.generate(prompt, max_tokens=max_tokens)
            except Exception as e:
                print("[WARNING] " + str(f"Summarization failed: {e}"))
                entry = data.copy()
                entry["insert_method"] = "default"
                return [entry]

            entry = data.copy()
            entry["summary"] = summary.strip()
            entry.setdefault("metadata", {})
            entry["metadata"]["original_text"] = text
            entry["metadata"]["is_summary"] = True
            entry["insert_method"] = "summary_insert"
            entry["insert_mode"] = "active"  # 摘要通常主动插入到 LTM
            entry["insert_params"] = {"target_tier": "ltm"}
            # embedding 在 execute() 末尾统一生成
            return [entry]

        elif transform_type == "compress":
            # ==== Compress 逻辑内联 ====
            compression_ratio = self.config.get("operators.pre_insert.compression_ratio", 0.5)

            try:
                # 尝试使用 LLMLingua
                from llmlingua import PromptCompressor

                model_name = self.config.get(
                    "operators.pre_insert.compression_model",
                    "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                )
                compressor = PromptCompressor(model_name, use_llmlingua2=True)

                result = compressor.compress_prompt(
                    text,
                    rate=compression_ratio,
                    use_context_level_filter=False,
                    force_tokens=["\n", ".", "[human]", "[bot]"],
                )
                compressed_text = result.get("compressed_prompt", text)

            except ImportError:
                print("[WARNING] " + "LLMLingua not installed, using simple truncation")
                # 简单截断作为后备
                target_len = int(len(text) * compression_ratio)
                compressed_text = text[:target_len]
            except Exception as e:
                print("[WARNING] " + str(f"Compression failed: {e}, using original text"))
                compressed_text = text

            entry = data.copy()
            entry["compressed_text"] = compressed_text
            entry["original_text"] = text
            entry["compression_ratio"] = len(compressed_text) / len(text) if text else 1.0
            entry["insert_method"] = "default"
            entry["insert_mode"] = "passive"
            return [entry]

        else:
            print("[WARNING] " + str(f"Unknown transform_type: {transform_type}, using default"))
            entry = data.copy()
            entry["insert_method"] = "default"
            entry["insert_mode"] = "passive"
            return [entry]

    # ==========================================================================
    # [C] 信息抽取类: extract
    # 子类型: keyword | entity | noun | persona | all
    # 论文: A-mem, LD-Agent, LAPS, HippoRAG
    # ==========================================================================

    def _execute_extract(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行信息抽取

        支持的 extract_type:
        - keyword: 关键词提取
        - entity: 实体抽取
        - noun: 名词提取
        - persona: 人格特征提取
        - all: 全部提取

        Args:
            data: 原始数据

        Returns:
            添加了抽取信息的记忆条目列表
        """
        extract_type = get_required_config(
            self.config, "operators.pre_insert.extract_type", "action=extract"
        )

        # 获取文本内容
        dialogs = data.get("dialogs", [])
        text = format_dialogue(dialogs)

        entry = data.copy()
        # 设置 refactor 字段供 MemoryInsert 使用
        entry["refactor"] = text
        extracted_info: dict[str, Any] = {}

        # ==== Keyword Extraction ====
        if extract_type in ["keyword", "all"]:
            if text:
                prompt_template = get_required_config(
                    self.config, "operators.pre_insert.keyword_prompt", "extract_type=keyword"
                )
                prompt = prompt_template.replace("{text}", text)

                try:
                    result = self._generator.generate_json(prompt, default={"keywords": []})
                    keywords = result.get("keywords", [])

                    # 限制数量
                    max_keywords = self.config.get("operators.pre_insert.max_keywords", 10)
                    extracted_info["keywords"] = keywords[:max_keywords]

                except Exception as e:
                    print("[WARNING] " + str(f"Keyword extraction failed: {e}"))
                    extracted_info["keywords"] = []
            else:
                extracted_info["keywords"] = []

        # ==== Entity Extraction ====
        if extract_type in ["entity", "all"]:
            if text:
                ner_model = self.config.get("operators.pre_insert.ner_model", "spacy")
                entity_types = self.config.get(
                    "operators.pre_insert.entity_types",
                    ["PERSON", "ORG", "LOC", "EVENT", "GPE", "DATE", "TIME"],
                )

                entities = []

                if ner_model == "spacy" and getattr(self, "_spacy_nlp", None):
                    doc = self._spacy_nlp(text)
                    for ent in doc.ents:
                        if ent.label_ in entity_types:
                            entities.append({"text": ent.text, "type": ent.label_})

                elif ner_model == "llm":
                    # 使用 LLM 进行 NER
                    prompt = f"""Extract named entities from the following text.
Entity types to extract: {", ".join(entity_types)}

Text: {text}

Return a JSON list of entities: [{{"text": "entity text", "type": "ENTITY_TYPE"}}]

Entities:"""
                    try:
                        entities = self._generator.generate_json(prompt, default=[])
                    except Exception as e:
                        print("[WARNING] " + str(f"LLM NER failed: {e}"))

                # 去重
                seen = set()
                unique_entities = []
                for ent in entities:
                    key = (ent.get("text", "").lower(), ent.get("type", ""))
                    if key not in seen:
                        seen.add(key)
                        unique_entities.append(ent)

                extracted_info["entities"] = unique_entities
            else:
                extracted_info["entities"] = []

        # ==== Noun Extraction ====
        if extract_type in ["noun", "all"]:
            if text and getattr(self, "_spacy_nlp", None):
                include_proper_nouns = self.config.get(
                    "operators.pre_insert.include_proper_nouns", True
                )

                doc = self._spacy_nlp(text)
                nouns = []

                for token in doc:
                    if token.pos_ == "NOUN":
                        nouns.append(token.lemma_)
                    elif token.pos_ == "PROPN" and include_proper_nouns:
                        nouns.append(token.text)

                # 去重并保持顺序
                seen = set()
                unique_nouns = []
                for noun in nouns:
                    if noun.lower() not in seen:
                        seen.add(noun.lower())
                        unique_nouns.append(noun)

                extracted_info["nouns"] = unique_nouns
            else:
                extracted_info["nouns"] = []

        # ==== Persona Extraction ====
        if extract_type in ["persona", "all"]:
            if text:
                prompt_template = get_required_config(
                    self.config, "operators.pre_insert.persona_prompt", "extract_type=persona"
                )
                prompt = prompt_template.replace("{dialogue}", text)

                persona_fields = self.config.get(
                    "operators.pre_insert.persona_fields", ["traits", "preferences", "facts"]
                )

                try:
                    personas = self._generator.generate_json(prompt, default={})

                    # 只保留配置的字段
                    filtered_personas = {}
                    for speaker, info in personas.items():
                        if isinstance(info, dict):
                            filtered_personas[speaker] = {
                                k: v for k, v in info.items() if k in persona_fields
                            }

                    extracted_info["personas"] = filtered_personas

                except Exception as e:
                    print("[WARNING] " + str(f"Persona extraction failed: {e}"))
                    extracted_info["personas"] = {}
            else:
                extracted_info["personas"] = {}

        # 添加到 metadata 或直接到 entry
        add_to_metadata = self.config.get("operators.pre_insert.add_to_metadata", True)
        if add_to_metadata:
            entry.setdefault("metadata", {}).update(extracted_info)
        else:
            entry.update(extracted_info)

        # 生成 embedding 用于向量检索
        if text and self._embedding_generator:
            embedding = self._embedding_generator.embed(text)
            if embedding:
                entry["embedding"] = embedding

        # 添加插入方法
        entry["insert_method"] = "extract_insert"
        entry["insert_mode"] = "passive"

        return [entry]

    # ==========================================================================
    # [D] 评分类: score
    # 子类型: importance | emotion
    # 论文: Generative Agents, EmotionalRAG
    # ==========================================================================

    def _execute_score(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行重要性/情感评分

        score_type:
        - importance: 重要性评分 (Generative Agents)
        - emotion:    情感评分 (EmotionalRAG)

        Args:
            data: 原始数据

        Returns:
            添加了评分的记忆条目列表
        """
        score_type = get_required_config(
            self.config, "operators.pre_insert.score_type", "action=score"
        )

        # 获取文本内容
        text = self._get_text_content(data)

        entry = data.copy()
        score_result = {}

        if score_type == "importance":
            # ==== Importance 逻辑内联 ====
            if not text:
                score_result = {"score": 5, "reason": "Empty content"}
            else:
                prompt_template = get_required_config(
                    self.config, "operators.pre_insert.importance_prompt", "score_type=importance"
                )
                prompt = prompt_template.replace("{text}", text)

                importance_scale = self.config.get("operators.pre_insert.importance_scale", [1, 10])
                min_score, max_score = importance_scale

                try:
                    result = self._generator.generate_json(
                        prompt, default={"score": 5, "reason": "Default score"}
                    )

                    score = result.get("score", 5)
                    # 确保分数在范围内
                    score = max(min_score, min(max_score, int(score)))
                    result["score"] = score

                    score_result = result

                except Exception as e:
                    print("[WARNING] " + str(f"Importance scoring failed: {e}"))
                    score_result = {"score": 5, "reason": f"Scoring failed: {e}"}

            # 根据分数决定插入方法和参数
            score = score_result.get("score", 5)
            if score >= 8:
                entry["insert_mode"] = "active"
                entry["insert_params"] = {"target_tier": "ltm", "priority": score}
                entry["insert_method"] = "priority_insert"
            elif score >= 5:
                entry["insert_mode"] = "passive"
                entry["insert_params"] = {"target_tier": "mtm"}
                entry["insert_method"] = "priority_insert"
            else:
                entry["insert_mode"] = "passive"
                entry["insert_method"] = "default"

        elif score_type == "emotion":
            # ==== Emotion 逻辑内联 ====
            if not text:
                score_result = {"category": "neutral", "intensity": 0.5, "vector": None}
            else:
                emotion_categories = self.config.get(
                    "operators.pre_insert.emotion_categories",
                    ["joy", "sadness", "anger", "fear", "surprise", "neutral"],
                )

                # 尝试使用情感分类模型
                emotion_model = self.config.get("operators.pre_insert.emotion_model", "llm")

                if emotion_model == "llm":
                    # 使用 LLM 进行情感分类
                    prompt = f"""Analyze the emotion in the following text.
Categories: {", ".join(emotion_categories)}

Text: {text}

Return a JSON object with:
- "category": the primary emotion (one of the categories)
- "intensity": emotion intensity from 0.0 to 1.0
- "secondary": (optional) secondary emotion if mixed

Result:"""

                    try:
                        score_result = self._generator.generate_json(
                            prompt,
                            default={"category": "neutral", "intensity": 0.5},
                        )

                    except Exception as e:
                        print("[WARNING] " + str(f"Emotion scoring failed: {e}"))
                        score_result = {"category": "neutral", "intensity": 0.5, "vector": None}

                # 如果配置了情感 embedding 模型，生成情感向量
                if self._embedding_generator and self._embedding_generator.is_available():
                    try:
                        emotion_vector = self._embedding_generator.embed(text)
                        score_result["vector"] = emotion_vector
                    except Exception as e:
                        print("[WARNING] " + str(f"Emotion embedding failed: {e}"))

            entry["insert_method"] = "emotion_insert"
            entry["insert_mode"] = "passive"

        else:
            print("[WARNING] " + str(f"Unknown score_type: {score_type}"))
            score_result = {}
            entry["insert_method"] = "default"
            entry["insert_mode"] = "passive"

        # 添加评分到 metadata
        add_to_metadata = self.config.get("operators.pre_insert.add_to_metadata", True)
        score_field = self.config.get("operators.pre_insert.score_field", "importance_score")

        if add_to_metadata:
            entry.setdefault("metadata", {})[score_field] = score_result
        else:
            entry[score_field] = score_result

        return [entry]

    # ==========================================================================
    # [E-1] 向量编码类: multi_embed
    # 论文: EmotionalRAG
    # ==========================================================================

    def _execute_multi_embed(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行多维向量编码

        生成多种类型的向量表示（语义、情感等）
        输出格式: dict | concat | separate
        """
        embeddings_config = self.config.get("operators.pre_insert.embeddings", [])

        if not embeddings_config:
            # 默认配置
            embeddings_config = [{"name": "semantic", "model": "default", "field": "content"}]

        dialogs = data.get("dialogs", [])
        content = format_dialogue(dialogs)

        entry = data.copy()
        embeddings_result: dict[str, list[float] | None] = {}

        for emb_config in embeddings_config:
            name = emb_config.get("name", "embedding")
            field = emb_config.get("field", "content")

            # 获取要编码的文本
            if field == "content":
                text_to_embed = content
            elif field == "entities":
                # 从 metadata 获取实体，拼接成字符串
                entities = entry.get("metadata", {}).get("entities", [])
                text_to_embed = " ".join([e.get("text", "") for e in entities])
            elif field == "keywords":
                keywords = entry.get("metadata", {}).get("keywords", [])
                text_to_embed = " ".join(keywords)
            else:
                text_to_embed = str(entry.get(field, content))

            if text_to_embed and self._embedding_generator.is_available():
                try:
                    embedding = self._embedding_generator.embed(text_to_embed)
                    embeddings_result[name] = embedding
                except Exception as e:
                    print("[WARNING] " + str(f"Embedding failed for {name}: {e}"))
                    embeddings_result[name] = None
            else:
                embeddings_result[name] = None

        # 根据输出格式处理结果
        output_format = self.config.get("operators.pre_insert.output_format", "dict")

        entry.setdefault("metadata", {})
        if output_format == "dict":
            entry["metadata"]["vectors"] = embeddings_result
        elif output_format == "concat":
            # 拼接所有向量
            all_vectors = [v for v in embeddings_result.values() if v is not None]
            if all_vectors:
                concat_vector = []
                for v in all_vectors:
                    concat_vector.extend(v)
                entry["embedding"] = concat_vector
            else:
                entry["embedding"] = None
        else:  # separate
            for name, vector in embeddings_result.items():
                entry["metadata"][f"embedding_{name}"] = vector

        # 添加插入方法
        entry["insert_method"] = "multi_index_insert"
        entry["insert_mode"] = "passive"

        return [entry]

    # ==========================================================================
    # [E-2] 向量编码类: scm_embed
    # 论文: SCM4LLMs
    # 同时保存: 原文(带轮次索引) + 摘要 + embedding
    # ==========================================================================

    def _execute_scm_embed(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行 SCM 样式的预处理

        SCM 核心逻辑:
        1. 每轮对话同时保存: 原文(带轮次索引) + 摘要 + embedding
        2. embedding 默认对原文计算 (embed_summary=False)
        3. 只有原文超过阈值才生成摘要 (summary_threshold)

        参考: SCM4LLMs/dialogue_test.py - summarize_embed_one_turn()

        配置参数:
        - summarize_prompt: 摘要生成 prompt
        - embed_summary: 是否对摘要做 embedding（默认 False，对原文）
        - summary_threshold: 原文 token 数超过此值才生成摘要（默认 300）
        """
        dialogs = data.get("dialogs", [])
        text = format_dialogue(dialogs)

        if not text:
            entry = data.copy()
            entry["insert_method"] = "default"
            entry["insert_mode"] = "passive"
            return [entry]

        # 构建带轮次索引的原文（SCM 格式）
        # SCM 原文: "[Turn X]\n\nUser: ...\n\nAssistant: ..."
        turn_index = data.get("turn_index", data.get("segment_index", 0))
        text_with_index = f"[Turn {turn_index + 1}]\n\n{text}"

        # 计算原文 token 数
        original_tokens = len(text)  # 简化：用字符数代替

        # 判断是否需要生成摘要
        summary = ""
        if original_tokens > self._scm_summary_threshold:
            # 生成摘要
            prompt = self._scm_summarize_prompt.replace("{dialogue}", text)
            # 兼容 SCM 原始模板变量
            prompt = prompt.replace("{input}", text)

            try:
                summary = self._generator.generate(prompt, max_tokens=200)
                summary = summary.strip()
                print(f"[INFO] SCM summary generated ({len(summary)} chars)")
            except Exception as e:
                print(f"[WARNING] SCM summarization failed: {e}")
                summary = ""
        else:
            # 原文很短，保留原文作为摘要（SCM 原文逻辑）
            summary = text_with_index
            print("[INFO] SCM: original text is short, keep as summary")

        # 选择用于 embedding 的文本
        if self._scm_embed_summary and summary:
            text_for_embed = summary
        else:
            text_for_embed = text_with_index

        # 生成 embedding
        embedding = None
        if self._embedding_generator and self._embedding_generator.is_available():
            try:
                embedding = self._embedding_generator.embed(text_for_embed)
            except Exception as e:
                print(f"[WARNING] SCM embedding failed: {e}")

        # 构建条目：同时包含原文和摘要
        entry = data.copy()
        entry["text"] = text_with_index  # 带索引的原文，用于存储和检索
        entry["original_text"] = text_with_index  # 元数据中保留原文
        entry["summary"] = summary  # 元数据中保留摘要
        entry["embedding"] = embedding
        entry["original_tokens"] = original_tokens
        entry["summary_tokens"] = len(summary) if summary else 0
        entry["insert_method"] = "scm_insert"
        entry["insert_mode"] = "passive"

        # 将原文和摘要也放入 metadata，便于后续 PostRetrieval 访问
        if "metadata" not in entry:
            entry["metadata"] = {}
        entry["metadata"]["original_text"] = text_with_index
        entry["metadata"]["summary"] = summary
        entry["metadata"]["turn_index"] = turn_index

        return [entry]

    # ==========================================================================
    # [E-3] 向量编码类: tri_embed
    # 论文: HippoRAG
    # 三元组提取 + 重构自然语言 + Embedding
    # ==========================================================================

    def _execute_tri_embed(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行三元组提取和 Embedding

        HippoRAG 核心逻辑:
        1. LLM 提取三元组 (subject, predicate, object)
        2. 重构为自然语言描述 (refactor)
        3. 对 refactor 生成 embedding
        """
        start_time = time.time()
        print("[TIMING-PRE] Extract and embed triples started")

        dialogs = data.get("dialogs", [])
        dialogue = format_dialogue(dialogs)

        # 使用 LLM 提取三元组并解析
        prompt = self._triple_extraction_prompt.replace("{dialogue}", dialogue)
        llm_start = time.time()
        print(f"[TIMING-PRE]   Format dialogue: {llm_start - start_time:.3f}s")
        triples, refactor_descriptions = self._generator.generate_triples(prompt)
        llm_time = time.time() - llm_start
        print(f"[TIMING-PRE]   LLM triple extraction: {llm_time:.3f}s")

        # 去重
        unique_triples, unique_refactors = self._generator.deduplicate_triples(
            triples, refactor_descriptions
        )

        if not unique_refactors:
            return []

        # 生成 Embedding
        embeddings = self._embedding_generator.embed_batch(unique_refactors)
        embed_time = time.time() - llm_start - llm_time
        print(f"[TIMING-PRE]   Embedding {len(unique_refactors)} triples: {embed_time:.3f}s")

        # 构建记忆条目列表
        memory_entries = []
        for i, (triple, refactor) in enumerate(zip(unique_triples, unique_refactors)):
            entry = {
                "dialogs": dialogs,
                "refactor": refactor,
                "embedding": embeddings[i] if embeddings is not None else None,
                "metadata": {
                    "original_text": dialogue,
                    "triple": triple,  # 三元组放入 metadata
                },
                "insert_method": "triple_insert",
                "insert_mode": "passive",
            }
            memory_entries.append(entry)

        total_time = time.time() - start_time
        print(
            f"[TIMING-PRE] Extract and embed finished: {total_time:.3f}s, {len(memory_entries)} entries"
        )
        return memory_entries
