"""Intent catalog and helpers (L3: sage-libs)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sage.libs.agentic.intent.types import KnowledgeDomain, UserIntent


@dataclass
class IntentTool:
    tool_id: str
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    knowledge_domains: list[str] = field(default_factory=list)
    category: str = "intent"


INTENT_TOOLS: list[IntentTool] = [
    IntentTool(
        tool_id=UserIntent.KNOWLEDGE_QUERY.value,
        name="知识库查询 / Knowledge Query",
        description=(
            """
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
        """
        ),
        keywords=[
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
    IntentTool(
        tool_id=UserIntent.SAGE_CODING.value,
        name="SAGE 编程助手 / SAGE Coding Assistant",
        description=(
            """
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
        """
        ),
        keywords=[
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
    ),
    IntentTool(
        tool_id=UserIntent.SYSTEM_OPERATION.value,
        name="系统操作 / System Operation",
        description=(
            """
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
        """
        ),
        keywords=[
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
            "服务",
            "service",
            "LLM",
            "Gateway",
            "Embedding",
            "vLLM",
            "集群",
            "cluster",
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
    ),
    IntentTool(
        tool_id=UserIntent.GENERAL_CHAT.value,
        name="普通对话 / General Chat",
        description=(
            """
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
        """
        ),
        keywords=[
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
            "thanks",
            "thank you",
            "please",
            "sorry",
            "okay",
            "ok",
            "sure",
            "got it",
            "understood",
            "帮助",
            "help",
            "你能做什么",
            "what can you do",
            "你是谁",
            "who are you",
            "介绍自己",
            "introduce yourself",
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
    ),
]


def get_intent_tool(intent: UserIntent) -> IntentTool | None:
    for tool in INTENT_TOOLS:
        if tool.tool_id == intent.value:
            return tool
    return None


def get_all_intent_keywords() -> dict[str, list[str]]:
    return {tool.tool_id: tool.keywords for tool in INTENT_TOOLS}


class IntentToolsLoader:
    """Loader compatible with SelectorResources."""

    def __init__(self, tools: list[IntentTool] | None = None):
        tools = tools or INTENT_TOOLS
        self._tools = {tool.tool_id: tool for tool in tools}

    def get_tool(self, tool_id: str) -> IntentTool | None:
        return self._tools.get(tool_id)

    def get_all_tools(self) -> list[IntentTool]:
        return list(self._tools.values())

    def iter_all(self):
        yield from self._tools.values()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._tools)
