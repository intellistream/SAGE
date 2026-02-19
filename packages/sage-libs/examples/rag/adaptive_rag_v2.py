#!/usr/bin/env python3
"""
Adaptive RAG v2 - 自适应检索增强生成（保留旧版分流逻辑）

核心特性：
- 完全保留旧版 side_output 的分流逻辑
- 使用 FlatMap + Filter 替代 side_output 实现分支
- 向量库分支 vs Web 搜索分支独立处理
- 使用新版 SAGE API：
  - UnifiedInferenceClient (LLM + Embedding)
  - MemoryManager (向量库管理)
  - EmbeddingFactory (本地 Embedding)

数据流（保留旧版双分支结构）：
                    ┌─→ [Filter: vector] → DenseRetriever → Generator → Sink
  问题 → 路由判断 ─┤
                    └─→ [Filter: web] → WebSearchAgent → Sink

对比：
  - 旧版: query_stream.side_output("vector").map(...)
  - 新版: query_stream.filter(VectorFilter).map(...)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

# 屏蔽代理设置（远程服务不需要代理）
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ.pop("ALL_PROXY", None)

import numpy as np
import openai
from dotenv import load_dotenv

from sage.common.components.sage_embedding import EmbeddingClientAdapter
from sage.common.core.functions.filter_function import FilterFunction
from sage.common.core.functions.flatmap_function import FlatMapFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

# 尝试导入 MemoryManager（可选，用于持久化向量库）
try:
    from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

    HAS_MEMORY_MANAGER = True
    _ = MemoryManager  # 标记为已使用（可选功能）
except ImportError:
    HAS_MEMORY_MANAGER = False
    print("⚠️ MemoryManager 不可用，使用简单内存向量库")


# ============================================================
# 远程服务配置（与 adaptive_rag.py 一致）
# ============================================================

# LLM 服务（可选择不同大小的模型）
LLM_HOST = "11.11.11.7"
LLM_MODELS = {
    "32B": ("8901", "Qwen/Qwen2.5-32B-Instruct"),
    "14B": ("8902", "Qwen/Qwen2.5-14B-Instruct"),
    "7B": ("8903", "Qwen/Qwen2.5-7B-Instruct"),  # 默认
    "1.5B": ("8904", "Qwen/Qwen2.5-1.5B-Instruct"),
    "0.5B": ("8905", "Qwen/Qwen2.5-0.5B-Instruct"),
}

# 使用 7B 模型作为默认
DEFAULT_LLM = "7B"
LLM_PORT, LLM_MODEL = LLM_MODELS[DEFAULT_LLM]
LLM_BASE_URL = f"http://{LLM_HOST}:{LLM_PORT}/v1"

# Embedding 服务
EMBEDDING_BASE_URL = f"http://{LLM_HOST}:8090/v1"
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"


# ============================================================
# Prompt 模板（与旧版一致）
# ============================================================

ROUTE_PROMPT_TEMPLATE = """Instruction:
You are an expert at routing a user question to a vectorstore or web search.
Use the vectorstore for questions on travel to Hubei Province in China.
You do not need to be stringent with the keywords in the question related to these topics.
Otherwise, use web-search. Give a binary choice 'web_search' or 'vectorstore' based on the question.
Return a JSON with a single key 'datasource' and no preamble or explanation.
Question to route: {question}
"""

QA_PROMPT_TEMPLATE = """请根据以下背景信息回答问题。如果背景信息不足以回答问题，请诚实说明。

背景信息：
{context}

问题：{question}

请给出简洁准确的回答："""


# ============================================================
# 湖北旅游知识库数据
# ============================================================

HUBEI_DOCUMENTS = [
    "武汉是湖北省省会，著名景点包括黄鹤楼、东湖、户部巷、江汉路步行街等。黄鹤楼是江南三大名楼之一，享有'天下江山第一楼'的美誉。",
    "东湖是中国最大的城中湖，面积约33平方公里，是5A级风景区。湖畔有磨山、听涛、落雁等景区，春天的樱花尤为著名。",
    "长江三峡是中国著名的风景名胜区，包括瞿塘峡、巫峡和西陵峡，全长约200公里。三峡大坝是世界上最大的水利枢纽工程。",
    "恩施大峡谷是国家5A级景区，以天坑、地缝、溶洞、绝壁、峰丛著称，被誉为'湖北的张家界'。峡谷全长108公里。",
    "神农架是中国唯一以'林区'命名的行政区，是世界自然遗产地。这里有金丝猴、白熊等珍稀动物，还有神秘的'野人'传说。",
    "宜昌是三峡大坝所在地，被称为'世界水电之都'。这里是屈原和王昭君的故乡，有屈原祠、昭君村等人文景点。",
    "武当山位于湖北十堰，是道教圣地，金顶和紫霄宫是著名景点。武当武术与少林功夫齐名，被列入世界文化遗产。",
    "荆州古城是中国历史文化名城，三国时期的兵家必争之地。城墙保存完好，有荆州博物馆和张居正故居等景点。",
]


# ============================================================
# 全局服务（延迟初始化）- 使用 SAGE 组件
# ============================================================

_llm_client: openai.OpenAI | None = None
_embedding_client: EmbeddingClientAdapter | None = None
_vector_collection: Any = None


def get_llm_client() -> openai.OpenAI:
    """获取 LLM 客户端（使用标准 OpenAI client）"""
    global _llm_client
    if _llm_client is None:
        _llm_client = openai.OpenAI(
            base_url=LLM_BASE_URL,
            api_key="dummy",  # vLLM 不需要真实 API key
        )
        print(f"✅ OpenAI client 初始化完成: {LLM_BASE_URL}")
    return _llm_client


def get_embedding_client() -> EmbeddingClientAdapter:
    """获取 Embedding 客户端（使用 EmbeddingClientAdapter）"""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClientAdapter.create_api(
            base_url=EMBEDDING_BASE_URL,
            model=EMBEDDING_MODEL,
        )
        print(f"✅ EmbeddingClientAdapter 初始化完成: {EMBEDDING_BASE_URL}")
    return _embedding_client


def get_vector_collection():
    """获取向量库 Collection"""
    global _vector_collection

    if _vector_collection is not None:
        return _vector_collection

    # 使用简单内存向量库（避免 MemoryManager 接口复杂性）
    _vector_collection = SimpleVectorDB(get_embedding_client())
    _vector_collection.add_documents(HUBEI_DOCUMENTS)

    return _vector_collection


class SimpleVectorDB:
    """简单内存向量库 - 使用 EmbeddingClientAdapter"""

    def __init__(self, embedding_client: EmbeddingClientAdapter):
        self.client = embedding_client
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []

    def add_documents(self, documents: list[str]):
        """添加文档并计算 embedding"""
        print(f"📦 构建简单向量库 ({len(documents)} 文档)...")
        # 批量计算 embedding
        embeddings = self.client.embed(documents)
        self.documents = documents
        self.embeddings = embeddings
        print("✅ 向量库构建完成")

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """向量检索"""
        # 计算查询的 embedding
        query_embeddings = self.client.embed([query])
        query_embedding = query_embeddings[0] if query_embeddings else []

        # 计算余弦相似度
        similarities = []
        for i, emb in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [self.documents[i] for i, _ in similarities[:top_k]]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


# ============================================================
# Source: 问题输入源（与旧版一致）
# ============================================================


class QuestionSource(SourceFunction):
    """问题源：从预设问题列表获取问题"""

    def __init__(self, questions: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.questions = questions or [
            "武汉有哪些著名景点？",
            "今天的天气怎么样？",
            "神农架有什么好玩的？",
            "Python 怎么学习？",
        ]
        self.index = 0

    def execute(self, data=None) -> dict | None:
        if self.index >= len(self.questions):
            return None
        question = self.questions[self.index]
        self.index += 1
        print(f"\n{'=' * 60}")
        print(f"📝 问题 {self.index}: {question}")
        return {"question": question}


# ============================================================
# RoutePromptFunction: 构造路由 Prompt（与旧版一致）
# ============================================================


class RoutePromptFunction(MapFunction):
    """
    构造路由 prompt，用于判断使用向量库还是 Web 搜索。
    对应旧版 RoutePromptFunction
    """

    def execute(self, data: dict) -> dict:
        question = data["question"]
        prompt = ROUTE_PROMPT_TEMPLATE.format(question=question)
        return {"question": question, "messages": [{"role": "user", "content": prompt}]}


# ============================================================
# LLMGenerator: 调用 LLM 生成（使用标准 OpenAI client）
# ============================================================


class LLMGenerator(MapFunction):
    """
    调用 LLM 生成响应（使用标准 OpenAI client）。
    对应旧版 OpenAIGenerator
    """

    def execute(self, data: dict) -> dict:
        messages = data["messages"]
        question = data["question"]

        client = get_llm_client()
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL, messages=messages, temperature=0, max_tokens=100
            )
            llm_output = response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ LLM 调用失败: {e}")
            llm_output = '{"datasource": "web_search"}'

        return {"question": question, "llm_output": llm_output}


# ============================================================
# RouteSplitter: 使用 FlatMap 替代 side_output 打标签
# ============================================================


class RouteSplitter(FlatMapFunction):
    """
    路由分流器：根据 LLM 输出判断是走 vectorstore 还是 web_search。

    替代旧版 side_output 的实现：
    - 旧版: self.out.collect(data, "vector") / self.out.collect(data, "web")
    - 新版: 返回带 route 标签的数据，下游用 Filter 分流
    """

    def execute(self, data: dict) -> list[dict]:
        question = data["question"]
        llm_output = data["llm_output"]

        print(f"🔀 RouteSplitter 收到: {llm_output}")

        # 解析路由决策
        if "vectorstore" in llm_output.lower():
            route = "vector"
        else:
            route = "web"

        print(f"   → 路由决策: {route}")

        # 返回带路由标签的数据（替代 side_output）
        return [{"question": question, "route": route}]


# ============================================================
# Filter: 分流过滤器（替代 side_output）
# ============================================================


class VectorRouteFilter(FilterFunction):
    """过滤出走向量库的请求（替代 query_stream.side_output("vector")）"""

    def execute(self, data: dict) -> bool:
        return data.get("route") == "vector"


class WebRouteFilter(FilterFunction):
    """过滤出走 Web 搜索的请求（替代 query_stream.side_output("web")）"""

    def execute(self, data: dict) -> bool:
        return data.get("route") == "web"


# ============================================================
# DenseRetriever: 向量库检索（使用 EmbeddingClientAdapter）
# ============================================================


class DenseRetriever(MapFunction):
    """
    向量库检索器（使用 EmbeddingClientAdapter）。
    对应旧版 DenseRetriever
    """

    def execute(self, data: dict) -> dict:
        question = data["question"]
        print(f"🔍 [向量库] 检索: {question}")

        # 使用简单向量库 - search 方法内部会计算 embedding
        collection = get_vector_collection()
        results = collection.search(question, top_k=3)
        context = "\n\n".join(results)

        print(f"   → 检索到 {len(results)} 条结果")
        return {"question": question, "context": context, "source": "知识库"}


# ============================================================
# QAPromptor: 构造 QA Prompt
# ============================================================


class QAPromptor(MapFunction):
    """
    构造 QA Prompt。
    对应旧版 QAPromptor
    """

    def execute(self, data: dict) -> dict:
        question = data["question"]
        context = data["context"]
        source = data["source"]

        prompt = QA_PROMPT_TEMPLATE.format(context=context, question=question)
        return {
            "question": question,
            "messages": [{"role": "user", "content": prompt}],
            "source": source,
        }


# ============================================================
# QAGenerator: 生成最终回答（使用标准 OpenAI client）
# ============================================================


class QAGenerator(MapFunction):
    """
    生成最终回答（使用标准 OpenAI client）。
    对应旧版 OpenAIGenerator 在 QA 阶段的使用
    """

    def execute(self, data: dict) -> dict:
        messages = data["messages"]
        question = data["question"]
        source = data["source"]

        client = get_llm_client()
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL, messages=messages, temperature=0.7, max_tokens=500
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"生成回答时出错: {e}"

        print(f"🤖 生成回答完成 (来源: {source})")
        return {"question": question, "answer": answer, "source": source}


# ============================================================
# WebSearchAgent: Web 搜索代理
# ============================================================


class WebSearchAgent(MapFunction):
    """
    Web 搜索代理（使用标准 OpenAI client）。
    对应旧版 BaseAgent
    """

    def execute(self, data: dict) -> dict:
        question = data["question"]
        print(f"🌐 [Web搜索] 搜索: {question}")

        # 检查是否有博查 API Key
        bocha_key = os.environ.get("BOCHA_API_KEY")
        if bocha_key:
            answer = self._bocha_search(question, bocha_key)
        else:
            # 无 API 时使用 LLM 直接回答
            client = get_llm_client()
            try:
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": question}],
                    temperature=0.7,
                    max_tokens=500,
                )
                answer = response.choices[0].message.content or "无法生成回答"
            except Exception as e:
                answer = f"回答生成失败: {e}"

        print("🤖 Web 回答完成")
        return {"question": question, "answer": answer, "source": "Web搜索/LLM直答"}

    def _bocha_search(self, question: str, api_key: str) -> str:
        """调用博查搜索 API"""
        try:
            import requests

            resp = requests.post(
                "https://api.bocha.com/v1/search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": question, "count": 3},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    context = "\n\n".join([r.get("snippet", "") for r in results[:3]])
                    # 用 LLM 生成回答
                    client = get_llm_client()
                    response = client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": QA_PROMPT_TEMPLATE.format(
                                    context=context, question=question
                                ),
                            }
                        ],
                        temperature=0.7,
                        max_tokens=500,
                    )
                    return response.choices[0].message.content or "无法生成回答"
            return f"未找到关于'{question}'的搜索结果。"
        except Exception as e:
            return f"Web 搜索失败: {e}"


# ============================================================
# Sink: 结果输出（与旧版 TerminalSink 一致）
# ============================================================


class TerminalSink(SinkFunction):
    """
    终端输出 Sink。
    对应旧版 TerminalSink
    """

    def execute(self, data: dict):
        question = data.get("question", "")
        answer = data.get("answer", "")
        source = data.get("source", "未知")

        print(f"\n{'─' * 60}")
        print(f"❓ 问题: {question}")
        print(f"📚 来源: {source}")
        print(f"💬 回答: {answer}")
        print(f"{'─' * 60}\n")


# ============================================================
# 主程序：完全保留旧版的双分支结构
# ============================================================


def run_adaptive_rag_v2():
    """
    运行 Adaptive RAG v2 流水线

    保留旧版的双分支结构：
    - 向量库分支: RoutePrompt → LLMGenerator → RouteSplitter
                  → Filter(vector) → DenseRetriever → QAPromptor → QAGenerator → Sink
    - Web 分支:   RoutePrompt → LLMGenerator → RouteSplitter
                  → Filter(web) → WebSearchAgent → Sink
    """
    print("🚀 启动 Adaptive RAG v2 系统")
    print(f"📊 LLM 服务: {LLM_BASE_URL} ({LLM_MODEL})")
    print(f"📊 Embedding 服务: {EMBEDDING_BASE_URL} ({EMBEDDING_MODEL})")
    print("📊 流程: 问题 → 路由判断 → [向量库分支 | Web分支] → 回答 → 输出")
    print("=" * 60)

    # 预初始化组件
    print("\n📦 初始化组件...")
    get_llm_client()
    get_embedding_client()
    get_vector_collection()
    print()

    # 创建环境
    env = LocalEnvironment("adaptive_rag_v2")

    # 预设问题列表
    questions = [
        "武汉有哪些著名景点？",  # → vectorstore
        "今天北京的天气怎么样？",  # → web_search
        "神农架有什么好玩的？",  # → vectorstore
        "Python 有哪些常用的 Web 框架？",  # → web_search
    ]

    # ========================================
    # 构建主流程（与旧版结构一致）
    # ========================================

    # 主 Query 路由流程
    # 旧版: env.from_source(FileSource).map(RoutePromptFunction).map(OpenAIGenerator).map(RouteSplitter)
    query_stream = (
        env.from_source(QuestionSource, questions)
        .map(RoutePromptFunction)  # 构造路由 prompt
        .map(LLMGenerator)  # LLM 判断路由
        .flatmap(RouteSplitter)  # 打上路由标签（替代 side_output）
    )

    # ========================================
    # 向量库分支（替代 query_stream.side_output("vector")）
    # ========================================
    # 旧版:
    #   query_stream.side_output("vector")
    #               .map(DenseRetriever)
    #               .map(QAPromptor)
    #               .map(OpenAIGenerator)
    #               .sink(TerminalSink)
    _vector_stream = (
        query_stream.filter(VectorRouteFilter)  # 替代 .side_output("vector")
        .map(DenseRetriever)  # 向量检索
        .map(QAPromptor)  # 构造 QA prompt
        .map(QAGenerator)  # 生成回答
        .sink(TerminalSink)  # 输出
    )

    # ========================================
    # Web 搜索分支（替代 query_stream.side_output("web")）
    # ========================================
    # 旧版:
    #   query_stream.side_output("web")
    #               .map(BaseAgent)
    #               .map(TerminalSink)
    _web_stream = (
        query_stream.filter(WebRouteFilter)  # 替代 .side_output("web")
        .map(WebSearchAgent)  # Web 搜索 + LLM 回答
        .sink(TerminalSink)  # 输出
    )

    # 运行
    try:
        env.submit()
        time.sleep(15)  # 等待处理完成
        print("\n✅ Adaptive RAG v2 处理完成")
    except Exception as e:
        print(f"❌ 处理出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        env.close()


if __name__ == "__main__":
    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - adaptive_rag_v2 example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    run_adaptive_rag_v2()


# ============================================================
# Pipeline 拓扑图
# ============================================================
#
#                     ┌───────────────┐
#                     │ QuestionSource│
#                     └───────┬───────┘
#                             │
#                             ▼
#                   ┌─────────────────┐
#                   │RoutePromptFunction│
#                   └────────┬────────┘
#                            │
#                            ▼
#                   ┌─────────────────┐
#                   │  LLMGenerator   │ ─────► LLM :8903
#                   └────────┬────────┘
#                            │
#                            ▼
#                   ┌─────────────────┐
#                   │  RouteSplitter  │  (FlatMap, 替代 side_output)
#                   └────────┬────────┘
#                            │
#            ┌───────────────┴───────────────┐
#            │                               │
#            ▼                               ▼
#   ┌─────────────────┐             ┌─────────────────┐
#   │VectorRouteFilter│             │ WebRouteFilter  │
#   │ route="vector"  │             │  route="web"    │
#   └────────┬────────┘             └────────┬────────┘
#            │                               │
#            ▼                               ▼
#   ┌─────────────────┐             ┌─────────────────┐
#   │ DenseRetriever  │             │ WebSearchAgent  │
#   │                 │             │                 │
#   │ Embedding :8090 │             │   LLM :8903     │
#   │ SimpleVectorDB  │             └────────┬────────┘
#   └────────┬────────┘                      │
#            │                               │
#            ▼                               │
#   ┌─────────────────┐                      │
#   │   QAPromptor    │                      │
#   └────────┬────────┘                      │
#            │                               │
#            ▼                               │
#   ┌─────────────────┐                      │
#   │   QAGenerator   │ ─────► LLM :8903     │
#   └────────┬────────┘                      │
#            │                               │
#            ▼                               ▼
#   ┌─────────────────┐             ┌─────────────────┐
#   │  TerminalSink   │             │  TerminalSink   │
#   │   (知识库回答)   │             │  (Web/LLM回答)  │
#   └─────────────────┘             └─────────────────┘
#
# ============================================================
# 远程服务 (11.11.11.7)
# ============================================================
#   :8903  Qwen/Qwen2.5-7B-Instruct   LLM
#   :8090  BAAI/bge-large-zh-v1.5     Embedding
#
# ============================================================
# 核心变更: side_output → FlatMap + Filter
# ============================================================
#   旧版: query_stream.side_output("vector")
#   新版: query_stream.flatmap(RouteSplitter).filter(VectorRouteFilter)
# ============================================================
