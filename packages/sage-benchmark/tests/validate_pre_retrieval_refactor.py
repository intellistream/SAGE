#!/usr/bin/env python3
"""Quick validation script for refactored PreRetrieval"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))


class SimpleConfig:
    """简单配置对象用于测试"""

    def __init__(self, config_dict):
        self._config = config_dict

    def get(self, key: str, default=None):
        """获取配置项"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value


def test_none_action():
    """测试 none action"""
    print("Testing none action...")
    from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval

    config_dict = {
        "operators": {"pre_retrieval": {"action": "none"}},
        "runtime": {
            "api_key": "sk-test",  # pragma: allowlist secret
            "base_url": "http://localhost:8001/v1",
            "model_name": "test-model",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = SimpleConfig(config_dict)
    pre_ret = PreRetrieval(config)

    data = {"question": "Hello"}
    result = pre_ret.execute(data)
    assert result == data
    print("✓ none action passed")


def test_optimize_instruction():
    """测试 optimize action with instruction type"""
    print("\nTesting optimize action (instruction)...")
    from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval

    config_dict = {
        "operators": {
            "pre_retrieval": {
                "action": "optimize",
                "optimize_type": "instruction",
                "instruction_prefix": "Search for: ",
                "instruction_suffix": "",
                "replace_original": True,
                "store_optimized": True,
            }
        },
        "runtime": {
            "api_key": "sk-test",  # pragma: allowlist secret
            "base_url": "http://localhost:8001/v1",
            "model_name": "test-model",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = SimpleConfig(config_dict)
    pre_ret = PreRetrieval(config)
    # Disable embedding generator for testing
    pre_ret._embedding_generator = None

    data = {"question": "Hello"}
    result = pre_ret.execute(data)
    assert result["question"] == "Search for: Hello"
    assert result["optimized_query"] == "Search for: Hello"
    print("✓ optimize (instruction) action passed")


def test_validate_action():
    """测试 validate action"""
    print("\nTesting validate action...")
    from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval

    config_dict = {
        "operators": {
            "pre_retrieval": {
                "action": "validate",
                "rules": [{"type": "length", "min": 3, "max": 100}],
                "on_fail": "default",
                "default_query": "Default query",
                "preprocessing": {
                    "strip_whitespace": True,
                    "lowercase": False,
                    "remove_punctuation": False,
                },
            }
        },
        "runtime": {
            "api_key": "sk-test",  # pragma: allowlist secret
            "base_url": "http://localhost:8001/v1",
            "model_name": "test-model",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = SimpleConfig(config_dict)
    pre_ret = PreRetrieval(config)

    # Valid query
    data = {"question": "Hello world"}
    result = pre_ret.execute(data)
    assert result["is_valid"] is True
    assert result["question"] == "Hello world"

    # Too short query
    data = {"question": "Hi"}
    result = pre_ret.execute(data)
    assert result["is_valid"] is False
    assert result["question"] == "Default query"
    print("✓ validate action passed")


def test_route_action():
    """测试 route action"""
    print("\nTesting route action...")
    from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval

    config_dict = {
        "operators": {
            "pre_retrieval": {
                "action": "route",
                "route_strategy": "keyword",
                "keyword_rules": [
                    {
                        "keywords": ["remember", "recall"],
                        "strategy": "deep_search",
                        "params": {"expand_links": True},
                    }
                ],
                "default_strategy": "semantic_search",
                "allow_multi_route": True,
                "max_routes": 2,
            }
        },
        "runtime": {
            "api_key": "sk-test",  # pragma: allowlist secret
            "base_url": "http://localhost:8001/v1",
            "model_name": "test-model",
            "embedding_base_url": "http://localhost:8090/v1",
            "embedding_model": "BAAI/bge-m3",
        },
    }
    config = SimpleConfig(config_dict)
    pre_ret = PreRetrieval(config)

    # Keyword match
    data = {"question": "Can you remember what I said?"}
    result = pre_ret.execute(data)
    assert "retrieval_hints" in result
    assert "deep_search" in result["retrieval_hints"]["strategies"]
    assert result["retrieval_hints"]["params"]["expand_links"] is True

    # No match - use default
    data = {"question": "What is AI?"}
    result = pre_ret.execute(data)
    assert "retrieval_hints" in result
    assert result["retrieval_hints"]["strategies"] == ["semantic_search"]
    print("✓ route action passed")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("PreRetrieval Refactor Validation")
    print("=" * 60)

    try:
        test_none_action()
        test_optimize_instruction()
        test_validate_action()
        test_route_action()

        print("\n" + "=" * 60)
        print("✓ All validation tests passed!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
