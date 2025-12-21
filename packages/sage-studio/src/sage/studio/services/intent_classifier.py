"""Intent Classifier for SAGE Studio Multi-Agent.

This module provides intent classification for the SAGE Studio chat interface,
determining user intent to route messages to appropriate agents.

Layer: L6 (sage-studio)
Dependencies: None (pure data structures in this file)

Design Notes:
    User intents are simplified to 4 categories:
    - KNOWLEDGE_QUERY: Any question requiring knowledge base retrieval
    - SAGE_CODING: SAGE framework programming tasks
    - SYSTEM_OPERATION: System management operations
    - GENERAL_CHAT: General conversation

    Key Innovation:
    INTENT_TOOLS models intents as "pseudo-tools" to reuse the sage-libs
    Tool Selection framework (KeywordSelector, EmbeddingSelector, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.libs.agentic.agents.action.tool_selection import ToolPrediction


class UserIntent(Enum):
    """User intent types.

    Simplified to 4 core intent categories:

    - KNOWLEDGE_QUERY: Questions requiring knowledge base search, including:
        - SAGE documentation questions
        - Research methodology guidance
        - User uploaded materials
    - SAGE_CODING: SAGE framework programming tasks, including:
        - Pipeline generation
        - Code debugging
        - API explanation
    - SYSTEM_OPERATION: System management operations, including:
        - Starting/stopping services
        - Checking status
        - Managing knowledge bases
    - GENERAL_CHAT: General conversation and greetings

    Examples:
        >>> intent = UserIntent.KNOWLEDGE_QUERY
        >>> intent.value
        'knowledge_query'
    """

    KNOWLEDGE_QUERY = "knowledge_query"
    SAGE_CODING = "sage_coding"
    SYSTEM_OPERATION = "system_operation"
    GENERAL_CHAT = "general_chat"


class KnowledgeDomain(Enum):
    """Knowledge domain categories.

    Used with KNOWLEDGE_QUERY intent to specify which knowledge sources
    should be searched.

    Domains:
        - SAGE_DOCS: Official SAGE framework documentation
        - EXAMPLES: Code examples and tutorials
        - RESEARCH_GUIDANCE: Research methodology and writing experience
          (mentor's guidance documents)
        - USER_UPLOADS: User uploaded materials and documents

    Examples:
        >>> domain = KnowledgeDomain.SAGE_DOCS
        >>> domain.value
        'sage_docs'
    """

    SAGE_DOCS = "sage_docs"
    EXAMPLES = "examples"
    RESEARCH_GUIDANCE = "research_guidance"
    USER_UPLOADS = "user_uploads"


@dataclass
class IntentResult:
    """Intent classification result.

    Contains the classified intent, confidence score, and additional metadata
    for routing user messages to appropriate handlers.

    Attributes:
        intent: The identified user intent type.
        confidence: Confidence score between 0 and 1.
        knowledge_domains: Relevant knowledge domains to search.
            Only applicable when intent is KNOWLEDGE_QUERY.
        matched_keywords: List of keywords that matched during classification.
        raw_prediction: Raw prediction result for debugging purposes.

    Examples:
        >>> result = IntentResult(
        ...     intent=UserIntent.KNOWLEDGE_QUERY,
        ...     confidence=0.85,
        ...     knowledge_domains=[KnowledgeDomain.SAGE_DOCS],
        ...     matched_keywords=["怎么", "安装"],
        ... )
        >>> result.should_search_knowledge()
        True
        >>> result.get_search_sources()
        ['sage_docs']
    """

    intent: UserIntent
    confidence: float
    knowledge_domains: list[KnowledgeDomain] | None = None
    matched_keywords: list[str] = field(default_factory=list)
    raw_prediction: ToolPrediction | None = None

    def __post_init__(self) -> None:
        """Validate confidence score is within valid range."""
        if not 0 <= self.confidence <= 1:
            msg = f"Confidence must be between 0 and 1, got {self.confidence}"
            raise ValueError(msg)

    def should_search_knowledge(self) -> bool:
        """Check if knowledge base search is needed.

        Returns:
            True if the intent requires knowledge base retrieval.
        """
        return self.intent == UserIntent.KNOWLEDGE_QUERY

    def get_search_sources(self) -> list[str]:
        """Get the list of knowledge sources to search.

        Returns:
            List of knowledge source identifiers. Returns default sources
            (sage_docs, examples) if no specific domains are specified.
        """
        if not self.knowledge_domains:
            # Default knowledge sources when none specified
            return ["sage_docs", "examples"]
        return [d.value for d in self.knowledge_domains]

    @property
    def suggested_sources(self) -> list[str]:
        """Alias for get_search_sources() for Task 3 compatibility.

        Returns:
            List of knowledge source identifiers to search.
        """
        return self.get_search_sources()

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if the classification has high confidence.

        Args:
            threshold: Confidence threshold (default: 0.7).

        Returns:
            True if confidence exceeds the threshold.
        """
        return self.confidence >= threshold


# Intent display names for UI
INTENT_DISPLAY_NAMES: dict[UserIntent, str] = {
    UserIntent.KNOWLEDGE_QUERY: "知识问答",
    UserIntent.SAGE_CODING: "编程助手",
    UserIntent.SYSTEM_OPERATION: "系统操作",
    UserIntent.GENERAL_CHAT: "普通对话",
}

# Knowledge domain display names for UI
DOMAIN_DISPLAY_NAMES: dict[KnowledgeDomain, str] = {
    KnowledgeDomain.SAGE_DOCS: "SAGE 文档",
    KnowledgeDomain.EXAMPLES: "代码示例",
    KnowledgeDomain.RESEARCH_GUIDANCE: "研究指导",
    KnowledgeDomain.USER_UPLOADS: "用户资料",
}


def get_intent_display_name(intent: UserIntent) -> str:
    """Get the display name for an intent.

    Args:
        intent: The user intent.

    Returns:
        Human-readable display name in Chinese.
    """
    return INTENT_DISPLAY_NAMES.get(intent, intent.value)


def get_domain_display_name(domain: KnowledgeDomain) -> str:
    """Get the display name for a knowledge domain.

    Args:
        domain: The knowledge domain.

    Returns:
        Human-readable display name in Chinese.
    """
    return DOMAIN_DISPLAY_NAMES.get(domain, domain.value)


# =============================================================================
# Intent Pseudo-Tools for Tool Selection Framework
# =============================================================================
#
# Key Design: Model intents as "pseudo-tools" to reuse sage-libs Tool Selection
# algorithms (KeywordSelector, EmbeddingSelector, HybridSelector, etc.).
#
# Each intent is represented as a tool-like object with:
# - tool_id: Maps to UserIntent enum value
# - name: Human-readable name
# - description: Detailed description for embedding-based matching
# - keywords: Keywords for keyword-based matching
# - capabilities: Additional capability tags
# =============================================================================


@dataclass
class IntentTool:
    """Pseudo-tool representation of user intent.

    This dataclass models an intent as a "tool" to reuse the sage-libs
    Tool Selection framework. The structure mimics the tool metadata
    expected by KeywordSelector and EmbeddingSelector.

    Attributes:
        tool_id: Unique identifier matching UserIntent enum value.
        name: Human-readable name for the intent.
        description: Detailed description of the intent, used for
            embedding-based semantic matching.
        keywords: List of keywords for keyword-based matching.
            Should include both Chinese and English terms.
        capabilities: Additional capability tags for matching.
        knowledge_domains: Relevant knowledge domains for KNOWLEDGE_QUERY.
        category: Always "intent" for intent pseudo-tools.

    Example:
        >>> tool = IntentTool(
        ...     tool_id="knowledge_query",
        ...     name="Knowledge Query",
        ...     description="Questions about SAGE documentation...",
        ...     keywords=["怎么", "如何", "what is", "how to"],
        ... )
        >>> tool.tool_id
        'knowledge_query'
    """

    tool_id: str
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    knowledge_domains: list[str] = field(default_factory=list)
    category: str = "intent"


# Intent pseudo-tools for Tool Selection framework
INTENT_TOOLS: list[IntentTool] = [
    # -------------------------------------------------------------------------
    # KNOWLEDGE_QUERY: Questions requiring knowledge base retrieval
    # -------------------------------------------------------------------------
    IntentTool(
        tool_id=UserIntent.KNOWLEDGE_QUERY.value,
        name="知识库查询 / Knowledge Query",
        description="""
        处理需要知识库检索的问题，包括：
        - SAGE 框架文档问答：怎么使用 Operator、Pipeline 是什么、API 说明
        - 研究方法论指导：导师上传的研究经验、写作方法、学术规范
        - 用户上传资料查询：PDF、文档、代码文件内容检索
        - 代码示例和教程：如何实现某功能、示例代码在哪里

        Questions that require knowledge base retrieval, including:
        - SAGE documentation: How to use Operators, what is a Pipeline, API docs
        - Research methodology guidance: mentor's research experience, writing tips
        - User uploaded materials: PDF, documents, code file content search
        - Code examples and tutorials: how to implement features, where are examples
        """,
        keywords=[
            # SAGE-specific terms
            "SAGE",
            "operator",
            "pipeline",
            "kernel",
            "middleware",
            "文档",
            "documentation",
            "docs",
            "API",
            "接口",
            "配置",
            "config",
            "configuration",
            "RAG",
            "检索增强生成",
            # Actions/Topics (Specific to SAGE/Tech)
            "安装",
            "install",
            "installation",
            "部署",
            "deploy",
            "setup",
            "使用",
            "usage",
            "use",
            "教程",
            "tutorial",
            "guide",
            "指南",
            "示例",
            "example",
            "examples",
            "demo",
            # Research guidance
            "论文",
            "paper",
            "研究",
            "research",
            "方法论",
            "methodology",
            "写作",
            "writing",
            "投稿",
            "submission",
        ],
        capabilities=[
            "documentation_search",
            "example_retrieval",
            "api_lookup",
            "research_guidance",
            "user_content_search",
        ],
        knowledge_domains=[
            KnowledgeDomain.SAGE_DOCS.value,
            KnowledgeDomain.EXAMPLES.value,
            KnowledgeDomain.RESEARCH_GUIDANCE.value,
            KnowledgeDomain.USER_UPLOADS.value,
        ],
    ),
    # -------------------------------------------------------------------------
    # SAGE_CODING: SAGE framework programming assistance
    # -------------------------------------------------------------------------
    IntentTool(
        tool_id=UserIntent.SAGE_CODING.value,
        name="SAGE 编程助手 / SAGE Coding Assistant",
        description="""
        处理 SAGE 框架相关的编程任务，包括：
        - Pipeline 生成：创建数据处理流水线、RAG 系统、问答系统
        - 代码调试：分析错误、修复 bug、解释异常信息
        - 代码编写：实现 Operator、编写节点、创建工作流
        - API 使用：调用 SAGE API、组合组件、配置服务

        SAGE framework programming tasks, including:
        - Pipeline generation: create data processing pipelines, RAG systems, QA systems
        - Code debugging: analyze errors, fix bugs, explain exceptions
        - Code writing: implement Operators, write nodes, create workflows
        - API usage: call SAGE APIs, compose components, configure services
        """,
        keywords=[
            # Pipeline generation
            "创建",
            "生成",
            "搭建",
            "构建",
            "设计",
            "create",
            "build",
            "generate",
            "design",
            "implement",
            "实现",
            "开发",
            "develop",
            # Pipeline-specific
            "pipeline",
            "流水线",
            "工作流",
            "workflow",
            "DAG",
            "拓扑",
            "topology",
            "节点",
            "node",
            "RAG",
            "问答",
            "QA",
            # Code-related
            "代码",
            "code",
            "函数",
            "function",
            "类",
            "class",
            "方法",
            "method",
            "模块",
            "module",
            # Debugging
            "调试",
            "debug",
            "bug",
            "错误",
            "error",
            "异常",
            "exception",
            "报错",
            "失败",
            "failed",
            "fix",
            "修复",
            "解决",
            "solve",
            # Code actions
            "写一个",
            "帮我写",
            "实现一个",
            "write",
            "编写",
            "优化",
            "optimize",
            "重构",
            "refactor",
        ],
        capabilities=[
            "pipeline_generation",
            "code_debugging",
            "code_writing",
            "api_guidance",
            "workflow_design",
        ],
        knowledge_domains=[],
    ),
    # -------------------------------------------------------------------------
    # SYSTEM_OPERATION: System management operations
    # -------------------------------------------------------------------------
    IntentTool(
        tool_id=UserIntent.SYSTEM_OPERATION.value,
        name="系统操作 / System Operation",
        description="""
        处理系统管理和操作请求，包括：
        - 服务管理：启动/停止 LLM 服务、Gateway、Embedding 服务
        - 状态查看：检查服务状态、查看日志、监控资源
        - 配置管理：修改配置、设置参数、更新设置
        - 知识库管理：加载/卸载知识库、索引管理、更新文档

        System management and operation requests, including:
        - Service management: start/stop LLM service, Gateway, Embedding service
        - Status checking: check service status, view logs, monitor resources
        - Configuration: modify config, set parameters, update settings
        - Knowledge base management: load/unload KB, index management, update docs
        """,
        keywords=[
            # Service operations
            "启动",
            "start",
            "停止",
            "stop",
            "重启",
            "restart",
            "运行",
            "run",
            "关闭",
            "shutdown",
            "kill",
            # Status checking
            "状态",
            "status",
            "检查",
            "check",
            "查看",
            "view",
            "日志",
            "log",
            "logs",
            "监控",
            "monitor",
            # Service names
            "服务",
            "service",
            "LLM",
            "Gateway",
            "Embedding",
            "vLLM",
            "集群",
            "cluster",
            # Configuration
            "配置",
            "config",
            "configuration",
            "设置",
            "setting",
            "参数",
            "parameter",
            "修改",
            "modify",
            "更新",
            "update",
            # Knowledge base
            "知识库",
            "knowledge base",
            "索引",
            "index",
            "加载",
            "load",
            "卸载",
            "unload",
            "刷新",
            "refresh",
        ],
        capabilities=[
            "service_management",
            "status_checking",
            "configuration",
            "knowledge_base_management",
            "log_viewing",
        ],
        knowledge_domains=[],
    ),
    # -------------------------------------------------------------------------
    # GENERAL_CHAT: General conversation and greetings
    # -------------------------------------------------------------------------
    IntentTool(
        tool_id=UserIntent.GENERAL_CHAT.value,
        name="普通对话 / General Chat",
        description="""
        处理日常对话和闲聊，包括：
        - 问候语：你好、早上好、再见
        - 感谢和礼貌用语：谢谢、不客气、请
        - 闲聊：聊天、随便聊聊、无特定目的的对话
        - 帮助请求：你能做什么、帮助、help

        General conversation and casual chat, including:
        - Greetings: hello, good morning, goodbye
        - Politeness: thank you, you're welcome, please
        - Casual chat: chat, just talking, no specific purpose
        - Help requests: what can you do, help, assistance
        """,
        keywords=[
            # Greetings - Chinese
            "你好",
            "您好",
            "嗨",
            "哈喽",
            "早上好",
            "下午好",
            "晚上好",
            "早",
            "晚安",
            "再见",
            "拜拜",
            "回见",
            # Greetings - English
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "bye",
            "goodbye",
            "see you",
            "how are you",
            "how do you do",
            "what's up",
            # Politeness - Chinese
            "谢谢",
            "感谢",
            "多谢",
            "不客气",
            "没关系",
            "请",
            "麻烦",
            "抱歉",
            "对不起",
            "好的",
            "可以",
            "明白",
            "了解",
            # Politeness - English
            "thanks",
            "thank you",
            "please",
            "sorry",
            "okay",
            "ok",
            "sure",
            "got it",
            "understood",
            # Help requests
            "帮助",
            "help",
            "你能做什么",
            "what can you do",
            "你是谁",
            "who are you",
            "介绍自己",
            "introduce yourself",
            # Casual
            "聊聊",
            "聊天",
            "chat",
            "嗯",
            "哦",
            "啊",
            "是的",
            "对",
            "好",
        ],
        capabilities=[
            "greeting",
            "politeness",
            "casual_chat",
            "help_request",
            "self_introduction",
        ],
        knowledge_domains=[],
    ),
]


def get_intent_tool(intent: UserIntent) -> IntentTool | None:
    """Get the IntentTool for a given UserIntent.

    Args:
        intent: The user intent enum value.

    Returns:
        The corresponding IntentTool, or None if not found.

    Example:
        >>> tool = get_intent_tool(UserIntent.KNOWLEDGE_QUERY)
        >>> tool.name
        '知识库查询 / Knowledge Query'
    """
    for tool in INTENT_TOOLS:
        if tool.tool_id == intent.value:
            return tool
    return None


def get_all_intent_keywords() -> dict[str, list[str]]:
    """Get all keywords grouped by intent.

    Returns:
        Dictionary mapping intent ID to list of keywords.

    Example:
        >>> keywords = get_all_intent_keywords()
        >>> 'SAGE' in keywords['knowledge_query']
        True
    """
    return {tool.tool_id: tool.keywords for tool in INTENT_TOOLS}


class IntentToolsLoader:
    """Mock loader for INTENT_TOOLS to integrate with SelectorResources.

    This class provides the same interface as the tool loaders used in
    sage-libs Tool Selection framework, allowing INTENT_TOOLS to be
    used with KeywordSelector, EmbeddingSelector, etc.

    Example:
        >>> loader = IntentToolsLoader()
        >>> list(loader.iter_all())[0].tool_id
        'knowledge_query'
    """

    def __init__(self, tools: list[IntentTool] | None = None):
        """Initialize the loader with intent tools.

        Args:
            tools: List of IntentTool objects. Defaults to INTENT_TOOLS.
        """
        if tools is None:
            tools = INTENT_TOOLS
        self._tools = {tool.tool_id: tool for tool in tools}

    def get_tool(self, tool_id: str) -> IntentTool | None:
        """Get a tool by its ID.

        Args:
            tool_id: The tool identifier.

        Returns:
            The IntentTool if found, None otherwise.
        """
        return self._tools.get(tool_id)

    def get_all_tools(self) -> list[IntentTool]:
        """Get all tools as a list.

        Returns:
            List of all IntentTool objects.
        """
        return list(self._tools.values())

    def iter_all(self):
        """Iterate over all tools.

        Yields:
            IntentTool objects one by one.
        """
        yield from self._tools.values()

    def __len__(self) -> int:
        """Return the number of tools."""
        return len(self._tools)


__all__ = [
    # Enums
    "UserIntent",
    "KnowledgeDomain",
    # Data classes
    "IntentResult",
    "IntentTool",
    # Constants
    "INTENT_TOOLS",
    "INTENT_DISPLAY_NAMES",
    "DOMAIN_DISPLAY_NAMES",
    # Helper classes
    "IntentToolsLoader",
    "IntentClassifier",
    # Functions
    "get_intent_display_name",
    "get_domain_display_name",
    "get_intent_tool",
    "get_all_intent_keywords",
]


# =============================================================================
# IntentClassifier - Core Classification Logic
# =============================================================================


class IntentClassifier:
    """Intent classifier that reuses sage-libs Tool Selection framework.

    This classifier models user intents as "pseudo-tools" and leverages
    the existing KeywordSelector from sage-libs for intent classification.
    This approach allows us to reuse mature, well-tested algorithms.

    Supported modes:
        - "keyword": Fast keyword-based matching using TF-IDF
        - "embedding": Semantic matching using embeddings (requires embedding client)
        - "llm": Intelligent classification using LLM (requires LLM client)
        - "hybrid": Combination of keyword and embedding (future)

    Example:
        >>> classifier = IntentClassifier(mode="keyword")
        >>> result = await classifier.classify("怎么配置 SAGE 的 LLM 服务？")
        >>> result.intent
        UserIntent.KNOWLEDGE_QUERY
        >>> result.confidence
        0.85

    Note:
        The classifier gracefully falls back to GENERAL_CHAT with low
        confidence when classification fails or no clear intent is detected.
    """

    def __init__(
        self,
        mode: str = "keyword",
        embedding_model: str | None = None,
    ) -> None:
        """Initialize the intent classifier.

        Args:
            mode: Selector mode. Currently supports "keyword", "llm".
                "embedding" and "hybrid" require additional setup.
            embedding_model: Embedding model identifier for embedding-based
                modes. Ignored for "keyword" mode.

        Raises:
            ValueError: If an unsupported mode is specified.
        """
        self.mode = mode
        self.embedding_model = embedding_model
        self._selector = None
        self._initialized = False
        self._llm_client = None

        # Validate mode
        supported_modes = {"keyword", "embedding", "hybrid", "llm"}
        if mode not in supported_modes:
            msg = f"Unsupported mode: {mode}. Must be one of {supported_modes}"
            raise ValueError(msg)

        # For non-keyword modes, we need embedding client
        if mode in ("embedding", "hybrid") and embedding_model is None:
            # Default embedding model
            self.embedding_model = "BAAI/bge-m3"

        # Initialize selector lazily or eagerly based on mode
        if mode == "keyword":
            self._initialize_keyword_selector()
        elif mode == "llm":
            self._initialize_llm_client()

    def _initialize_llm_client(self) -> None:
        """Initialize the LLM client."""
        try:
            from sage.common.components.sage_llm import UnifiedInferenceClient
            from sage.common.config.ports import SagePorts

            # Explicitly connect to local Gateway to avoid accidental cloud fallback
            # The Gateway (port 8888) now supports /v1/models, so this is safe
            gateway_url = f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
            self._llm_client = UnifiedInferenceClient.create(control_plane_url=gateway_url)
            self._initialized = True
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to initialize LLM client: {e}. Falling back to simple keyword matching."
            )
            self.mode = "keyword"
            self._initialize_keyword_selector()

    def _initialize_keyword_selector(self) -> None:
        """Initialize the keyword-based selector."""
        try:
            from sage.libs.agentic.agents.action.tool_selection import (
                KeywordSelector,
                SelectorResources,
            )
            from sage.libs.agentic.agents.action.tool_selection.schemas import (
                KeywordSelectorConfig,
            )

            # Create tools loader with our intent tools
            tools_loader = IntentToolsLoader(INTENT_TOOLS)

            # Create resources
            resources = SelectorResources(
                tools_loader=tools_loader,
                embedding_client=None,
            )

            # Create config
            config = KeywordSelectorConfig(
                name="intent_keyword",
                top_k=1,  # We only need the best match
                min_score=0.0,
                method="tfidf",  # TF-IDF works well for short queries
                lowercase=True,
                remove_stopwords=False,  # Keep Chinese stopwords
                ngram_range=(1, 2),
            )

            # Create selector
            self._selector = KeywordSelector.from_config(config, resources)
            self._initialized = True

        except ImportError as e:
            # sage-libs not available, fall back to simple matching
            import logging

            logging.getLogger(__name__).warning(
                f"sage-libs Tool Selection not available: {e}. "
                "Falling back to simple keyword matching."
            )
            self._selector = None
            self._initialized = True

    async def classify(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> IntentResult:
        """Classify user intent from message.

        Args:
            message: User's input message.
            history: Optional conversation history for context.
                Each entry should have "role" and "content" keys.
            context: Optional additional context string.

        Returns:
            IntentResult containing the classified intent, confidence,
            and relevant metadata.

        Note:
            If classification fails, returns GENERAL_CHAT with low
            confidence as a safe fallback.
        """
        # Handle empty message
        if not message or not message.strip():
            return IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.3,
                matched_keywords=[],
            )

        # Use appropriate classification method
        if self.mode == "llm" and self._llm_client:
            return await self._classify_with_llm(message, history)
        elif self._selector is not None:
            return self._classify_with_selector(message, history, context)
        else:
            return self._classify_simple(message)

    async def _classify_with_llm(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> IntentResult:
        """Classify using LLM."""
        import asyncio

        prompt = f"""
You are an intent classifier for the SAGE AI framework.
Classify the user's message into one of the following intents:

1. knowledge_query: Questions requiring knowledge base search (SAGE docs, research papers, examples).
2. sage_coding: SAGE framework programming tasks (pipeline generation, debugging, API usage).
3. system_operation: System management (start/stop services, check status).
4. general_chat: General conversation, greetings, or questions not related to SAGE.

User Message: {message}

Return ONLY the intent name (e.g., "knowledge_query").
"""
        try:
            # Run synchronous LLM call in thread pool
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: self._llm_client.chat([{"role": "user", "content": prompt}])
            )

            # UnifiedInferenceClient.chat returns a string by default
            content = response.strip().lower()

            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"LLM Intent Classification Raw Response: '{content}'")

            # Normalize content to handle spaces vs underscores (e.g. "knowledge query" -> "knowledge_query")
            content_normalized = content.replace(" ", "_")

            # Extract intent
            for intent in UserIntent:
                # Check both original and normalized
                if intent.value in content or intent.value in content_normalized:
                    # Determine knowledge domains if needed
                    knowledge_domains = None
                    if intent == UserIntent.KNOWLEDGE_QUERY:
                        # Default domains for LLM classification
                        knowledge_domains = [KnowledgeDomain.SAGE_DOCS, KnowledgeDomain.EXAMPLES]

                    return IntentResult(
                        intent=intent,
                        confidence=0.9,  # High confidence for LLM
                        knowledge_domains=knowledge_domains,
                        matched_keywords=[],
                    )

            # Fallback if LLM output is unclear
            logger.warning(
                f"LLM output '{content}' did not match any known intent. Falling back to simple classification."
            )
            return self._classify_simple(message)

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"LLM classification failed: {e}")
            return self._classify_simple(message)

    def _classify_with_selector(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> IntentResult:
        """Classify using sage-libs selector."""
        from sage.libs.agentic.agents.action.tool_selection.schemas import (
            ToolSelectionQuery,
        )

        # Build query
        query = ToolSelectionQuery(
            sample_id="intent_classification",
            instruction=message,
            context={"history": history} if history else {},
            candidate_tools=[tool.tool_id for tool in INTENT_TOOLS],
        )

        # Execute selection
        predictions = self._selector.select(query, top_k=1)

        if not predictions:
            return IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.3,
                matched_keywords=[],
            )

        # Get top prediction
        top = predictions[0]

        # Map to UserIntent
        try:
            intent = UserIntent(top.tool_id)
        except ValueError:
            # Unknown intent, fallback
            return IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.3,
                matched_keywords=[],
            )

        # Get knowledge domains for KNOWLEDGE_QUERY
        knowledge_domains = None
        if intent == UserIntent.KNOWLEDGE_QUERY:
            tool = get_intent_tool(intent)
            if tool and tool.knowledge_domains:
                knowledge_domains = [KnowledgeDomain(d) for d in tool.knowledge_domains]

        return IntentResult(
            intent=intent,
            confidence=top.score,
            knowledge_domains=knowledge_domains,
            matched_keywords=top.metadata.get("matched_keywords", []),
            raw_prediction=top,
        )

    def _classify_simple(self, message: str) -> IntentResult:
        """Simple keyword-based classification fallback.

        Used when sage-libs is not available.
        """
        message_lower = message.lower()
        best_intent = UserIntent.GENERAL_CHAT
        best_score = 0.0
        matched_keywords: list[str] = []

        for tool in INTENT_TOOLS:
            score = 0.0
            matches = []

            for keyword in tool.keywords:
                if keyword.lower() in message_lower:
                    score += 1.0
                    matches.append(keyword)

            # Normalize by number of keywords
            if tool.keywords:
                # Improved scoring: match count / sqrt(total) to favor matches but penalize very long lists less
                # Or just simple match count for now, but capped
                normalized_score = min(score * 0.5, 1.0)  # Each keyword adds 0.5 confidence
            else:
                normalized_score = 0.0

            if normalized_score > best_score:
                best_score = normalized_score
                try:
                    best_intent = UserIntent(tool.tool_id)
                except ValueError:
                    continue
                matched_keywords = matches

        # Get knowledge domains
        knowledge_domains = None
        if best_intent == UserIntent.KNOWLEDGE_QUERY:
            tool = get_intent_tool(best_intent)
            if tool and tool.knowledge_domains:
                knowledge_domains = [KnowledgeDomain(d) for d in tool.knowledge_domains]

        return IntentResult(
            intent=best_intent,
            confidence=best_score if best_score > 0 else 0.3,
            knowledge_domains=knowledge_domains,
            matched_keywords=matched_keywords,
        )

    @property
    def is_initialized(self) -> bool:
        """Check if the classifier is properly initialized."""
        return self._initialized
