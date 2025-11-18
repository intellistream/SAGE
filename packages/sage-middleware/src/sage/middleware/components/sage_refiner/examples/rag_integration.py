"""
RAG管道集成示例
==============

演示如何将Refiner集成到SAGE RAG管道中。
"""

# 注意：这个示例需要完整的SAGE环境才能运行
# 这里提供完整的代码结构供参考


def rag_pipeline_with_refiner():
    """
    RAG管道集成Refiner的完整示例

    管道流程:
    1. 批量数据源
    2. 向量检索 (Retriever)
    3. 上下文压缩 (Refiner) ← 新增
    4. Prompt构建 (Promptor)
    5. 生成答案 (Generator)
    6. 评估 (Evaluators)
    """

    # ===== 配置 =====
    config = {
        # 数据源配置
        "source": {
            "dataset_path": "your_dataset_path",
            "split": "test",
            "batch_size": 10,
        },
        # 检索器配置
        "retriever": {
            "top_k": 10,
            "db_path": "./chroma_db",
            "collection_name": "documents",
        },
        # Refiner配置 - 关键部分
        "refiner": {
            "algorithm": "simple",  # 或 "long_refiner"
            "budget": 4000,  # token预算
            "enable_cache": True,
            "enable_profile": True,  # 启用性能分析
            # LongRefiner配置（如果使用）
            # "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
            # "query_analysis_module_lora_path": "/path/to/lora/query",
            # ...
        },
        # Promptor配置
        "promptor": {"template": "qa", "max_length": 8000},
        # Generator配置
        "generator": {"model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 512},
        # 评估配置
        "evaluate": {},
    }

    # ===== 构建管道 =====
    # 这个代码需要在SAGE环境中运行
    """
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.libs.foundation.io.batch import JSONLBatch
    from sage.middleware.operators.rag import ChromaRetriever
    from sage.middleware.operators.rag import QAPromptor
    from sage.middleware.operators.rag import OpenAIGenerator
    from sage.middleware.operators.rag import F1Evaluate, CompressionRateEvaluate

    env = LocalEnvironment()

    (
        env.from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(RefinerAdapter, config["refiner"])  # ← 添加Refiner
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .map(F1Evaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])  # 评估压缩率
    )

    env.submit()
    """

    print("RAG管道配置示例:")
    print("=" * 60)
    import json

    print(json.dumps(config, indent=2))
    print("=" * 60)
    print("\n要运行此管道，请:")
    print("1. 确保安装了完整的SAGE环境")
    print("2. 准备好数据集和向量数据库")
    print("3. 如果使用LongRefiner，准备好模型和LoRA权重")
    print("4. 取消注释上面的代码并运行")


def conditional_refiner():
    """
    条件性使用Refiner

    根据检索结果的长度决定是否启用压缩。
    """
    print("\n条件性Refiner示例:")
    print("=" * 60)

    # 示例配置
    config_with_refiner = {
        "enable_refiner": True,  # 通过flag控制
        "refiner": {"algorithm": "simple", "budget": 2000},
    }

    config_without_refiner = {
        "enable_refiner": False,  # 禁用
        "refiner": {"algorithm": "none"},  # 或使用none算法
    }

    print("配置1 - 启用Refiner:")
    import json

    print(json.dumps(config_with_refiner, indent=2))

    print("\n配置2 - 禁用Refiner:")
    print(json.dumps(config_without_refiner, indent=2))

    print("\n可以在运行时动态切换配置!")


def multi_stage_compression():
    """
    多阶段压缩示例

    在管道的不同阶段使用不同的压缩策略。
    """
    print("\n多阶段压缩示例:")
    print("=" * 60)

    config = {
        # 第一次压缩：粗筛选
        "refiner_1": {"algorithm": "simple", "budget": 8000},
        # 第二次压缩：精筛选（使用LongRefiner）
        "refiner_2": {"algorithm": "long_refiner", "budget": 4000},
    }

    print("两阶段压缩配置:")
    import json

    print(json.dumps(config, indent=2))

    print("\n管道结构:")
    print("  Retriever (top_k=20)")
    print("  → Refiner 1 (Simple, budget=8000)  # 粗筛选")
    print("  → Refiner 2 (LongRefiner, budget=4000)  # 精筛选")
    print("  → Generator")


if __name__ == "__main__":
    rag_pipeline_with_refiner()
    conditional_refiner()
    multi_stage_compression()

    print("\n" + "=" * 60)
    print("RAG集成示例完成!")
    print("=" * 60)
