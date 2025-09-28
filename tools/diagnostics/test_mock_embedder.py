#!/usr/bin/env python3
"""
测试MockEmbedder场景，模拟CICD环境中embedding模型加载失败的情况
"""

import os
import sys

sys.path.append("/home/shuhao/SAGE")

# 模拟网络问题，阻止HuggingFace模型下载
import unittest.mock


def mock_model_load_failure(*args, **kwargs):
    raise Exception("Network error: Unable to download model")


# 覆盖AutoTokenizer和AutoModel的from_pretrained方法
with unittest.mock.patch(
    "transformers.AutoTokenizer.from_pretrained", side_effect=mock_model_load_failure
), unittest.mock.patch(
    "transformers.AutoModel.from_pretrained", side_effect=mock_model_load_failure
):

    from sage.middleware.components.neuromem.memory_manager import \
        MemoryManager

    def test_with_mock_embedder():
        print("🧪 测试：模拟CICD环境中使用MockEmbedder的情况")

        # 创建MemoryManager实例
        manager = MemoryManager()

        # 创建一个新的内存集合
        config = {
            "name": "mock_test_collection",
            "backend_type": "VDB",
            "description": "Mock测试集合",
        }

        vdb_collection = manager.create_collection(config)

        index_config = {
            "name": "mock_test_index",
            "embedding_model": "default",
            "dim": 384,
            "backend_type": "FAISS",
            "description": "Mock测试索引",
            "index_parameter": {},
        }
        vdb_collection.create_index(config=index_config)

        # 插入测试数据
        vdb_collection.insert(
            index_name="mock_test_index",
            raw_data="想吃广东菜",
            metadata={"priority": "low", "tag": "food"},
        )

        # 检测使用的embedding模型类型
        embedding_model = vdb_collection.embedding_model_factory.get("default")
        is_using_mock = (
            hasattr(embedding_model, "kwargs")
            and "embed_model" in embedding_model.kwargs
            and hasattr(embedding_model.kwargs["embed_model"], "method_name")
            and embedding_model.kwargs["embed_model"].method_name == "mockembedder"
        )

        print(f"📊 使用的模型类型: {'MockEmbedder' if is_using_mock else 'Real Model'}")

        if is_using_mock:
            print("✅ 成功检测到MockEmbedder，使用适配的阈值")
            threshold = 0.01
        else:
            print("❌ 未按预期使用MockEmbedder")
            threshold = 0.3

        results = vdb_collection.retrieve(
            index_name="mock_test_index",
            raw_data="广东菜",
            with_metadata=True,
            threshold=threshold,
        )

        print(f"🔍 搜索结果数量: {len(results)}")
        if results:
            print("✅ 测试成功：即使在MockEmbedder环境下也能找到匹配结果")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result.get('text', 'N/A')}")
        else:
            print("❌ 测试失败：未找到匹配结果")

        # 清理
        manager.delete_collection("mock_test_collection")
        return len(results) > 0

    # 运行测试
    success = test_with_mock_embedder()
    print(f"\n🎯 测试结果: {'通过' if success else '失败'}")
