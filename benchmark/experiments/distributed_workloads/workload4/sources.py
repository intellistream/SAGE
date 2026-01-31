"""
Workload 4 双流源算子

实现双流数据源算子，生成 Query 和 Document 事件流。

包含三个核心算子：
1. Workload4QuerySource - 查询源(Query 流)
2. Workload4DocumentSource - 文档源(Document 流)
3. EmbeddingPrecompute - Embedding 预计算算子
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.runtime.communication.packet import StopSignal

if TYPE_CHECKING:
    from .models import DocumentEvent, QueryEvent

try:
    from .models import DocumentEvent, QueryEvent
except ImportError:
    from models import DocumentEvent, QueryEvent


# === 查询和文档模板 ===

QUERY_TEMPLATES = {
    "factual": {
        "finance": [
            "What is the current stock price of {company}?",
            "How does {metric} affect company valuation?",
            "What are the key financial indicators for {sector}?",
            "Define {term} in financial context",
            "What is the difference between {term1} and {term2}?",
        ],
        "healthcare": [
            "What are the symptoms of {disease}?",
            "How is {treatment} administered?",
            "What are the side effects of {drug}?",
            "Define {medical_term} in medical context",
            "What is the recommended dosage for {medication}?",
        ],
        "technology": [
            "What is {technology} and how does it work?",
            "What are the key features of {product}?",
            "How to configure {system}?",
            "What is the difference between {tech1} and {tech2}?",
            "What are the system requirements for {software}?",
        ],
        "general": [
            "What is the definition of {term}?",
            "How to {action}?",
            "What are the benefits of {topic}?",
            "Explain {concept} in simple terms",
            "What is the history of {subject}?",
        ],
    },
    "analytical": {
        "finance": [
            "Compare the performance of {company1} and {company2} in Q3",
            "Analyze the impact of {event} on {sector} stocks",
            "What are the trends in {market} over the past year?",
            "Evaluate the risk factors for investing in {industry}",
            "How does {economic_indicator} correlate with {market_metric}?",
        ],
        "healthcare": [
            "Compare the effectiveness of {treatment1} vs {treatment2} for {condition}",
            "Analyze the trends in {disease} prevalence over the past decade",
            "What are the risk factors associated with {health_condition}?",
            "Evaluate the cost-effectiveness of {healthcare_intervention}",
            "How does {lifestyle_factor} affect {health_outcome}?",
        ],
        "technology": [
            "Compare {tech1} and {tech2} in terms of performance and scalability",
            "Analyze the evolution of {technology} over the past 5 years",
            "What are the pros and cons of {architecture} design?",
            "Evaluate the security implications of {technology}",
            "How does {factor} impact {system_performance}?",
        ],
        "general": [
            "Compare {option1} and {option2} for {use_case}",
            "Analyze the trends in {topic} over time",
            "What are the advantages and disadvantages of {approach}?",
            "Evaluate the impact of {factor} on {outcome}",
            "How do {variable1} and {variable2} interact?",
        ],
    },
    "exploratory": {
        "finance": [
            "What are emerging trends in {sector} investment?",
            "How might {global_event} reshape the {market} landscape?",
            "What innovations are disrupting traditional {industry}?",
            "Explore potential opportunities in {emerging_market}",
            "What are future scenarios for {financial_topic}?",
        ],
        "healthcare": [
            "What are emerging treatments for {disease_category}?",
            "How might {technology} transform healthcare delivery?",
            "What are the ethical implications of {medical_innovation}?",
            "Explore potential breakthroughs in {research_area}",
            "What future challenges face the healthcare industry?",
        ],
        "technology": [
            "What are emerging trends in {tech_domain}?",
            "How might {new_technology} change the industry?",
            "What are potential applications of {technology} in {domain}?",
            "Explore future possibilities for {technology_area}",
            "What challenges might {technology} face in adoption?",
        ],
        "general": [
            "What are emerging trends in {field}?",
            "How might {factor} shape the future of {domain}?",
            "What are potential innovations in {area}?",
            "Explore possibilities for {topic}",
            "What future scenarios might unfold for {subject}?",
        ],
    },
}

# 占位符替换词典
PLACEHOLDER_VALUES = {
    "company": ["Apple", "Microsoft", "Amazon", "Google", "Tesla", "NVIDIA"],
    "company1": ["Apple", "Microsoft", "Amazon"],
    "company2": ["Google", "Tesla", "NVIDIA"],
    "metric": ["P/E ratio", "debt-to-equity", "ROE", "EPS", "revenue growth"],
    "sector": ["technology", "healthcare", "finance", "energy", "consumer goods"],
    "term": ["volatility", "liquidity", "arbitrage", "hedge fund", "derivative"],
    "term1": ["stocks", "bonds", "ETFs"],
    "term2": ["mutual funds", "index funds", "REITs"],
    "disease": ["diabetes", "hypertension", "influenza", "arthritis", "asthma"],
    "treatment": ["chemotherapy", "immunotherapy", "physical therapy", "dialysis"],
    "drug": ["aspirin", "metformin", "lisinopril", "omeprazole", "atorvastatin"],
    "medical_term": ["inflammation", "metabolism", "homeostasis", "pathology"],
    "medication": ["insulin", "antibiotics", "antihypertensives", "statins"],
    "technology": ["Docker", "Kubernetes", "GraphQL", "WebAssembly", "5G"],
    "product": ["SAGE framework", "Ray cluster", "vLLM", "LangChain", "FastAPI"],
    "system": ["distributed pipeline", "Ray cluster", "embedding service"],
    "tech1": ["REST API", "gRPC", "WebSocket"],
    "tech2": ["GraphQL", "JSON-RPC", "MQTT"],
    "software": ["SAGE", "Ray", "Docker", "Python 3.10", "Ubuntu 22.04"],
    "action": ["optimize pipeline performance", "configure scheduler", "debug errors"],
    "topic": ["distributed computing", "LLM inference", "vector databases"],
    "concept": ["data pipeline", "semantic search", "batch processing"],
    "subject": ["artificial intelligence", "cloud computing", "microservices"],
    "event": ["Federal Reserve rate hike", "market correction", "earnings report"],
    "market": ["stock market", "bond market", "commodity market", "forex"],
    "industry": ["tech sector", "healthcare", "renewable energy", "AI startups"],
    "economic_indicator": ["GDP growth", "inflation rate", "unemployment"],
    "market_metric": ["stock prices", "trading volume", "market volatility"],
    "treatment1": ["surgery", "medication", "lifestyle changes"],
    "treatment2": ["physical therapy", "alternative medicine", "watchful waiting"],
    "condition": ["chronic pain", "anxiety", "sleep disorders", "obesity"],
    "health_condition": ["cardiovascular disease", "cancer", "mental health"],
    "healthcare_intervention": ["preventive care", "early screening", "vaccination"],
    "lifestyle_factor": ["diet", "exercise", "stress", "sleep quality"],
    "health_outcome": ["longevity", "quality of life", "disease risk"],
    "architecture": ["microservices", "monolithic", "event-driven", "serverless"],
    "factor": ["latency", "scalability", "cost", "security"],
    "system_performance": ["throughput", "response time", "resource utilization"],
    "option1": ["cloud deployment", "on-premise", "hybrid approach"],
    "option2": ["serverless", "containerized", "virtual machines"],
    "use_case": ["high-throughput pipelines", "real-time processing", "batch jobs"],
    "approach": ["synchronous", "asynchronous", "event-driven", "batch processing"],
    "outcome": ["user satisfaction", "system reliability", "cost efficiency"],
    "variable1": ["CPU cores", "memory size", "network bandwidth"],
    "variable2": ["throughput", "latency", "resource usage"],
    "global_event": ["pandemic", "geopolitical tension", "climate change"],
    "emerging_market": ["cryptocurrency", "ESG investing", "fintech"],
    "financial_topic": ["digital currencies", "decentralized finance"],
    "disease_category": ["autoimmune diseases", "neurodegenerative disorders"],
    "medical_innovation": ["gene therapy", "personalized medicine", "AI diagnosis"],
    "research_area": ["cancer immunology", "regenerative medicine", "neuroscience"],
    "tech_domain": ["edge computing", "quantum computing", "neuromorphic chips"],
    "new_technology": ["blockchain", "federated learning", "synthetic biology"],
    "domain": ["healthcare", "finance", "manufacturing", "education"],
    "technology_area": ["AI/ML", "IoT", "robotics", "biotech"],
    "field": ["education", "transportation", "agriculture", "entertainment"],
}

DOCUMENT_TEMPLATES = {
    "finance": [
        "{company} reported {metric} of {value} in Q{quarter}, {trend} compared to last quarter. "
        "The {sector} sector shows {pattern} with average {indicator} at {number}%. "
        "Analysts forecast {prediction} for the upcoming quarter based on {factor}.",
        "Market analysis: {market} experienced {movement} with volume reaching {volume} shares. "
        "{economic_indicator} data suggests {implication}. Investment strategies focusing on "
        "{strategy} have shown {performance} returns over {timeframe}.",
        "Financial advisory: {term} plays a crucial role in portfolio management. "
        "Understanding the relationship between {term1} and {term2} helps investors "
        "make informed decisions. Current market conditions favor {approach} strategies.",
    ],
    "healthcare": [
        "Clinical study: {disease} patients treated with {treatment} showed {outcome}. "
        "The {medical_term} response was measured across {sample_size} participants. "
        "Side effects of {drug} included {effects}, with {percentage}% experiencing mild symptoms.",
        "{treatment1} vs {treatment2} comparison for {condition}: effectiveness rates of "
        "{rate1}% and {rate2}% respectively. Patient outcomes measured by {metric} showed "
        "{finding}. Healthcare providers recommend {recommendation} based on {criteria}.",
        "Research findings: {lifestyle_factor} significantly impacts {health_outcome}. "
        "Studies show that {intervention} can reduce risk by {percentage}%. "
        "Current guidelines suggest {recommendation} for optimal health maintenance.",
    ],
    "technology": [
        "{technology} architecture: Key features include {feature1}, {feature2}, and {feature3}. "
        "Performance benchmarks show {metric} improvements of {percentage}% compared to {tech2}. "
        "System requirements: {requirement1}, {requirement2}, compatible with {platform}.",
        "Technical comparison: {tech1} offers {advantage1} while {tech2} provides {advantage2}. "
        "For {use_case}, the recommended approach is {recommendation}. "
        "Implementation considerations include {factor1}, {factor2}, and {factor3}.",
        "Best practices: When configuring {system}, consider {consideration1} and {consideration2}. "
        "Common issues include {issue}, which can be resolved by {solution}. "
        "Performance tuning involves adjusting {parameter} based on {workload}.",
    ],
    "general": [
        "{concept} definition: {explanation}. Key characteristics include {char1}, {char2}, "
        "and {char3}. Applications span across {domain1}, {domain2}, and {domain3}. "
        "Benefits include {benefit1} and {benefit2}.",
        "Comprehensive guide: {topic} encompasses {aspect1}, {aspect2}, and {aspect3}. "
        "Historical context: {history}. Current trends show {trend}. "
        "Future outlook suggests {prediction}.",
        "Practical advice: To achieve {goal}, follow these steps: {step1}, {step2}, {step3}. "
        "Common pitfalls include {pitfall1} and {pitfall2}. "
        "Success factors: {factor1}, {factor2}, and {factor3}.",
    ],
}

# 文档填充词典
DOC_PLACEHOLDER_VALUES = {
    **PLACEHOLDER_VALUES,  # 继承查询的占位符
    "value": ["$2.5B", "15.2%", "3.8M units", "89 points"],
    "quarter": ["1", "2", "3", "4"],
    "trend": ["increasing", "decreasing", "stabilizing", "fluctuating"],
    "pattern": ["strong growth", "moderate decline", "high volatility"],
    "indicator": ["growth rate", "profit margin", "market share"],
    "number": ["12.5", "8.3", "15.7", "6.9"],
    "prediction": ["continued growth", "market consolidation", "increased volatility"],
    "movement": ["upward trend", "correction", "consolidation", "volatility spike"],
    "volume": ["1.2B", "850M", "2.3B"],
    "implication": ["economic recovery", "market uncertainty", "sector rotation"],
    "strategy": ["value investing", "growth stocks", "dividend yield"],
    "performance": ["above-average", "steady", "exceptional"],
    "timeframe": ["6 months", "1 year", "2 years"],
    "outcome": ["positive response", "significant improvement", "mixed results"],
    "sample_size": ["500", "1,200", "2,500"],
    "effects": ["nausea, dizziness", "fatigue, headache", "mild discomfort"],
    "percentage": ["15", "23", "8", "42"],
    "rate1": ["78", "85", "92"],
    "rate2": ["68", "82", "89"],
    "finding": ["significant improvement", "comparable efficacy", "better tolerability"],
    "criteria": ["patient history", "risk factors", "clinical guidelines"],
    "intervention": ["regular exercise", "dietary changes", "stress management"],
    "recommendation": ["annual screening", "lifestyle modification", "consultation"],
    "feature1": ["scalability", "fault tolerance", "low latency"],
    "feature2": ["high throughput", "easy integration", "resource efficiency"],
    "feature3": ["built-in monitoring", "auto-scaling", "security features"],
    "requirement1": ["Python 3.10+", "8GB RAM", "4 CPU cores"],
    "requirement2": ["Linux/macOS", "Docker support", "network connectivity"],
    "platform": ["Ubuntu 22.04", "Docker", "Kubernetes"],
    "advantage1": ["better performance", "easier setup", "lower cost"],
    "advantage2": ["more features", "better scalability", "wider compatibility"],
    "consideration1": ["resource limits", "network topology", "security policies"],
    "consideration2": ["performance requirements", "cost constraints", "team expertise"],
    "factor1": ["workload characteristics", "resource availability"],
    "factor2": ["latency requirements", "throughput targets"],
    "factor3": ["cost optimization", "maintenance overhead"],
    "issue": ["connection timeout", "memory leak", "performance degradation"],
    "solution": ["adjusting timeout values", "implementing caching", "tuning parameters"],
    "parameter": ["batch size", "parallelism", "buffer size"],
    "workload": ["read-heavy", "write-intensive", "mixed patterns"],
    "explanation": ["a systematic approach", "an organized framework", "a structured method"],
    "char1": ["modularity", "flexibility", "robustness"],
    "char2": ["efficiency", "reliability", "maintainability"],
    "char3": ["scalability", "security", "usability"],
    "domain1": ["healthcare", "finance", "education"],
    "domain2": ["manufacturing", "retail", "logistics"],
    "domain3": ["entertainment", "telecommunications", "energy"],
    "benefit1": ["improved efficiency", "reduced costs", "enhanced quality"],
    "benefit2": ["faster development", "better scalability", "increased reliability"],
    "aspect1": ["theoretical foundations", "practical applications"],
    "aspect2": ["implementation strategies", "performance optimization"],
    "aspect3": ["best practices", "common pitfalls"],
    "history": ["originated in the 1990s", "evolved from earlier concepts"],
    "goal": ["optimal performance", "maximum efficiency", "best results"],
    "step1": ["initial assessment", "requirements gathering"],
    "step2": ["implementation planning", "resource allocation"],
    "step3": ["execution and monitoring", "continuous improvement"],
    "pitfall1": ["over-engineering", "premature optimization"],
    "pitfall2": ["insufficient testing", "poor documentation"],
}


class Workload4QuerySource(SourceFunction):
    """
    Workload 4 查询源。

    特点:
    - 以配置的 QPS 生成查询
    - 查询类型和类别多样化
    - 支持合成查询(基于模板)
    - 自动轮转类型和类别以保证分布

    Args:
        num_tasks: 总任务数(查询数)
        qps: 生成速率(queries per second)
        query_types: 查询类型列表(默认全部三种)
        categories: 类别列表(默认全部四种)
        query_type_distribution: 查询类型分布比例
        category_distribution: 类别分布比例
        seed: 随机种子(用于可复现性)
    """

    def __init__(
        self,
        num_tasks: int,
        qps: float,
        query_types: list[str] | None = None,
        categories: list[str] | None = None,
        query_type_distribution: dict[str, float] | None = None,
        category_distribution: dict[str, float] | None = None,
        seed: int = 42,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_tasks = num_tasks
        self.qps = qps

        # ctx 还未设置，logger 不可用 - 在第一次 execute() 时记录
        self._initialization_logged = False

        self.query_types = query_types or ["factual", "analytical", "exploratory"]
        self.categories = categories or ["finance", "healthcare", "technology", "general"]

        # 默认分布
        self.query_type_dist = query_type_distribution or {
            "factual": 0.4,
            "analytical": 0.35,
            "exploratory": 0.25,
        }
        self.category_dist = category_distribution or {
            "finance": 0.30,
            "healthcare": 0.25,
            "technology": 0.25,
            "general": 0.20,
        }

        self.seed = seed
        self.rng = random.Random(seed)

        # 计算间隔时间
        self.interval = 1.0 / qps if qps > 0 else 0.0

        # 任务计数
        self.task_count = 0

    def _fill_template(self, template: str) -> str:
        """填充模板占位符"""
        result = template
        for placeholder, values in PLACEHOLDER_VALUES.items():
            if "{" + placeholder + "}" in result:
                value = self.rng.choice(values)
                result = result.replace("{" + placeholder + "}", value)
        return result

    def _generate_query(self, query_id: str, timestamp: float) -> QueryEvent:
        """生成单个查询事件"""
        # 根据分布选择类型和类别
        query_type = self.rng.choices(
            list(self.query_type_dist.keys()), weights=list(self.query_type_dist.values()), k=1
        )[0]

        category = self.rng.choices(
            list(self.category_dist.keys()), weights=list(self.category_dist.values()), k=1
        )[0]

        # 选择模板并填充
        template = self.rng.choice(QUERY_TEMPLATES[query_type][category])
        query_text = self._fill_template(template)
        self.logger.info(f"[TEMPLATE] Generated query template: {template}")
        return QueryEvent(
            query_id=query_id,
            query_text=query_text,
            query_type=query_type,
            category=category,
            timestamp=timestamp,
            embedding=None,  # 将由 EmbeddingPrecompute 填充
        )

    def execute(self, data=None) -> QueryEvent | StopSignal:
        """
        生成单个查询事件。

        每次调用返回一个 QueryEvent，直到达到 num_tasks 后返回 StopSignal。
        使用速率控制确保符合目标 QPS。

        Returns:
            QueryEvent if task_count < num_tasks, else StopSignal
        """
        # DEBUG: 第一次执行时记录初始化信息
        if not self._initialization_logged:
            self.logger.info(
                f"[INIT] Workload4QuerySource initialized with num_tasks={self.num_tasks}, qps={self.qps}"
            )
            self._initialization_logged = True

        # DEBUG: Log EVERY execution
        self.logger.info(
            f"[EXEC] Workload4QuerySource.execute() called: task_count={self.task_count}, num_tasks={self.num_tasks}"
        )

        # 检查是否已完成
        if self.task_count >= self.num_tasks:
            self.logger.info(
                f"[STOP] Workload4QuerySource completed - generated {self.task_count}/{self.num_tasks} queries"
            )
            return StopSignal(f"Query source completed: {self.task_count} queries generated")

        # 初始化启动时间(第一次调用时)
        if not hasattr(self, "_start_time"):
            self._start_time = time.time()

        # 控制生成速率(避免过快)
        if self.interval > 0:
            elapsed = time.time() - self._start_time
            expected_count = int(elapsed * self.qps)

            # 如果生成太快，等待一下
            if self.task_count >= expected_count:
                wait_time = (self.task_count + 1) / self.qps - elapsed
                if wait_time > 0:
                    time.sleep(min(wait_time, 0.01))  # 最多等待10ms

        # 生成查询
        query_id = f"q_{self.task_count:06d}"
        timestamp = time.time()
        query = self._generate_query(query_id, timestamp)

        self.task_count += 1
        self.logger.info(f"[GEN] Generated query {self.task_count}/{self.num_tasks}: {query_id}")
        return query


class Workload4DocumentSource(SourceFunction):
    """
    Workload 4 文档源。

    特点:
    - 以配置的 QPS 生成文档事件
    - 文档类别与查询类别对齐
    - 支持从知识库采样或合成生成
    - 文档内容丰富，适合语义匹配

    Args:
        num_docs: 总文档数
        qps: 生成速率(documents per second)
        categories: 类别列表(默认全部四种)
        category_distribution: 类别分布比例
        knowledge_base: 外部知识库(可选)
        seed: 随机种子
    """

    def __init__(
        self,
        num_docs: int,
        qps: float,
        categories: list[str] | None = None,
        category_distribution: dict[str, float] | None = None,
        knowledge_base: list[dict[str, Any]] | None = None,
        seed: int = 42,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_docs = num_docs
        self.qps = qps

        # ctx 还未设置，logger 不可用 - 在第一次 execute() 时记录
        self._initialization_logged = False

        self.categories = categories or ["finance", "healthcare", "technology", "general"]

        # 默认分布
        self.category_dist = category_distribution or {
            "finance": 0.30,
            "healthcare": 0.25,
            "technology": 0.25,
            "general": 0.20,
        }

        self.knowledge_base = knowledge_base
        self.seed = seed
        self.rng = random.Random(seed)

        # 计算间隔时间
        self.interval = 1.0 / qps if qps > 0 else 0.0

        # 文档计数
        self.doc_count = 0

    def _fill_doc_template(self, template: str) -> str:
        """填充文档模板占位符"""
        result = template
        for placeholder, values in DOC_PLACEHOLDER_VALUES.items():
            if "{" + placeholder + "}" in result:
                value = self.rng.choice(values)
                result = result.replace("{" + placeholder + "}", value)
        return result

    def _generate_document(self, doc_id: str, timestamp: float) -> DocumentEvent:
        """生成单个文档事件"""
        # 根据分布选择类别
        category = self.rng.choices(
            list(self.category_dist.keys()), weights=list(self.category_dist.values()), k=1
        )[0]

        # 如果有知识库，优先从知识库采样
        if self.knowledge_base:
            kb_item = self.rng.choice(self.knowledge_base)
            doc_text = kb_item.get("content", "")
            metadata = {
                "title": kb_item.get("title", ""),
                "source": "knowledge_base",
            }
        else:
            # 否则使用模板生成
            template = self.rng.choice(DOCUMENT_TEMPLATES[category])
            doc_text = self._fill_doc_template(template)
            metadata = {"source": "synthetic"}

        return DocumentEvent(
            doc_id=doc_id,
            doc_text=doc_text,
            doc_category=category,
            timestamp=timestamp,
            embedding=None,  # 将由 EmbeddingPrecompute 填充
            metadata=metadata,
        )

    def execute(self, data=None) -> DocumentEvent | StopSignal:
        """
        生成单个文档事件。

        每次调用返回一个 DocumentEvent，直到达到 num_docs 后返回 StopSignal。
        使用速率控制确保符合目标 QPS。

        Returns:
            DocumentEvent if doc_count < num_docs, else StopSignal
        """
        # DEBUG: 第一次执行时记录初始化信息
        if not self._initialization_logged:
            self.logger.info(
                f"[INIT] Workload4DocumentSource initialized with num_docs={self.num_docs}, qps={self.qps}"
            )
            self._initialization_logged = True

        # DEBUG: Log EVERY execution
        self.logger.info(
            f"[EXEC] Workload4DocumentSource.execute() called: doc_count={self.doc_count}, num_docs={self.num_docs}"
        )

        # 检查是否已完成
        if self.doc_count >= self.num_docs:
            self.logger.info(
                f"[STOP] Workload4DocumentSource completed - generated {self.doc_count}/{self.num_docs} documents"
            )
            return StopSignal(f"Document source completed: {self.doc_count} documents generated")

        # 初始化启动时间(第一次调用时)
        if not hasattr(self, "_start_time"):
            self._start_time = time.time()
        self.logger.info(f"Generating document {self.doc_count + 1}/{self.num_docs}")
        # 控制生成速率
        if self.interval > 0:
            elapsed = time.time() - self._start_time
            expected_count = int(elapsed * self.qps)

            # 如果生成太快，等待一下
            if self.doc_count >= expected_count:
                wait_time = (self.doc_count + 1) / self.qps - elapsed
                if wait_time > 0:
                    time.sleep(min(wait_time, 0.01))  # 最多等待10ms

        # 生成文档
        doc_id = f"d_{self.doc_count:06d}"
        timestamp = time.time()
        doc = self._generate_document(doc_id, timestamp)

        self.doc_count += 1
        self.logger.info(f"[GEN] Generated document {self.doc_count}/{self.num_docs}: {doc_id}")
        return doc


class EmbeddingPrecompute(MapFunction):
    """
    为 Query 和 Document 预计算 Embedding。

    特点:
    - 支持批量调用优化性能
    - 自动处理 QueryEvent 和 DocumentEvent 两种类型
    - 使用 OpenAI 兼容的 Embedding API
    - 支持重试和错误处理

    Args:
        embedding_base_url: Embedding 服务地址
        embedding_model: 模型名称
        batch_size: 批量大小(用于优化)
        timeout: 请求超时时间(秒)
        max_retries: 最大重试次数
    """

    def __init__(
        self,
        embedding_base_url: str = "http://11.11.11.7:8090/v1",
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        batch_size: int = 32,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries

        # 批量缓存(当前实现为单次处理，未来可优化为真正的批量)
        self._batch_cache: list[tuple[Any, str]] = []

    def _call_embedding_api(self, texts: list[str]) -> list[list[float]]:
        """
        调用 Embedding API(OpenAI 兼容)。

        Args:
            texts: 文本列表

        Returns:
            embedding 列表
        """
        import requests

        url = f"{self.embedding_base_url}/embeddings"
        payload = {
            "input": texts,
            "model": self.embedding_model,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings

            except Exception as e:
                if attempt == self.max_retries - 1:
                    # 最后一次重试失败，抛出异常
                    raise RuntimeError(
                        f"Embedding API call failed after {self.max_retries} attempts: {e}"
                    ) from e
                # 重试前短暂等待
                time.sleep(0.5 * (attempt + 1))

        return []

    def execute(self, data: QueryEvent | DocumentEvent) -> QueryEvent | DocumentEvent:
        """
        为 Query 或 Document 预计算 Embedding。

        Args:
            data: QueryEvent 或 DocumentEvent

        Returns:
            带有 embedding 的事件
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(data, StopSignal):
            return data

        # 提取文本
        if isinstance(data, QueryEvent):
            text = data.query_text
        elif isinstance(data, DocumentEvent):
            text = data.doc_text
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")

        # 调用 API(单个文本)
        # 注意：这里可以优化为批量调用，但需要复杂的批处理逻辑
        try:
            embeddings = self._call_embedding_api([text])
            if embeddings:
                data.embedding = embeddings[0]
            else:
                # API 返回空，使用零向量占位
                data.embedding = [0.0] * 1024  # 假设 1024 维
        except Exception as e:
            # 错误处理：记录错误但不中断流
            print(f"Warning: Embedding computation failed for {data}: {e}")
            data.embedding = [0.0] * 1024  # 零向量占位

        return data


# === 批量 Embedding 优化版本(可选)===


class BatchedEmbeddingPrecompute(MapFunction):
    """
    批量 Embedding 预计算算子(优化版本)。

    注意：这个版本需要配合 batch() 算子使用，或者实现内部缓冲。
    当前 SAGE 的 MapFunction 是逐个处理，真正的批量需要更复杂的状态管理。

    这里仅作为演示，实际使用建议用单个版本配合上游的 batch 算子。
    """

    def __init__(
        self,
        embedding_base_url: str = "http://11.11.11.7:8090/v1",
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        batch_size: int = 32,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries

        # 内部缓冲
        self._buffer: list[QueryEvent | DocumentEvent] = []

    def _call_embedding_api(self, texts: list[str]) -> list[list[float]]:
        """调用 Embedding API(同上)"""
        import requests

        url = f"{self.embedding_base_url}/embeddings"
        payload = {
            "input": texts,
            "model": self.embedding_model,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Embedding API call failed after {self.max_retries} attempts: {e}"
                    ) from e
                time.sleep(0.5 * (attempt + 1))

        return []

    def _flush_buffer(self) -> list[QueryEvent | DocumentEvent]:
        """刷新缓冲区，批量计算 embedding"""
        if not self._buffer:
            return []

        # 提取文本
        texts = []
        for item in self._buffer:
            if isinstance(item, QueryEvent):
                texts.append(item.query_text)
            elif isinstance(item, DocumentEvent):
                texts.append(item.doc_text)

        # 批量调用 API
        try:
            embeddings = self._call_embedding_api(texts)
            for item, emb in zip(self._buffer, embeddings):
                item.embedding = emb
        except Exception as e:
            print(f"Warning: Batch embedding failed: {e}")
            # 使用零向量占位
            for item in self._buffer:
                item.embedding = [0.0] * 1024

        # 清空缓冲并返回
        result = self._buffer[:]
        self._buffer = []
        return result

    def execute(self, data: QueryEvent | DocumentEvent) -> QueryEvent | DocumentEvent:
        """
        添加到缓冲区，达到 batch_size 时批量处理。

        注意：这个实现有局限性，因为 MapFunction 的 execute 只能返回单个值。
        真正的批量需要使用 BatchFunction 或者 FlatMapFunction。

        当前实现：仅演示逻辑，实际使用建议用单个版本。
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(data, StopSignal):
            return data
        self._buffer.append(data)

        if len(self._buffer) >= self.batch_size:
            # 刷新缓冲
            processed = self._flush_buffer()
            # 只返回当前这个(其他的会丢失，这是局限)
            # 实际应该用 FlatMapFunction
            return data
        else:
            # 缓冲未满，返回当前(embedding 尚未填充)
            return data

    def close(self) -> None:
        """关闭时刷新剩余缓冲"""
        if self._buffer:
            self._flush_buffer()
        super().close()


# === 工具函数 ===


def create_query_source(config: dict[str, Any]) -> Workload4QuerySource:
    """
    根据配置创建查询源。

    Args:
        config: 配置字典，应包含：
            - num_tasks
            - query_qps
            - query_type_distribution (可选)
            - category_distribution (可选)
            - seed (可选)

    Returns:
        Workload4QuerySource 实例
    """
    return Workload4QuerySource(
        num_tasks=config.get("num_tasks", 100),
        qps=config.get("query_qps", 40.0),
        query_type_distribution=config.get("query_type_distribution"),
        category_distribution=config.get("category_distribution"),
        seed=config.get("seed", 42),
    )


def create_document_source(config: dict[str, Any]) -> Workload4DocumentSource:
    """
    根据配置创建文档源。

    Args:
        config: 配置字典，应包含：
            - num_docs (或根据 num_tasks 和 doc_qps 计算)
            - doc_qps
            - category_distribution (可选)
            - knowledge_base (可选)
            - seed (可选)

    Returns:
        Workload4DocumentSource 实例
    """
    # 计算文档数量：基于持续时间和 QPS
    num_tasks = config.get("num_tasks", 100)
    query_qps = config.get("query_qps", 40.0)
    doc_qps = config.get("doc_qps", 25.0)
    duration = num_tasks / query_qps if query_qps > 0 else 0
    num_docs = int(duration * doc_qps)

    return Workload4DocumentSource(
        num_docs=config.get("num_docs", num_docs),
        qps=doc_qps,
        category_distribution=config.get("category_distribution"),
        knowledge_base=config.get("knowledge_base"),
        seed=config.get("seed", 42),
    )


def create_embedding_precompute(config: dict[str, Any]) -> EmbeddingPrecompute:
    """
    根据配置创建 Embedding 预计算算子。

    Args:
        config: 配置字典，应包含：
            - embedding_base_url
            - embedding_model
            - embedding_batch_size (可选)
            - embedding_timeout (可选)

    Returns:
        EmbeddingPrecompute 实例
    """
    return EmbeddingPrecompute(
        embedding_base_url=config.get("embedding_base_url", "http://11.11.11.7:8090/v1"),
        embedding_model=config.get("embedding_model", "BAAI/bge-large-en-v1.5"),
        batch_size=config.get("embedding_batch_size", 32),
        timeout=config.get("embedding_timeout", 30.0),
    )
