#!/usr/bin/env python3
"""Quick validation script for refactored PreInsert"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert


class MockConfig:
    """Mock config for testing without YAML files"""

    def __init__(self, config_dict):
        self._data = config_dict

    def get(self, key: str, default=None):
        """Get config value by dot-separated key"""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default


def test_none_action():
    """测试 none action"""
    print("Testing none action...")
    config_dict = {
        "operators": {"pre_insert": {"action": "none"}},
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = MockConfig(config_dict)
    pre_insert = PreInsert(config)

    data = {"dialogs": [{"speaker": "A", "text": "Hello"}]}
    result = pre_insert.execute(data)

    assert "memory_entries" in result
    assert len(result["memory_entries"]) == 1
    assert result["memory_entries"][0]["insert_method"] == "default"
    assert result["memory_entries"][0]["insert_mode"] == "passive"
    print("✓ none action passed")


def test_transform_chunking():
    """测试 transform action with chunking"""
    print("\nTesting transform action (chunking)...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "transform",
                "transform_type": "chunking",
                "chunk_size": 50,
                "chunk_overlap": 10,
                "chunk_strategy": "fixed",
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = MockConfig(config_dict)
    pre_insert = PreInsert(config)

    data = {
        "dialogs": [
            {"speaker": "A", "text": "This is a long text. " * 10},
        ]
    }
    result = pre_insert.execute(data)

    assert "memory_entries" in result
    assert len(result["memory_entries"]) > 0
    for entry in result["memory_entries"]:
        assert entry["insert_method"] == "chunk_insert"
        assert entry["insert_mode"] == "passive"
        assert "chunk_text" in entry
        assert "chunk_index" in entry
    print("✓ transform chunking passed")


def test_extract_action():
    """测试 extract action (without actual NER models)"""
    print("\nTesting extract action...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "extract",
                "extract_type": "keyword",
                "keyword_prompt": "Extract keywords from: {text}",
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
        },
    }
    config = MockConfig(config_dict)
    _pre_insert = PreInsert(config)

    # This will not actually call LLM in test, but should initialize correctly
    print("✓ extract action initialized")


def test_score_importance():
    """测试 score action with importance"""
    print("\nTesting score action (importance)...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "score",
                "score_type": "importance",
                "importance_prompt": "Rate importance (1-10): {text}",
                "importance_scale": [1, 10],
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
        },
    }
    config = MockConfig(config_dict)
    _pre_insert = PreInsert(config)

    # This will not actually call LLM in test, but should initialize correctly
    print("✓ score action initialized")


def test_multi_embed():
    """测试 multi_embed action"""
    print("\nTesting multi_embed action...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "multi_embed",
                "embeddings": [{"name": "semantic", "model": "default", "field": "content"}],
                "output_format": "dict",
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = MockConfig(config_dict)
    _pre_insert = PreInsert(config)

    # This will not actually call embedding service, but should initialize correctly
    print("✓ multi_embed action initialized")


def test_validate_action():
    """测试 validate action"""
    print("\nTesting validate action...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "validate",
                "rules": [{"type": "length", "min": 10, "max": 1000}],
                "on_fail": "warn",
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = MockConfig(config_dict)
    pre_insert = PreInsert(config)

    # Test with valid data
    data = {"dialogs": [{"speaker": "A", "text": "This is a valid text with enough length."}]}
    result = pre_insert.execute(data)

    assert "memory_entries" in result
    assert len(result["memory_entries"]) == 1
    assert result["memory_entries"][0]["insert_method"] == "default"
    assert result["memory_entries"][0]["insert_mode"] == "passive"

    # Test with invalid data (too short)
    data_short = {"dialogs": [{"speaker": "A", "text": "Hi"}]}
    result_short = pre_insert.execute(data_short)

    assert "memory_entries" in result_short
    if len(result_short["memory_entries"]) > 0:
        # Should have warnings
        assert result_short["memory_entries"][0]["insert_method"] == "default"

    print("✓ validate action passed")


def test_tri_embed_init():
    """测试 tri_embed action 初始化"""
    print("\nTesting tri_embed action initialization...")
    config_dict = {
        "operators": {
            "pre_insert": {
                "action": "tri_embed",
                "triple_extraction_prompt": "Extract triples from: {dialogue}",
            }
        },
        "runtime": {
            "api_key": "test-key",  # pragma: allowlist secret
            "model_name": "qwen-turbo",
            "base_url": "http://127.0.0.1:8001/v1",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = MockConfig(config_dict)
    _pre_insert = PreInsert(config)

    print("✓ tri_embed action initialized")


def main():
    print("=" * 60)
    print("Validating refactored PreInsert")
    print("=" * 60)

    try:
        test_none_action()
        test_transform_chunking()
        test_extract_action()
        test_score_importance()
        test_multi_embed()
        test_validate_action()
        test_tri_embed_init()

        print("\n" + "=" * 60)
        print("All validation tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
