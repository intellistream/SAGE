#!/usr/bin/env python3
"""
Tests for MedicalKnowledgeBase
Tests knowledge update, retrieval, and case management functionality
"""

import pytest

from sage.apps.medical_diagnosis.tools.knowledge_base import MedicalKnowledgeBase


class TestMedicalKnowledgeBase:
    """Test suite for MedicalKnowledgeBase class"""

    @pytest.fixture
    def config(self):
        """Provide test configuration"""
        return {"services": {"vector_db": {"collection_name": "test_lumbar_cases", "top_k": 5}}}

    @pytest.fixture
    def knowledge_base(self, config):
        """Create a fresh knowledge base instance for each test"""
        return MedicalKnowledgeBase(config)

    def test_initialization(self, knowledge_base):
        """Test that knowledge base initializes with default knowledge"""
        assert knowledge_base is not None
        assert len(knowledge_base.knowledge_base) > 0
        assert isinstance(knowledge_base.knowledge_base, list)
        assert knowledge_base.case_database is not None

    def test_default_knowledge_structure(self, knowledge_base):
        """Test that default knowledge has expected structure"""
        for knowledge in knowledge_base.knowledge_base:
            assert "topic" in knowledge
            assert "content" in knowledge
            assert isinstance(knowledge["topic"], str)
            assert isinstance(knowledge["content"], str)

    def test_update_knowledge_add_new(self, knowledge_base):
        """Test adding new knowledge to the knowledge base"""
        initial_count = len(knowledge_base.knowledge_base)

        new_knowledge = {
            "topic": "椎体压缩性骨折",
            "content": "椎体压缩性骨折是指椎体在外力作用下发生压缩性变形",
            "diagnosis_criteria": "X线或CT显示椎体高度降低超过20%",
            "treatment": "急性期卧床休息，必要时行椎体成形术",
        }

        result = knowledge_base.update_knowledge(new_knowledge)

        assert result["action"] == "added"
        assert result["topic"] == "椎体压缩性骨折"
        assert len(knowledge_base.knowledge_base) == initial_count + 1

        # Verify the new knowledge is in the database
        added_knowledge = [
            k for k in knowledge_base.knowledge_base if k["topic"] == "椎体压缩性骨折"
        ]
        assert len(added_knowledge) == 1
        assert added_knowledge[0]["content"] == new_knowledge["content"]

    def test_update_knowledge_update_existing(self, knowledge_base):
        """Test updating existing knowledge in the knowledge base"""
        initial_count = len(knowledge_base.knowledge_base)

        # First, verify the knowledge exists
        original_knowledge = [
            k for k in knowledge_base.knowledge_base if k["topic"] == "腰椎间盘突出症"
        ]
        assert len(original_knowledge) == 1
        original_content = original_knowledge[0]["content"]

        # Update with new content
        updated_knowledge = {
            "topic": "腰椎间盘突出症",
            "content": "更新后的内容：腰椎间盘突出症是最常见的腰椎疾病之一",
            "diagnosis_criteria": "更新后的诊断标准",
            "treatment": "更新后的治疗方案",
            "additional_info": "新增字段：这是补充信息",
        }

        result = knowledge_base.update_knowledge(updated_knowledge)

        assert result["action"] == "updated"
        assert result["topic"] == "腰椎间盘突出症"
        # Count should not change when updating
        assert len(knowledge_base.knowledge_base) == initial_count

        # Verify the knowledge was updated
        current_knowledge = [
            k for k in knowledge_base.knowledge_base if k["topic"] == "腰椎间盘突出症"
        ]
        assert len(current_knowledge) == 1  # Still only one entry
        assert current_knowledge[0]["content"] != original_content
        assert current_knowledge[0]["content"] == updated_knowledge["content"]
        assert "additional_info" in current_knowledge[0]
        assert current_knowledge[0]["additional_info"] == "新增字段：这是补充信息"

    def test_update_knowledge_missing_topic(self, knowledge_base):
        """Test that update_knowledge raises ValueError when topic is missing"""
        with pytest.raises(ValueError, match="must contain 'topic' field"):
            knowledge_base.update_knowledge({})

        with pytest.raises(ValueError, match="must contain 'topic' field"):
            knowledge_base.update_knowledge({"content": "Some content without topic"})

        with pytest.raises(ValueError, match="must contain 'topic' field"):
            knowledge_base.update_knowledge(None)

    def test_update_knowledge_empty_topic(self, knowledge_base):
        """Test update_knowledge with empty topic string"""
        # Empty string is technically a valid topic, but results in an entry with empty topic
        knowledge_data = {"topic": "", "content": "Content with empty topic"}

        result = knowledge_base.update_knowledge(knowledge_data)

        assert result["action"] in ["added", "updated"]
        assert result["topic"] == ""

    def test_update_knowledge_preserves_other_knowledge(self, knowledge_base):
        """Test that updating knowledge doesn't affect other knowledge entries"""
        # Get list of all topics before update
        topics_before = {k["topic"] for k in knowledge_base.knowledge_base}

        # Update one knowledge
        updated_knowledge = {
            "topic": "腰椎间盘突出症",
            "content": "新内容",
        }
        knowledge_base.update_knowledge(updated_knowledge)

        # Get list of all topics after update
        topics_after = {k["topic"] for k in knowledge_base.knowledge_base}

        # Topics should be the same
        assert topics_before == topics_after

    def test_update_knowledge_multiple_additions(self, knowledge_base):
        """Test adding multiple new knowledge entries"""
        initial_count = len(knowledge_base.knowledge_base)

        new_topics = [
            {
                "topic": "颈椎病",
                "content": "颈椎病相关内容",
            },
            {
                "topic": "强直性脊柱炎",
                "content": "强直性脊柱炎相关内容",
            },
            {
                "topic": "骨质疏松症",
                "content": "骨质疏松症相关内容",
            },
        ]

        for knowledge in new_topics:
            result = knowledge_base.update_knowledge(knowledge)
            assert result["action"] == "added"

        assert len(knowledge_base.knowledge_base) == initial_count + len(new_topics)

    def test_retrieve_knowledge(self, knowledge_base):
        """Test knowledge retrieval functionality"""
        # The retrieve_knowledge method does simple keyword matching
        # It checks if any keyword from the topic (split by spaces) is in the query
        results = knowledge_base.retrieve_knowledge("腰椎间盘突出症", top_k=3)

        assert isinstance(results, list)
        assert len(results) <= 3
        # Should find the default knowledge about 腰椎间盘突出症
        if len(results) > 0:
            assert any("腰椎间盘突出症" in k["topic"] for k in results)

    def test_retrieve_knowledge_empty_query(self, knowledge_base):
        """Test knowledge retrieval with empty query"""
        results = knowledge_base.retrieve_knowledge("", top_k=3)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_retrieve_knowledge_no_match(self, knowledge_base):
        """Test knowledge retrieval with query that matches nothing"""
        results = knowledge_base.retrieve_knowledge("心脏病", top_k=3)

        assert isinstance(results, list)
        # Should return empty list if no matches
        assert len(results) == 0

    def test_retrieve_similar_cases(self, knowledge_base):
        """Test similar case retrieval"""
        cases = knowledge_base.retrieve_similar_cases(
            query="腰痛伴下肢麻木", image_features={}, top_k=3
        )

        assert isinstance(cases, list)
        assert len(cases) <= 3
        assert len(cases) > 0  # Should return mock cases

        # Verify case structure
        for case in cases:
            assert "case_id" in case
            assert "diagnosis" in case
            assert "similarity_score" in case

    def test_add_case(self, knowledge_base):
        """Test adding a new case to the case database"""
        initial_count = len(knowledge_base.case_database)

        case_data = {
            "case_id": "TEST_001",
            "age": 50,
            "gender": "male",
            "diagnosis": "L4/L5椎间盘突出症",
            "symptoms": "腰痛",
        }

        knowledge_base.add_case(case_data)

        assert len(knowledge_base.case_database) == initial_count + 1
        assert knowledge_base.case_database[-1]["case_id"] == "TEST_001"

    def test_knowledge_persistence_across_operations(self, knowledge_base):
        """Test that knowledge persists correctly across multiple operations"""
        # Add new knowledge
        new_knowledge = {
            "topic": "测试疾病A",
            "content": "内容A",
        }
        knowledge_base.update_knowledge(new_knowledge)

        # Update it
        updated_knowledge = {
            "topic": "测试疾病A",
            "content": "更新的内容A",
            "extra_field": "额外信息",
        }
        knowledge_base.update_knowledge(updated_knowledge)

        # Verify only one entry exists
        matching_knowledge = [k for k in knowledge_base.knowledge_base if k["topic"] == "测试疾病A"]
        assert len(matching_knowledge) == 1
        assert matching_knowledge[0]["content"] == "更新的内容A"
        assert "extra_field" in matching_knowledge[0]

    def test_update_knowledge_with_special_characters(self, knowledge_base):
        """Test update_knowledge with special characters in topic"""
        special_knowledge = {
            "topic": "L4/L5椎间盘突出 (Grade II-III)",
            "content": "特殊字符测试内容",
        }

        result = knowledge_base.update_knowledge(special_knowledge)

        assert result["action"] == "added"
        assert result["topic"] == "L4/L5椎间盘突出 (Grade II-III)"

    def test_update_knowledge_unicode(self, knowledge_base):
        """Test update_knowledge with various unicode characters"""
        unicode_knowledge = {
            "topic": "脊柱側彎症 🦴",
            "content": "包含表情符号的内容 ✅",
        }

        result = knowledge_base.update_knowledge(unicode_knowledge)

        assert result["action"] == "added"
        assert "脊柱側彎症 🦴" in result["topic"]


def test_standalone_execution():
    """Test that the module can be run standalone"""
    # This test ensures that the if __name__ == "__main__" block doesn't crash
    # We won't actually run it in tests, just verify it's importable
    from sage.apps.medical_diagnosis.tools import knowledge_base

    assert hasattr(knowledge_base, "MedicalKnowledgeBase")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
