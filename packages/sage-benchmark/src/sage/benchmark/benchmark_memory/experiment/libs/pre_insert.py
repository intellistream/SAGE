"""预插入处理模块 - 记忆插入前的预处理操作

记忆体架构说明：
================
记忆体分为【记忆操作】和【记忆数据结构】两部分：

记忆操作（4 种）：
- 插入前操作 (PreInsert): 预处理记忆数据，决定插入方式，仅允许检索记忆数据结构
- 插入后操作 (PostInsert): 优化记忆数据结构，允许进行检索-删除-插入（replace）
- 检索前操作 (PreRetrieval): 预处理提问，不允许访问记忆数据结构
- 检索后操作 (PostRetrieval): 处理返回结果，允许多次查询并拼接成 prompt

记忆数据结构：
- 存储结构 + 插入/检索/删除接口
- 插入可提供多种方法，检索和删除方法固定

本模块职责（PreInsert - 插入前操作）：
- 预处理记忆数据
- 决定如何插入
- 过程中仅允许对记忆数据结构进行检索（通过 service_name 访问）

D2 维度：PreInsert 开发
支持的 action：
- none: 直接透传
- tri_embed: HippoRAG 三元组提取 + embedding
- transform: 内容转换（chunking, topic_segment, fact_extract, summarize, compress）
- extract: 信息抽取（keyword, entity, noun, persona, all）
- score: 重要性评分（importance, emotion）
- multi_embed: 多维向量编码
- validate: 输入验证
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import DialogueParser
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.benchmark.benchmark_memory.experiment.utils.triple_parser import TripleParser
from sage.common.core import MapFunction


class PreInsert(MapFunction):
    """记忆插入前的预处理算子

    作为记忆操作的一部分，负责在记忆插入前进行预处理。

    职责：
    - 预处理记忆数据
    - 决定如何插入（通过 memory_entries 返回插入方法和数据）
    - 过程中仅允许对记忆数据结构进行检索（通过 service_name 访问）

    具体操作：
    - 数据验证 (validate)
    - 格式转换 (transform)
    - 信息抽取 (extract)
    - 重要性评分 (score)
    - 多维编码 (multi_embed)

    支持的 action:
    - none: 直接透传
    - tri_embed: 三元组提取 + embedding (HippoRAG)
    - transform: 内容转换 (MemGPT, SeCom, LoCoMo)
    - extract: 信息抽取 (A-mem, LD-Agent, LAPS)
    - score: 重要性评分 (Generative Agents, EmotionalRAG)
    - multi_embed: 多维向量编码 (EmotionalRAG)
    - validate: 输入验证

    Attributes:
        service_name: 要访问的记忆服务名称，用于在预处理过程中检索记忆数据结构

    注：短期记忆通常使用 none，长期记忆需要更多预处理
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

        # 此处默认初始化共通工具（对外请求服务的和内部都使用的，比如共用解析器、LLM 和 Embedding）
        self._dialogue_parser = DialogueParser()
        self._generator: LLMGenerator = LLMGenerator.from_config(self.config)
        self._embedding_generator: EmbeddingGenerator = EmbeddingGenerator.from_config(self.config)

        # 根据 action 初始化特定配置和工具
        self.action = get_required_config(self.config, "operators.pre_insert.action")
        self._init_for_action()

    def _init_for_action(self):
        """根据 action 类型初始化特定配置和工具"""
        if self.action == "tri_embed":
            self._triple_parser = TripleParser()
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

        elif self.action == "validate":
            self._content_hashes: set[str] = set()

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行预处理

        Args:
            data: 原始对话数据（字典格式）

        Returns:
            处理后的数据（字典格式），包含 memory_entries 队列
        """
        # 根据 action 模式生成记忆条目队列
        if self.action == "none":
            entries = [data]

        elif self.action == "tri_embed":
            entries = self._extract_and_embed_triples(data)

        elif self.action == "transform":
            entries = self._execute_transform(data)

        elif self.action == "extract":
            entries = self._execute_extract(data)

        elif self.action == "score":
            entries = self._execute_score(data)

        elif self.action == "multi_embed":
            entries = self._execute_multi_embed(data)

        elif self.action == "validate":
            entries = self._execute_validate(data)

        else:
            # 未知操作模式，原样返回
            print("[WARNING] " + str(f"Unknown action: {self.action}, passing through"))
            entries = [data]

        # 在原字典基础上添加 memory_entries 队列
        data["memory_entries"] = entries
        return data

    # ========================================================================
    # Transform Action (D2-1)
    # 支持: chunking, topic_segment, fact_extract, summarize, compress
    # 参考: MemGPT, SeCom, LoCoMo
    # ========================================================================

    def _execute_transform(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行内容转换

        Args:
            data: 原始数据

        Returns:
            转换后的记忆条目列表
        """
        transform_type = get_required_config(
            self.config, "operators.pre_insert.transform_type", "action=transform"
        )

        if transform_type == "chunking":
            return self._transform_chunking(data)
        elif transform_type == "topic_segment":
            return self._transform_topic_segment(data)
        elif transform_type == "fact_extract":
            return self._transform_fact_extract(data)
        elif transform_type == "summarize":
            return self._transform_summarize(data)
        elif transform_type == "compress":
            return self._transform_compress(data)
        else:
            print("[WARNING] " + str(f"Unknown transform_type: {transform_type}, using chunking"))
            return self._transform_chunking(data)

    def _transform_chunking(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """分块处理 - 参考 MemGPT

        将长文本分割成固定大小的块，支持重叠窗口

        必需配置参数:
        - chunk_size: 每个块的最大字符数
        - chunk_overlap: 块之间的重叠字符数
        - chunk_strategy: 分块策略 (fixed/sentence/paragraph)
        """
        chunk_size = get_required_config(
            self.config, "operators.pre_insert.chunk_size", "transform_type=chunking"
        )
        chunk_overlap = get_required_config(
            self.config, "operators.pre_insert.chunk_overlap", "transform_type=chunking"
        )
        chunk_strategy = self.config.get("operators.pre_insert.chunk_strategy", "fixed")

        # 获取文本内容
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return [data]

        # 根据策略分块
        if chunk_strategy == "sentence":
            chunks = self._chunk_by_sentence(text, chunk_size, chunk_overlap)
        elif chunk_strategy == "paragraph":
            chunks = self._chunk_by_paragraph(text, chunk_size, chunk_overlap)
        else:  # fixed
            chunks = self._chunk_fixed(text, chunk_size, chunk_overlap)

        # 构建条目
        entries = []
        for i, chunk in enumerate(chunks):
            entry = data.copy()
            entry["chunk_text"] = chunk
            entry["chunk_index"] = i
            entry["total_chunks"] = len(chunks)
            entries.append(entry)

        return entries if entries else [data]

    def _chunk_fixed(self, text: str, size: int, overlap: int) -> list[str]:
        """固定大小分块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks

    def _chunk_by_sentence(self, text: str, size: int, overlap: int) -> list[str]:
        """按句子边界分块"""
        # 简单的句子分割 (支持中英文)
        sentence_endings = re.compile(r"[.!?。！？]+[\s]*")
        sentences = sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_size + sentence_len > size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # 保留部分句子作为重叠
                overlap_sentences = []
                overlap_size = 0
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= overlap:
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

        return chunks

    def _chunk_by_paragraph(self, text: str, size: int, overlap: int) -> list[str]:
        """按段落边界分块"""
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_len = len(para)
            if current_size + para_len > size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _transform_topic_segment(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """话题分段 - 参考 SeCom

        使用 LLM 识别对话中的话题边界，将对话分成不同的话题段落

        配置参数:
        - segment_prompt: 分段 prompt 模板
        - min_segment_size: 最小段落大小
        - max_segment_size: 最大段落大小
        """
        dialogs = data.get("dialogs", [])
        if not dialogs:
            return [data]

        # 格式化对话（带索引）
        formatted_dialogs = []
        for i, dialog in enumerate(dialogs):
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", dialog.get("clean_text", ""))
            formatted_dialogs.append(f"[Exchange {i}]: {speaker}: {text}")
        dialogue_text = "\n".join(formatted_dialogs)

        # 使用 LLM 识别话题边界
        prompt_template = get_required_config(
            self.config, "operators.pre_insert.segment_prompt", "transform_type=topic_segment"
        )
        prompt = prompt_template.replace("{dialogue}", dialogue_text)

        try:
            response = self._generator.generate(prompt)
            segments = self._parse_json_response(response, default=[])
        except Exception as e:
            print(
                "[WARNING] "
                + str(f"Topic segmentation failed: {e}, falling back to single segment")
            )
            return [data]

        if not segments:
            return [data]

        # 构建分段条目
        min_size = self.config.get("operators.pre_insert.min_segment_size", 100)
        max_size = self.config.get("operators.pre_insert.max_segment_size", 500)

        entries = []
        for i, segment in enumerate(segments):
            exchange_indices = segment.get("exchanges", [])
            topic = segment.get("topic", f"segment_{i}")

            # 提取该段的对话
            segment_dialogs = [dialogs[idx] for idx in exchange_indices if idx < len(dialogs)]
            segment_text = self._dialogue_parser.format(segment_dialogs)

            # 检查大小约束
            if len(segment_text) < min_size:
                continue
            if len(segment_text) > max_size:
                # 进一步分块
                sub_entries = self._transform_chunking({**data, "dialogs": segment_dialogs})
                for sub in sub_entries:
                    sub["topic"] = topic
                    sub["segment_index"] = i
                entries.extend(sub_entries)
            else:
                entry = data.copy()
                entry["segment_dialogs"] = segment_dialogs
                entry["segment_text"] = segment_text
                entry["topic"] = topic
                entry["segment_index"] = i
                entry["total_segments"] = len(segments)
                entries.append(entry)

        return entries if entries else [data]

    def _transform_fact_extract(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """事实提取 - 参考 LoCoMo

        从对话中提取事实性陈述

        配置参数:
        - fact_prompt: 事实提取 prompt 模板
        - fact_format: 输出格式 (statement/triple/json)
        """
        dialogs = data.get("dialogs", [])
        if not dialogs:
            return [data]

        # 格式化对话（带 dialog_id）
        formatted_dialogs = []
        for i, dialog in enumerate(dialogs):
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", dialog.get("clean_text", ""))
            dia_id = dialog.get("dia_id", i)
            formatted_dialogs.append(f"[{dia_id}] {speaker}: {text}")
        dialogue_text = "\n".join(formatted_dialogs)

        # 使用 LLM 提取事实
        prompt_template = get_required_config(
            self.config, "operators.pre_insert.fact_prompt", "transform_type=fact_extract"
        )
        prompt = prompt_template.replace("{dialogue}", dialogue_text)

        try:
            response = self._generator.generate(prompt)
            facts = self._parse_json_response(response, default=[])
        except Exception as e:
            print("[WARNING] " + str(f"Fact extraction failed: {e}"))
            return [data]

        if not facts:
            return [data]

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
            entries.append(entry)

        return entries if entries else [data]

    def _transform_summarize(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """内容摘要

        配置参数:
        - summary_prompt: 摘要 prompt 模板
        - summary_max_tokens: 摘要最大 token 数
        """
        dialogs = data.get("dialogs", [])
        dialogue_text = self._dialogue_parser.format(dialogs)

        if not dialogue_text:
            return [data]

        # 使用 LLM 生成摘要
        prompt_template = get_required_config(
            self.config, "operators.pre_insert.summary_prompt", "transform_type=summarize"
        )
        prompt = prompt_template.replace("{dialogue}", dialogue_text)

        try:
            max_tokens = self.config.get("operators.pre_insert.summary_max_tokens", 200)
            summary = self._generator.generate(prompt, max_tokens=max_tokens)
        except Exception as e:
            print("[WARNING] " + str(f"Summarization failed: {e}"))
            return [data]

        entry = data.copy()
        entry["summary"] = summary.strip()
        entry["original_text"] = dialogue_text
        return [entry]

    def _transform_compress(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """内容压缩 - 参考 SeCom (LLMLingua)

        使用压缩模型减少文本长度同时保留关键信息

        配置参数:
        - compression_ratio: 目标压缩率 (0-1)
        - compression_model: 压缩模型名称
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return [data]

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
        return [entry]

    # ========================================================================
    # Extract Action (D2-2)
    # 支持: keyword, entity, noun, persona, all
    # 参考: A-mem, LD-Agent, LAPS, HippoRAG
    # ========================================================================

    def _execute_extract(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行信息抽取

        Args:
            data: 原始数据

        Returns:
            添加了抽取信息的记忆条目列表
        """
        extract_type = get_required_config(
            self.config, "operators.pre_insert.extract_type", "action=extract"
        )

        entry = data.copy()
        extracted_info: dict[str, Any] = {}

        if extract_type == "keyword" or extract_type == "all":
            extracted_info["keywords"] = self._extract_keywords(data)

        if extract_type == "entity" or extract_type == "all":
            extracted_info["entities"] = self._extract_entities(data)

        if extract_type == "noun" or extract_type == "all":
            extracted_info["nouns"] = self._extract_nouns(data)

        if extract_type == "persona" or extract_type == "all":
            extracted_info["personas"] = self._extract_personas(data)

        # 添加到 metadata 或直接到 entry
        add_to_metadata = self.config.get("operators.pre_insert.add_to_metadata", True)
        if add_to_metadata:
            entry.setdefault("metadata", {}).update(extracted_info)
        else:
            entry.update(extracted_info)

        return [entry]

    def _extract_keywords(self, data: dict[str, Any]) -> list[str]:
        """关键词提取 - 参考 A-mem

        使用 LLM 提取关键概念和术语
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return []

        prompt_template = get_required_config(
            self.config, "operators.pre_insert.keyword_prompt", "extract_type=keyword"
        )
        prompt = prompt_template.replace("{text}", text)

        try:
            response = self._generator.generate(prompt)
            result = self._parse_json_response(response, default={"keywords": []})
            keywords = result.get("keywords", [])

            # 限制数量
            max_keywords = self.config.get("operators.pre_insert.max_keywords", 10)
            return keywords[:max_keywords]

        except Exception as e:
            print("[WARNING] " + str(f"Keyword extraction failed: {e}"))
            return []

    def _extract_entities(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """实体抽取 - 参考 HippoRAG, LAPS

        使用 spaCy 或 LLM 识别命名实体
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return []

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
                response = self._generator.generate(prompt)
                entities = self._parse_json_response(response, default=[])
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

        return unique_entities

    def _extract_nouns(self, data: dict[str, Any]) -> list[str]:
        """名词提取 - 参考 LD-Agent

        使用 spaCy 提取名词短语
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text or not getattr(self, "_spacy_nlp", None):
            return []

        include_proper_nouns = self.config.get("operators.pre_insert.include_proper_nouns", True)

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

        return unique_nouns

    def _extract_personas(self, data: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
        """人格特征提取 - 参考 LD-Agent

        从对话中提取说话者的性格特征、偏好和事实信息
        """
        dialogs = data.get("dialogs", [])
        dialogue_text = self._dialogue_parser.format(dialogs)

        if not dialogue_text:
            return {}

        prompt_template = get_required_config(
            self.config, "operators.pre_insert.persona_prompt", "extract_type=persona"
        )
        prompt = prompt_template.replace("{dialogue}", dialogue_text)

        persona_fields = self.config.get(
            "operators.pre_insert.persona_fields", ["traits", "preferences", "facts"]
        )

        try:
            response = self._generator.generate(prompt)
            personas = self._parse_json_response(response, default={})

            # 只保留配置的字段
            filtered_personas = {}
            for speaker, info in personas.items():
                if isinstance(info, dict):
                    filtered_personas[speaker] = {
                        k: v for k, v in info.items() if k in persona_fields
                    }

            return filtered_personas

        except Exception as e:
            print("[WARNING] " + str(f"Persona extraction failed: {e}"))
            return {}

    # ========================================================================
    # Score Action (D2-3)
    # 支持: importance, emotion
    # 参考: Generative Agents, EmotionalRAG
    # ========================================================================

    def _execute_score(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行重要性评分

        Args:
            data: 原始数据

        Returns:
            添加了评分的记忆条目列表
        """
        score_type = get_required_config(
            self.config, "operators.pre_insert.score_type", "action=score"
        )
        entry = data.copy()

        if score_type == "importance":
            score_result = self._score_importance(data)
        elif score_type == "emotion":
            score_result = self._score_emotion(data)
        else:
            print("[WARNING] " + str(f"Unknown score_type: {score_type}"))
            score_result = {}

        # 添加评分到 metadata
        add_to_metadata = self.config.get("operators.pre_insert.add_to_metadata", True)
        score_field = self.config.get("operators.pre_insert.score_field", "importance_score")

        if add_to_metadata:
            entry.setdefault("metadata", {})[score_field] = score_result
        else:
            entry[score_field] = score_result

        return [entry]

    def _score_importance(self, data: dict[str, Any]) -> dict[str, Any]:
        """重要性评分 - 参考 Generative Agents

        使用 LLM 评估记忆的重要性 (1-10)
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return {"score": 5, "reason": "Empty content"}

        prompt_template = get_required_config(
            self.config, "operators.pre_insert.importance_prompt", "score_type=importance"
        )
        prompt = prompt_template.replace("{text}", text)

        importance_scale = self.config.get("operators.pre_insert.importance_scale", [1, 10])
        min_score, max_score = importance_scale

        try:
            response = self._generator.generate(prompt)
            result = self._parse_json_response(
                response, default={"score": 5, "reason": "Default score"}
            )

            score = result.get("score", 5)
            # 确保分数在范围内
            score = max(min_score, min(max_score, int(score)))
            result["score"] = score

            return result

        except Exception as e:
            print("[WARNING] " + str(f"Importance scoring failed: {e}"))
            return {"score": 5, "reason": f"Scoring failed: {e}"}

    def _score_emotion(self, data: dict[str, Any]) -> dict[str, Any]:
        """情感评分 - 参考 EmotionalRAG

        识别文本的情感类别和强度
        """
        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        if not text:
            return {"category": "neutral", "intensity": 0.5, "vector": None}

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
                response = self._generator.generate(prompt)
                result = self._parse_json_response(
                    response,
                    default={"category": "neutral", "intensity": 0.5},
                )
                return result

            except Exception as e:
                print("[WARNING] " + str(f"Emotion scoring failed: {e}"))

        # 如果配置了情感 embedding 模型，生成情感向量
        if self._embedding_generator and self._embedding_generator.is_available():
            try:
                emotion_vector = self._embedding_generator.embed(text)
                return {
                    "category": "unknown",
                    "intensity": 0.5,
                    "vector": emotion_vector,
                }
            except Exception as e:
                print("[WARNING] " + str(f"Emotion embedding failed: {e}"))

        return {"category": "neutral", "intensity": 0.5, "vector": None}

    # ========================================================================
    # Multi-Embed Action (D2-4)
    # 支持多维向量编码
    # 参考: EmotionalRAG
    # ========================================================================

    def _execute_multi_embed(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行多维向量编码

        生成多种类型的向量表示（语义、情感等）

        配置参数:
        - embeddings: 向量配置列表，每个包含 name, model, field
        - output_format: 输出格式 (dict/concat/separate)
        """
        embeddings_config = self.config.get("operators.pre_insert.embeddings", [])

        if not embeddings_config:
            # 默认配置
            embeddings_config = [{"name": "semantic", "model": "default", "field": "content"}]

        dialogs = data.get("dialogs", [])
        content = self._dialogue_parser.format(dialogs)

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

        if output_format == "dict":
            entry["embeddings"] = embeddings_result
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
                entry[f"embedding_{name}"] = vector

        return [entry]

    # ========================================================================
    # Validate Action (D2-5)
    # 支持: length, language, content, duplicate
    # ========================================================================

    def _execute_validate(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """执行输入验证

        验证输入数据是否符合规则，不符合则根据 on_fail 策略处理

        配置参数:
        - rules: 验证规则列表
        - on_fail: 失败处理策略 (skip/warn/error/transform)
        - transform_action: on_fail=transform 时使用的转换动作
        """
        rules = self.config.get("operators.pre_insert.rules", [])
        on_fail = self.config.get("operators.pre_insert.on_fail", "skip")

        dialogs = data.get("dialogs", [])
        text = self._dialogue_parser.format(dialogs)

        validation_errors = []

        for rule in rules:
            error = self._validate_rule(text, data, rule)
            if error:
                validation_errors.append(error)

        if validation_errors:
            if on_fail == "skip":
                print("[INFO] " + str(f"Validation failed, skipping: {validation_errors}"))
                return []  # 返回空列表，跳过此条目
            elif on_fail == "warn":
                print("[WARNING] " + str(f"Validation warnings: {validation_errors}"))
                entry = data.copy()
                entry["validation_warnings"] = validation_errors
                return [entry]
            elif on_fail == "error":
                raise ValueError(f"Validation failed: {validation_errors}")
            elif on_fail == "transform":
                # 使用指定的转换动作处理
                transform_action = self.config.get(
                    "operators.pre_insert.transform_action", "summarize"
                )
                original_transform_type = self.config.get("operators.pre_insert.transform_type")
                # 临时修改配置
                self.config._data.setdefault("operators", {}).setdefault("pre_insert", {})[
                    "transform_type"
                ] = transform_action
                try:
                    entries = self._execute_transform(data)
                finally:
                    # 恢复原配置
                    if original_transform_type:
                        self.config._data["operators"]["pre_insert"]["transform_type"] = (
                            original_transform_type
                        )
                return entries

        return [data]

    def _validate_rule(self, text: str, data: dict[str, Any], rule: dict[str, Any]) -> str | None:
        """验证单个规则

        Returns:
            错误消息，如果验证通过则返回 None
        """
        rule_type = rule.get("type")

        if rule_type == "length":
            min_len = rule.get("min", 0)
            max_len = rule.get("max", float("inf"))
            text_len = len(text)

            if text_len < min_len:
                return f"Text too short: {text_len} < {min_len}"
            if text_len > max_len:
                return f"Text too long: {text_len} > {max_len}"

        elif rule_type == "language":
            allowed = rule.get("allowed", [])
            if allowed:
                try:
                    from langdetect import detect

                    detected = detect(text)
                    if detected not in allowed:
                        return f"Language not allowed: {detected} not in {allowed}"
                except ImportError:
                    print("[WARNING] " + "langdetect not installed, skipping language check")
                except Exception as e:
                    print("[WARNING] " + str(f"Language detection failed: {e}"))

        elif rule_type == "content":
            blacklist = rule.get("blacklist", [])
            for word in blacklist:
                if word.lower() in text.lower():
                    return f"Blacklisted content found: {word}"

        elif rule_type == "duplicate":
            threshold = rule.get("similarity_threshold", 0.95)
            content_hash = hashlib.md5(text.encode()).hexdigest()

            # 精确重复检测
            if content_hash in self._content_hashes:
                return "Duplicate content detected"
            self._content_hashes.add(content_hash)

            # 如果阈值 < 1，进行相似度检测
            if threshold < 1.0 and self._embedding_generator:
                # TODO: 实现基于 embedding 的相似度检测
                # Issue URL: https://github.com/intellistream/SAGE/issues/1266
                # 这需要维护已有记忆的 embedding 索引
                pass

        return None

    # ========================================================================
    # 原有的 tri_embed 实现
    # ========================================================================

    def _extract_and_embed_triples(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """提取三元组并进行 Embedding

        Args:
            data: 对话数据（字典格式），包含 "dialogs" 字段

        Returns:
            记忆条目列表，每个条目包含 triple, refactor, embedding
        """
        dialogs = data.get("dialogs", [])
        dialogue = self._dialogue_parser.format(dialogs)

        # 使用 LLM 提取三元组
        prompt = self._triple_extraction_prompt.replace("{dialogue}", dialogue)
        triples_text = self._generator.generate(prompt)

        # 解析三元组并重构为自然语言描述
        triples, refactor_descriptions = self._triple_parser.parse_and_refactor(triples_text)

        # 去重
        unique_triples, unique_refactors = self._triple_parser.deduplicate(
            triples, refactor_descriptions
        )

        if not unique_refactors:
            return []

        # 生成 Embedding
        embeddings = self._embedding_generator.embed_batch(unique_refactors)

        # 构建记忆条目列表
        memory_entries = []
        for i, (triple, refactor) in enumerate(zip(unique_triples, unique_refactors)):
            entry = {
                "dialogs": dialogs,
                "triple": triple,
                "refactor": refactor,
                "embedding": embeddings[i] if embeddings is not None else None,
            }
            memory_entries.append(entry)

        return memory_entries

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _parse_json_response(self, response: str, default: Any = None) -> Any:
        """解析 LLM 返回的 JSON 响应

        Args:
            response: LLM 返回的文本
            default: 解析失败时的默认值

        Returns:
            解析后的 JSON 对象
        """
        if default is None:
            default = {}

        try:
            # 清理响应文本
            response_cleaned = response.strip()

            # 尝试找到 JSON 内容
            if not response_cleaned.startswith(("{", "[")):
                # 查找第一个 { 或 [
                start_brace = response_cleaned.find("{")
                start_bracket = response_cleaned.find("[")

                if start_brace == -1 and start_bracket == -1:
                    return default

                if start_brace == -1:
                    start_idx = start_bracket
                elif start_bracket == -1:
                    start_idx = start_brace
                else:
                    start_idx = min(start_brace, start_bracket)

                response_cleaned = response_cleaned[start_idx:]

            # 找到匹配的结束符
            if response_cleaned.startswith("{"):
                end_idx = response_cleaned.rfind("}") + 1
            else:
                end_idx = response_cleaned.rfind("]") + 1

            if end_idx > 0:
                response_cleaned = response_cleaned[:end_idx]

            return json.loads(response_cleaned)

        except json.JSONDecodeError as e:
            print("[WARNING] " + str(f"JSON parsing error: {e}"))
            # DEBUG: f"Raw response: {response}"
            return default

    def _get_text_content(self, data: dict[str, Any]) -> str:
        """从数据中获取文本内容"""
        dialogs = data.get("dialogs", [])
        return self._dialogue_parser.format(dialogs)
