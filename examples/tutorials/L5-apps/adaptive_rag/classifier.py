"""
Query Complexity Classifier - 问题复杂度分类器

基于 Adaptive-RAG 论文实现的问题复杂度分类器。

复杂度等级:
- A (ZERO): 简单问题，LLM 可直接回答，无需检索
- B (SINGLE): 中等问题，需要单步检索
- C (MULTI): 复杂问题，需要多跳迭代检索

分类器可以使用:
1. 基于规则的启发式分类 (RuleBasedClassifier)
2. 小型语言模型分类 (T5Classifier)
3. LLM-based 分类 (LLMClassifier)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 复杂度等级定义
class QueryComplexityLevel(str, Enum):
    """问题复杂度等级"""

    ZERO = "A"  # 无需检索，LLM 直接回答
    SINGLE = "B"  # 单步检索
    MULTI = "C"  # 多跳迭代检索

    @classmethod
    def from_label(cls, label: str) -> "QueryComplexityLevel":
        """从标签字符串解析复杂度等级"""
        label = label.upper().strip()
        if label in ("A", "ZERO", "NO_RETRIEVAL", "SIMPLE"):
            return cls.ZERO
        elif label in ("B", "SINGLE", "ONE", "MEDIUM"):
            return cls.SINGLE
        elif label in ("C", "MULTI", "MULTIPLE", "COMPLEX", "ITERATIVE"):
            return cls.MULTI
        else:
            # 默认返回 SINGLE 作为折中策略
            return cls.SINGLE


@dataclass
class ClassificationResult:
    """分类结果"""

    query: str
    complexity: QueryComplexityLevel
    confidence: float = 1.0
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def strategy(self) -> str:
        """返回对应的策略名称"""
        strategy_map = {
            QueryComplexityLevel.ZERO: "no_retrieval",
            QueryComplexityLevel.SINGLE: "single_retrieval",
            QueryComplexityLevel.MULTI: "iterative_retrieval",
        }
        return strategy_map[self.complexity]


class BaseClassifier(ABC):
    """分类器基类"""

    @abstractmethod
    def classify(self, query: str) -> ClassificationResult:
        """对单个查询进行复杂度分类"""
        pass

    def batch_classify(self, queries: list[str]) -> list[ClassificationResult]:
        """批量分类"""
        return [self.classify(q) for q in queries]


class RuleBasedClassifier(BaseClassifier):
    """
    基于规则的启发式分类器

    使用关键词和句法特征判断问题复杂度:
    - 简单问题: 定义类、事实类问题
    - 中等问题: 需要单一来源的问题
    - 复杂问题: 包含多实体、比较、推理词汇的问题
    """

    # 多跳问题关键词
    MULTI_HOP_KEYWORDS = [
        "and",
        "compare",
        "comparison",
        "difference",
        "between",
        "both",
        "relationship",
        "related",
        "connection",
        "after",
        "before",
        "then",
        "first",
        "second",
        "finally",
        "consequently",
        "therefore",
        "because",
        "why did",
        "how did",
        "what happened when",
        "as a result",
    ]

    # 简单问题关键词
    SIMPLE_KEYWORDS = [
        "what is",
        "what are",
        "define",
        "definition",
        "who is",
        "when was",
        "where is",
        "how many",
        "how much",
        "name the",
        "list the",
    ]

    # 推理词汇
    REASONING_KEYWORDS = [
        "why",
        "how",
        "explain",
        "reason",
        "cause",
        "effect",
        "impact",
        "influence",
        "lead to",
        "result in",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        # 可配置的阈值
        self.multi_hop_threshold = self.config.get("multi_hop_threshold", 2)
        self.entity_count_threshold = self.config.get("entity_count_threshold", 3)

    def classify(self, query: str) -> ClassificationResult:
        """基于规则的分类"""
        query_lower = query.lower()

        # 计算多跳特征得分
        multi_hop_score = self._count_multi_hop_features(query_lower)

        # 计算简单问题特征
        simple_score = self._count_simple_features(query_lower)

        # 计算实体数量（简单启发式）
        entity_count = self._estimate_entity_count(query)

        # 决策逻辑
        if multi_hop_score >= self.multi_hop_threshold or entity_count >= self.entity_count_threshold:
            complexity = QueryComplexityLevel.MULTI
            confidence = min(0.9, 0.5 + multi_hop_score * 0.1 + entity_count * 0.05)
            reasoning = f"Detected {multi_hop_score} multi-hop keywords, {entity_count} entities"
        elif simple_score > 0 and multi_hop_score == 0:
            complexity = QueryComplexityLevel.ZERO
            confidence = min(0.8, 0.5 + simple_score * 0.15)
            reasoning = f"Simple factual question pattern detected"
        else:
            complexity = QueryComplexityLevel.SINGLE
            confidence = 0.6
            reasoning = "Default to single-hop retrieval"

        return ClassificationResult(
            query=query,
            complexity=complexity,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "multi_hop_score": multi_hop_score,
                "simple_score": simple_score,
                "entity_count": entity_count,
            },
        )

    def _count_multi_hop_features(self, query: str) -> int:
        """计算多跳特征数量"""
        count = 0
        for keyword in self.MULTI_HOP_KEYWORDS:
            if keyword in query:
                count += 1
        # 检查推理词汇
        for keyword in self.REASONING_KEYWORDS:
            if keyword in query:
                count += 0.5
        return int(count)

    def _count_simple_features(self, query: str) -> int:
        """计算简单问题特征"""
        count = 0
        for keyword in self.SIMPLE_KEYWORDS:
            if query.startswith(keyword) or f" {keyword}" in query:
                count += 1
        return count

    def _estimate_entity_count(self, query: str) -> int:
        """估计实体数量（基于大写词汇）"""
        words = query.split()
        # 计算首字母大写的词（排除句首）
        capitalized = sum(
            1 for i, word in enumerate(words) if i > 0 and word[0].isupper() and word.isalpha()
        )
        return capitalized


class LLMClassifier(BaseClassifier):
    """
    基于 LLM 的分类器

    使用 LLM 进行零样本或少样本分类。
    适用于需要更精确分类的场景。
    """

    DEFAULT_PROMPT = """Analyze the following question and classify its complexity level for a RAG system.

Question: {query}

Classification Guidelines:
- Level A (ZERO): Simple factual questions that an LLM can answer directly from its knowledge.
  Examples: "What is the capital of France?", "Define machine learning."
  
- Level B (SINGLE): Questions requiring a single retrieval step to find relevant documents.
  Examples: "What is the latest iPhone model?", "What are the symptoms of COVID-19?"
  
- Level C (MULTI): Complex questions requiring multiple retrieval steps or reasoning across documents.
  Examples: "Compare the economic policies of Obama and Trump.", 
            "What was the cause of World War I and how did it lead to World War II?"

Respond with ONLY the classification letter (A, B, or C) followed by a brief explanation.

Classification:"""

    def __init__(
        self,
        llm_client: Any = None,
        model: str = "gpt-3.5-turbo",
        prompt_template: str | None = None,
    ):
        self.llm_client = llm_client
        self.model = model
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT

    def classify(self, query: str) -> ClassificationResult:
        """使用 LLM 进行分类"""
        if self.llm_client is None:
            # 尝试创建默认客户端
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self.llm_client = UnifiedInferenceClient.create()
            except ImportError:
                raise RuntimeError("LLM client not available. Please provide an llm_client.")

        prompt = self.prompt_template.format(query=query)

        try:
            response = self.llm_client.chat(prompt)
            # 解析响应
            response_text = response.strip() if isinstance(response, str) else response.content.strip()
            classification, reasoning = self._parse_response(response_text)

            return ClassificationResult(
                query=query,
                complexity=classification,
                confidence=0.85,  # LLM 分类的默认置信度
                reasoning=reasoning,
                metadata={"raw_response": response_text},
            )
        except Exception as e:
            # 降级到规则分类
            fallback = RuleBasedClassifier()
            result = fallback.classify(query)
            result.metadata["llm_error"] = str(e)
            result.metadata["fallback"] = True
            return result

    def _parse_response(self, response: str) -> tuple[QueryComplexityLevel, str]:
        """解析 LLM 响应"""
        # 提取第一个字母作为分类
        response_upper = response.upper()
        for char in response_upper:
            if char in ("A", "B", "C"):
                classification = QueryComplexityLevel.from_label(char)
                # 剩余部分作为解释
                reasoning = response[response.upper().index(char) + 1 :].strip()
                if reasoning.startswith(":") or reasoning.startswith("-"):
                    reasoning = reasoning[1:].strip()
                return classification, reasoning

        # 默认返回 SINGLE
        return QueryComplexityLevel.SINGLE, "Unable to parse classification"


class T5Classifier(BaseClassifier):
    """
    基于 T5 模型的分类器

    使用微调后的 T5 模型进行问题复杂度分类。
    这是论文中使用的主要分类方法。

    模型训练:
    - 使用 silver labels: 基于不同策略的实际预测结果标注
    - 使用 binary labels: 基于数据集固有偏置标注
    """

    def __init__(
        self,
        model_path: str | None = None,
        model_name: str = "t5-large",
        device: str = "auto",
    ):
        self.model_path = model_path
        self.model_name = model_name
        self.device = device
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return

        try:
            from transformers import T5ForConditionalGeneration, T5Tokenizer

            if self.model_path:
                self._tokenizer = T5Tokenizer.from_pretrained(self.model_path)
                self._model = T5ForConditionalGeneration.from_pretrained(self.model_path)
            else:
                # 使用预训练模型（需要微调才能有效工作）
                self._tokenizer = T5Tokenizer.from_pretrained(self.model_name)
                self._model = T5ForConditionalGeneration.from_pretrained(self.model_name)

            if self.device == "auto":
                import torch

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = self._model.to(self.device)
            self._model.eval()
        except ImportError:
            raise RuntimeError(
                "transformers library not available. Install with: pip install transformers"
            )

    def classify(self, query: str) -> ClassificationResult:
        """使用 T5 模型进行分类"""
        self._load_model()

        import torch

        # 构造输入
        input_text = f"classify question complexity: {query}"
        inputs = self._tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 生成
        with torch.no_grad():
            outputs = self._model.generate(**inputs, max_length=10, num_beams=1)

        # 解码
        prediction = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        classification = QueryComplexityLevel.from_label(prediction)

        return ClassificationResult(
            query=query,
            complexity=classification,
            confidence=0.9,
            reasoning=f"T5 model prediction: {prediction}",
            metadata={"raw_prediction": prediction},
        )


# 工厂函数
def create_classifier(
    classifier_type: str = "rule",
    **kwargs,
) -> BaseClassifier:
    """
    创建分类器实例

    Args:
        classifier_type: 分类器类型 ("rule", "llm", "t5")
        **kwargs: 传递给分类器的参数

    Returns:
        分类器实例
    """
    classifiers = {
        "rule": RuleBasedClassifier,
        "llm": LLMClassifier,
        "t5": T5Classifier,
    }

    if classifier_type not in classifiers:
        raise ValueError(f"Unknown classifier type: {classifier_type}. Available: {list(classifiers.keys())}")

    return classifiers[classifier_type](**kwargs)


# 默认导出
QueryComplexityClassifier = RuleBasedClassifier
