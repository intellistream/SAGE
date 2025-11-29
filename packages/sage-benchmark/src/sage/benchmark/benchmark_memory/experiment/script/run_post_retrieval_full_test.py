"""Full test script for PostRetrieval with all actions (filter, merge, augment, compress).

This script tests D5-2 (filter), D5-3 (merge), D5-4 (augment), D5-5 (compress).
"""

from datetime import datetime, timedelta, timezone

from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import PostRetrieval
from sage.benchmark.benchmark_memory.experiment.utils.config_loader import RuntimeConfig


def test_filter_threshold():
    """测试 filter: threshold。"""
    print("\n========== Test Filter: threshold ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "filter",
                "filter_type": "threshold",
                "score_threshold": 0.5,
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "High score memory", "score": 0.9, "metadata": {}},
            {"text": "Medium score memory", "score": 0.6, "metadata": {}},
            {"text": "Low score memory", "score": 0.3, "metadata": {}},
        ]
    }

    result = post_retrieval.execute(data)
    print(f"Original count: 3")
    print(f"Filtered count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 2, "Should keep 2 items with score >= 0.5"
    print("✓ Filter threshold test passed")


def test_filter_top_k():
    """测试 filter: top_k。"""
    print("\n========== Test Filter: top_k ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "filter",
                "filter_type": "top_k",
                "k": 2,
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Memory 1", "score": 0.9, "metadata": {}},
            {"text": "Memory 2", "score": 0.8, "metadata": {}},
            {"text": "Memory 3", "score": 0.7, "metadata": {}},
            {"text": "Memory 4", "score": 0.6, "metadata": {}},
        ]
    }

    result = post_retrieval.execute(data)
    print(f"Original count: 4")
    print(f"Top-k count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 2, "Should keep top 2 items"
    print("✓ Filter top_k test passed")


def test_filter_token_budget():
    """测试 filter: token_budget。"""
    print("\n========== Test Filter: token_budget ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "filter",
                "filter_type": "token_budget",
                "token_budget": 50,
                "token_counter": "char",
                "overflow_strategy": "drop",
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Short memory 1", "score": 0.9, "metadata": {}},  # 14 chars
            {"text": "Short memory 2", "score": 0.8, "metadata": {}},  # 14 chars
            {"text": "Short memory 3", "score": 0.7, "metadata": {}},  # 14 chars
            {"text": "This is a very long memory that will exceed the budget", "score": 0.6, "metadata": {}},  # 55 chars
        ]
    }

    result = post_retrieval.execute(data)
    print(f"Original count: 4")
    print(f"Budget-filtered count: {len(result['memory_data'])}")
    total_chars = sum(len(item["text"]) for item in result["memory_data"])
    print(f"Total characters: {total_chars}")
    for item in result["memory_data"]:
        print(f"  - {item['text'][:30]}... ({len(item['text'])} chars)")

    assert total_chars <= 50, "Total characters should not exceed budget"
    print("✓ Filter token_budget test passed")


def test_filter_dedup():
    """测试 filter: dedup (退化为文本去重，因为没有 embedding service)。"""
    print("\n========== Test Filter: dedup ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "filter",
                "filter_type": "dedup",
                "dedup_strategy": "keep_first",
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Duplicate memory", "score": 0.9, "metadata": {}},
            {"text": "Unique memory", "score": 0.8, "metadata": {}},
            {"text": "Duplicate memory", "score": 0.7, "metadata": {}},
        ]
    }

    result = post_retrieval.execute(data)
    print(f"Original count: 3")
    print(f"Dedup count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 2, "Should remove duplicate"
    print("✓ Filter dedup test passed")


def test_merge_concat():
    """测试 merge: concat。"""
    print("\n========== Test Merge: concat ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "merge",
                "merge_type": "concat",
                "merge_sources": ["context_data"],
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Memory 1", "score": 0.9, "metadata": {}},
        ],
        "context_data": [
            {"text": "Context 1", "score": 0.8, "metadata": {}},
            {"text": "Context 2", "score": 0.7, "metadata": {}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Original memory_data count: 1")
    print(f"Merged count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 3, "Should concat memory_data + context_data"
    print("✓ Merge concat test passed")


def test_merge_interleave():
    """测试 merge: interleave。"""
    print("\n========== Test Merge: interleave ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "merge",
                "merge_type": "interleave",
                "merge_sources": ["context_data"],
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Memory 1", "score": 0.9, "metadata": {}},
            {"text": "Memory 2", "score": 0.8, "metadata": {}},
        ],
        "context_data": [
            {"text": "Context 1", "score": 0.7, "metadata": {}},
            {"text": "Context 2", "score": 0.6, "metadata": {}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Interleaved count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 4, "Should interleave memory_data + context_data"
    # Check interleave order: Memory 1, Context 1, Memory 2, Context 2
    assert result["memory_data"][0]["text"] == "Memory 1"
    assert result["memory_data"][1]["text"] == "Context 1"
    assert result["memory_data"][2]["text"] == "Memory 2"
    assert result["memory_data"][3]["text"] == "Context 2"
    print("✓ Merge interleave test passed")


def test_merge_weighted():
    """测试 merge: weighted。"""
    print("\n========== Test Merge: weighted ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "merge",
                "merge_type": "weighted",
                "merge_sources": ["context_data"],
                "merge_weights": {"items": 0.7, "context_data": 0.3},
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Shared memory", "score": 0.8, "metadata": {}},
        ],
        "context_data": [
            {"text": "Shared memory", "score": 0.6, "metadata": {}},  # Same text, will be merged
            {"text": "Unique context", "score": 0.5, "metadata": {}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Weighted merge count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']}")

    assert len(result["memory_data"]) == 2, "Should merge items with same text"
    # Check weighted average: 0.7 * 0.8 + 0.3 * 0.6 = 0.74
    shared_item = next(item for item in result["memory_data"] if item["text"] == "Shared memory")
    expected_score = (0.7 * 0.8 + 0.3 * 0.6) / (0.7 + 0.3)
    assert abs(shared_item["score"] - expected_score) < 0.01, f"Weighted score should be {expected_score}"
    print("✓ Merge weighted test passed")


def test_merge_rrf():
    """测试 merge: rrf (Reciprocal Rank Fusion)。"""
    print("\n========== Test Merge: rrf ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "merge",
                "merge_type": "rrf",
                "merge_sources": ["context_data"],
                "rrf_k": 60,
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Memory A", "score": 0.9, "metadata": {}},  # rank 1 in memory_data
            {"text": "Memory B", "score": 0.8, "metadata": {}},  # rank 2 in memory_data
        ],
        "context_data": [
            {"text": "Memory B", "score": 0.7, "metadata": {}},  # rank 1 in context_data (same as Memory B)
            {"text": "Context C", "score": 0.6, "metadata": {}},  # rank 2 in context_data
        ],
    }

    result = post_retrieval.execute(data)
    print(f"RRF merge count: {len(result['memory_data'])}")
    for item in result["memory_data"]:
        print(f"  - {item['text']}: {item['score']:.4f}")

    # Memory B should have highest RRF score: 1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325
    # Memory A: 1/(60+1) = 0.0164
    # Context C: 1/(60+2) = 0.0161
    assert result["memory_data"][0]["text"] == "Memory B", "Memory B should have highest RRF score"
    print("✓ Merge rrf test passed")


def test_augment_context():
    """测试 augment: context。"""
    print("\n========== Test Augment: context ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "augment",
                "augment_type": "context",
                "augment_fields": ["user_name", "user_age"],
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "User likes pizza", "score": 0.9, "metadata": {}},
        ],
        "user_name": "John",
        "user_age": 30,
    }

    result = post_retrieval.execute(data)
    print(f"Augmented memory_data:")
    for item in result["memory_data"]:
        print(f"  - {item['text']}")

    assert "[user_name: John, user_age: 30]" in result["memory_data"][0]["text"], "Should add context fields"
    print("✓ Augment context test passed")


def test_augment_metadata():
    """测试 augment: metadata。"""
    print("\n========== Test Augment: metadata ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "augment",
                "augment_type": "metadata",
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Important memory", "score": 0.9, "metadata": {"importance": 8, "emotion": "happy"}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Augmented memory_data:")
    for item in result["memory_data"]:
        print(f"  - {item['text']}")

    assert "[importance: 8, emotion: happy]" in result["memory_data"][0]["text"], "Should add metadata to text"
    print("✓ Augment metadata test passed")


def test_augment_temporal():
    """测试 augment: temporal。"""
    print("\n========== Test Augment: temporal ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "augment",
                "augment_type": "temporal",
                "time_field": "timestamp",
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    now = datetime.now(timezone.utc)
    two_hours_ago = now - timedelta(hours=2)

    data = {
        "memory_data": [
            {"text": "Recent memory", "score": 0.9, "metadata": {"timestamp": two_hours_ago.isoformat()}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Augmented memory_data:")
    for item in result["memory_data"]:
        print(f"  - {item['text']}")

    assert "[2 hours ago]" in result["memory_data"][0]["text"], "Should add temporal info"
    print("✓ Augment temporal test passed")


def test_compress_extractive():
    """测试 compress: extractive。"""
    print("\n========== Test Compress: extractive ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "compress",
                "compress_type": "extractive",
                "compress_ratio": 0.5,
                "compress_max_length": 100,
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    long_text = (
        "This is the first sentence. This is the second sentence. "
        "This is the third sentence. This is the fourth sentence. "
        "This is the fifth sentence. This is the sixth sentence."
    )

    data = {
        "memory_data": [
            {"text": long_text, "score": 0.9, "metadata": {}},
        ],
    }

    result = post_retrieval.execute(data)
    print(f"Original length: {len(long_text)}")
    print(f"Compressed length: {len(result['memory_data'][0]['text'])}")
    print(f"Compressed text: {result['memory_data'][0]['text']}")

    assert len(result["memory_data"][0]["text"]) <= 100, "Should compress to max_length"
    print("✓ Compress extractive test passed")


def main():
    """Run all tests."""
    print("========================================")
    print("PostRetrieval Full Test Suite")
    print("========================================")

    # Filter tests
    test_filter_threshold()
    test_filter_top_k()
    test_filter_token_budget()
    test_filter_dedup()

    # Merge tests
    test_merge_concat()
    test_merge_interleave()
    test_merge_weighted()
    test_merge_rrf()

    # Augment tests
    test_augment_context()
    test_augment_metadata()
    test_augment_temporal()

    # Compress tests
    test_compress_extractive()

    print("\n========================================")
    print("✓ All tests passed!")
    print("========================================")


if __name__ == "__main__":
    main()
