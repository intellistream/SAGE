#!/usr/bin/env python3
"""
测试 Gateway 使用 sage chat 基础设施

验证新的 RAG Pipeline 是否正常工作
"""

import asyncio
import sys


async def test_gateway_rag():
    """测试 Gateway RAG Pipeline"""

    print("=" * 70)
    print("测试 Gateway RAG (使用 sage chat 基础设施)")
    print("=" * 70)

    # 1. 先运行 sage chat ingest 构建索引
    print("\n[步骤 1] 检查 sage chat 索引...")

    from pathlib import Path

    index_root = Path.home() / ".sage" / "cache" / "chat"
    manifest_file = index_root / "docs-public_manifest.json"

    if not manifest_file.exists():
        print(f"  ⚠️  索引不存在: {manifest_file}")
        print("  请先运行: sage chat ingest")
        print("  或者等待 Gateway 自动构建索引（首次启动时）")
        return False

    print(f"  ✅ 找到索引: {manifest_file}")

    # 2. 加载 manifest
    print("\n[步骤 2] 加载索引配置...")

    import json

    with open(manifest_file, "r") as f:
        manifest = json.load(f)

    print(f"  - 索引名称: {manifest['index_name']}")
    print(f"  - 文档数: {manifest['num_documents']}")
    print(f"  - 片段数: {manifest['num_chunks']}")
    print(f"  - DB 路径: {manifest['db_path']}")

    # 3. 测试 SageDB 加载
    print("\n[步骤 3] 测试 SageDB 加载...")

    try:
        from sage.middleware.components.sage_db.python.sage_db import SageDB
        from sage.common.components.sage_embedding import get_embedding_model

        # 创建 embedder
        embed_config = manifest.get("embedding", {})
        embedding_method = embed_config.get("method", "hash")

        embedder = get_embedding_model(embedding_method, dim=384)
        print(f"  ✅ Embedder 创建成功: {embedding_method} (dim={embedder.get_dim()})")

        # 加载 DB
        db_path = Path(manifest["db_path"])
        db = SageDB(embedder.get_dim())
        db.load(str(db_path))
        print("  ✅ SageDB 加载成功")

    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 4. 测试检索
    print("\n[步骤 4] 测试文档检索...")

    test_query = "什么是SAGE"

    try:
        query_vector = embedder.embed(test_query)
        results = db.search(query_vector, top_k=3, return_metadata=True)

        print(f"  查询: {test_query}")
        print(f"  检索到 {len(results)} 个结果:")

        for idx, item in enumerate(results, 1):
            metadata = dict(item.metadata) if hasattr(item, "metadata") else {}
            doc_path = metadata.get("doc_path", "unknown")
            heading = metadata.get("heading", "")
            text_preview = metadata.get("text", "")[:100]
            score = float(getattr(item, "score", 0.0))

            print(f"\n  [{idx}] {doc_path}")
            print(f"      标题: {heading}")
            print(f"      得分: {score:.4f}")
            print(f"      预览: {text_preview}...")

        print("\n  ✅ 检索测试通过")

    except Exception as e:
        print(f"  ❌ 检索失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 5. 测试完整 RAG Pipeline
    print("\n[步骤 5] 测试完整 RAG Pipeline...")

    try:
        from sage.libs.integrations.openaiclient import OpenAIClient
        import os
        import textwrap

        # 提取上下文
        contexts = []
        for item in results:
            metadata = dict(item.metadata) if hasattr(item, "metadata") else {}
            contexts.append(metadata.get("text", ""))

        # 构建 prompt
        context_block = "\n\n".join(
            f"[{idx}] {textwrap.dedent(ctx).strip()}"
            for idx, ctx in enumerate(contexts, start=1)
            if ctx
        )

        system_instructions = textwrap.dedent(
            """
            You are SAGE 内嵌编程助手。回答用户关于 SAGE 的问题，依据提供的上下文进行解释。
            - 如果上下文不足以回答，请坦诚说明并给出下一步建议。
            - 引用时使用 [编号] 表示。
            - 回答保持简洁，直接给出步骤或示例代码。
            """
        ).strip()

        if context_block:
            system_instructions += f"\n\n已检索上下文:\n{context_block}"

        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": test_query.strip()},
        ]

        # 调用 LLM
        api_key = (
            os.getenv("SAGE_CHAT_API_KEY")
            or os.getenv("ALIBABA_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
        )

        if not api_key:
            print("  ⚠️  跳过 LLM 调用（缺少 API Key）")
            print("  提示: 设置 DASHSCOPE_API_KEY 环境变量")
        else:
            client = OpenAIClient(
                model_name="qwen-max",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=api_key,
                seed=42,
            )

            response = client.chat(messages, temperature=0.2, stream=False)

            print("  ✅ RAG 回答生成成功")
            print("\n  回答预览:")
            print(f"  {response[:300]}...")

    except Exception as e:
        print(f"  ❌ RAG Pipeline 失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！")
    print("=" * 70)
    print("\n现在可以重启 Gateway 使用新的 RAG 实现")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_gateway_rag())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
