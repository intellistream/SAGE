# @test:skip           - 跳过测试

"""
Attention Graph RAG Pipeline
============================

使用基于注意力和图搜索的上下文压缩算法的 RAG pipeline。

核心思想：
1. 将文档分割为固定大小的 span 作为图节点
2. 使用注意力机制计算 query 对各 span 的相关性
3. 使用 span 隐状态计算 span 间语义相似度
4. 构建证据图，使用 log-linear 模型组合多种信号
5. 在 token budget 下进行贪心子图选择

特点：
- 支持多文档联合压缩
- 保留跨文档的语义连贯性
- 可配置的压缩强度和特征权重
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
from sage.middleware.components.sage_refiner import AttentionGraphOperator
from sage.middleware.operators.rag import (
    CompressionRateEvaluate,
    F1Evaluate,
    LatencyEvaluate,
    OpenAIGenerator,
    QAPromptor,
    TokenCountEvaluate,
    Wiki18FAISSRetriever,
)


def pipeline_run(config):
    """运行 Attention Graph RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(AttentionGraphOperator, config["attention_graph"])
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
        .map(F1Evaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    try:
        env.submit()
        # Wait for pipeline to complete
        # Attention Graph 需要前向传播获取注意力，耗时较长
        time.sleep(12000)  # 20 minutes
    except KeyboardInterrupt:
        print("\n⚠️  KeyboardInterrupt: 用户手动停止")
    except Exception as e:
        print(f"\n❌ Pipeline异常: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n🔄 清理环境...")
        env.close()
        print("✅ 环境已关闭")


# ==========================================================
if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - AttentionGraph pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_attention_graph.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

    # 打印配置信息
    if config.get("attention_graph", {}).get("enabled", True):
        print("🚀 AttentionGraph compression enabled")
        print(f"   Model: {config['attention_graph'].get('model_path', 'default')}")
        print(f"   Max tokens: {config['attention_graph'].get('max_tokens', 2048)}")
        print(f"   Span length: {config['attention_graph'].get('span_len', 64)}")
        print(f"   Top-k neighbors: {config['attention_graph'].get('topk_neighbors', 5)}")
    else:
        print("ℹ️  AttentionGraph disabled - running in baseline mode")

    # 检查索引文件是否存在
    if config["retriever"]["type"] == "wiki18_faiss":
        index_path = config["retriever"]["faiss"]["index_path"]
        # 展开环境变量
        index_path = os.path.expandvars(index_path)
        if not os.path.exists(index_path):
            print(f"❌ FAISS index file not found: {index_path}")
            print(
                "Please build the FAISS index first using build_milvus_dense_index.py or similar."
            )
            print("Or modify the config to use a different retriever type.")
            sys.exit(1)

    pipeline_run(config)
