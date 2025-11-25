"""
Example: High-Performance Batch Embedding with EmbeddingService

This example demonstrates how to use EmbeddingService for efficient
batch embedding of large datasets, which is the recommended approach
for vector database insertion performance.
"""


def example_basic_batch_embedding():
    """Example 1: Basic batch embedding with EmbeddingService"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Batch Embedding")
    print("=" * 70)

    from sage.common.components.sage_embedding import EmbeddingService

    # Configure EmbeddingService
    config = {
        "method": "hf",
        "model": "BAAI/bge-small-zh-v1.5",
        "batch_size": 32,
        "normalize": True,
        "cache_enabled": True,
        "cache_size": 10000,
    }

    service = EmbeddingService(config)
    service.setup()

    # Sample texts
    texts = [
        "人工智能正在改变世界",
        "机器学习是AI的核心",
        "深度学习推动了AI发展",
        "自然语言处理很重要",
        "向量数据库用于存储嵌入",
    ]

    # Batch embed
    result = service.embed(texts, return_stats=True)

    print(f"\n✓ Embedded {result['count']} texts")
    print(f"✓ Dimension: {result['dimension']}")
    print(f"✓ Stats: {result['stats']}")

    service.cleanup()


def example_large_dataset_embedding():
    """Example 2: Large dataset embedding with caching"""
    print("\n" + "=" * 70)
    print("Example 2: Large Dataset Embedding")
    print("=" * 70)

    from sage.common.components.sage_embedding import EmbeddingService

    config = {
        "method": "hf",
        "model": "BAAI/bge-small-zh-v1.5",
        "batch_size": 64,
        "normalize": True,
        "cache_enabled": True,
        "cache_size": 50000,
    }

    service = EmbeddingService(config)
    service.setup()

    # Simulate large dataset
    num_docs = 1000
    texts = [f"Document {i}: This is sample content for testing." for i in range(num_docs)]

    print(f"\nEmbedding {num_docs} documents...")
    
    # Use larger batch size for efficiency
    result = service.embed(texts, batch_size=128, return_stats=True)

    print(f"✓ Embedded {result['count']} documents")
    print(f"✓ Computed: {result['stats']['computed']}")
    print(f"✓ Cached: {result['stats']['cached']}")

    # Re-embed same texts to show caching
    print("\nRe-embedding (should use cache)...")
    result2 = service.embed(texts[:100], return_stats=True)
    print(f"✓ Cache hit rate: {result2['stats']['cache_hit_rate']:.2%}")

    service.cleanup()


def example_embedding_strategies():
    """Example 3: Different embedding strategies"""
    print("\n" + "=" * 70)
    print("Example 3: Embedding Strategies")
    print("=" * 70)

    strategies = """
Strategy Selection Guide:

1. Small datasets (< 1K texts):
   - method: "hf"
   - batch_size: 16
   - cache_enabled: False

2. Medium datasets (1K - 10K texts):
   - method: "hf"
   - batch_size: 32
   - cache_enabled: True

3. Large datasets (10K - 100K texts):
   - method: "hf"
   - batch_size: 64-128
   - cache_enabled: True
   - cache_size: 100000

4. Production scale (100K+ texts):
   - method: "vllm"
   - batch_size: 256
   - Use vLLM service for high throughput

5. Cloud deployment:
   - method: "openai"
   - batch_size: 100 (API limit)
   - Rate limiting required
"""
    print(strategies)


def example_vllm_config():
    """Example 4: vLLM configuration for high throughput"""
    print("\n" + "=" * 70)
    print("Example 4: vLLM Configuration")
    print("=" * 70)

    vllm_config = """
# YAML configuration for vLLM-backed embedding service

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
      batch_size: 256
      normalize: true
      cache_enabled: true
      cache_size: 100000

# Usage in pipeline:
# result = self.call_service("embedding", payload={
#     "task": "embed",
#     "inputs": texts,
#     "options": {"batch_size": 256}
# })
"""
    print(vllm_config)


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("HIGH-PERFORMANCE BATCH EMBEDDING EXAMPLES")
    print("=" * 70)
    print("\nThese examples demonstrate the recommended approach for")
    print("high-performance vector database insertion using EmbeddingService.")

    import os
    is_test_mode = os.getenv("SAGE_TEST_MODE") == "true" or os.getenv("CI") == "true"

    if is_test_mode:
        # In test mode, just show the examples
        print("\n🧪 Test mode: Showing example configurations\n")
        example_embedding_strategies()
        example_vllm_config()
    else:
        try:
            example_basic_batch_embedding()
            example_large_dataset_embedding()
        except ImportError as e:
            print(f"\nNote: {e}")
            print("Install SAGE to run the embedding examples.")

        example_embedding_strategies()
        example_vllm_config()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("1. Use EmbeddingService for batch embedding")
    print("2. Enable caching for repeated texts")
    print("3. Adjust batch_size based on hardware")
    print("4. Use vLLM for production scale")


if __name__ == "__main__":
    main()
