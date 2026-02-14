#!/usr/bin/env python3
"""
Advanced RAG Topology - 完整 RAG 系统拓扑结构
=============================================

本示例展示如何基于 SAGE 框架构建一个包含以下组件的完整 RAG 系统：
- sage_flow: 向量流处理引擎（高性能数据流）
- sage_db: 向量数据库（文档检索）
- sage_tsdb: 时序数据库（对话历史、日志、指标）
- sage_refiner: 上下文压缩/精炼器
- LLM: 推理引擎 (SageLLMGenerator)

LLM 引擎选项:
    - engine_type="sagellm" (推荐): SAGE 统一推理引擎
    - engine_type="vllm" (deprecated): 将重定向到 sagellm

    后端类型 (backend_type):
    - "vllm": 使用 vLLM 后端 (需要 GPU)
    - "mock": 模拟模式 (无需 GPU, 用于测试)
    - "openai": 使用 OpenAI API
    - "dashscope": 使用 DashScope API

运行:
    python advanced_rag_topology.py           # 正常运行 (需要模型/GPU)
    python advanced_rag_topology.py --mock    # Mock 模式 (无需 GPU)

拓扑结构图：
============

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SAGE RAG Pipeline 拓扑                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────┐
                              │  sage_flow    │ ← 向量批处理加速 (C++ 高性能)
                              │ (向量流引擎)   │
                              └───────┬───────┘
                                      │ 加速向量计算
    ┌───────────────┐     ┌───────────▼───┐     ┌───────────────┐     ┌───────────────┐
    │    Source     │────▶│   Embedder    │────▶│   Retriever   │────▶│   Reranker    │
    │  (问题输入)    │     │  (向量编码)    │     │  (sage_db)    │     │  (重排序)      │
    │   [文本]      │     │ [文本→向量]    │     │ [向量→文档]   │     │ [文档重排]     │
    └───────────────┘     └───────────────┘     └───────┬───────┘     └───────┬───────┘
                                                        │                     │
                                                        ▼                     │
                                                ┌───────────────┐             │
                                                │   sage_tsdb   │             │
                                                │ (查询日志)     │             │
                                                └───────────────┘             │
                                                                              ▼
    ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
    │    Sink       │◀────│   Generator   │◀────│   Promptor    │◀────│   Refiner     │
    │   (输出)      │     │    (LLM)      │     │  (提示构建)    │     │  (上下文压缩)  │
    │   [文本]      │     │ [Prompt→回答] │     │ [组装Prompt]  │     │ [文本→压缩文本]│
    └───────────────┘     └───────┬───────┘     └───────────────┘     └───────────────┘
                                  │                                   (sage_refiner)
                                  ▼
                          ┌───────────────┐
                          │   sage_tsdb   │
                          │  (响应日志)    │
                          └───────────────┘
```

各组件数据类型说明：
- sage_flow: 向量批处理引擎，加速 Embedder 的向量计算（输入文本批次，输出向量批次）
- sage_db: 向量数据库，输入查询向量，输出相关文档列表
- sage_tsdb: 时序数据库，记录时间戳+指标数据
- sage_refiner: 上下文压缩器，输入长文档文本，输出压缩后的文本（文本→文本）
- LLM: 推理引擎，输入 Prompt 文本，输出回答文本

数据流路径：
1. Source → 接收用户问题 [文本]
2. Embedder (+ sage_flow) → 将问题编码为向量 [文本→向量]，sage_flow 加速批量计算
3. Retriever (sage_db) → 从向量数据库检索相关文档 [向量→文档列表]
4. sage_tsdb → 记录查询历史，用于分析和优化
5. Reranker → 对检索结果重排序 [文档列表→排序后文档列表]
6. Refiner (sage_refiner) → 压缩上下文 [长文本→压缩文本]，控制 token 预算
7. Promptor → 构建 LLM 提示 [压缩文本+问题→Prompt]
8. Generator (LLM) → 生成回答 [Prompt→回答]
9. Sink → 输出结果
10. sage_tsdb → 记录响应日志和指标

层级分布 (遵循 SAGE 架构规范):
- L1 (common): 基础函数类 (SourceFunction, MapFunction, SinkFunction)
- L2 (platform): 平台服务
- L3 (kernel/libs): Environment, DataStream API, Embedding, Retriever 基础
- L4 (middleware): sage_db, sage_tsdb, sage_flow, sage_refiner (C++ 扩展)
- L5 (cli/tools): 命令行接口和开发工具

独立仓库 (不在 SAGE 核心架构中):
- sage-examples: 应用示例
- sage-studio: 用户界面和可视化
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
from dotenv import load_dotenv

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger

# ================================================================================
# 配置数据类
# ================================================================================


@dataclass
class RAGTopologyConfig:
    """RAG 拓扑配置"""

    # 向量数据库配置 (sage_db)
    db_config: dict[str, Any] = field(
        default_factory=lambda: {
            "collection_name": "rag_knowledge_base",
            "dim": 384,  # 嵌入维度
            "metric": "cosine",
            "top_k": 10,
        }
    )

    # 时序数据库配置 (sage_tsdb)
    tsdb_config: dict[str, Any] = field(
        default_factory=lambda: {
            "enable_query_log": True,
            "enable_response_log": True,
            "retention_days": 30,
            "metrics_interval_ms": 1000,
        }
    )

    # 向量流处理配置 (sage_flow)
    flow_config: dict[str, Any] = field(
        default_factory=lambda: {
            "batch_size": 32,
            "enable_batching": True,
            "timeout_ms": 5000,
        }
    )

    # Refiner 配置 (上下文压缩)
    refiner_config: dict[str, Any] = field(
        default_factory=lambda: {
            "algorithm": "simple",  # simple, long_refiner, llmlingua2
            "budget": 4000,  # token 预算
            "enable_cache": True,
        }
    )

    # LLM 推理配置
    llm_config: dict[str, Any] = field(
        default_factory=lambda: {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "temperature": 0.7,
            "max_tokens": 512,
        }
    )


# ================================================================================
# 1. Source - 问题输入源
# ================================================================================


class QuestionSource(SourceFunction):
    """
    问题数据源 - 接收用户查询

    在实际应用中，可替换为：
    - API 接口接收
    - 消息队列消费
    - 文件批量读取
    """

    def __init__(self, questions: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.questions = questions or [
            "SAGE 框架支持哪些 LLM 后端?",
            "如何在 SAGE 中实现分布式 Pipeline?",
            "sage_db 和 sage_tsdb 有什么区别?",
        ]
        self.index = 0
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

    def execute(self, data=None):
        if self.index >= len(self.questions):
            return None

        question = self.questions[self.index]
        self.index += 1

        self.logger.info(f"📝 [Source] 发送问题 #{self.index}: {question}")

        return {
            "query_id": f"q_{self.index}_{int(time.time())}",
            "query": question,
            "timestamp": datetime.now().isoformat(),
        }


# ================================================================================
# 2. Embedder - 向量编码器 (与 sage_flow 集成)
# ================================================================================


class EmbeddingOperator(MapFunction):
    """
    向量嵌入算子 - 将文本编码为向量

    集成 sage_flow 进行高效向量流处理：
    - 批量编码优化
    - GPU 加速（如果可用）
    - 缓存机制
    """

    def __init__(self, dim: int = 384, **kwargs):
        super().__init__(**kwargs)
        self.dim = dim
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

        # 尝试加载真实的 Embedding 模型
        self._embedder = None
        self._init_embedder()

    def _init_embedder(self):
        """初始化嵌入模型"""
        try:
            from sage.common.components.sage_embedding import EmbeddingFactory

            self._embedder = EmbeddingFactory.create(
                "hf",
                model="BAAI/bge-small-zh-v1.5",
            )
            self.logger.info("✓ 已加载 HuggingFace Embedding 模型")
        except Exception as e:
            self.logger.warning(f"无法加载 Embedding 模型，使用模拟: {e}")
            self._embedder = None

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        query = data["query"]

        if self._embedder:
            # 使用真实模型编码
            query_vector = self._embedder.embed(query)
            query_vector = np.array(query_vector)
        else:
            # 模拟向量编码（用于演示）
            np.random.seed(hash(query) % 2**32)
            query_vector = np.random.randn(self.dim).astype(np.float32)
            query_vector = query_vector / np.linalg.norm(query_vector)

        data["query_vector"] = query_vector
        self.logger.info(f"🔢 [Embedder] 向量编码完成, dim={len(query_vector)}")

        return data


# ================================================================================
# 3. Retriever - 向量检索器 (基于 sage_db)
# ================================================================================


class VectorRetriever(MapFunction):
    """
    向量检索算子 - 从 sage_db 检索相关文档

    核心功能：
    - 基于 FAISS 的高效相似度搜索
    - 支持元数据过滤
    - 混合检索（向量 + 关键词）
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.top_k = self.config.get("top_k", 5)
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

        # 模拟知识库
        self._knowledge_base = self._init_knowledge_base()
        self._db = None
        self._init_db()

    def _init_knowledge_base(self) -> list[dict[str, Any]]:
        """初始化模拟知识库"""
        return [
            {
                "id": "doc_1",
                "content": "SAGE 支持多种 LLM 后端，包括 vLLM、OpenAI API、DashScope 等。通过 UnifiedInferenceClient 可以统一调用不同后端。",
                "metadata": {"topic": "llm", "source": "docs"},
            },
            {
                "id": "doc_2",
                "content": "SAGE 基于 Ray 构建分布式执行能力。使用 RemoteEnvironment 可以在集群上运行 Pipeline，JobManager 负责任务调度。",
                "metadata": {"topic": "distributed", "source": "docs"},
            },
            {
                "id": "doc_3",
                "content": "sage_db 是高性能向量数据库，基于 FAISS 实现，用于文档检索。sage_tsdb 是时序数据库，用于存储时间序列数据如监控指标、对话历史等。",
                "metadata": {"topic": "database", "source": "docs"},
            },
            {
                "id": "doc_4",
                "content": "sage_flow 是向量流处理引擎，支持高效的批量向量运算。sage_refiner 提供上下文压缩功能，可以将长文档压缩到指定的 token 预算内。",
                "metadata": {"topic": "components", "source": "docs"},
            },
            {
                "id": "doc_5",
                "content": "SAGE 的 dataflow 范式采用声明式 API：env.from_source().map().map().sink()。这种方式便于优化和分布式执行。",
                "metadata": {"topic": "api", "source": "docs"},
            },
        ]

    def _init_db(self):
        """尝试初始化 sage_db"""
        try:
            from sage.middleware.components.sage_vdb import SageDB

            self._db = SageDB(dim=self.config.get("dim", 384))
            self.logger.info("✓ 已初始化 sage_db")
        except Exception as e:
            self.logger.warning(f"无法初始化 sage_db，使用模拟检索: {e}")
            self._db = None

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        query = data["query"]
        _query_vector = data.get("query_vector")  # 保留以备将来使用

        # 简单的关键词匹配检索（演示用）
        retrieved_docs = []
        for doc in self._knowledge_base:
            # 计算简单的相关性分数
            score = sum(1 for word in query.split() if word in doc["content"])
            if score > 0:
                retrieved_docs.append({"doc": doc, "score": score})

        # 按分数排序
        retrieved_docs.sort(key=lambda x: x["score"], reverse=True)
        retrieved_docs = retrieved_docs[: self.top_k]

        data["retrieved_documents"] = [item["doc"] for item in retrieved_docs]
        data["retrieval_scores"] = [item["score"] for item in retrieved_docs]

        self.logger.info(f"🔍 [Retriever] 检索到 {len(retrieved_docs)} 篇相关文档")

        return data


# ================================================================================
# 4. TSDB Logger - 时序数据记录 (基于 sage_tsdb)
# ================================================================================


class TSDBLogger(MapFunction):
    """
    时序数据记录算子 - 使用 sage_tsdb 记录查询和响应

    记录内容：
    - 查询时间戳和内容
    - 检索延迟
    - 生成延迟
    - 响应质量指标
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

        self._tsdb = None
        self._init_tsdb()

    def _init_tsdb(self):
        """尝试初始化 sage_tsdb"""
        try:
            from sage.middleware.components.sage_tsdb import SageTSDB

            self._tsdb = SageTSDB()
            self.logger.info("✓ 已初始化 sage_tsdb")
        except Exception as e:
            self.logger.warning(f"无法初始化 sage_tsdb，使用内存记录: {e}")
            self._tsdb = None

        # 内存中的备用日志
        self._memory_log: list[dict[str, Any]] = []

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # 记录时序数据
        log_entry = {
            "timestamp": int(time.time() * 1000),  # 毫秒时间戳
            "query_id": data.get("query_id"),
            "query": data.get("query"),
            "num_retrieved": len(data.get("retrieved_documents", [])),
            "stage": "retrieval_complete",
        }

        if self._tsdb:
            try:
                self._tsdb.insert(
                    metric_name="rag_queries",
                    timestamp=log_entry["timestamp"],
                    value=1.0,
                    tags={"query_id": log_entry["query_id"]},
                    fields=log_entry,
                )
            except Exception as e:
                self.logger.warning(f"TSDB 写入失败: {e}")

        self._memory_log.append(log_entry)
        self.logger.info(f"📊 [TSDB] 记录查询日志: {data.get('query_id')}")

        return data


# ================================================================================
# 5. Reranker - 重排序器
# ================================================================================


class DocumentReranker(MapFunction):
    """
    文档重排序算子

    使用交叉编码器或其他重排序模型对检索结果进行精排。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        documents = data.get("retrieved_documents", [])
        query = data.get("query", "")

        if not documents:
            return data

        # 模拟重排序（实际应使用 BGE Reranker 等模型）
        reranked_docs = []
        for doc in documents:
            # 简单的相关性评分
            content = doc.get("content", "")
            score = sum(1 for word in query.split() if word.lower() in content.lower())
            reranked_docs.append({"doc": doc, "rerank_score": score * 1.5})

        reranked_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        data["retrieved_documents"] = [item["doc"] for item in reranked_docs]
        data["rerank_scores"] = [item["rerank_score"] for item in reranked_docs]

        self.logger.info(
            f"📋 [Reranker] 重排序完成, top doc score: {reranked_docs[0]['rerank_score'] if reranked_docs else 0}"
        )

        return data


# ================================================================================
# 6. Refiner - 上下文压缩器 (基于 sage_refiner)
# ================================================================================


class ContextRefiner(MapFunction):
    """
    上下文压缩算子 - 使用 sage_refiner 压缩检索到的文档

    支持多种压缩算法：
    - simple: 简单截断
    - long_refiner: LongRefiner 算法
    - llmlingua2: LLMLingua2 快速压缩
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.budget = self.config.get("budget", 4000)
        self.algorithm = self.config.get("algorithm", "simple")
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

        self._refiner = None
        self._init_refiner()

    def _init_refiner(self):
        """初始化 refiner (使用 isage-refiner 包)"""
        try:
            if self.algorithm == "long_refiner":
                from sage_refiner import LongRefinerCompressor

                self._refiner = LongRefinerCompressor()
                self.logger.info("✓ 已初始化 LongRefinerCompressor")
            elif self.algorithm == "reform":
                from sage_refiner import REFORMCompressor

                self._refiner = REFORMCompressor()
                self.logger.info("✓ 已初始化 REFORMCompressor")
            else:
                # simple/none - no compressor needed
                self._refiner = None
                self.logger.info(f"使用简单截断模式 (algorithm={self.algorithm})")
        except ImportError as e:
            self.logger.warning(f"isage-refiner 未安装，使用简单截断: {e}")
            self._refiner = None
        except Exception as e:
            self.logger.warning(f"无法初始化 refiner，使用简单截断: {e}")
            self._refiner = None

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        documents = data.get("retrieved_documents", [])
        query = data.get("query", "")

        if not documents:
            data["refined_context"] = ""
            return data

        # 合并文档内容
        full_context = "\n\n".join(doc.get("content", "") for doc in documents)

        if self._refiner:
            try:
                # isage-refiner uses 'contents' key and returns dict
                documents_for_refiner = [{"contents": full_context}]
                result = self._refiner.compress(
                    question=query,
                    document_list=documents_for_refiner,
                    budget=self.budget,
                )
                refined_context = result.get("compressed_context", full_context)
            except Exception as e:
                self.logger.warning(f"Refiner 压缩失败: {e}")
                refined_context = full_context[: self.budget]
        else:
            # 简单截断
            refined_context = full_context[: self.budget]

        data["refined_context"] = refined_context
        data["original_length"] = len(full_context)
        data["refined_length"] = len(refined_context)

        compression_ratio = len(refined_context) / max(len(full_context), 1)
        self.logger.info(f"🗜️ [Refiner] 压缩完成, ratio: {compression_ratio:.2%}")

        return data


# ================================================================================
# 7. Promptor - 提示构建器
# ================================================================================


class RAGPromptor(MapFunction):
    """
    RAG 提示构建算子

    将查询和压缩后的上下文组合成 LLM 可用的提示。
    """

    def __init__(self, template: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.template = (
            template
            or """请根据以下背景信息回答用户问题。

背景信息：
{context}

用户问题：{query}

请给出准确、简洁的回答："""
        )
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        query = data.get("query", "")
        context = data.get("refined_context", "")

        prompt = self.template.format(context=context, query=query)
        data["prompt"] = prompt

        self.logger.info(f"📝 [Promptor] 提示构建完成, length: {len(prompt)}")

        return data


# ================================================================================
# 8. Generator - LLM 推理引擎
# ================================================================================


class LLMGenerator(MapFunction):
    """
    LLM 生成算子 - 使用 SAGE 的统一推理客户端

    支持多种后端 (engine_type/backend_type):
    - sagellm + vllm: 本地 vLLM 后端 (推荐, 需要 GPU)
    - sagellm + mock: 模拟模式 (无需 GPU, 用于测试)
    - sagellm + openai: OpenAI API
    - sagellm + dashscope: DashScope API
    """

    def __init__(self, config: dict[str, Any] | None = None, use_mock: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.use_mock = use_mock
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

        self._client = None
        self._generator = None
        self._init_client()

    def _init_client(self):
        """初始化 LLM 客户端"""
        # 优先使用 SageLLMGenerator (推荐)
        try:
            from sage.middleware.operators import SageLLMGenerator

            # 确定 backend_type
            if self.use_mock:
                backend_type = "mock"
            else:
                backend_type = self.config.get("backend_type", "vllm")

            self._generator = SageLLMGenerator(
                model_id=self.config.get("model", "Qwen/Qwen2.5-7B-Instruct"),
                backend_type=backend_type,
                # engine_type="sagellm" is default
            )
            self.logger.info(f"✓ 已初始化 SageLLMGenerator (backend={backend_type})")
            return
        except Exception as e:
            self.logger.warning(f"SageLLMGenerator 初始化失败: {e}")

        # Fallback: 尝试 UnifiedInferenceClient
        try:
            from sage.common.components.sage_llm import UnifiedInferenceClient

            self._client = UnifiedInferenceClient.create()
            self.logger.info("✓ 已初始化 UnifiedInferenceClient")
        except Exception as e:
            self.logger.warning(f"无法初始化 LLM 客户端，使用模拟回答: {e}")
            self._client = None

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        prompt = data.get("prompt", "")
        query = data.get("query", "")

        start_time = time.time()

        # 优先使用 SageLLMGenerator
        if self._generator:
            try:
                # SageLLMGenerator 使用 execute 方法
                result = self._generator.execute({"prompt": prompt})
                answer = result.get("response", "") if isinstance(result, dict) else str(result)
            except Exception as e:
                self.logger.warning(f"SageLLMGenerator 调用失败: {e}")
                answer = self._mock_answer(query, data.get("refined_context", ""))
        elif self._client:
            try:
                response = self._client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.get("temperature", 0.7),
                    max_tokens=self.config.get("max_tokens", 512),
                )
                answer = response.get("content", "")
            except Exception as e:
                self.logger.warning(f"LLM 调用失败: {e}")
                answer = self._mock_answer(query, data.get("refined_context", ""))
        else:
            answer = self._mock_answer(query, data.get("refined_context", ""))

        latency = time.time() - start_time

        data["answer"] = answer
        data["generation_latency"] = latency

        self.logger.info(f"🤖 [Generator] 生成完成, latency: {latency:.2f}s")

        return data

    def _mock_answer(self, query: str, context: str) -> str:
        """模拟 LLM 回答"""
        if "LLM" in query or "后端" in query:
            return "SAGE 支持多种 LLM 后端，包括 vLLM（本地高性能推理）、OpenAI API、DashScope 等。通过 UnifiedInferenceClient 可以统一调用。"
        elif "分布式" in query:
            return "SAGE 基于 Ray 构建分布式能力。使用 RemoteEnvironment 在集群运行 Pipeline，JobManager 负责调度。"
        elif "sage_db" in query or "sage_tsdb" in query or "区别" in query:
            return "sage_db 是向量数据库，用于文档检索；sage_tsdb 是时序数据库，用于存储时间序列数据如监控指标和对话历史。"
        else:
            return f"根据提供的信息，这个问题涉及：{context[:100]}..."


# ================================================================================
# 9. Response TSDB Logger - 响应日志记录
# ================================================================================


class ResponseTSDBLogger(MapFunction):
    """记录响应到时序数据库"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = CustomLogger.get_logger(self.__class__.__name__)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # 记录响应指标
        log_entry = {
            "timestamp": int(time.time() * 1000),
            "query_id": data.get("query_id"),
            "answer_length": len(data.get("answer", "")),
            "generation_latency": data.get("generation_latency", 0),
            "compression_ratio": data.get("refined_length", 0)
            / max(data.get("original_length", 1), 1),
        }

        self.logger.info(f"📊 [TSDB] 记录响应指标: latency={log_entry['generation_latency']:.2f}s")

        data["response_metrics"] = log_entry
        return data


# ================================================================================
# 10. Sink - 结果输出
# ================================================================================


class RAGResultSink(SinkFunction):
    """
    RAG 结果输出

    支持多种输出方式：
    - 终端打印
    - 文件保存
    - API 回调
    """

    def __init__(self, output_file: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.output_file = output_file
        self.logger = CustomLogger.get_logger(self.__class__.__name__)
        self.results: list[dict[str, Any]] = []

    def execute(self, data: dict[str, Any]):
        query = data.get("query", "")
        answer = data.get("answer", "")
        metrics = data.get("response_metrics", {})

        # 格式化输出
        print("\n" + "=" * 70)
        print(f"❓ 问题: {query}")
        print("-" * 70)
        print(f"💬 回答: {answer}")
        print("-" * 70)
        print(
            f"📊 指标: latency={metrics.get('generation_latency', 0):.2f}s, compression={metrics.get('compression_ratio', 0):.2%}"
        )
        print("=" * 70 + "\n")

        self.results.append(data)
        self.logger.info(f"✅ [Sink] 结果输出完成: {data.get('query_id')}")


# ================================================================================
# Pipeline 构建与执行
# ================================================================================


def build_rag_topology(config: RAGTopologyConfig | None = None, use_mock: bool = False):
    """
    构建 RAG 拓扑

    拓扑结构：
    Source → Embedder → Retriever → TSDBLogger → Reranker
           → Refiner → Promptor → Generator → ResponseLogger → Sink

    Args:
        config: RAG 拓扑配置
        use_mock: 是否使用 mock 模式 (无需 GPU)
    """
    from sage.kernel.api.local_environment import LocalEnvironment

    config = config or RAGTopologyConfig()

    # 创建执行环境
    env = LocalEnvironment("AdvancedRAGTopology")

    # 构建 dataflow pipeline
    (
        env.from_source(QuestionSource)
        .map(EmbeddingOperator, dim=config.db_config.get("dim", 384))
        .map(VectorRetriever, config=config.db_config)
        .map(TSDBLogger, config=config.tsdb_config)
        .map(DocumentReranker)
        .map(ContextRefiner, config=config.refiner_config)
        .map(RAGPromptor)
        .map(LLMGenerator, config=config.llm_config, use_mock=use_mock)
        .map(ResponseTSDBLogger)
        .sink(RAGResultSink)
    )

    return env


def main():
    """运行 RAG 拓扑演示"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SAGE Advanced RAG Topology Demo")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用 mock 模式运行 (无需 GPU/模型)",
    )
    args = parser.parse_args()

    load_dotenv()

    print("\n" + "=" * 70)
    print("🚀 SAGE Advanced RAG Topology Demo")
    if args.mock:
        print("🧪 Mock 模式: 使用模拟 LLM (无需 GPU)")
    print("=" * 70 + "\n")

    # 配置
    config = RAGTopologyConfig(
        db_config={
            "collection_name": "rag_demo",
            "dim": 384,
            "top_k": 5,
        },
        refiner_config={
            "algorithm": "simple",
            "budget": 2000,
        },
        llm_config={
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "temperature": 0.7,
            "max_tokens": 256,
            "backend_type": "mock" if args.mock else "vllm",
        },
    )

    # 构建拓扑
    env = build_rag_topology(config, use_mock=args.mock)

    # 执行
    print("📦 开始执行 RAG Pipeline...\n")
    env.submit(autostop=True)

    print("\n✅ RAG Pipeline 执行完成.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
