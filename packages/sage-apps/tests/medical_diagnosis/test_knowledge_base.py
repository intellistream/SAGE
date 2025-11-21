#!/usr/bin/env python3
"""
Tests for MedicalKnowledgeBase
"""

import json
from pathlib import Path

import pytest

from sage.apps.medical_diagnosis.tools.knowledge_base import MedicalKnowledgeBase


class TestMedicalKnowledgeBase:
    """Test MedicalKnowledgeBase class"""

    def test_initialization_basic(self):
        """Test basic initialization without data files"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        assert kb is not None
        assert isinstance(kb.knowledge_base, list)
        assert len(kb.knowledge_base) > 0  # Should have at least default knowledge
        assert isinstance(kb.case_database, list)

    def test_default_knowledge_loaded(self):
        """Test that default knowledge is loaded"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        # Check that default knowledge contains expected topics
        topics = [k["topic"] for k in kb.knowledge_base]
        assert "腰椎间盘突出症" in topics
        assert "腰椎退行性变" in topics
        assert "椎管狭窄" in topics

    def test_retrieve_knowledge_basic(self):
        """Test basic knowledge retrieval"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        # Search for knowledge about disc herniation
        results = kb.retrieve_knowledge("腰椎间盘突出", top_k=3)

        assert isinstance(results, list)
        # Should find at least one result
        assert len(results) >= 1
        # First result should be relevant
        assert "腰椎" in results[0]["topic"] or "椎间盘" in results[0]["topic"]

    def test_retrieve_similar_cases_basic(self):
        """Test basic case retrieval"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        # Search for similar cases
        results = kb.retrieve_similar_cases(
            query="腰痛伴下肢麻木", image_features={}, top_k=3
        )

        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 3
        # Each result should have required fields
        for case in results:
            assert "case_id" in case
            assert "diagnosis" in case

    def test_add_case(self):
        """Test adding a new case"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        initial_count = len(kb.case_database)

        new_case = {
            "case_id": "TEST_001",
            "age": 50,
            "gender": "male",
            "diagnosis": "腰椎间盘突出症",
        }

        kb.add_case(new_case)

        assert len(kb.case_database) == initial_count + 1
        assert kb.case_database[-1]["case_id"] == "TEST_001"

    def test_update_knowledge(self):
        """Test updating knowledge base"""
        config = {}
        kb = MedicalKnowledgeBase(config)

        initial_count = len(kb.knowledge_base)

        new_knowledge = {
            "topic": "测试疾病",
            "content": "这是一个测试疾病的描述",
            "treatment": "测试治疗方法",
        }

        kb.update_knowledge(new_knowledge)

        assert len(kb.knowledge_base) == initial_count + 1
        assert kb.knowledge_base[-1]["topic"] == "测试疾病"

    def test_load_from_nonexistent_path(self):
        """Test loading with nonexistent data path"""
        config = {"data_path": "/nonexistent/path/to/data"}
        kb = MedicalKnowledgeBase(config)

        # Should still initialize with default knowledge
        assert len(kb.knowledge_base) >= 3
        assert len(kb.case_database) == 0

    @pytest.mark.skipif(
        not (
            Path(__file__).parent.parent.parent
            / "src"
            / "sage"
            / "apps"
            / "medical_diagnosis"
            / "data"
            / "processed"
            / "stats.json"
        ).exists(),
        reason="Test data not available",
    )
    def test_load_from_dataset(self):
        """Test loading knowledge from actual dataset if available"""
        # Point to the actual data directory
        medical_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "sage"
            / "apps"
            / "medical_diagnosis"
        )
        data_path = medical_dir / "data" / "processed"

        config = {"data_path": str(data_path)}
        kb = MedicalKnowledgeBase(config)

        # Should have loaded additional knowledge
        assert len(kb.knowledge_base) > 3  # More than just default knowledge

    @pytest.mark.skipif(
        not (
            Path(__file__).parent.parent.parent
            / "src"
            / "sage"
            / "apps"
            / "medical_diagnosis"
            / "data"
            / "processed"
            / "all_cases.json"
        ).exists(),
        reason="Test data not available",
    )
    def test_load_case_database(self):
        """Test loading case database from dataset if available"""
        # Point to the actual data directory
        medical_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "sage"
            / "apps"
            / "medical_diagnosis"
        )
        data_path = medical_dir / "data" / "processed"

        config = {"data_path": str(data_path)}
        kb = MedicalKnowledgeBase(config)

        # Should have loaded cases
        assert len(kb.case_database) > 0

        # Test case retrieval with loaded cases
        results = kb.retrieve_similar_cases(
            query="椎间盘突出", image_features={}, top_k=3
        )

        assert len(results) > 0
