"""
Phase 2 Tests: Verify all embedding wrappers are properly registered and functional.

This test suite validates:
1. All 11 embedding methods are registered
2. Each wrapper can be imported
3. Basic instantiation works (when dependencies are available)
4. Registry provides correct metadata
"""

import pytest
from sage.common.components.sage_embedding import (
    EmbeddingRegistry,
    check_model_availability,
    get_embedding_model,
    list_embedding_models,
)


class TestPhase2Registration:
    """测试所有 embedding 方法的注册"""

    def test_all_methods_registered(self):
        """测试所有 11 个方法是否已注册"""
        models = list_embedding_models()

        expected_methods = {
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
        }

        registered_methods = set(models.keys())
        print(f"\n已注册的方法: {registered_methods}")

        assert expected_methods == registered_methods, (
            f"注册方法不匹配！\n"
            f"预期: {expected_methods}\n"
            f"实际: {registered_methods}\n"
            f"缺失: {expected_methods - registered_methods}\n"
            f"多余: {registered_methods - expected_methods}"
        )

    def test_metadata_completeness(self):
        """测试所有方法的元数据是否完整"""
        models = list_embedding_models()

        required_fields = {
            "display_name",
            "description",
            "requires_api_key",
            "requires_download",  # 注意: factory 导出为 requires_download
            "examples",  # 注意: factory 导出为 examples
        }

        for method, info in models.items():
            missing = required_fields - set(info.keys())
            assert not missing, f"方法 {method} 缺少字段: {missing}"

    def test_wrapper_imports(self):
        """测试所有 wrapper 类可以被导入

        Note: Heavy wrappers use lazy loading, so they must be imported
        from their specific modules, not from the top-level package.
        """
        from sage.common.components.sage_embedding import HashEmbedding, MockEmbedding
        from sage.common.components.sage_embedding.wrappers.bedrock_wrapper import (
            BedrockEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.cohere_wrapper import (
            CohereEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.hf_wrapper import (
            HFEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.jina_wrapper import (
            JinaEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.nvidia_openai_wrapper import (
            NvidiaOpenAIEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.ollama_wrapper import (
            OllamaEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.openai_wrapper import (
            OpenAIEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.siliconcloud_wrapper import (
            SiliconCloudEmbedding,
        )
        from sage.common.components.sage_embedding.wrappers.zhipu_wrapper import (
            ZhipuEmbedding,
        )

        wrappers = [
            HashEmbedding,
            MockEmbedding,
            HFEmbedding,
            OpenAIEmbedding,
            JinaEmbedding,
            ZhipuEmbedding,
            CohereEmbedding,
            BedrockEmbedding,
            OllamaEmbedding,
            SiliconCloudEmbedding,
            NvidiaOpenAIEmbedding,
        ]

        for wrapper_cls in wrappers:
            assert wrapper_cls is not None
            assert hasattr(wrapper_cls, "embed")
            assert hasattr(wrapper_cls, "get_dim")
            print(f"✓ {wrapper_cls.__name__} 导入成功")



class TestNoAPIKeyMethods:
    """测试不需要 API Key 的方法（可以直接实例化）"""

    def test_hash_embedding(self):
        """测试 Hash Embedding"""
        emb = get_embedding_model("hash", dim=384)
        assert emb is not None
        assert emb.get_dim() == 384

        vec = emb.embed("test")
        assert isinstance(vec, list)
        assert len(vec) == 384
        print(f"✓ Hash Embedding: {emb}")

    def test_mock_embedding(self):
        """测试 Mock Embedding"""
        emb = get_embedding_model("mockembedder", dim=128)
        assert emb is not None
        assert emb.get_dim() == 128

        vec = emb.embed("test")
        assert isinstance(vec, list)
        assert len(vec) == 128
        print(f"✓ Mock Embedding: {emb}")


class TestAPIKeyMethods:
    """测试需要 API Key 的方法（期望抛出错误）"""

    def test_openai_requires_api_key(self):
        """测试 OpenAI 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.openai_wrapper import (
            OpenAIEmbedding,
        )

        # 临时清除环境变量
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                OpenAIEmbedding(model="text-embedding-3-small")
        finally:
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key

    def test_jina_requires_api_key(self):
        """测试 Jina 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.jina_wrapper import (
            JinaEmbedding,
        )

        old_key = os.environ.pop("JINA_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                JinaEmbedding(model="jina-embeddings-v3")
        finally:
            if old_key:
                os.environ["JINA_API_KEY"] = old_key

    def test_zhipu_requires_api_key(self):
        """测试 Zhipu 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.zhipu_wrapper import (
            ZhipuEmbedding,
        )

        old_key = os.environ.pop("ZHIPUAI_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                ZhipuEmbedding(model="embedding-3")
        finally:
            if old_key:
                os.environ["ZHIPUAI_API_KEY"] = old_key

    def test_cohere_requires_api_key(self):
        """测试 Cohere 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.cohere_wrapper import (
            CohereEmbedding,
        )

        old_key = os.environ.pop("COHERE_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                CohereEmbedding(model="embed-multilingual-v3.0")
        finally:
            if old_key:
                os.environ["COHERE_API_KEY"] = old_key

    def test_bedrock_requires_credentials(self):
        """测试 Bedrock 需要 AWS 凭证"""
        import os

        from sage.common.components.sage_embedding.wrappers.bedrock_wrapper import (
            BedrockEmbedding,
        )

        # 临时清除 AWS 环境变量
        old_keys = {
            "AWS_ACCESS_KEY_ID": os.environ.pop("AWS_ACCESS_KEY_ID", None),
            "AWS_SECRET_ACCESS_KEY": os.environ.pop("AWS_SECRET_ACCESS_KEY", None),
        }
        try:
            with pytest.raises(RuntimeError, match="需要 AWS 凭证"):
                BedrockEmbedding(model="amazon.titan-embed-text-v2:0")
        finally:
            for key, val in old_keys.items():
                if val:
                    os.environ[key] = val

    def test_siliconcloud_requires_api_key(self):
        """测试 SiliconCloud 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.siliconcloud_wrapper import (
            SiliconCloudEmbedding,
        )

        old_key = os.environ.pop("SILICONCLOUD_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                SiliconCloudEmbedding(model="netease-youdao/bce-embedding-base_v1")
        finally:
            if old_key:
                os.environ["SILICONCLOUD_API_KEY"] = old_key

    def test_nvidia_openai_requires_api_key(self):
        """测试 NVIDIA OpenAI 需要 API Key"""
        import os

        from sage.common.components.sage_embedding.wrappers.nvidia_openai_wrapper import (
            NvidiaOpenAIEmbedding,
        )

        # 清除所有可能的API key环境变量
        old_nvidia_key = os.environ.pop("NVIDIA_API_KEY", None)
        old_openai_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="需要 API Key"):
                NvidiaOpenAIEmbedding(model="nvidia/llama-3.2-nv-embedqa-1b-v1")
        finally:
            if old_nvidia_key:
                os.environ["NVIDIA_API_KEY"] = old_nvidia_key
            if old_openai_key:
                os.environ["OPENAI_API_KEY"] = old_openai_key


class TestModelAvailability:
    """测试模型可用性检查"""

    def test_hash_always_available(self):
        """Hash Embedding 应该始终可用"""
        result = check_model_availability("hash")
        assert result["status"] == "available"

    def test_mock_always_available(self):
        """Mock Embedding 应该始终可用"""
        result = check_model_availability("mockembedder")
        assert result["status"] == "available"

    def test_openai_needs_api_key(self):
        """OpenAI 应该显示需要 API Key"""
        import os

        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = check_model_availability("openai")
            assert result["status"] == "needs_api_key"
            assert "API" in result["message"] or "api" in result["message"].lower()
        finally:
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key

    def test_hf_needs_download(self):
        """HF 模型应该显示需要下载"""
        result = check_model_availability("hf", model="test-model-xxx")
        # HF 模型如果不存在，应该显示 needs_download
        assert result["status"] in ("needs_download", "cached", "available")


class TestExampleModels:
    """测试每个方法的示例模型列表"""

    def test_all_methods_have_examples(self):
        """所有方法都应该有示例模型"""
        models = list_embedding_models()

        for method, info in models.items():
            assert "examples" in info  # factory 导出为 "examples"
            assert len(info["examples"]) > 0, f"{method} 没有示例模型"
            print(f"{method}: {info['examples']}")


class TestWrapperRepresentation:
    """测试 wrapper 的字符串表示"""

    def test_hash_repr(self):
        """测试 Hash Embedding 的 __repr__"""
        emb = get_embedding_model("hash", dim=384)
        repr_str = repr(emb)
        assert "HashEmbedding" in repr_str
        assert "384" in repr_str
        print(f"Hash repr: {repr_str}")

    def test_mock_repr(self):
        """测试 Mock Embedding 的 __repr__"""
        emb = get_embedding_model("mockembedder", dim=128)
        repr_str = repr(emb)
        assert "MockEmbedding" in repr_str
        assert "128" in repr_str
        print(f"Mock repr: {repr_str}")


class TestBatchEmbedding:
    """测试批量 embedding"""

    def test_hash_batch(self):
        """测试 Hash 批量 embedding"""
        emb = get_embedding_model("hash", dim=384)
        texts = ["text1", "text2", "text3"]
        vecs = emb.embed_batch(texts)

        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    def test_mock_batch(self):
        """测试 Mock 批量 embedding"""
        emb = get_embedding_model("mockembedder", dim=128)
        texts = ["text1", "text2", "text3"]
        vecs = emb.embed_batch(texts)

        assert len(vecs) == 3
        assert all(len(v) == 128 for v in vecs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
