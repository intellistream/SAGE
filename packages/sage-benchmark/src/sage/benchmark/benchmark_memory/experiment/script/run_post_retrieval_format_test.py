"""Test script for PostRetrieval format action.

This script tests D5-6 (format) with 4 subtypes: template, structured, chat, xml.
"""

from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import PostRetrieval
from sage.benchmark.benchmark_memory.experiment.utils.config_loader import RuntimeConfig


def test_format_template():
    """测试 format: template。"""
    print("\n========== Test Format: template ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "format",
                "format_type": "template",
                "template": "## Relevant Memories\n{memories}\n\n## User Profile\n{profile}",
                "memory_template": "- [{timestamp}] {text}",
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {
                "text": "User likes pizza",
                "score": 0.9,
                "metadata": {"timestamp": "2025-11-28T10:00:00"},
            },
            {
                "text": "User is a developer",
                "score": 0.8,
                "metadata": {"timestamp": "2025-11-27T15:30:00"},
            },
        ],
        "user_profile": "Name: John, Age: 30",
    }

    result = post_retrieval.execute(data)
    print("Formatted history_text:")
    print(result["history_text"])

    assert "Relevant Memories" in result["history_text"], "Should contain section title"
    assert "User likes pizza" in result["history_text"], "Should contain memory text"
    assert "User Profile" in result["history_text"], "Should contain profile section"
    assert "John" in result["history_text"], "Should contain profile content"
    print("✓ Format template test passed")


def test_format_structured():
    """测试 format: structured。"""
    print("\n========== Test Format: structured ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "format",
                "format_type": "structured",
                "structure": [
                    {"section": "Recent Conversations", "source": "memory_data", "max_items": 2},
                    {"section": "User Info", "source": "user_profile"},
                ],
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Memory 1", "score": 0.9, "metadata": {}},
            {"text": "Memory 2", "score": 0.8, "metadata": {}},
            {"text": "Memory 3", "score": 0.7, "metadata": {}},
        ],
        "user_profile": "John is a developer",
    }

    result = post_retrieval.execute(data)
    print("Formatted history_text:")
    print(result["history_text"])

    assert "## Recent Conversations" in result["history_text"], "Should contain section 1"
    assert "## User Info" in result["history_text"], "Should contain section 2"
    assert "Memory 1" in result["history_text"], "Should contain memory 1"
    assert "Memory 2" in result["history_text"], "Should contain memory 2"
    assert "John is a developer" in result["history_text"], "Should contain profile"
    # Memory 3 should not be included (max_items=2)
    assert "Memory 3" not in result["history_text"], "Should respect max_items"
    print("✓ Format structured test passed")


def test_format_chat():
    """测试 format: chat。"""
    print("\n========== Test Format: chat ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "format",
                "format_type": "chat",
                "role_mapping": {"user": "Human", "assistant": "AI"},
                "include_timestamps": True,
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "Hello!", "score": 0.9, "metadata": {"role": "user", "timestamp": "10:00"}},
            {
                "text": "Hi there!",
                "score": 0.8,
                "metadata": {"role": "assistant", "timestamp": "10:01"},
            },
            {
                "text": "How are you?",
                "score": 0.7,
                "metadata": {"role": "user", "timestamp": "10:02"},
            },
        ],
    }

    result = post_retrieval.execute(data)
    print("Formatted history_text:")
    print(result["history_text"])

    assert "Human: Hello!" in result["history_text"], "Should map user to Human"
    assert "AI: Hi there!" in result["history_text"], "Should map assistant to AI"
    assert "[10:00]" in result["history_text"], "Should include timestamps"
    print("✓ Format chat test passed")


def test_format_xml():
    """测试 format: xml。"""
    print("\n========== Test Format: xml ==========")

    config = RuntimeConfig(config_path=None)
    config._config = {
        "operators": {
            "post_retrieval": {
                "action": "format",
                "format_type": "xml",
                "xml_tags": {"memories": "relevant_context", "profile": "user_profile"},
            }
        }
    }

    post_retrieval = PostRetrieval(config)

    data = {
        "memory_data": [
            {"text": "User likes pizza", "score": 0.9, "metadata": {"category": "preference"}},
            {"text": "User is a developer", "score": 0.8, "metadata": {"category": "occupation"}},
        ],
        "user_profile": "Name: John, Age: 30",
    }

    result = post_retrieval.execute(data)
    print("Formatted history_text:")
    print(result["history_text"])

    assert "<relevant_context>" in result["history_text"], "Should have memories tag"
    assert "</relevant_context>" in result["history_text"], "Should close memories tag"
    assert "<memory>" in result["history_text"], "Should have memory tags"
    assert "<text>User likes pizza</text>" in result["history_text"], "Should have text tags"
    assert "<score>0.9</score>" in result["history_text"], "Should have score tags"
    assert "<user_profile>" in result["history_text"], "Should have profile tag"
    assert "Name: John" in result["history_text"], "Should include profile content"
    print("✓ Format xml test passed")


def main():
    """Run all format tests."""
    print("========================================")
    print("PostRetrieval Format Action Test Suite")
    print("========================================")

    test_format_template()
    test_format_structured()
    test_format_chat()
    test_format_xml()

    print("\n========================================")
    print("✓ All format tests passed!")
    print("========================================")


if __name__ == "__main__":
    main()
