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
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils.config_loader import get_required_config
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction


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
        self.action = get_required_config(self.config, "operators.pre_retrieval.action")

        # 共享工具（LLM 和 Embedding），依赖外部模型部署
        self._generator = LLMGenerator.from_config(self.config)
        self._embedding_generator = EmbeddingGenerator.from_config(self.config)

        # 根据 action 初始化特定配置和工具
        self._init_for_action()

    # ==================== 初始化方法 ====================

    def _init_for_action(self):
        """根据 action 类型初始化对应配置和工具"""
        if self.action == "optimize":
            # optimize action 配置
            self.optimize_type = get_required_config(
                self.config, "operators.pre_retrieval.optimize_type", "action=optimize"
            )

            if self.optimize_type == "keyword_extract":
                self.extractor = get_required_config(
                    self.config,
                    "operators.pre_retrieval.extractor",
                    "optimize_type=keyword_extract",
                )
                self.extract_types = self.config.get(
                    "operators.pre_retrieval.extract_types", ["NOUN", "PROPN"]
                )
                self.max_keywords = get_required_config(
                    self.config,
                    "operators.pre_retrieval.max_keywords",
                    "optimize_type=keyword_extract",
                )
                self.keyword_prompt = self.config.get("operators.pre_retrieval.keyword_prompt")

                if self.extractor == "spacy":
                    import subprocess

                    import spacy

                    model_name = get_required_config(
                        self.config, "operators.pre_retrieval.spacy_model", "extractor=spacy"
                    )
                    try:
                        self._nlp = spacy.load(model_name)
                    except OSError:
                        print(f"spaCy model {model_name} not found, attempting to download...")
                        subprocess.run(
                            ["python", "-m", "spacy", "download", model_name], check=True
                        )
                        self._nlp = spacy.load(model_name)

                elif self.extractor == "nltk":
                    import nltk
                    from nltk import pos_tag, word_tokenize
                    from nltk.stem import WordNetLemmatizer

                    for resource, path in [
                        ("punkt", "tokenizers/punkt"),
                        ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger"),
                        ("wordnet", "corpora/wordnet"),
                    ]:
                        try:
                            nltk.data.find(path)
                        except LookupError:
                            nltk.download(resource, quiet=True)
                    self._word_tokenize = word_tokenize
                    self._pos_tag = pos_tag
                    self._lemmatizer = WordNetLemmatizer()
                    self._nltk_pos_mapping = {
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

                elif self.extractor == "llm":
                    if not self.keyword_prompt:
                        raise ValueError(
                            "缺少必需配置: operators.pre_retrieval.keyword_prompt (extractor=llm)"
                        )

            elif self.optimize_type == "expand":
                self.expand_prompt = get_required_config(
                    self.config, "operators.pre_retrieval.expand_prompt", "optimize_type=expand"
                )
                self.expand_count = get_required_config(
                    self.config, "operators.pre_retrieval.expand_count", "optimize_type=expand"
                )
                self.merge_strategy = self.config.get(
                    "operators.pre_retrieval.merge_strategy", "union"
                )

            elif self.optimize_type == "rewrite":
                self.rewrite_prompt = get_required_config(
                    self.config, "operators.pre_retrieval.rewrite_prompt", "optimize_type=rewrite"
                )

            elif self.optimize_type == "instruction":
                self.instruction_prefix = get_required_config(
                    self.config,
                    "operators.pre_retrieval.instruction_prefix",
                    "optimize_type=instruction",
                )
                self.instruction_suffix = self.config.get(
                    "operators.pre_retrieval.instruction_suffix", ""
                )

            self.replace_original = self.config.get(
                "operators.pre_retrieval.replace_original", False
            )
            self.store_optimized = self.config.get("operators.pre_retrieval.store_optimized", True)

        elif self.action == "multi_embed":
            # multi_embed action 配置
            self.embeddings_config = self.config.get("operators.pre_retrieval.embeddings", [])
            if not self.embeddings_config:
                self.embeddings_config = [
                    {"name": "semantic", "model": "BAAI/bge-m3", "weight": 0.6}
                ]

            self._embedding_generators: dict[str, tuple[EmbeddingGenerator, float]] = {}
            base_url = self.config.get("runtime.embedding_base_url")
            for emb_config in self.embeddings_config:
                name = emb_config.get("name", "default")
                model = emb_config.get("model", "BAAI/bge-m3")
                weight = emb_config.get("weight", 1.0)
                generator = EmbeddingGenerator(base_url=base_url, model_name=model)
                self._embedding_generators[name] = (generator, weight)

            self.output_format = self.config.get("operators.pre_retrieval.output_format", "dict")
            self.match_insert_config = self.config.get(
                "operators.pre_retrieval.match_insert_config", True
            )

        elif self.action == "decompose":
            # decompose action 配置
            self.decompose_strategy = get_required_config(
                self.config, "operators.pre_retrieval.decompose_strategy", "action=decompose"
            )
            self.max_sub_queries = get_required_config(
                self.config, "operators.pre_retrieval.max_sub_queries", "action=decompose"
            )
            self.sub_query_action = self.config.get(
                "operators.pre_retrieval.sub_query_action", "parallel"
            )
            self.decompose_merge_strategy = self.config.get(
                "operators.pre_retrieval.merge_strategy", "union"
            )

            if self.decompose_strategy == "llm":
                self.decompose_prompt = get_required_config(
                    self.config,
                    "operators.pre_retrieval.decompose_prompt",
                    "decompose_strategy=llm",
                )
            elif self.decompose_strategy == "rule":
                self.split_keywords = get_required_config(
                    self.config, "operators.pre_retrieval.split_keywords", "decompose_strategy=rule"
                )

        elif self.action == "route":
            # route action 配置
            self.route_strategy = get_required_config(
                self.config, "operators.pre_retrieval.route_strategy", "action=route"
            )
            self.allow_multi_route = self.config.get(
                "operators.pre_retrieval.allow_multi_route", True
            )
            self.max_routes = self.config.get("operators.pre_retrieval.max_routes", 2)
            # 注意：default_route 改名为 default_strategy 以避免歧义
            self.default_strategy = self.config.get(
                "operators.pre_retrieval.default_strategy"
            ) or get_required_config(
                self.config, "operators.pre_retrieval.default_route", "action=route"
            )

            if self.route_strategy == "keyword":
                self.keyword_rules = get_required_config(
                    self.config, "operators.pre_retrieval.keyword_rules", "route_strategy=keyword"
                )
            elif self.route_strategy == "classifier":
                self.classifier_model = get_required_config(
                    self.config,
                    "operators.pre_retrieval.classifier_model",
                    "route_strategy=classifier",
                )
                self.route_mapping = get_required_config(
                    self.config,
                    "operators.pre_retrieval.route_mapping",
                    "route_strategy=classifier",
                )
            elif self.route_strategy == "llm":
                self.route_prompt = get_required_config(
                    self.config, "operators.pre_retrieval.route_prompt", "route_strategy=llm"
                )

        elif self.action == "validate":
            # validate action 配置
            self.validation_rules = get_required_config(
                self.config, "operators.pre_retrieval.rules", "action=validate"
            )
            self.on_fail = self.config.get("operators.pre_retrieval.on_fail", "default")
            self.default_query = self.config.get("operators.pre_retrieval.default_query", "Hello")
            self.preprocessing = self.config.get(
                "operators.pre_retrieval.preprocessing",
                {"strip_whitespace": True, "lowercase": False, "remove_punctuation": False},
            )
            self.blocked_patterns = []
            for rule in self.validation_rules:
                if rule.get("type") == "safety":
                    self.blocked_patterns.extend(rule.get("blocked_patterns", []))

        elif self.action == "scm_gate":
            # SCM Memory Controller: 判断是否需要激活记忆
            # 论文要求: LLM 判断是否需要检索，若不需要则跳过
            self.gate_prompt = self.config.get(
                "operators.pre_retrieval.gate_prompt",
                """Given the following question, determine if memory retrieval is needed to answer it.

Question: {question}

Consider:
1. Is this a question about past conversations or personal information?
2. Does it require context from previous interactions?
3. Is it a simple greeting or general knowledge question?

Answer with JSON: {{"need_memory": true/false, "reason": "brief explanation"}}""",
            )
            self.gate_default = self.config.get("operators.pre_retrieval.gate_default", True)

    # ==================== 执行方法 ====================

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行预处理

        Args:
            data: PipelineRequest 对象或原始检索请求，包含：
                - "question": 查询问题（字符串）
                - 其他检索参数

        Returns:
            处理后的数据，根据 action 不同添加不同字段
        """
        action_handlers = {
            "none": self._execute_none,
            "embedding": self._execute_embedding,
            "optimize": self._execute_optimize,
            "multi_embed": self._execute_multi_embed,
            "decompose": self._execute_decompose,
            "route": self._execute_route,
            "validate": self._execute_validate,
            "scm_gate": self._execute_scm_gate,
        }

        handler = action_handlers.get(self.action)
        if handler:
            return handler(data)
        else:
            print(f"[WARNING] Unknown action: {self.action}, passing through")
            return data

    # ==================== 大类操作方法 ====================

    def _execute_none(self, data: dict[str, Any]) -> dict[str, Any]:
        """none action: 透传数据"""
        return data

    def _execute_embedding(self, data: dict[str, Any]) -> dict[str, Any]:
        """embedding action: 对查询问题进行 Embedding

        Args:
            data: 检索请求数据，包含 "question" 字段

        Returns:
            添加了 "query_embedding" 字段的数据
        """
        question = data.get("question")
        if question:
            embedding = self._embedding_generator.embed(question)
            data["query_embedding"] = embedding
        return data

    # ==================== optimize action 实现 ====================

    def _execute_optimize(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行查询优化（optimize action）

        支持的 optimize_type:
        - keyword_extract: 关键词提取
        - expand: 查询扩展
        - rewrite: 查询改写
        - instruction: 指令增强
        """
        question = data.get("question", "")
        if not question:
            return data

        optimized_query = question  # 默认值

        if self.optimize_type == "keyword_extract":
            # ---- keyword_extract 逻辑内联 ----
            if self.extractor == "spacy":
                # spaCy 关键词提取内联
                doc = self._nlp(question)
                keywords = []
                for token in doc:
                    if token.pos_ in self.extract_types:
                        keywords.append(token.lemma_)
                keywords = list(dict.fromkeys(keywords))[: self.max_keywords]
                optimized_query = ",".join(keywords) if keywords else question

            elif self.extractor == "nltk":
                # NLTK 关键词提取内联
                tokens = self._word_tokenize(question)
                tagged = self._pos_tag(tokens)
                keywords = []
                for word, tag in tagged:
                    universal_tag = self._nltk_pos_mapping.get(tag, "")
                    if universal_tag in self.extract_types:
                        lemma = self._lemmatizer.lemmatize(word.lower())
                        keywords.append(lemma)
                keywords = list(dict.fromkeys(keywords))[: self.max_keywords]
                optimized_query = ",".join(keywords) if keywords else question

            elif self.extractor == "llm":
                # LLM 关键词提取内联
                prompt = self.keyword_prompt or (
                    f"Extract the key search terms from this query. "
                    f"Return only the keywords separated by commas, nothing else.\n\n"
                    f"Query: {question}\n\nKeywords:"
                )
                prompt = prompt.format(query=question)
                try:
                    result = self._generator.generate(prompt, max_tokens=100, temperature=0.3)
                    keywords = [k.strip() for k in result.strip().split(",")]
                    keywords = keywords[: self.max_keywords]
                    optimized_query = ",".join(keywords) if keywords else question
                except Exception as e:
                    print(f"LLM keyword extraction failed: {e}")
                    optimized_query = question

        elif self.optimize_type == "expand":
            # ---- expand 逻辑内联 ----
            prompt = self.expand_prompt.format(query=question, count=self.expand_count)
            try:
                result = self._generator.generate(prompt, max_tokens=300, temperature=0.7)
                lines = result.strip().split("\n")
                expanded_queries = [
                    line.strip().lstrip("0123456789.-) ") for line in lines if line.strip()
                ]
                expanded_queries = expanded_queries[: self.expand_count]

                if self.merge_strategy == "union":
                    optimized_query = [question] + expanded_queries
                else:
                    optimized_query = expanded_queries if expanded_queries else [question]
            except Exception as e:
                print(f"Query expansion failed: {e}")
                optimized_query = [question]

        elif self.optimize_type == "rewrite":
            # ---- rewrite 逻辑内联 ----
            prompt = self.rewrite_prompt.format(query=question)
            try:
                result = self._generator.generate(prompt, max_tokens=200, temperature=0.5)
                optimized_query = result.strip() or question
            except Exception as e:
                print(f"Query rewrite failed: {e}")
                optimized_query = question

        elif self.optimize_type == "instruction":
            # ---- instruction 逻辑内联 ----
            optimized_query = f"{self.instruction_prefix}{question}{self.instruction_suffix}"

        # 存储优化结果
        if self.store_optimized:
            data["optimized_query"] = optimized_query
            data["original_query"] = question

        # 是否替换原始查询
        if self.replace_original:
            if isinstance(optimized_query, list):
                data["question"] = optimized_query[0] if optimized_query else question
            else:
                data["question"] = optimized_query

        # 对优化后的查询进行 embedding
        if self._embedding_generator is not None:
            query_to_embed = optimized_query if self.replace_original else question
            if isinstance(query_to_embed, str):
                data["query_embedding"] = self._embedding_generator.embed(query_to_embed)
            elif isinstance(query_to_embed, list):
                # 多查询场景
                embeddings = [self._embedding_generator.embed(q) for q in query_to_embed]
                data["query_embeddings"] = embeddings

        return data

    # ==================== multi_embed action 实现 ====================

    def _execute_multi_embed(self, data: dict[str, Any]) -> dict[str, Any]:
        """多维向量生成（multi_embed action）

        参考 EmotionalRAG 实现，生成多个维度的 embedding：
        - semantic: 语义向量
        - emotion: 情感向量
        - 其他自定义维度
        """
        question = data.get("question", "")
        if not question:
            return data

        embeddings: dict[str, Any] = {}
        weights: dict[str, float] = {}

        # 并行生成各维度的 embedding
        def generate_embedding(name: str, generator: EmbeddingGenerator, weight: float):
            emb = generator.embed(question)
            return name, emb, weight

        with ThreadPoolExecutor(max_workers=len(self._embedding_generators)) as executor:
            futures = []
            for name, (generator, weight) in self._embedding_generators.items():
                futures.append(executor.submit(generate_embedding, name, generator, weight))

            for future in as_completed(futures):
                try:
                    name, emb, weight = future.result()
                    if emb is not None:
                        embeddings[name] = emb
                        weights[name] = weight
                except Exception as e:
                    print(f"Embedding generation failed: {e}")

        # 根据输出格式存储
        if self.output_format == "dict":
            data["query_embeddings"] = embeddings
            data["embedding_weights"] = weights
        else:
            # list 格式：按权重排序的向量列表
            sorted_items = sorted(
                embeddings.items(), key=lambda x: weights.get(x[0], 0), reverse=True
            )
            data["query_embeddings"] = [emb for _, emb in sorted_items]
            data["embedding_weights"] = [weights.get(name, 0) for name, _ in sorted_items]
            data["embedding_names"] = [name for name, _ in sorted_items]

        return data

    # ==================== decompose action 实现 ====================

    def _execute_decompose(self, data: dict[str, Any]) -> dict[str, Any]:
        """查询分解（decompose action）

        将复杂查询分解为多个子查询
        """
        question = data.get("question", "")
        if not question:
            return data

        sub_queries = [question]  # 默认值

        if self.decompose_strategy == "llm":
            # ---- LLM 分解逻辑内联 ----
            prompt = self.decompose_prompt.format(query=question)
            try:
                result = self._generator.generate(prompt, max_tokens=500, temperature=0.5)

                # 尝试解析 JSON 数组
                try:
                    match = re.search(r"\[.*?\]", result, re.DOTALL)
                    if match:
                        parsed_queries = json.loads(match.group())
                        if isinstance(parsed_queries, list):
                            sub_queries = parsed_queries[: self.max_sub_queries]
                except json.JSONDecodeError:
                    pass

                # 如果不是 JSON，尝试按行解析
                if sub_queries == [question]:
                    lines = result.strip().split("\n")
                    parsed_lines = []
                    for line in lines:
                        line = line.strip().lstrip("0123456789.-) ")
                        if line and not line.startswith("[") and not line.endswith("]"):
                            parsed_lines.append(line)
                    if parsed_lines:
                        sub_queries = parsed_lines[: self.max_sub_queries]

            except Exception as e:
                print(f"Query decomposition failed: {e}")
                sub_queries = [question]

        elif self.decompose_strategy == "rule":
            # ---- 规则分解逻辑内联 ----
            pattern = r"\b(?:" + "|".join(re.escape(kw) for kw in self.split_keywords) + r")\b"
            parts = re.split(pattern, question, flags=re.IGNORECASE)
            parsed_parts = [p.strip() for p in parts if p.strip()]
            if parsed_parts:
                sub_queries = parsed_parts[: self.max_sub_queries]

        elif self.decompose_strategy == "hybrid":
            # ---- 混合策略内联 ----
            # 先用规则
            pattern = r"\b(?:" + "|".join(re.escape(kw) for kw in self.split_keywords) + r")\b"
            parts = re.split(pattern, question, flags=re.IGNORECASE)
            parsed_parts = [p.strip() for p in parts if p.strip()]

            if len(parsed_parts) > 1:
                sub_queries = parsed_parts[: self.max_sub_queries]
            else:
                # 规则失败，使用 LLM
                prompt = self.decompose_prompt.format(query=question)
                try:
                    result = self._generator.generate(prompt, max_tokens=500, temperature=0.5)
                    try:
                        match = re.search(r"\[.*?\]", result, re.DOTALL)
                        if match:
                            parsed_queries = json.loads(match.group())
                            if isinstance(parsed_queries, list):
                                sub_queries = parsed_queries[: self.max_sub_queries]
                    except json.JSONDecodeError:
                        lines = result.strip().split("\n")
                        parsed_lines = []
                        for line in lines:
                            line = line.strip().lstrip("0123456789.-) ")
                            if line and not line.startswith("[") and not line.endswith("]"):
                                parsed_lines.append(line)
                        if parsed_lines:
                            sub_queries = parsed_lines[: self.max_sub_queries]
                except Exception as e:
                    print(f"Hybrid decomposition (LLM fallback) failed: {e}")

        data["sub_queries"] = sub_queries
        data["original_query"] = question
        data["sub_query_action"] = self.sub_query_action

        # 如果需要对子查询进行 embedding
        if self._embedding_generator is not None:
            if self.sub_query_action == "parallel":
                # 并行生成所有子查询的 embedding
                sub_embeddings = [self._embedding_generator.embed(q) for q in sub_queries]
                data["sub_query_embeddings"] = sub_embeddings
            else:
                # 串行处理时只生成第一个的 embedding
                data["query_embedding"] = self._embedding_generator.embed(sub_queries[0])

        return data

    # ==================== route action 实现 ====================

    def _execute_route(self, data: dict[str, Any]) -> dict[str, Any]:
        """检索路由（route action）- 输出检索策略提示

        根据查询内容决定使用哪些检索策略。
        注意：这里输出的是"策略提示"(hints)，而非服务选择。
        单一服务将根据这些提示调整检索行为。

        参考实现:
        - MemoryOS: 并行查询所有源
        - MemGPT: 函数调用决定

        输出:
        - retrieval_hints: 包含 strategies 和 params 的提示信息
        """
        question = data.get("question", "")
        if not question:
            return data

        strategies: list[str] = []
        params: dict[str, Any] = {}

        if self.route_strategy == "keyword":
            # ---- keyword 路由内联 ----
            query_lower = question.lower()
            matched_strategies: list[str] = []
            merged_params: dict[str, Any] = {}

            for rule in self.keyword_rules:
                keywords = rule.get("keywords", [])
                strategy = rule.get("strategy") or rule.get("target")
                rule_params = rule.get("params", {})

                for keyword in keywords:
                    if keyword.lower() in query_lower:
                        if strategy and strategy not in matched_strategies:
                            matched_strategies.append(strategy)
                            merged_params.update(rule_params)
                        break

            strategies = matched_strategies if matched_strategies else [self.default_strategy]
            params = merged_params

        elif self.route_strategy == "classifier":
            # ---- classifier 路由内联 ----
            # TODO: 实现分类器路由
            # Issue URL: https://github.com/intellistream/SAGE/issues/1267
            print("Classifier routing not implemented, using default strategy")
            strategies = [self.default_strategy]
            params = {}

        elif self.route_strategy == "llm":
            # ---- LLM 路由内联 ----
            prompt = self.route_prompt.format(query=question)
            try:
                result = self._generator.generate(prompt, max_tokens=100, temperature=0.3)

                # 尝试解析 JSON 对象（新格式：包含 strategies 和 params）
                try:
                    match = re.search(r"\{.*?\}", result, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        if isinstance(parsed, dict):
                            parsed_strategies = parsed.get("strategies", [])
                            parsed_params = parsed.get("params", {})
                            if parsed_strategies:
                                strategies = parsed_strategies
                                params = parsed_params
                except json.JSONDecodeError:
                    pass

                # 尝试解析 JSON 数组（旧格式兼容）
                if not strategies:
                    try:
                        match = re.search(r"\[.*?\]", result, re.DOTALL)
                        if match:
                            parsed_array = json.loads(match.group())
                            if isinstance(parsed_array, list):
                                strategies = [r for r in parsed_array if isinstance(r, str)]
                    except json.JSONDecodeError:
                        pass

                # 如果不是 JSON，尝试解析文本中的策略关键词
                if not strategies:
                    known_strategies = [
                        "deep_search",
                        "temporal_search",
                        "persona_search",
                        "semantic_search",
                        "short_term_memory",
                        "long_term_memory",
                        "knowledge_base",
                    ]
                    for strategy in known_strategies:
                        if strategy in result.lower():
                            strategies.append(strategy)

                if not strategies:
                    strategies = [self.default_strategy]

            except Exception as e:
                print(f"LLM routing failed: {e}")
                strategies = [self.default_strategy]
                params = {}

        else:
            strategies = [self.default_strategy]
            params = {}

        # 限制策略数量
        if not self.allow_multi_route:
            strategies = strategies[:1]
        else:
            strategies = strategies[: self.max_routes]

        # 确保至少有一个策略
        if not strategies:
            strategies = [self.default_strategy]

        # 输出 retrieval_hints（语义清晰，表示"提示"而非"路由目标"）
        data["retrieval_hints"] = {
            "strategies": strategies,
            "params": params,
            "route_strategy": self.route_strategy,
        }

        return data

    # ==================== validate action 实现 ====================

    def _execute_validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """查询验证和预处理（validate action）

        验证查询是否符合要求，并进行必要的预处理
        """
        question = data.get("question", "")
        original_question = question

        # ---- 预处理逻辑内联 ----
        if self.preprocessing.get("strip_whitespace", True):
            question = question.strip()

        if self.preprocessing.get("lowercase", False):
            question = question.lower()

        if self.preprocessing.get("remove_punctuation", False):
            question = re.sub(r"[^\w\s]", "", question)

        # ---- 验证规则逻辑内联 ----
        is_valid = True
        error_message = ""

        for rule in self.validation_rules:
            rule_type = rule.get("type")

            if rule_type == "length":
                min_len = rule.get("min", 1)
                max_len = rule.get("max", 10000)
                if len(question) < min_len:
                    is_valid = False
                    error_message = f"Query too short (min: {min_len})"
                    break
                if len(question) > max_len:
                    is_valid = False
                    error_message = f"Query too long (max: {max_len})"
                    break

            elif rule_type == "language":
                allowed = rule.get("allowed", [])
                if allowed:
                    # ---- 语言检测逻辑内联 ----
                    detected = None
                    if re.search(r"[\u4e00-\u9fff]", question):
                        detected = "zh"
                    elif re.search(r"[\u3040-\u309f\u30a0-\u30ff]", question):
                        detected = "ja"
                    elif re.search(r"[\uac00-\ud7af]", question):
                        detected = "ko"
                    elif re.search(r"[a-zA-Z]", question):
                        detected = "en"

                    if detected and detected not in allowed:
                        is_valid = False
                        error_message = f"Language {detected} not allowed"
                        break

            elif rule_type == "safety":
                for pattern in self.blocked_patterns:
                    if pattern.lower() in question.lower():
                        is_valid = False
                        error_message = "Query contains blocked pattern"
                        break
                if not is_valid:
                    break

        # 处理验证结果
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

    def _execute_scm_gate(self, data: dict[str, Any]) -> dict[str, Any]:
        """SCM Memory Controller: 判断是否需要激活记忆检索

        论文要求 (SCM4LLMs):
        检索前判断：
        - 是否需要激活记忆？
        - LLM 回答 yes/no
        - 若 no，跳过检索

        流程:
        1. 构建 gate prompt
        2. 调用 LLM 判断
        3. 解析结果，设置 skip_retrieval 标志

        Args:
            data: 检索请求数据，包含 "question" 字段

        Returns:
            处理后的数据，添加 gate_result 和可能的 skip_retrieval 标志
        """
        question = data.get("question", "")

        if not question:
            # 空查询，使用默认行为
            data["skip_retrieval"] = not self.gate_default
            data["gate_result"] = {
                "need_memory": self.gate_default,
                "reason": "Empty question, using default",
            }
            return data

        # 构建 prompt
        prompt = self.gate_prompt.replace("{question}", question)

        try:
            response = self._generator.generate(prompt)
            result = self._parse_gate_response(response)

            need_memory = result.get("need_memory", self.gate_default)
            reason = result.get("reason", "")

            data["gate_result"] = {
                "need_memory": need_memory,
                "reason": reason,
            }

            if not need_memory:
                data["skip_retrieval"] = True
                print(f"[SCM_GATE] Skipping retrieval: {reason}")

        except Exception as e:  # noqa: BLE001
            # LLM 调用失败，使用默认行为
            print(f"[SCM_GATE] LLM call failed: {e}, using default={self.gate_default}")
            data["gate_result"] = {
                "need_memory": self.gate_default,
                "reason": f"LLM error: {e}",
            }
            if not self.gate_default:
                data["skip_retrieval"] = True

        return data

    def _parse_gate_response(self, response: str) -> dict:
        """解析 gate LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，包含 need_memory 和 reason
        """
        try:
            # 尝试解析 JSON
            result_text = response.strip()
            start_idx = result_text.find("{")
            end_idx = result_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = result_text[start_idx:end_idx]
                result = json.loads(json_str)
                return {
                    "need_memory": bool(result.get("need_memory", True)),
                    "reason": str(result.get("reason", "")),
                }
        except json.JSONDecodeError:
            pass

        # JSON 解析失败，尝试关键词匹配
        response_lower = response.lower()
        if "no" in response_lower or "false" in response_lower:
            return {"need_memory": False, "reason": "Detected 'no' in response"}
        elif "yes" in response_lower or "true" in response_lower:
            return {"need_memory": True, "reason": "Detected 'yes' in response"}

        # 默认需要记忆
        return {"need_memory": True, "reason": "Could not parse response"}
