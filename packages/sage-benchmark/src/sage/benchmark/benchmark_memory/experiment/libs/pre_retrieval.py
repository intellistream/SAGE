"""预检索处理模块 - 在记忆检索前的预处理（可选）

对于短期记忆（STM），通常不需要预处理，直接检索即可。
此模块实现以下功能：
- none: 透传
- embedding: 基础向量化
- optimize: 查询优化（关键词提取、扩展、改写、指令增强）
- multi_embed: 多维向量生成
- decompose: 复杂查询分解
- route: 检索路由
- validate: 查询验证

参考实现:
- LD-Agent: 关键词提取 (spaCy)
- HippoRAG: 指令前缀 (instruction prefix)
- EmotionalRAG: 多维 Embedding (semantic + emotion)
- MemoryOS/MemGPT: 多源路由
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction

logger = logging.getLogger(__name__)


class PreRetrieval(MapFunction):
    """记忆检索前的预处理算子

    职责：
    - 查询优化 (optimize)
    - 多维向量化 (multi_embed)
    - 查询分解 (decompose)
    - 检索路由 (route)
    - 查询验证 (validate)
    - 基础向量化 (embedding)

    注：短期记忆通常不需要此步骤
    """

    def __init__(self, config):
        """初始化 PreRetrieval

        Args:
            config: RuntimeConfig 对象，从中获取 operators.pre_retrieval.action
        """
        super().__init__()
        self.config = config
        self.action = self._get_required_config("operators.pre_retrieval.action")

        # 根据 action 初始化不同的组件
        if self.action == "embedding":
            self._init_embedding()
        elif self.action == "optimize":
            self._init_optimize()
        elif self.action == "multi_embed":
            self._init_multi_embed()
        elif self.action == "decompose":
            self._init_decompose()
        elif self.action == "route":
            self._init_route()
        elif self.action == "validate":
            self._init_validate()

    def _get_required_config(self, key: str, context: str = "") -> any:
        """获取必需配置，缺失则报错

        Args:
            key: 配置键路径
            context: 上下文说明

        Returns:
            配置值

        Raises:
            ValueError: 配置缺失时抛出
        """
        value = self.config.get(key)
        if value is None:
            ctx = f" ({context})" if context else ""
            raise ValueError(f"缺少必需配置: {key}{ctx}")
        return value

    # ==================== 初始化方法 ====================

    def _init_embedding(self):
        """初始化基础 Embedding"""
        self.embedding_generator = EmbeddingGenerator.from_config(self.config)

    def _init_optimize(self):
        """初始化查询优化组件

        支持的优化类型：
        - keyword_extract: 关键词提取 (LD-Agent)
        - expand: 查询扩展
        - rewrite: 查询改写 (HippoRAG Query2Doc)
        - instruction: 指令增强 (HippoRAG)
        """
        self.optimize_type = self._get_required_config(
            "operators.pre_retrieval.optimize_type", "action=optimize"
        )

        # 关键词提取配置
        if self.optimize_type == "keyword_extract":
            self.extractor = self._get_required_config(
                "operators.pre_retrieval.extractor", "optimize_type=keyword_extract"
            )
            self.extract_types = self.config.get(
                "operators.pre_retrieval.extract_types", ["NOUN", "PROPN"]
            )
            self.max_keywords = self._get_required_config(
                "operators.pre_retrieval.max_keywords", "optimize_type=keyword_extract"
            )
            self.keyword_prompt = self.config.get("operators.pre_retrieval.keyword_prompt")

            # 初始化提取器
            if self.extractor == "spacy":
                self._init_spacy()
            elif self.extractor == "nltk":
                self._init_nltk()
            elif self.extractor == "llm":
                if not self.keyword_prompt:
                    raise ValueError(
                        "缺少必需配置: operators.pre_retrieval.keyword_prompt (extractor=llm)"
                    )
                self.generator = LLMGenerator.from_config(self.config)

        # 查询扩展配置
        elif self.optimize_type == "expand":
            self.expand_prompt = self._get_required_config(
                "operators.pre_retrieval.expand_prompt", "optimize_type=expand"
            )
            self.expand_count = self._get_required_config(
                "operators.pre_retrieval.expand_count", "optimize_type=expand"
            )
            self.merge_strategy = self.config.get(
                "operators.pre_retrieval.merge_strategy", "union"
            )
            self.generator = LLMGenerator.from_config(self.config)

        # 查询改写配置
        elif self.optimize_type == "rewrite":
            self.rewrite_prompt = self._get_required_config(
                "operators.pre_retrieval.rewrite_prompt", "optimize_type=rewrite"
            )
            self.generator = LLMGenerator.from_config(self.config)

        # 指令增强配置 (HippoRAG style)
        elif self.optimize_type == "instruction":
            self.instruction_prefix = self._get_required_config(
                "operators.pre_retrieval.instruction_prefix", "optimize_type=instruction"
            )
            self.instruction_suffix = self.config.get(
                "operators.pre_retrieval.instruction_suffix", ""
            )

        # 通用配置
        self.replace_original = self.config.get(
            "operators.pre_retrieval.replace_original", False
        )
        self.store_optimized = self.config.get(
            "operators.pre_retrieval.store_optimized", True
        )

        # 如果需要对优化后的查询进行 embedding
        if self.config.get("operators.pre_retrieval.embed_optimized", False):
            self.embedding_generator = EmbeddingGenerator.from_config(self.config)
        else:
            self.embedding_generator = None

    def _init_spacy(self):
        """初始化 spaCy 分词器"""
        try:
            import spacy

            model_name = self._get_required_config(
                "operators.pre_retrieval.spacy_model", "extractor=spacy"
            )
            try:
                self.nlp = spacy.load(model_name)
            except OSError:
                # 尝试下载模型
                logger.warning(f"spaCy model {model_name} not found, attempting to download...")
                import subprocess

                subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
                self.nlp = spacy.load(model_name)
        except ImportError:
            raise ImportError("spaCy is required for keyword extraction. Install with: pip install spacy")

    def _init_nltk(self):
        """初始化 NLTK 分词器"""
        try:
            import nltk

            # 确保必要的数据已下载
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            try:
                nltk.data.find("taggers/averaged_perceptron_tagger")
            except LookupError:
                nltk.download("averaged_perceptron_tagger", quiet=True)
            try:
                nltk.data.find("corpora/wordnet")
            except LookupError:
                nltk.download("wordnet", quiet=True)

            from nltk import pos_tag, word_tokenize
            from nltk.stem import WordNetLemmatizer

            self.word_tokenize = word_tokenize
            self.pos_tag = pos_tag
            self.lemmatizer = WordNetLemmatizer()

            # NLTK POS tags 到通用 POS 的映射
            self.nltk_pos_mapping = {
                "NN": "NOUN",
                "NNS": "NOUN",
                "NNP": "PROPN",
                "NNPS": "PROPN",
                "VB": "VERB",
                "VBD": "VERB",
                "VBG": "VERB",
                "VBN": "VERB",
                "VBP": "VERB",
                "VBZ": "VERB",
                "JJ": "ADJ",
                "JJR": "ADJ",
                "JJS": "ADJ",
            }
        except ImportError:
            raise ImportError("NLTK is required for keyword extraction. Install with: pip install nltk")

    def _init_multi_embed(self):
        """初始化多维 Embedding

        参考 EmotionalRAG 实现，支持多个 embedding 模型并行生成
        """
        self.embeddings_config = self.config.get("operators.pre_retrieval.embeddings", [])
        if not self.embeddings_config:
            # 默认配置：语义 + 情感
            self.embeddings_config = [
                {"name": "semantic", "model": "BAAI/bge-m3", "weight": 0.6},
            ]

        # 初始化各个 embedding 生成器
        self.embedding_generators: dict[str, tuple[EmbeddingGenerator, float]] = {}
        base_url = self.config.get("runtime.embedding_base_url")

        for emb_config in self.embeddings_config:
            name = emb_config.get("name", "default")
            model = emb_config.get("model", "BAAI/bge-m3")
            weight = emb_config.get("weight", 1.0)

            generator = EmbeddingGenerator(
                base_url=base_url,
                model_name=model,
            )
            self.embedding_generators[name] = (generator, weight)

        self.output_format = self.config.get("operators.pre_retrieval.output_format", "dict")
        self.match_insert_config = self.config.get(
            "operators.pre_retrieval.match_insert_config", True
        )

    def _init_decompose(self):
        """初始化查询分解

        将复杂查询分解为多个子查询
        """
        self.decompose_strategy = self._get_required_config(
            "operators.pre_retrieval.decompose_strategy", "action=decompose"
        )
        self.max_sub_queries = self._get_required_config(
            "operators.pre_retrieval.max_sub_queries", "action=decompose"
        )
        self.sub_query_action = self.config.get(
            "operators.pre_retrieval.sub_query_action", "parallel"
        )
        self.decompose_merge_strategy = self.config.get(
            "operators.pre_retrieval.merge_strategy", "union"
        )

        if self.decompose_strategy == "llm":
            self.decompose_prompt = self._get_required_config(
                "operators.pre_retrieval.decompose_prompt", "decompose_strategy=llm"
            )
            self.generator = LLMGenerator.from_config(self.config)

        elif self.decompose_strategy == "rule":
            self.split_keywords = self._get_required_config(
                "operators.pre_retrieval.split_keywords", "decompose_strategy=rule"
            )

        # 如果需要对子查询进行 embedding
        if self.config.get("operators.pre_retrieval.embed_sub_queries", False):
            self.embedding_generator = EmbeddingGenerator.from_config(self.config)
        else:
            self.embedding_generator = None

    def _init_route(self):
        """初始化检索路由

        根据查询内容路由到不同的检索源
        参考 MemoryOS 和 MemGPT 实现
        """
        self.route_strategy = self._get_required_config(
            "operators.pre_retrieval.route_strategy", "action=route"
        )
        self.allow_multi_route = self.config.get(
            "operators.pre_retrieval.allow_multi_route", True
        )
        self.max_routes = self.config.get("operators.pre_retrieval.max_routes", 2)
        self.default_route = self._get_required_config(
            "operators.pre_retrieval.default_route", "action=route"
        )

        if self.route_strategy == "keyword":
            self.keyword_rules = self._get_required_config(
                "operators.pre_retrieval.keyword_rules", "route_strategy=keyword"
            )

        elif self.route_strategy == "classifier":
            self.classifier_model = self._get_required_config(
                "operators.pre_retrieval.classifier_model", "route_strategy=classifier"
            )
            self.route_mapping = self._get_required_config(
                "operators.pre_retrieval.route_mapping", "route_strategy=classifier"
            )
            # TODO: 初始化分类器模型
            # Issue URL: https://github.com/intellistream/SAGE/issues/1268

        elif self.route_strategy == "llm":
            self.route_prompt = self._get_required_config(
                "operators.pre_retrieval.route_prompt", "route_strategy=llm"
            )
            self.generator = LLMGenerator.from_config(self.config)

    def _init_validate(self):
        """初始化查询验证

        验证查询是否符合要求，进行预处理
        """
        self.validation_rules = self._get_required_config(
            "operators.pre_retrieval.rules", "action=validate"
        )
        self.on_fail = self.config.get("operators.pre_retrieval.on_fail", "default")
        self.default_query = self.config.get("operators.pre_retrieval.default_query", "Hello")

        # 预处理配置
        self.preprocessing = self.config.get(
            "operators.pre_retrieval.preprocessing",
            {
                "strip_whitespace": True,
                "lowercase": False,
                "remove_punctuation": False,
            },
        )

        # 安全检查模式
        self.blocked_patterns = []
        for rule in self.validation_rules:
            if rule.get("type") == "safety":
                patterns = rule.get("blocked_patterns", [])
                self.blocked_patterns.extend(patterns)

    # ==================== 执行方法 ====================

    def execute(self, data):
        """执行预处理

        Args:
            data: PipelineRequest 对象或原始检索请求，包含：
                - "question": 查询问题（字符串）
                - 其他检索参数

        Returns:
            处理后的数据，根据 action 不同添加不同字段
        """
        # 根据 action 模式执行不同操作
        if self.action == "none":
            return data
        elif self.action == "embedding":
            return self._embed_question(data)
        elif self.action == "optimize":
            return self._optimize_query(data)
        elif self.action == "multi_embed":
            return self._multi_embed_query(data)
        elif self.action == "decompose":
            return self._decompose_query(data)
        elif self.action == "route":
            return self._route_query(data)
        elif self.action == "validate":
            return self._validate_query(data)
        else:
            # 未知操作模式，透传
            return data

    def _embed_question(self, data):
        """对查询问题进行 Embedding

        Args:
            data: 检索请求数据，包含 "question" 字段

        Returns:
            添加了 "query_embedding" 字段的数据
        """
        question = data.get("question")
        embedding = self.embedding_generator.embed(question)
        data["query_embedding"] = embedding
        return data

    # ==================== optimize action 实现 ====================

    def _optimize_query(self, data) -> dict[str, Any]:
        """执行查询优化

        根据 optimize_type 调用不同的优化方法
        """
        question = data.get("question", "")

        if self.optimize_type == "keyword_extract":
            optimized = self._extract_keywords(question)
        elif self.optimize_type == "expand":
            optimized = self._expand_query(question)
        elif self.optimize_type == "rewrite":
            optimized = self._rewrite_query(question)
        elif self.optimize_type == "instruction":
            optimized = self._add_instruction(question)
        else:
            optimized = question

        # 存储优化结果
        if self.store_optimized:
            data["optimized_query"] = optimized
            data["original_query"] = question

        # 是否替换原始查询
        if self.replace_original:
            data["question"] = optimized

        # 是否对优化后的查询进行 embedding
        if self.embedding_generator is not None:
            query_to_embed = optimized if self.replace_original else question
            data["query_embedding"] = self.embedding_generator.embed(query_to_embed)

        return data

    def _extract_keywords(self, query: str) -> str:
        """关键词提取

        参考 LD-Agent 实现，使用 spaCy/NLTK/LLM 提取名词等关键词
        """
        if self.extractor == "spacy":
            return self._extract_keywords_spacy(query)
        elif self.extractor == "nltk":
            return self._extract_keywords_nltk(query)
        elif self.extractor == "llm":
            return self._extract_keywords_llm(query)
        else:
            return query

    def _extract_keywords_spacy(self, query: str) -> str:
        """使用 spaCy 提取关键词

        参考 LD-Agent 实现：
        tokenized_item = self.lemma_tokenizer(query_item)
        query_nouns_item = list(set([token.lemma_ for token in tokenized_item if token.pos_ == "NOUN"]))
        """
        doc = self.nlp(query)

        # 提取指定词性的词元
        keywords = []
        for token in doc:
            if token.pos_ in self.extract_types:
                keywords.append(token.lemma_)

        # 去重并限制数量
        keywords = list(dict.fromkeys(keywords))[: self.max_keywords]

        return ",".join(keywords) if keywords else query

    def _extract_keywords_nltk(self, query: str) -> str:
        """使用 NLTK 提取关键词"""
        tokens = self.word_tokenize(query)
        tagged = self.pos_tag(tokens)

        keywords = []
        for word, tag in tagged:
            universal_tag = self.nltk_pos_mapping.get(tag, "")
            if universal_tag in self.extract_types:
                lemma = self.lemmatizer.lemmatize(word.lower())
                keywords.append(lemma)

        # 去重并限制数量
        keywords = list(dict.fromkeys(keywords))[: self.max_keywords]

        return ",".join(keywords) if keywords else query

    def _extract_keywords_llm(self, query: str) -> str:
        """使用 LLM 提取关键词"""
        prompt = self.keyword_prompt or (
            f"Extract the key search terms from this query. "
            f"Return only the keywords separated by commas, nothing else.\n\n"
            f"Query: {query}\n\nKeywords:"
        )
        prompt = prompt.format(query=query)

        try:
            result = self.generator.generate(prompt, max_tokens=100, temperature=0.3)
            # 清理结果
            keywords = [k.strip() for k in result.strip().split(",")]
            keywords = keywords[: self.max_keywords]
            return ",".join(keywords) if keywords else query
        except Exception as e:
            logger.warning(f"LLM keyword extraction failed: {e}")
            return query

    def _expand_query(self, query: str) -> str | list[str]:
        """查询扩展

        使用 LLM 生成多个替代查询表述
        """
        prompt = self.expand_prompt.format(query=query, count=self.expand_count)

        try:
            result = self.generator.generate(prompt, max_tokens=300, temperature=0.7)

            # 解析扩展查询
            lines = result.strip().split("\n")
            expanded_queries = [line.strip().lstrip("0123456789.-) ") for line in lines if line.strip()]
            expanded_queries = expanded_queries[: self.expand_count]

            # 根据合并策略返回
            if self.merge_strategy == "union":
                return [query] + expanded_queries
            else:
                return expanded_queries if expanded_queries else [query]

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return [query]

    def _rewrite_query(self, query: str) -> str:
        """查询改写

        参考 HippoRAG Query2Doc，使用 LLM 改写查询
        """
        prompt = self.rewrite_prompt.format(query=query)

        try:
            result = self.generator.generate(prompt, max_tokens=200, temperature=0.5)
            return result.strip() or query
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
            return query

    def _add_instruction(self, query: str) -> str:
        """添加检索指令

        参考 HippoRAG 实现，添加指令前缀/后缀以增强检索效果
        instruction = "Retrieve passages that help answer the question: "
        augmented_query = instruction + query
        """
        return f"{self.instruction_prefix}{query}{self.instruction_suffix}"

    # ==================== multi_embed action 实现 ====================

    def _multi_embed_query(self, data) -> dict[str, Any]:
        """多维向量生成

        参考 EmotionalRAG 实现，生成多个维度的 embedding：
        - semantic: 语义向量
        - emotion: 情感向量
        - 其他自定义维度
        """
        question = data.get("question", "")

        embeddings: dict[str, Any] = {}
        weights: dict[str, float] = {}

        # 并行生成各维度的 embedding
        def generate_embedding(name: str, generator: EmbeddingGenerator, weight: float):
            emb = generator.embed(question)
            return name, emb, weight

        with ThreadPoolExecutor(max_workers=len(self.embedding_generators)) as executor:
            futures = []
            for name, (generator, weight) in self.embedding_generators.items():
                futures.append(executor.submit(generate_embedding, name, generator, weight))

            for future in as_completed(futures):
                try:
                    name, emb, weight = future.result()
                    if emb is not None:
                        embeddings[name] = emb
                        weights[name] = weight
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")

        # 根据输出格式存储
        if self.output_format == "dict":
            data["query_embeddings"] = embeddings
            data["embedding_weights"] = weights
        else:
            # list 格式：按权重排序的向量列表
            sorted_items = sorted(embeddings.items(), key=lambda x: weights.get(x[0], 0), reverse=True)
            data["query_embeddings"] = [emb for _, emb in sorted_items]
            data["embedding_weights"] = [weights.get(name, 0) for name, _ in sorted_items]
            data["embedding_names"] = [name for name, _ in sorted_items]

        return data

    # ==================== decompose action 实现 ====================

    def _decompose_query(self, data) -> dict[str, Any]:
        """查询分解

        将复杂查询分解为多个子查询
        """
        question = data.get("question", "")

        if self.decompose_strategy == "llm":
            sub_queries = self._decompose_with_llm(question)
        elif self.decompose_strategy == "rule":
            sub_queries = self._decompose_with_rules(question)
        elif self.decompose_strategy == "hybrid":
            # 先用规则，如果没有分解成功再用 LLM
            sub_queries = self._decompose_with_rules(question)
            if len(sub_queries) <= 1:
                sub_queries = self._decompose_with_llm(question)
        else:
            sub_queries = [question]

        data["sub_queries"] = sub_queries
        data["original_query"] = question
        data["sub_query_action"] = self.sub_query_action

        # 如果需要对子查询进行 embedding
        if self.embedding_generator is not None:
            if self.sub_query_action == "parallel":
                # 并行生成所有子查询的 embedding
                sub_embeddings = self.embedding_generator.embed_batch(sub_queries)
                data["sub_query_embeddings"] = sub_embeddings
            else:
                # 串行处理时只生成第一个的 embedding
                data["query_embedding"] = self.embedding_generator.embed(sub_queries[0])

        return data

    def _decompose_with_llm(self, query: str) -> list[str]:
        """使用 LLM 分解查询"""
        prompt = self.decompose_prompt.format(query=query)

        try:
            result = self.generator.generate(prompt, max_tokens=500, temperature=0.5)

            # 尝试解析 JSON 数组
            try:
                # 查找 JSON 数组
                match = re.search(r'\[.*?\]', result, re.DOTALL)
                if match:
                    sub_queries = json.loads(match.group())
                    if isinstance(sub_queries, list):
                        return sub_queries[: self.max_sub_queries]
            except json.JSONDecodeError:
                pass

            # 如果不是 JSON，尝试按行解析
            lines = result.strip().split("\n")
            sub_queries = []
            for line in lines:
                line = line.strip().lstrip("0123456789.-) ")
                if line and not line.startswith("[") and not line.endswith("]"):
                    sub_queries.append(line)

            return sub_queries[: self.max_sub_queries] if sub_queries else [query]

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
            return [query]

    def _decompose_with_rules(self, query: str) -> list[str]:
        """使用规则分解查询"""
        # 构建分割正则
        pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in self.split_keywords) + r')\b'

        # 分割查询
        parts = re.split(pattern, query, flags=re.IGNORECASE)
        sub_queries = [p.strip() for p in parts if p.strip()]

        return sub_queries[: self.max_sub_queries] if sub_queries else [query]

    # ==================== route action 实现 ====================

    def _route_query(self, data) -> dict[str, Any]:
        """检索路由

        根据查询内容决定查询哪些记忆源
        参考 MemoryOS（并行查询所有源）和 MemGPT（函数调用决定）
        """
        question = data.get("question", "")

        if self.route_strategy == "keyword":
            routes = self._route_by_keyword(question)
        elif self.route_strategy == "classifier":
            routes = self._route_by_classifier(question)
        elif self.route_strategy == "llm":
            routes = self._route_by_llm(question)
        else:
            routes = [self.default_route]

        # 限制路由数量
        if not self.allow_multi_route:
            routes = routes[:1]
        else:
            routes = routes[: self.max_routes]

        # 确保至少有一个路由
        if not routes:
            routes = [self.default_route]

        data["retrieval_routes"] = routes
        data["route_strategy"] = self.route_strategy

        return data

    def _route_by_keyword(self, query: str) -> list[str]:
        """基于关键词的路由

        检查查询中是否包含特定关键词，决定路由目标
        """
        query_lower = query.lower()
        matched_routes = []

        for rule in self.keyword_rules:
            keywords = rule.get("keywords", [])
            target = rule.get("target")

            for keyword in keywords:
                if keyword.lower() in query_lower:
                    if target not in matched_routes:
                        matched_routes.append(target)
                    break

        return matched_routes if matched_routes else [self.default_route]

    def _route_by_classifier(self, query: str) -> list[str]:
        """基于分类器的路由

        使用预训练分类器判断查询意图
        """
        # TODO: 实现分类器路由
        # Issue URL: https://github.com/intellistream/SAGE/issues/1267
        # 这里需要加载和使用意图分类模型
        logger.warning("Classifier routing not implemented, using default route")
        return [self.default_route]

    def _route_by_llm(self, query: str) -> list[str]:
        """基于 LLM 的路由

        使用 LLM 判断应该查询哪些记忆源
        """
        prompt = self.route_prompt.format(query=query)

        try:
            result = self.generator.generate(prompt, max_tokens=100, temperature=0.3)

            # 尝试解析 JSON 数组
            try:
                match = re.search(r'\[.*?\]', result, re.DOTALL)
                if match:
                    routes = json.loads(match.group())
                    if isinstance(routes, list):
                        return [r for r in routes if isinstance(r, str)]
            except json.JSONDecodeError:
                pass

            # 如果不是 JSON，尝试解析文本
            routes = []
            for source in ["short_term_memory", "long_term_memory", "knowledge_base"]:
                if source in result.lower():
                    routes.append(source)

            return routes if routes else [self.default_route]

        except Exception as e:
            logger.warning(f"LLM routing failed: {e}")
            return [self.default_route]

    # ==================== validate action 实现 ====================

    def _validate_query(self, data) -> dict[str, Any]:
        """查询验证和预处理

        验证查询是否符合要求，并进行必要的预处理
        """
        question = data.get("question", "")
        original_question = question

        # 预处理
        question = self._preprocess_query(question)

        # 验证
        is_valid, error_message = self._validate_rules(question)

        if not is_valid:
            data["validation_error"] = error_message
            data["is_valid"] = False

            if self.on_fail == "error":
                raise ValueError(f"Query validation failed: {error_message}")
            elif self.on_fail == "skip":
                data["skip_retrieval"] = True
            else:  # default
                question = self.default_query
                data["used_default"] = True
        else:
            data["is_valid"] = True

        # 更新查询
        if question != original_question:
            data["original_question"] = original_question
            data["question"] = question

        return data

    def _preprocess_query(self, query: str) -> str:
        """预处理查询"""
        if self.preprocessing.get("strip_whitespace", True):
            query = query.strip()

        if self.preprocessing.get("lowercase", False):
            query = query.lower()

        if self.preprocessing.get("remove_punctuation", False):
            query = re.sub(r'[^\w\s]', '', query)

        return query

    def _validate_rules(self, query: str) -> tuple[bool, str]:
        """验证查询规则"""
        for rule in self.validation_rules:
            rule_type = rule.get("type")

            if rule_type == "length":
                min_len = rule.get("min", 1)
                max_len = rule.get("max", 10000)
                if len(query) < min_len:
                    return False, f"Query too short (min: {min_len})"
                if len(query) > max_len:
                    return False, f"Query too long (max: {max_len})"

            elif rule_type == "language":
                allowed = rule.get("allowed", [])
                if allowed:
                    detected = self._detect_language(query)
                    if detected and detected not in allowed:
                        return False, f"Language {detected} not allowed"

            elif rule_type == "safety":
                for pattern in self.blocked_patterns:
                    if pattern.lower() in query.lower():
                        return False, f"Query contains blocked pattern"

        return True, ""

    def _detect_language(self, text: str) -> str | None:
        """简单的语言检测

        基于字符集的启发式检测
        """
        # 检测中文
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"

        # 检测日文
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return "ja"

        # 检测韩文
        if re.search(r'[\uac00-\ud7af]', text):
            return "ko"

        # 默认英文
        if re.search(r'[a-zA-Z]', text):
            return "en"

        return None
