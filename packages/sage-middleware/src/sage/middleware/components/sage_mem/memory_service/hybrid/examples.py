"""Hybrid Services 使用示例

演示如何使用 hybrid.multi_index 服务实现：
1. Mem0 基础版（VDB + KV）
2. Mem0ᵍ 图增强版（VDB + KV + Graph）
3. EmotionalRAG 双向量（语义向量 + 情感向量）
4. 自定义多索引组合

Author: SAGE Team
Created: 2025-12-24
"""

from __future__ import annotations

import numpy as np


def example_mem0_basic():
    """示例1: Mem0 基础版（VDB + KV）"""
    print("\n" + "=" * 60)
    print("示例1: Mem0 基础版（VDB + KV）")
    print("=" * 60)

    from sage.middleware.components.sage_mem.memory_service.hybrid import (
        MultiIndexMemoryService,
    )

    # 创建服务（默认配置：语义向量 + 关键词）
    service = MultiIndexMemoryService(
        indexes=[
            {"name": "semantic", "type": "vdb", "dim": 768},
            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
        ],
        fusion_strategy="rrf",
        rrf_k=60,
        collection_name="mem0_basic",
    )

    # 插入记忆（被动模式，自动检测相似项）
    vector = np.random.rand(768).astype(np.float32)
    memory_id = service.insert(
        entry="今天天气很好",
        vector=vector,
        metadata={"source": "user"},
        insert_mode="passive",  # 被动模式，触发 CRUD 检测
    )

    print(f"✓ 插入记忆: {memory_id[:16]}...")

    # 检查被动插入状态（供 PostInsert 使用）
    status = service.get_status()
    if status["pending_action"] == "crud":
        print(f"✓ 检测到相似项: {len(status['pending_similar'])} 个")
        service.clear_pending_status()
    else:
        print("✓ 无相似项，直接插入")

    # 多路融合检索
    query_vector = np.random.rand(768).astype(np.float32)
    results = service.retrieve(
        query="天气",
        vector=query_vector,
        top_k=5,
    )

    print(f"✓ 检索结果: {len(results)} 条")
    for r in results[:2]:
        print(f"  - {r['text'][:20]}... (score: {r['score']:.3f})")

    # 统计信息
    stats = service.get_stats()
    print("\n统计信息:")
    print(f"  - 总记忆数: {stats['memory_count']}")
    print(f"  - 融合策略: {stats['fusion_strategy']}")
    print(f"  - 索引数量: {stats['index_count']}")
    for idx_name, idx_stats in stats["indexes"].items():
        print(f"  - {idx_name}: {idx_stats['type']} ({idx_stats['count']} 条)")


def example_mem0_graph():
    """示例2: Mem0ᵍ 图增强版（VDB + KV + Graph）"""
    print("\n" + "=" * 60)
    print("示例2: Mem0ᵍ 图增强版（VDB + KV + Graph）")
    print("=" * 60)

    from sage.middleware.components.sage_mem.memory_service.hybrid import (
        MultiIndexMemoryService,
    )

    # 创建图增强版服务
    service = MultiIndexMemoryService(
        indexes=[
            {"name": "semantic", "type": "vdb", "dim": 768},
            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
            {"name": "entity_graph", "type": "graph"},
        ],
        fusion_strategy="rrf",
        collection_name="mem0_graph",
        graph_enabled=True,
        entity_extraction=True,
        relation_extraction=True,
    )

    # 插入带图边的记忆
    vector = np.random.rand(768).astype(np.float32)
    memory_id = service.insert(
        entry="张三在北京工作",
        vector=vector,
        metadata={
            "source": "user",
            "edges": [
                ("entity_1", 0.9, "works_in"),  # 张三 -> 北京
            ],
        },
    )

    print(f"✓ 插入带图边的记忆: {memory_id[:16]}...")

    # 图检索（从起始节点开始）
    results = service.retrieve(
        query="北京",
        vector=vector,
        metadata={
            "start_node": "entity_1",  # 从实体节点开始检索
            "indexes": ["semantic", "keyword", "entity_graph"],
        },
        top_k=5,
    )

    print(f"✓ 图增强检索结果: {len(results)} 条")


def example_emotional_rag():
    """示例3: EmotionalRAG 双向量（语义 + 情感）"""
    print("\n" + "=" * 60)
    print("示例3: EmotionalRAG 双向量（语义 + 情感）")
    print("=" * 60)

    from sage.middleware.components.sage_mem.memory_service.hybrid import (
        MultiIndexMemoryService,
    )

    # 创建双向量索引服务
    service = MultiIndexMemoryService(
        indexes=[
            {"name": "semantic", "type": "vdb", "dim": 768},
            {"name": "emotional", "type": "vdb", "dim": 128},
            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
        ],
        fusion_strategy="weighted",
        fusion_weights={
            "semantic": 0.5,
            "emotional": 0.3,
            "keyword": 0.2,
        },
        collection_name="emotional_rag",
    )

    # 插入带多向量的记忆
    semantic_vec = np.random.rand(768).astype(np.float32)
    emotional_vec = np.random.rand(128).astype(np.float32)

    memory_id = service.insert(
        entry="我今天非常开心！",
        vector=semantic_vec,  # 默认向量
        metadata={
            "vectors": {
                "semantic": semantic_vec,
                "emotional": emotional_vec,
            },
            "emotion": "happy",
        },
    )

    print(f"✓ 插入双向量记忆: {memory_id[:16]}...")

    # 双向量检索
    query_semantic = np.random.rand(768).astype(np.float32)
    query_emotional = np.random.rand(128).astype(np.float32)

    results = service.retrieve(
        query="开心",
        vector=query_semantic,
        metadata={
            "vectors": {
                "semantic": query_semantic,
                "emotional": query_emotional,
            },
        },
        top_k=5,
    )

    print(f"✓ 双向量融合检索结果: {len(results)} 条")


def example_from_config():
    """示例4: 从配置创建 Service（Pipeline 集成）"""
    print("\n" + "=" * 60)
    print("示例4: 从配置创建 Service（Pipeline 集成）")
    print("=" * 60)

    # Mock 配置对象
    class MockConfig:
        def __init__(self):
            self.data = {
                "services": {
                    "hybrid.multi_index": {
                        "indexes": [
                            {"name": "semantic", "type": "vdb", "dim": 768},
                            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
                        ],
                        "fusion_strategy": "rrf",
                        "rrf_k": 60,
                        "collection_name": "hybrid_memory",
                        "graph_enabled": False,
                    },
                },
            }

        def get(self, key, default=None):
            keys = key.split(".")
            value = self.data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value

    config = MockConfig()

    # 从 Registry 获取 Service 类
    from sage.middleware.components.sage_mem.memory_service import (
        MemoryServiceRegistry,
    )

    service_class = MemoryServiceRegistry.get("hybrid.multi_index")

    # 从配置创建 ServiceFactory
    factory = service_class.from_config("hybrid.multi_index", config)

    print("✓ ServiceFactory 创建成功:")
    print(f"  - service_name: {factory.service_name}")
    print(f"  - service_class: {factory.service_class.__name__}")
    print(f"  - kwargs: {list(factory.service_kwargs.keys())}")

    # 在 Pipeline 中使用（示意）
    print("\n在 Pipeline 中注册:")
    print("  env.register_service_factory('hybrid.multi_index', factory)")


def example_crud_workflow():
    """示例5: CRUD 决策工作流（Mem0 核心功能）"""
    print("\n" + "=" * 60)
    print("示例5: CRUD 决策工作流（Mem0 核心功能）")
    print("=" * 60)

    from sage.middleware.components.sage_mem.memory_service.hybrid import (
        MultiIndexMemoryService,
    )

    service = MultiIndexMemoryService(
        indexes=[
            {"name": "semantic", "type": "vdb", "dim": 768},
            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
        ],
        fusion_strategy="rrf",
        collection_name="mem0_crud",
    )

    # 第一次插入
    vector1 = np.random.rand(768).astype(np.float32)
    id1 = service.insert(
        entry="今天是星期一",
        vector=vector1,
        insert_mode="passive",
    )
    print(f"✓ 首次插入: {id1[:16]}... (无相似项)")

    # 第二次插入（相似内容）
    vector2 = vector1 + np.random.rand(768).astype(np.float32) * 0.01  # 相似向量
    id2 = service.insert(
        entry="今天是周一",
        vector=vector2,
        insert_mode="passive",
    )

    # 检查待处理状态
    status = service.get_status()
    print(f"\n✓ 第二次插入: {id2[:16]}...")
    if status["pending_action"] == "crud":
        print(f"  - 检测到相似项: {len(status['pending_similar'])} 个")
        print(f"  - 新条目: {status['pending_items'][0]['text']}")
        print(f"  - 最相似的已有条目: {status['pending_similar'][0]['text']}")
        print("\n  PostInsert 可以基于此状态决定:")
        print("  - CREATE: 创建新条目")
        print("  - UPDATE: 更新已有条目")
        print("  - DELETE: 删除重复条目")

        # 模拟 PostInsert 决策后清除状态
        service.clear_pending_status()
        print("\n✓ 状态已清除（决策完成）")
    else:
        print("  - 无相似项")


if __name__ == "__main__":
    print("=" * 60)
    print("Hybrid Services 使用示例")
    print("=" * 60)

    # 注意：这些示例需要完整的 SAGE 环境和依赖
    # 如果遇到 C++ 扩展错误，请使用 ksage conda 环境运行

    try:
        example_mem0_basic()
        example_mem0_graph()
        example_emotional_rag()
        example_from_config()
        example_crud_workflow()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n提示: 请在 ksage conda 环境中运行:")
        print("  conda run -n ksage python <script>.py")
        import traceback

        traceback.print_exc()
