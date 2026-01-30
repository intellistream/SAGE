"""
Workload 4 - Task 5: 图遍历示例

展示如何使用图内存服务和检索算子。
"""

import numpy as np

try:
    from graph_memory import (
        GraphMemoryRetriever,
        GraphMemoryService,
        build_knowledge_graph,
        register_graph_memory_service,
    )
    from models import DocumentEvent, JoinedEvent, QueryEvent
except ImportError:
    from workload4.graph_memory import (
        GraphMemoryRetriever,
        GraphMemoryService,
        build_knowledge_graph,
    )
    from workload4.models import DocumentEvent, JoinedEvent, QueryEvent


def example_1_graph_service_basic():
    """示例 1: 基础图服务使用"""
    print("=" * 80)
    print("示例 1: 基础图服务使用")
    print("=" * 80)

    # 1. 准备知识库
    np.random.seed(42)
    knowledge_base = []

    topics = ["AI", "ML", "DL", "NLP", "CV", "RL", "KG", "IR", "DB", "HPC"]

    for i, topic in enumerate(topics):
        # 为每个主题生成 embedding
        embedding = np.random.randn(128).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        knowledge_base.append(
            {
                "node_id": f"topic_{topic.lower()}",
                "content": f"Knowledge about {topic} ({topic} related content)",
                "embedding": embedding.tolist(),
                "node_type": "concept",
            }
        )

    # 2. 创建并构建图服务
    service = GraphMemoryService(
        config={},
        embedding_dim=128,
        similarity_threshold=0.5,  # 较低阈值，构建更多边
    )

    service.build_graph(knowledge_base)

    print("✓ 图构建完成:")
    print(f"  - 节点数: {service.graph.number_of_nodes()}")
    print(f"  - 边数: {service.graph.number_of_edges()}")
    print()

    # 3. 执行搜索
    query_emb = knowledge_base[0]["embedding"]  # 使用第一个主题的 embedding

    results = service.search(
        query_embedding=query_emb,
        max_depth=2,
        max_nodes=5,
        beam_width=3,
    )

    print(f"✓ 搜索结果 (返回 {len(results)} 个节点):")
    for i, result in enumerate(results, 1):
        path_str = " -> ".join(result["path"])
        print(
            f"  {i}. {result['node_id']} (深度={result['depth']}, "
            f"相关度={result['relevance_score']:.3f})"
        )
        print(f"     路径: {path_str}")
        print(f"     内容: {result['content'][:50]}...")
        print()


def example_2_graph_with_documents():
    """示例 2: 从文档构建知识图"""
    print("=" * 80)
    print("示例 2: 从文档构建知识图")
    print("=" * 80)

    # 模拟一些技术文档
    documents = [
        {
            "node_id": "doc_transformer",
            "content": "Transformer architecture uses self-attention mechanism",
            "embedding": np.random.randn(64).tolist(),
        },
        {
            "node_id": "doc_bert",
            "content": "BERT is based on Transformer encoder",
            "embedding": np.random.randn(64).tolist(),
        },
        {
            "node_id": "doc_gpt",
            "content": "GPT uses Transformer decoder for generation",
            "embedding": np.random.randn(64).tolist(),
        },
        {
            "node_id": "doc_attention",
            "content": "Attention mechanism computes weighted sum of values",
            "embedding": np.random.randn(64).tolist(),
        },
        {
            "node_id": "doc_llm",
            "content": "Large Language Models are trained on massive corpora",
            "embedding": np.random.randn(64).tolist(),
        },
    ]

    # 归一化 embeddings
    for doc in documents:
        emb = np.array(doc["embedding"])
        doc["embedding"] = (emb / np.linalg.norm(emb)).tolist()

    # 构建图
    graph = build_knowledge_graph(
        documents,
        embedding_dim=64,
        similarity_threshold=0.3,
    )

    print("✓ 知识图统计:")
    print(f"  - 节点数: {graph.number_of_nodes()}")
    print(f"  - 边数: {graph.number_of_edges()}")
    print()

    # 打印边的权重
    print("✓ 图的边:")
    for source, target, data in graph.edges(data=True):
        print(f"  {source} -> {target} (权重={data['weight']:.3f})")
    print()


def example_3_graph_retriever_operator():
    """示例 3: 图遍历算子使用"""
    print("=" * 80)
    print("示例 3: 图遍历算子使用")
    print("=" * 80)

    # 创建算子
    retriever = GraphMemoryRetriever(
        max_depth=3,
        max_nodes=10,
        beam_width=5,
    )

    print("✓ 算子配置:")
    print(f"  - 最大深度: {retriever.max_depth}")
    print(f"  - 最大节点数: {retriever.max_nodes}")
    print(f"  - Beam 宽度: {retriever.beam_width}")
    print()

    # 创建测试数据
    query = QueryEvent(
        query_id="query_1",
        query_text="What is machine learning?",
        query_type="factual",
        category="technology",
        timestamp=1000.0,
        embedding=np.random.randn(128).tolist(),
    )

    doc = DocumentEvent(
        doc_id="doc_1",
        doc_text="Machine learning is a subset of AI",
        doc_category="technology",
        timestamp=1001.0,
        embedding=np.random.randn(128).tolist(),
    )

    joined = JoinedEvent(
        joined_id="query_1_1002.0",
        query=query,
        matched_docs=[doc],
        join_timestamp=1002.0,
        semantic_score=0.85,
    )

    print("✓ 输入数据:")
    print(f"  - Query ID: {joined.query.query_id}")
    print(f"  - Query Text: {joined.query.query_text}")
    print(f"  - Embedding 维度: {len(joined.query.embedding)}")
    print()

    # 注意: execute() 需要在实际 SAGE 环境中调用服务
    print("✓ 算子可以在 SAGE Pipeline 中使用:")
    print("  graph_results = joined.map(GraphMemoryRetriever(...))")
    print()


def example_4_advanced_bfs_traversal():
    """示例 4: 高级 BFS 遍历"""
    print("=" * 80)
    print("示例 4: 高级 BFS 遍历（展示路径）")
    print("=" * 80)

    # 创建一个小型知识图
    np.random.seed(123)
    knowledge_base = []

    # 创建分层结构: 根节点 -> 子节点 -> 叶子节点
    levels = [
        ["root"],
        ["child_1", "child_2", "child_3"],
        ["leaf_1", "leaf_2", "leaf_3", "leaf_4"],
    ]

    idx = 0
    for level_idx, level in enumerate(levels):
        for node_name in level:
            embedding = np.random.randn(32).astype(np.float32)
            # 同层节点相似度高一些
            if level_idx > 0:
                embedding += 0.3 * np.random.randn(32)
            embedding = embedding / np.linalg.norm(embedding)

            knowledge_base.append(
                {
                    "node_id": node_name,
                    "content": f"Content of {node_name}",
                    "embedding": embedding.tolist(),
                    "node_type": "level_" + str(level_idx),
                }
            )
            idx += 1

    # 构建服务
    service = GraphMemoryService(
        config={},
        embedding_dim=32,
        similarity_threshold=0.4,
    )
    service.build_graph(knowledge_base)

    print("✓ 分层知识图:")
    print("  - 第 0 层 (root): 1 个节点")
    print("  - 第 1 层 (child): 3 个节点")
    print("  - 第 2 层 (leaf): 4 个节点")
    print(f"  - 总边数: {service.graph.number_of_edges()}")
    print()

    # 从根节点开始遍历
    root_embedding = knowledge_base[0]["embedding"]

    results = service.search(
        query_embedding=root_embedding,
        max_depth=2,
        max_nodes=8,
        beam_width=3,
    )

    print("✓ BFS 遍历结果 (从 root 开始):")
    for i, result in enumerate(results, 1):
        indent = "  " * result["depth"]
        path_str = " -> ".join(result["path"])
        print(
            f"{i}. {indent}{result['node_id']} "
            f"(深度={result['depth']}, 分数={result['relevance_score']:.3f})"
        )
        print(f"   {indent}路径: {path_str}")
    print()


def example_5_service_registration():
    """示例 5: 服务注册（伪代码）"""
    print("=" * 80)
    print("示例 5: 在 SAGE 环境中注册图内存服务")
    print("=" * 80)

    print("""
在实际 SAGE Pipeline 中注册服务的步骤:

1. 准备知识库数据:
   knowledge_base = [
       {"node_id": "...", "content": "...", "embedding": [...], ...},
       ...
   ]

2. 在 RemoteEnvironment 中注册服务:
   from workload4.graph_memory import register_graph_memory_service

   success = register_graph_memory_service(
       env=remote_env,
       knowledge_base=knowledge_base,
       embedding_dim=1024,
       similarity_threshold=0.7,
       service_name="graph_memory",
   )

3. 在 Pipeline 中使用算子:
   graph_results = joined_stream.map(
       GraphMemoryRetriever(
           max_depth=3,
           max_nodes=200,
           beam_width=10,
           service_name="graph_memory",
       )
   )

4. 算子会自动调用服务:
   - call_service("graph_memory", "search", ...)
   - 返回 list[GraphMemoryResult]
    """)
    print()


if __name__ == "__main__":
    print("\n" + "🔍 Workload 4 图遍历示例" + "\n")

    # 运行所有示例
    example_1_graph_service_basic()
    example_2_graph_with_documents()
    example_3_graph_retriever_operator()
    example_4_advanced_bfs_traversal()
    example_5_service_registration()

    print("=" * 80)
    print("✓ 所有示例执行完成")
    print("=" * 80)
