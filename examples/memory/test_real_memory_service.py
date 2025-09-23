#!/usr/bin/env python3
"""
Real SAGE MemoryService pipeline demo (no mocks)

This example builds a SAGE pipeline that uses the real KV, VDB (FAISS), and Graph services,
orchestrated by MemoryService. It demonstrates storing conversations as memories and then
querying them via vector similarity search, all through self.call_service within pipeline
functions.

Requirements:
  - Python 3.10+
  - faiss-cpu installed (pip install faiss-cpu)

Quick run:
  - python examples/memory/test_real_memory_service.py

Notes:
  - Services are registered via env.register_service_factory(name, factory)
  - Pipeline uses env.from_batch(...).map(...).sink(...)
  - Service calls happen via self.call_service["memory_service"].<method>
"""

import os
import time
from typing import Any, Dict, List

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.services.graph.graph_service import \
    create_graph_service_factory
from sage.middleware.services.kv.kv_service import create_kv_service_factory
from sage.middleware.services.memory.memory_service import \
    create_memory_service_factory
from sage.middleware.services.vdb.vdb_service import create_vdb_service_factory


def mock_embedding(text: str) -> List[float]:
    """Deterministic mock embedding based on content hash (demo only)."""
    import hashlib

    import numpy as np

    h = hashlib.md5(text.encode()).hexdigest()
    seed = int(h, 16) % (2**32)
    rng = np.random.default_rng(seed)
    return rng.random(384, dtype=np.float32).tolist()


def create_sample_conversations() -> List[Dict[str, Any]]:
    return [
        {
            "user_message": "你好，我想学习Python编程，应该从哪里开始？",
            "ai_response": "你好！学习Python编程是一个很好的选择。要开始学习，我建议：1. 安装Python环境 2. 学习基础语法 3. 练习编写简单程序",
            "topic": "programming",
        },
        {
            "user_message": "Python中变量和数据类型有哪些？",
            "ai_response": "Python有以下基本数据类型：1. 整数(int) 2. 浮点数(float) 3. 字符串(str) 4. 布尔值(bool) 5. 列表(list) 6. 元组(tuple) 7. 字典(dict)",
            "topic": "programming",
        },
        {
            "user_message": "我对机器学习很感兴趣，有什么建议？",
            "ai_response": "机器学习是一个很有前景的领域！建议从以下方面开始：1. 学习Python基础 2. 掌握数学基础（线性代数、概率论）3. 学习scikit-learn等库 4. 实践项目",
            "topic": "ai",
        },
        {
            "user_message": "周末我想放松一下，有什么推荐？",
            "ai_response": "周末放松很重要！可以考虑：1. 户外活动如散步或骑行 2. 阅读书籍 3. 学习新技能 4. 和朋友聚餐 记住保持工作生活平衡！",
            "topic": "lifestyle",
        },
        {
            "user_message": "我最近总是感觉疲惫，有什么改善方法？",
            "ai_response": "感觉疲惫可能是多种原因造成的。建议：1. 保证充足睡眠（7-9小时）2. 规律饮食，摄入均衡营养 3. 适量运动 4. 管理压力 5. 如持续严重，建议咨询医生",
            "topic": "health",
        },
    ]


class StoreMemories(BaseFunction):
    """Store user/AI messages (and optional semantic memory) via MemoryService"""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def execute(self, conversation: Dict[str, Any]):
        user_message = conversation["user_message"]
        ai_response = conversation["ai_response"]
        topic = conversation.get("topic", "general")

        memory = self.call_service["memory_service"]

        stored_ids: List[str] = []
        now = time.time()

        # user message
        uid = memory.store_memory(
            content=user_message,
            vector=mock_embedding(user_message),
            session_id=self.session_id,
            memory_type="conversation",
            metadata={"speaker": "user", "topic": topic, "timestamp": now},
        )
        stored_ids.append(uid)

        # ai response
        aid = memory.store_memory(
            content=ai_response,
            vector=mock_embedding(ai_response),
            session_id=self.session_id,
            memory_type="conversation",
            metadata={"speaker": "ai", "topic": topic, "timestamp": now},
        )
        stored_ids.append(aid)

        # optional semantic memory
        if "python" in user_message.lower() or "编程" in user_message:
            semantic_content = f"用户对编程感兴趣：{user_message[:50]}..."
            sid = memory.store_memory(
                content=semantic_content,
                vector=mock_embedding(semantic_content),
                session_id=self.session_id,
                memory_type="knowledge",
                metadata={
                    "topic": "programming",
                    "importance": "medium",
                    "timestamp": now,
                },
                create_knowledge_graph=True,
            )
            stored_ids.append(sid)

        return {"session_id": self.session_id, "stored_ids": stored_ids, "topic": topic}


class PrintStoreResult(BaseFunction):
    def execute(self, data: Dict[str, Any]):
        print(
            f"🗄️ Stored {len(data.get('stored_ids', []))} memories for session {data['session_id']} (topic={data.get('topic')})"
        )
        return data


class SearchMemories(BaseFunction):
    def __init__(self, session_id: str, top_k: int = 3):
        super().__init__()
        self.session_id = session_id
        self.top_k = top_k

    def execute(self, query: str):
        vector = mock_embedding(query)
        memory = self.call_service["memory_service"]
        results = memory.search_memories(
            query_vector=vector, session_id=self.session_id, limit=self.top_k
        )
        summary = [
            {
                "id": r.get("id"),
                "type": r.get("memory_type"),
                "score": r.get("similarity_score"),
                "preview": (r.get("content") or "")[:60],
            }
            for r in results
        ]
        return {"query": query, "results": summary}


class PrintSearchResult(BaseFunction):
    def execute(self, data: Dict[str, Any]):
        print(f"\n🔍 查询: {data['query']}")
        for i, r in enumerate(data.get("results", []), 1):
            print(f"  {i}. [{r['type']}] {r['preview']}... (相似度: {r['score']:.4f})")
        return data


def run_memory_service_pipeline():
    print("🚀 SAGE MemoryService Pipeline Demo")
    print("=" * 60)

    # Skip in test mode (CI)
    if os.getenv("SAGE_EXAMPLES_MODE") == "test":
        print("🧪 测试模式：跳过 MemoryService 示例（需要FAISS依赖）")
        return

    # Verify FAISS availability early to avoid runtime failure inside service
    try:
        import faiss  # noqa: F401
    except Exception:
        print("❌ FAISS not installed. Please run: pip install faiss-cpu")
        return

    print("📋 初始化SAGE环境和服务注册...")
    env = LocalEnvironment("memory_service_pipeline")

    # Register services (KV, VDB, Graph, Memory)
    kv_factory = create_kv_service_factory(
        service_name="kv_service", backend_type="memory", max_size=10000
    )
    env.register_service_factory("kv_service", kv_factory)

    vdb_factory = create_vdb_service_factory(
        service_name="vdb_service", embedding_dimension=384, index_type="IndexFlatL2"
    )
    env.register_service_factory("vdb_service", vdb_factory)

    graph_factory = create_graph_service_factory(
        service_name="graph_service",
        backend_type="memory",
        max_nodes=10000,
        max_relationships=50000,
    )
    env.register_service_factory("graph_service", graph_factory)

    memory_factory = create_memory_service_factory(
        service_name="memory_service",
        kv_service_name="kv_service",
        vdb_service_name="vdb_service",
        graph_service_name="graph_service",
        default_vector_dimension=384,
        enable_knowledge_graph=True,
    )
    env.register_service_factory("memory_service", memory_factory)

    # Data and session
    conversations = create_sample_conversations()
    session_id = "test_session_001"

    # Stage 1: store memories
    (
        env.from_batch(conversations)
        .map(StoreMemories, session_id=session_id, parallelism=1)
        .sink(PrintStoreResult, parallelism=1)
    )

    # Stage 2: queries
    queries = ["Python编程学习", "健康和疲惫", "机器学习建议"]
    (
        env.from_batch(queries)
        .map(SearchMemories, session_id=session_id, top_k=3, parallelism=1)
        .sink(PrintSearchResult, parallelism=1)
    )

    # Submit and wait for completion
    print("\n▶️  提交管道...")
    env.submit(autostop=True)
    print("✅ 管道执行完成")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    try:
        run_memory_service_pipeline()
    except KeyboardInterrupt:
        print("\n👋 已中断")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback

        traceback.print_exc()
