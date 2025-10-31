#!/usr/bin/env python3
"""
SAGE Embedding 方法演示

展示所有 11 个 embedding 方法的使用。

@test:allow-demo
"""

from sage.common.components.sage_embedding import (
    check_model_availability,
    get_embedding_model,
    list_embedding_models,
)


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
    else:
        print(f"{'=' * 60}")


def list_all_methods():
    """列出所有可用的 embedding 方法"""
    print_separator("所有 Embedding 方法")

    models = list_embedding_models()

    for method, info in models.items():
        print(f"\n📦 {method} - {info['display_name']}")
        print(f"   描述: {info['description']}")

        features = []
        if info["requires_api_key"]:
            features.append("🔑 需要 API Key")
        else:
            features.append("🔓 无需 API Key")

        if info["requires_download"]:
            features.append("📥 需要下载模型")
        else:
            features.append("☁️ 云端服务")

        if info["default_dimension"]:
            features.append(f"📊 默认维度: {info['default_dimension']}")

        print(f"   特性: {', '.join(features)}")

        if info["examples"]:
            print(f"   示例: {', '.join(info['examples'][:3])}")


def check_all_status():
    """检查所有方法的可用性"""
    print_separator("方法可用性检查")

    methods = [
        "hash",
        "mockembedder",
        "hf",
        "openai",
        "jina",
        "zhipu",
        "cohere",
        "bedrock",
        "ollama",
        "siliconcloud",
        "nvidia_openai",
    ]

    for method in methods:
        result = check_model_availability(method)
        status_icon = {
            "available": "✅",
            "cached": "✅",
            "needs_api_key": "⚠️",
            "needs_download": "⚠️",
            "unavailable": "❌",
        }.get(result["status"], "❓")

        print(f"{status_icon} {method:20} - {result['message']}")


def demo_no_api_key_methods():
    """演示无需 API Key 的方法"""
    print_separator("演示：无需 API Key 的方法")

    # Hash Embedding
    print("\n1. Hash Embedding (轻量级)")
    try:
        emb = get_embedding_model("hash", dim=384)
        vec = emb.embed("Hello World")
        print(f"   {emb}")
        print(f"   向量维度: {len(vec)}")
        print(f"   向量示例: {vec[:5]}...")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

    # Mock Embedding
    print("\n2. Mock Embedding (测试用)")
    try:
        emb = get_embedding_model("mockembedder", dim=128)
        vec = emb.embed("Test")
        print(f"   {emb}")
        print(f"   向量维度: {len(vec)}")
        print(f"   向量示例: {vec[:5]}...")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def demo_batch_embedding():
    """演示批量 embedding"""
    print_separator("演示：批量 Embedding")

    print("\n批量处理 3 个文本:")
    texts = ["文本1", "文本2", "文本3"]

    try:
        emb = get_embedding_model("hash", dim=256)
        vecs = emb.embed_batch(texts)
        print(f"   ✅ 成功生成 {len(vecs)} 个向量")
        print(f"   每个向量维度: {len(vecs[0])}")
        for i, vec in enumerate(vecs):
            print(f"   向量 {i + 1}: {vec[:3]}...")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def demo_api_key_methods():
    """演示需要 API Key 的方法（仅展示如何调用）"""
    print_separator("演示：需要 API Key 的方法（代码示例）")

    examples = {
        "openai": """
# OpenAI Embedding
emb = get_embedding_model(
    "openai",
    model="text-embedding-3-small",
    api_key="sk-xxx"
)
vec = emb.embed("hello world")
""",
        "jina": """
# Jina Embedding (Late Chunking)
emb = get_embedding_model(
    "jina",
    dimensions=256,
    late_chunking=True,
    api_key="jina-xxx"
)
vec = emb.embed("你好世界")
""",
        "zhipu": """
# 智谱 Embedding (批量)
emb = get_embedding_model(
    "zhipu",
    model="embedding-3",
    api_key="zhipu-xxx"
)
vecs = emb.embed_batch(["文本1", "文本2", "文本3"])
""",
        "cohere": """
# Cohere Embedding (多种 input_type)
emb = get_embedding_model(
    "cohere",
    model="embed-multilingual-v3.0",
    input_type="classification",
    api_key="cohere-xxx"
)
vec = emb.embed("positive review")
""",
        "bedrock": """
# AWS Bedrock Embedding
emb = get_embedding_model(
    "bedrock",
    model="amazon.titan-embed-text-v2:0",
    aws_access_key_id="xxx",
    aws_secret_access_key="xxx"
)
vec = emb.embed("hello world")
""",
        "ollama": """
# Ollama Embedding (本地)
emb = get_embedding_model(
    "ollama",
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
vec = emb.embed("hello world")
""",
        "siliconcloud": """
# SiliconCloud Embedding
emb = get_embedding_model(
    "siliconcloud",
    model="netease-youdao/bce-embedding-base_v1",
    api_key="silicon-xxx"
)
vec = emb.embed("你好")
""",
        "nvidia_openai": """
# NVIDIA NIM Embedding
emb = get_embedding_model(
    "nvidia_openai",
    model="nvidia/llama-3.2-nv-embedqa-1b-v1",
    input_type="passage",
    api_key="nvapi-xxx"
)
vec = emb.embed("document text")
""",
    }

    for method, code in examples.items():
        print(f"\n{method}:")
        print(code)


def main():
    """主函数"""
    print(
        """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     SAGE Embedding 方法演示                              ║
║     Phase 2 Complete - 11 个统一接口                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """
    )

    # 1. 列出所有方法
    list_all_methods()

    # 2. 检查可用性
    check_all_status()

    # 3. 演示无 API Key 方法
    demo_no_api_key_methods()

    # 4. 演示批量 embedding
    demo_batch_embedding()

    # 5. 展示 API Key 方法示例
    demo_api_key_methods()

    print_separator()
    print("\n✅ 演示完成！")
    print("\n💡 提示:")
    print("   - 无需 API Key 的方法可以直接使用")
    print("   - 需要 API Key 的方法需要先设置环境变量或传递参数")
    print("   - 使用 list_embedding_models() 查看所有方法")
    print("   - 使用 check_model_availability() 检查状态")
    print_separator()


if __name__ == "__main__":
    main()
