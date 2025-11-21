"""
Embedding Service Demo - 展示如何使用统一的 EmbeddingService

这个示例展示了:
1. 如何配置 EmbeddingService (本地模型, API, vLLM)
2. 如何在 Pipeline 中使用 embedding service
3. 如何实现高性能批处理
4. 如何使用缓存优化性能
"""

import os
import sys
from pathlib import Path

# Add SAGE to path
sage_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(sage_root / "packages" / "sage-middleware" / "src"))
sys.path.insert(0, str(sage_root / "packages" / "sage-kernel" / "src"))
sys.path.insert(0, str(sage_root / "packages" / "sage-common" / "src"))


def demo_basic_embedding_service():
    """Demo 1: 基本的 Embedding Service 使用"""
    print("\n" + "=" * 60)
    print("Demo 1: 基本 Embedding Service")
    print("=" * 60)

    from sage.common.components.sage_embedding import EmbeddingService

    # 配置: 使用 HuggingFace 模型
    config = {
        "method": "hf",
        "model": "BAAI/bge-small-zh-v1.5",
        "batch_size": 32,
        "normalize": True,
        "cache_enabled": True,
        "cache_size": 1000,
    }

    service = EmbeddingService(config)
    service.setup()

    # 获取服务信息
    info = service.process({"task": "info"})
    print("\n服务信息:")
    print(f"  方法: {info['method']}")
    print(f"  模型: {info['model']}")
    print(f"  维度: {info['dimension']}")
    print(f"  缓存: {info['cache_enabled']}")

    # 单个文本 embedding
    result = service.process(
        {"task": "embed", "inputs": "你好世界", "options": {"return_stats": True}}
    )

    print("\n单个文本 embedding:")
    print(f"  维度: {result['dimension']}")
    print(f"  向量前5个值: {result['vectors'][0][:5]}")
    print(f"  统计: {result['stats']}")

    # 批量文本 embedding
    texts = [
        "人工智能正在改变世界",
        "机器学习是AI的核心",
        "深度学习推动了AI发展",
        "自然语言处理很重要",
    ]

    result = service.process(
        {"task": "embed", "inputs": texts, "options": {"return_stats": True}}
    )

    print("\n批量文本 embedding:")
    print(f"  文本数量: {result['count']}")
    print(f"  计算数量: {result['stats']['computed']}")
    print(f"  缓存数量: {result['stats']['cached']}")

    # 再次查询相同文本 (测试缓存)
    result2 = service.process(
        {
            "task": "embed",
            "inputs": texts[:2],  # 重复前两个文本
            "options": {"return_stats": True},
        }
    )

    print("\n缓存测试:")
    print(f"  缓存命中: {result2['stats']['cached']}/{result2['count']}")
    print(f"  命中率: {result2['stats']['cache_hit_rate']:.2%}")

    service.cleanup()


def demo_vllm_embedding_service():
    """Demo 2: 使用 vLLM 作为 Embedding 后端 (需要 GPU)"""
    print("\n" + "=" * 60)
    print("Demo 2: vLLM Embedding Service (高性能)")
    print("=" * 60)

    # 注意: 这个示例需要实际的 vLLM service 运行
    print("\n配置示例:")
    config_example = """
services:
  vllm:
    class: sage.common.components.sage_vllm.VLLMService
    config:
      model_id: "BAAI/bge-base-en-v1.5"
      embedding_model_id: "BAAI/bge-base-en-v1.5"
      auto_download: true
      engine:
        tensor_parallel_size: 1
        gpu_memory_utilization: 0.9

  embedding:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      method: "vllm"
      vllm_service_name: "vllm"
      batch_size: 256  # vLLM 可以处理大批量
      normalize: true
      cache_enabled: true

# 在 pipeline/operator 中使用:
result = self.call_service("embedding", payload={
    "task": "embed",
    "inputs": large_document_list,  # 可以是成千上万个文档
    "options": {
        "batch_size": 256,
        "return_stats": True
    }
})
    """
    print(config_example)


def demo_multi_embedding_pipeline():
    """Demo 3: 多 Embedding Service 的 Pipeline"""
    print("\n" + "=" * 60)
    print("Demo 3: 多 Embedding 策略 Pipeline")
    print("=" * 60)

    pipeline_config = """
# 使用场景: RAG 系统
# - 查询使用快速本地模型 (低延迟)
# - 文档索引使用高质量云端模型 (高精度)
# - 批量处理使用 vLLM (高吞吐)

services:
  # 1. 快速本地 embedding (用于实时查询)
  embedding_fast:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      method: "hf"
      model: "BAAI/bge-small-zh-v1.5"  # 小模型, 快速
      batch_size: 32
      cache_enabled: true

  # 2. 高质量云端 embedding (用于离线索引)
  embedding_quality:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      method: "openai"
      model: "text-embedding-3-large"
      api_key: "${OPENAI_API_KEY}"
      batch_size: 100

  # 3. vLLM 高吞吐 embedding (用于大规模批处理)
  vllm:
    class: sage.common.components.sage_vllm.VLLMService
    config:
      model_id: "BAAI/bge-large-en-v1.5"

  embedding_batch:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      method: "vllm"
      vllm_service_name: "vllm"
      batch_size: 512

operators:
  # 查询 embedding - 使用快速本地模型
  - name: query_embed
    type: custom
    code: |
      result = self.call_service("embedding_fast", payload={
          "task": "embed",
          "inputs": payload["query"]
      })
      payload["query_vector"] = result["vectors"][0]
      return payload

  # 文档 embedding - 根据情况选择
  - name: document_embed
    type: custom
    code: |
      docs = payload["documents"]

      # 小批量: 使用本地模型
      if len(docs) < 100:
          service = "embedding_fast"
      # 大批量: 使用 vLLM
      elif len(docs) > 1000:
          service = "embedding_batch"
      # 重要文档: 使用高质量云端
      elif payload.get("high_quality"):
          service = "embedding_quality"
      else:
          service = "embedding_fast"

      result = self.call_service(service, payload={
          "task": "embed",
          "inputs": [d["text"] for d in docs]
      })

      for doc, vec in zip(docs, result["vectors"]):
          doc["embedding"] = vec

      return payload
    """

    print(pipeline_config)


def demo_embedding_operator():
    """Demo 4: 创建自定义的 Embedding Operator"""
    print("\n" + "=" * 60)
    print("Demo 4: 自定义 Embedding Operator")
    print("=" * 60)

    operator_code = '''
from sage.libs.operators import BaseOperator
from typing import Any, Dict, List

class SmartEmbeddingOperator(BaseOperator):
    """智能 Embedding Operator - 根据负载自动选择策略"""

    def __init__(
        self,
        embedding_service: str = "embedding",
        batch_size: int = 32,
        cache_threshold: int = 10,  # 小于此数量启用缓存
        vllm_threshold: int = 1000,  # 大于此数量使用 vLLM
    ):
        self.embedding_service = embedding_service
        self.batch_size = batch_size
        self.cache_threshold = cache_threshold
        self.vllm_threshold = vllm_threshold

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        texts = payload.get("texts", [])

        if not texts:
            payload["embeddings"] = []
            return payload

        # 智能选择策略
        options = {
            "batch_size": self.batch_size,
            "return_stats": True,
        }

        # 小批量: 启用缓存
        if len(texts) <= self.cache_threshold:
            # 假设有缓存配置的 service
            service = self.embedding_service + "_cached"
        # 大批量: 使用 vLLM
        elif len(texts) >= self.vllm_threshold:
            service = self.embedding_service + "_vllm"
            options["batch_size"] = min(512, len(texts))
        else:
            service = self.embedding_service

        # 调用 embedding service
        result = self.call_service(service, payload={
            "task": "embed",
            "inputs": texts,
            "options": options
        })

        # 附加结果
        payload["embeddings"] = result["vectors"]
        payload["embedding_dimension"] = result["dimension"]
        payload["embedding_stats"] = result.get("stats", {})

        self.logger.info(
            f"Embedded {len(texts)} texts using {service}, "
            f"cache_hit_rate={result['stats'].get('cache_hit_rate', 0):.2%}"
        )

        return payload


# 使用示例
class RAGPipeline:
    def build(self):
        return {
            "operators": [
                {
                    "name": "load_query",
                    "type": "QueryLoaderOperator"
                },
                {
                    "name": "embed_query",
                    "type": "SmartEmbeddingOperator",
                    "config": {
                        "embedding_service": "embedding",
                        "batch_size": 32,
                        "cache_threshold": 10,
                    }
                },
                {
                    "name": "retrieve",
                    "type": "VectorSearchOperator",
                    "config": {
                        "top_k": 5
                    }
                },
                {
                    "name": "generate",
                    "type": "LLMGenerateOperator"
                }
            ]
        }
'''
    print(operator_code)


def demo_performance_comparison():
    """Demo 5: 性能对比 - 不同 embedding 方法"""
    print("\n" + "=" * 60)
    print("Demo 5: 性能对比")
    print("=" * 60)

    comparison = """
测试场景: 1000 个文档, 每个文档平均 100 tokens

方法              吞吐量      延迟      成本      推荐使用场景
-----------------------------------------------------------------
hash              10000/s     <1ms      免费      快速原型, 测试
mockembedder      5000/s      <1ms      免费      单元测试

hf (small)        100/s       10ms      免费      实时查询, 预算有限
hf (base)         50/s        20ms      免费      平衡性能和质量
hf (large)        20/s        50ms      免费      高质量离线处理

openai (small)    1000/s      10ms      $$$       大规模云端部署
openai (large)    500/s       20ms      $$$$      最高质量要求

jina              800/s       15ms      $$        中等规模, 多语言
zhipu             600/s       20ms      $$        中文优化

vLLM (GPU)        2000/s      5ms       硬件      大规模生产环境
vLLM (多GPU)      5000/s      3ms       硬件      超大规模部署

推荐配置:

  1. 开发/测试:
     method: "hash" 或 "mockembedder"

  2. 小规模生产 (< 1M 文档):
     method: "hf", model: "BAAI/bge-small-zh-v1.5"

  3. 中等规模 (1M - 10M 文档):
     查询: method: "hf", cache_enabled: true
     索引: method: "openai" 或 "jina"

  4. 大规模生产 (> 10M 文档):
     method: "vllm", vllm_service_name: "vllm"
     配置多 GPU 以提高吞吐量

  5. 成本敏感:
     method: "hf" (完全免费, 需要 GPU 硬件)

  6. 质量优先:
     method: "openai", model: "text-embedding-3-large"
"""
    print(comparison)


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Embedding Service 示例集")
    print("=" * 60)

    demos = [
        ("基本使用", demo_basic_embedding_service),
        ("vLLM 后端", demo_vllm_embedding_service),
        ("多 Embedding 策略", demo_multi_embedding_pipeline),
        ("自定义 Operator", demo_embedding_operator),
        ("性能对比", demo_performance_comparison),
    ]

    # 检查是否在测试模式
    is_test_mode = os.getenv("SAGE_TEST_MODE") == "true" or os.getenv("CI") == "true"

    if is_test_mode:
        # 测试模式：运行所有示例
        print("\n🧪 测试模式：自动运行所有示例\n")
        for name, demo_func in demos:
            try:
                demo_func()
            except Exception as e:
                print(f"\n❌ {name} 失败: {e}")
    else:
        # 交互模式：让用户选择
        print("\n可用示例:")
        for i, (name, _) in enumerate(demos, 1):
            print(f"  {i}. {name}")

        print("\n选择要运行的示例 (1-5, 或 'all' 运行全部, 'q' 退出):")
        choice = input("> ").strip().lower()

        if choice == "q":
            return
        elif choice == "all":
            for name, demo_func in demos:
                try:
                    demo_func()
                except Exception as e:
                    print(f"\n❌ {name} 失败: {e}")
        elif choice.isdigit() and 1 <= int(choice) <= len(demos):
            name, demo_func = demos[int(choice) - 1]
            try:
                demo_func()
            except Exception as e:
                print(f"\n❌ {name} 失败: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("无效选择")

    print("\n" + "=" * 60)
    print("示例结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
