#!/usr/bin/env python3
"""
Workload 4 双流源配置示例

演示三种配置方式：
1. 直接使用配置类
2. 从 YAML 文件加载
3. 使用自定义知识库
"""

import sys
from pathlib import Path

# 添加 workload4 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

import yaml


def example_1_direct_config():
    """示例 1: 直接使用配置类"""
    print("=" * 80)
    print("示例 1: 直接使用配置类")
    print("=" * 80)

    from workload4 import Workload4Config

    # 创建配置
    config = Workload4Config(
        # 基础配置
        num_tasks=50,
        query_qps=20.0,
        doc_qps=15.0,
        # 数据分布
        query_type_distribution={
            "factual": 0.5,
            "analytical": 0.3,
            "exploratory": 0.2,
        },
        category_distribution={
            "finance": 0.4,
            "technology": 0.4,
            "general": 0.2,
            "healthcare": 0.0,  # 不生成医疗类
        },
        # Embedding 服务
        embedding_base_url="http://11.11.11.7:8090/v1",
        embedding_model="BAAI/bge-large-en-v1.5",
        # 随机种子
        seed=42,
    )

    # 验证配置
    try:
        config.validate()
        print("✅ 配置验证通过")
    except AssertionError as e:
        print(f"❌ 配置错误: {e}")
        return

    # 显示配置
    print("\n配置详情:")
    print(f"  任务数量: {config.num_tasks}")
    print(f"  Query QPS: {config.query_qps}")
    print(f"  Document QPS: {config.doc_qps}")
    print(f"  预计文档数: {int(config.num_tasks / config.query_qps * config.doc_qps)}")
    print(f"  预计运行时长: {config.num_tasks / config.query_qps:.1f}s")
    print(f"\n  查询类型分布: {config.query_type_distribution}")
    print(f"  类别分布: {config.category_distribution}")

    # 使用配置创建源算子
    from workload4 import (
        create_document_source,
        create_embedding_precompute,
        create_query_source,
    )

    print("\n创建源算子...")
    query_source = create_query_source(config.__dict__)
    doc_source = create_document_source(config.__dict__)
    embedding_precompute = create_embedding_precompute(config.__dict__)

    print("✅ 源算子创建成功")
    print(f"  Query Source: {query_source.__class__.__name__}")
    print(f"  Document Source: {doc_source.__class__.__name__}")
    print(f"  Embedding Precompute: {embedding_precompute.__class__.__name__}")


def example_2_yaml_config():
    """示例 2: 从 YAML 文件加载配置"""
    print("\n" + "=" * 80)
    print("示例 2: 从 YAML 文件加载配置")
    print("=" * 80)

    from workload4 import Workload4Config

    # 检查配置文件是否存在
    config_file = Path(__file__).parent / "workload4_config.yaml"
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        print("   请先创建配置文件")
        return

    print(f"加载配置文件: {config_file}")

    # 加载 YAML 配置
    with open(config_file) as f:
        config_dict = yaml.safe_load(f)

    # 创建配置对象
    config = Workload4Config(**config_dict)

    print("✅ 配置加载成功")
    print("\n配置详情:")
    print(f"  任务数量: {config.num_tasks}")
    print(f"  QPS: Query {config.query_qps} / Doc {config.doc_qps}")
    print(f"  节点数: {config.num_nodes}")
    print(f"  Embedding 服务: {config.embedding_base_url}")
    print(f"  知识库路径: {config.knowledge_base_path or '(使用内置模板)'}")


def example_3_custom_knowledge_base():
    """示例 3: 使用自定义知识库"""
    print("\n" + "=" * 80)
    print("示例 3: 使用自定义知识库")
    print("=" * 80)

    from workload4 import Workload4DocumentSource

    # 创建自定义知识库
    knowledge_base = [
        {
            "id": "sage_001",
            "title": "SAGE Framework Overview",
            "content": "SAGE is a Python 3.10+ framework for building AI/LLM data processing pipelines with declarative dataflow.",
        },
        {
            "id": "sage_002",
            "title": "Workload 4 Architecture",
            "content": "Workload 4 features dual-stream input, 60s semantic join, dual-path VDB retrieval, and graph memory traversal.",
        },
        {
            "id": "sage_003",
            "title": "Distributed Scheduling",
            "content": "SAGE supports multiple scheduler strategies: FIFO, LoadAware, Priority, RoundRobin for distributed task execution.",
        },
    ]

    print(f"创建知识库: {len(knowledge_base)} 个文档")
    for doc in knowledge_base:
        print(f"  - [{doc['id']}] {doc['title']}")

    # 使用知识库创建文档源
    doc_source = Workload4DocumentSource(
        num_docs=10,  # 会循环采样知识库
        qps=10.0,
        knowledge_base=knowledge_base,
        seed=42,
    )

    print("\n生成文档示例:")
    count = 0
    for doc in doc_source.execute():
        if doc is not None and count < 3:
            print(f"\n  文档 {count + 1}:")
            print(f"    ID: {doc.doc_id}")
            print(f"    Category: {doc.doc_category}")
            print(f"    Source: {doc.metadata.get('source')}")
            print(f"    Title: {doc.metadata.get('title')}")
            print(f"    Content: {doc.doc_text[:80]}...")
            count += 1
        elif doc is None:
            break


def example_4_load_from_file():
    """示例 4: 从文件加载知识库"""
    print("\n" + "=" * 80)
    print("示例 4: 从文件加载知识库")
    print("=" * 80)

    import json

    from workload4 import Workload4DocumentSource

    # 创建示例知识库文件
    kb_file = Path("/tmp/test_knowledge_base.jsonl")

    print(f"创建示例知识库文件: {kb_file}")
    with open(kb_file, "w", encoding="utf-8") as f:
        for i in range(5):
            doc = {
                "id": f"test_{i:03d}",
                "title": f"Test Document {i}",
                "content": f"This is test document number {i} with some example content.",
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # 从文件加载
    print("从文件加载知识库...")
    knowledge_base = []
    with open(kb_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                knowledge_base.append(json.loads(line))

    print(f"✅ 加载成功: {len(knowledge_base)} 个文档")

    # 使用加载的知识库
    doc_source = Workload4DocumentSource(
        num_docs=10,
        qps=10.0,
        knowledge_base=knowledge_base,
    )

    print("文档源创建成功，将生成 10 个文档（循环采样）")

    # 清理
    kb_file.unlink()
    print(f"清理临时文件: {kb_file}")


def example_5_pipeline_integration():
    """示例 5: Pipeline 集成（仅展示代码结构）"""
    print("\n" + "=" * 80)
    print("示例 5: Pipeline 集成示例（代码展示）")
    print("=" * 80)

    code = """
from sage.kernel.runtime import RemoteEnvironment
from workload4 import (
    Workload4Config,
    Workload4QuerySource,
    Workload4DocumentSource,
    EmbeddingPrecompute,
)

# 1. 创建配置
config = Workload4Config(
    num_tasks=100,
    query_qps=40.0,
    doc_qps=25.0,
    use_remote=True,
    num_nodes=8,
)

# 2. 创建分布式环境
env = RemoteEnvironment(
    name="workload4_dual_stream",
    num_nodes=config.num_nodes,
    head_node=config.head_node,
)

# 3. 构建查询流
query_stream = env.from_source(
    Workload4QuerySource,
    num_tasks=config.num_tasks,
    qps=config.query_qps,
    seed=42,
)
query_stream = query_stream.map(
    EmbeddingPrecompute,
    embedding_base_url=config.embedding_base_url,
    embedding_model=config.embedding_model,
)

# 4. 构建文档流
doc_stream = env.from_source(
    Workload4DocumentSource,
    num_docs=int(config.num_tasks / config.query_qps * config.doc_qps),
    qps=config.doc_qps,
    seed=42,
)
doc_stream = doc_stream.map(
    EmbeddingPrecompute,
    embedding_base_url=config.embedding_base_url,
    embedding_model=config.embedding_model,
)

# 5. 语义 Join（Task 3 实现后可用）
# from workload4 import SemanticJoinOperator
# joined = query_stream.join(
#     doc_stream,
#     SemanticJoinOperator(
#         window_seconds=config.join_window_seconds,
#         threshold=config.join_threshold,
#     ),
# )

# 6. 后续 stages...
# VDB 检索、图遍历、聚类、重排序、生成等

# 7. 执行 Pipeline
env.submit(autostop=True)
"""

    print("Pipeline 集成代码结构:")
    print(code)
    print("\n注意: 完整 Pipeline 需要 Task 3-10 实现完成后才能运行")


def main():
    """运行所有示例"""
    examples = [
        ("直接配置", example_1_direct_config),
        ("YAML 配置", example_2_yaml_config),
        ("自定义知识库", example_3_custom_knowledge_base),
        ("从文件加载", example_4_load_from_file),
        ("Pipeline 集成", example_5_pipeline_integration),
    ]

    print("\n" + "=" * 80)
    print("Workload 4 双流源配置示例")
    print("=" * 80)
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print()

    choice = input("选择示例 (1-5, 或 'all' 运行全部): ").strip().lower()
    print()

    if choice == "all":
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"❌ 示例 '{name}' 运行失败: {e}")
            print()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        idx = int(choice) - 1
        try:
            examples[idx][1]()
        except Exception as e:
            print(f"❌ 运行失败: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("无效选择，运行第一个示例...")
        examples[0][1]()


if __name__ == "__main__":
    main()
