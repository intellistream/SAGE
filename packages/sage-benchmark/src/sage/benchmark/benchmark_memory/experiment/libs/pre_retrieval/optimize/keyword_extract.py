"""KeywordExtractAction - 关键词提取策略

使用记忆体：
- LD-Agent: hierarchical_memory，提取关键词用于检索
- HippoRAG: graph_memory，提取实体作为查询

支持的提取器：
- spacy: 使用spaCy进行词性标注和关键词提取
- nltk: 使用NLTK进行词性标注和关键词提取
- llm: 使用LLM提取关键词

特点：
- 提取名词、专有名词等作为关键词
- 支持多种NLP工具
- 可配置提取类型和数量
"""

import subprocess

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class KeywordExtractAction(BasePreRetrievalAction):
    """关键词提取Action

    从查询中提取关键词，用于更精准的检索。
    """

    def _init_action(self) -> None:
        """初始化关键词提取器"""
        self.extractor = self._get_config_value(
            "extractor", required=True, context="optimize_type=keyword_extract"
        )

        self.extract_types = self._get_config_value("extract_types", default=["NOUN", "PROPN"])

        self.max_keywords = self._get_config_value(
            "max_keywords", required=True, context="optimize_type=keyword_extract"
        )

        # 根据extractor类型初始化工具
        if self.extractor == "spacy":
            self._init_spacy()
        elif self.extractor == "nltk":
            self._init_nltk()
        elif self.extractor == "llm":
            self._init_llm()
        else:
            raise ValueError(f"Unsupported extractor: {self.extractor}")

    def _init_spacy(self) -> None:
        """初始化spaCy模型"""
        import spacy

        model_name = self._get_config_value("spacy_model", required=True, context="extractor=spacy")

        try:
            self._nlp = spacy.load(model_name)
        except OSError:
            print(f"spaCy model {model_name} not found, attempting to download...")
            subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
            self._nlp = spacy.load(model_name)

    def _init_nltk(self) -> None:
        """初始化NLTK资源"""
        import nltk
        from nltk import pos_tag, word_tokenize
        from nltk.stem import WordNetLemmatizer

        # 下载必需资源
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

        # NLTK到通用POS的映射
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

    def _init_llm(self) -> None:
        """初始化LLM关键词提取"""
        self.keyword_prompt = self._get_config_value(
            "keyword_prompt", required=True, context="extractor=llm"
        )
        # LLM生成器将由PreRetrieval主类提供
        self._llm_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """提取关键词

        Args:
            input_data: 输入数据

        Returns:
            包含关键词的输出数据
        """
        question = input_data.question

        # 提取关键词
        if self.extractor == "spacy":
            keywords = self._extract_with_spacy(question)
        elif self.extractor == "nltk":
            keywords = self._extract_with_nltk(question)
        elif self.extractor == "llm":
            keywords = self._extract_with_llm(question)
        else:
            keywords = []

        # 生成查询字符串
        query = ", ".join(keywords) if keywords else question

        return PreRetrievalOutput(
            query=query,
            query_embedding=None,  # 由外部统一生成
            metadata={
                "keywords": keywords,
                "original_query": question,
                "extractor": self.extractor,
                "needs_embedding": True,
            },
            retrieve_mode="passive",
        )

    def _extract_with_spacy(self, text: str) -> list[str]:
        """使用spaCy提取关键词"""
        doc = self._nlp(text)
        keywords = []

        for token in doc:
            if token.pos_ in self.extract_types:
                keywords.append(token.lemma_)

        return keywords[: self.max_keywords]

    def _extract_with_nltk(self, text: str) -> list[str]:
        """使用NLTK提取关键词"""
        tokens = self._word_tokenize(text)
        tagged = self._pos_tag(tokens)
        keywords = []

        for word, pos in tagged:
            # 转换NLTK POS到通用格式
            universal_pos = self._nltk_pos_mapping.get(pos, "")
            if universal_pos in self.extract_types:
                lemma = self._lemmatizer.lemmatize(word.lower())
                keywords.append(lemma)

        return keywords[: self.max_keywords]

    def _extract_with_llm(self, text: str) -> list[str]:
        """使用LLM提取关键词"""
        if self._llm_generator is None:
            raise RuntimeError("LLM generator not set. Call set_llm_generator first.")

        prompt = self.keyword_prompt.format(question=text, max_keywords=self.max_keywords)
        response = self._llm_generator.generate(prompt)

        # 解析LLM响应（假设返回逗号分隔的关键词）
        keywords = [kw.strip() for kw in response.split(",")]
        return keywords[: self.max_keywords]
