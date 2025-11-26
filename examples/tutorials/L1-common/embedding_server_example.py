"""
Embedding Server 使用示例

这个示例展示如何使用本地 embedding 服务器，
无需修改任何原有代码，直接通过 apply_embedding_model 调用。
"""

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)

    # 创建 embedding 模型实例（连接到本地服务器）
    embedding_model = apply_embedding_model(
        name="openai",  # 使用 openai 方法（兼容 OpenAI API）
        model="BAAI/bge-m3",  # 模型名称（任意，服务器会忽略）
        base_url="http://localhost:8091/v1",  # 本地服务器地址
        api_key="dummy",  # 本地服务不需要真实的 API key
    )

    # 测试 embedding
    text = "Hello, this is a test sentence."
    print(f"\nInput text: {text}")

    embedding = embedding_model.embed(text)
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")


def example_batch_processing():
    """批量处理示例"""
    print("\n" + "=" * 60)
    print("示例 2: 批量处理")
    print("=" * 60)

    embedding_model = apply_embedding_model(
        name="openai",
        model="BAAI/bge-m3",
        base_url="http://localhost:8091/v1",
        api_key="dummy",
    )

    # 多个文本
    texts = [
        "What is machine learning?",
        "Deep learning is a subset of machine learning.",
        "Natural language processing uses neural networks.",
    ]

    print(f"\nProcessing {len(texts)} texts...")
    for i, text in enumerate(texts, 1):
        embedding = embedding_model.embed(text)
        print(f"{i}. Text: '{text[:50]}...' -> Embedding dim: {len(embedding)}")


def example_with_different_server():
    """使用不同服务器端口的示例"""
    print("\n" + "=" * 60)
    print("示例 3: 使用不同服务器")
    print("=" * 60)

    # 假设你在端口 8081 运行另一个模型
    embedding_model = apply_embedding_model(
        name="openai",
        model="custom-model",
        base_url="http://localhost:8081/v1",  # 不同端口
        api_key="dummy",
    )

    text = "Testing with different server port"
    try:
        embedding = embedding_model.embed(text)
        print(f"Success! Embedding dimension: {len(embedding)}")
    except Exception as e:
        print(f"Error (expected if server not running): {e}")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 4: 错误处理")
    print("=" * 60)

    embedding_model = apply_embedding_model(
        name="openai",
        model="BAAI/bge-m3",
        base_url="http://localhost:8091/v1",
        api_key="dummy",
    )

    # 测试空文本
    try:
        embedding = embedding_model.embed("")
        print(f"Empty text embedding dimension: {len(embedding)}")
    except Exception as e:
        print(f"Error with empty text: {e}")

    # 测试很长的文本（会被截断）
    long_text = "This is a very long sentence. " * 100
    try:
        embedding = embedding_model.embed(long_text)
        print(f"Long text (truncated) embedding dimension: {len(embedding)}")
    except Exception as e:
        print(f"Error with long text: {e}")


def main():
    """主函数"""
    print("\n")
    print("=" * 60)
    print("Embedding Server 使用示例")
    print("=" * 60)
    print("\n请确保 embedding 服务器已启动:")
    print(
        "  bash packages/sage-common/src/sage/common/components/sage_embedding/start_embedding_server.sh 8091"
    )
    print("\n或手动启动:")
    print(
        "  python packages/sage-common/src/sage/common/components/sage_embedding/embedding_server.py --model BAAI/bge-m3 --port 8091"
    )
    print("\n" + "=" * 60 + "\n")

    try:
        # 运行示例
        example_basic_usage()
        example_batch_processing()
        example_with_different_server()
        example_error_handling()

        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保 embedding 服务器正在运行:")
        print(
            "  bash packages/sage-common/src/sage/common/components/sage_embedding/start_embedding_server.sh 8091"
        )


if __name__ == "__main__":
    main()
