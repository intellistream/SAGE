#!/usr/bin/env python3
"""
Tests for MedicalKnowledgeBase
Tests knowledge update, retrieval, and case management functionality
"""

import json
from pathlib import Path

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

    def test_initialization_basic(self):
        """Test basic initialization without data files"""
        config = {"verbose": False}
        kb = MedicalKnowledgeBase(config)

        assert kb is not None
        assert isinstance(kb.knowledge_base, list)
        assert len(kb.knowledge_base) > 0  # Should have at least default knowledge
        assert isinstance(kb.case_database, list)

    def test_default_knowledge_loaded(self):
        """Test that default knowledge is loaded"""
        config = {"verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Check that default knowledge contains expected topics
        topics = [k["topic"] for k in kb.knowledge_base]
        assert "腰椎间盘突出症" in topics
        assert "腰椎退行性变" in topics
        assert "椎管狭窄" in topics

    def test_retrieve_knowledge_basic(self):
        """Test basic knowledge retrieval"""
        config = {"verbose": False}
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
        config = {"verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Search for similar cases
        results = kb.retrieve_similar_cases(query="腰痛伴下肢麻木", image_features={}, top_k=3)

        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 3
        # Each result should have required fields
        for case in results:
            assert "case_id" in case
            assert "diagnosis" in case

    def test_add_case(self):
        """Test adding a new case"""
        config = {"verbose": False}
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
        config = {"verbose": False}
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
        config = {"data_path": "/nonexistent/path/to/data", "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Should still initialize with default knowledge
        assert len(kb.knowledge_base) >= 3
        assert len(kb.case_database) == 0

    def test_configuration_options(self):
        """Test configuration options work correctly"""
        config = {
            "verbose": False,
            "enable_dataset_knowledge": False,
            "enable_report_knowledge": False,
            "enable_case_database": False,
        }
        kb = MedicalKnowledgeBase(config)

        # Should only have default knowledge (3 entries)
        assert len(kb.knowledge_base) == 3
        assert len(kb.case_database) == 0

    def test_max_reports_configuration(self):
        """Test max_reports configuration option"""
        config = {
            "verbose": False,
            "max_reports": 10,
        }
        kb = MedicalKnowledgeBase(config)

        # Should initialize without error
        assert kb._max_reports == 10

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
            Path(__file__).parent.parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"
        )
        data_path = medical_dir / "data" / "processed"

        config = {"data_path": str(data_path), "verbose": False}
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
            Path(__file__).parent.parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"
        )
        data_path = medical_dir / "data" / "processed"

        config = {"data_path": str(data_path), "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Should have loaded cases
        assert len(kb.case_database) > 0

        # Test case retrieval with loaded cases
        results = kb.retrieve_similar_cases(query="椎间盘突出", image_features={}, top_k=3)

        assert len(results) > 0


class TestMedicalKnowledgeBaseWithMockData:
    """Test MedicalKnowledgeBase with mock data files"""

    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create a mock data directory with test files"""
        # Create processed data directory
        processed_dir = tmp_path / "processed"
        processed_dir.mkdir()

        # Create stats.json
        stats = {
            "total_samples": 100,
            "disease_distribution": {
                "椎间盘突出": 30,
                "椎管狭窄": 20,
                "正常": 50,  # This should be filtered out
            },
            "severity_distribution": {
                "轻度": 40,
                "中度": 35,
                "重度": 25,
            },
        }
        with open(processed_dir / "stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False)

        # Create all_cases.json
        cases = [
            {
                "case_id": "case_0001",
                "patient_id": "P0001",
                "age": 45,
                "gender": "男",
                "disease": "椎间盘突出",
                "severity": "中度",
                "image_path": "images/case_0001.jpg",
                "report_path": "reports/case_0001_report.txt",
            },
            {
                "case_id": "case_0002",
                "patient_id": "P0002",
                "age": 55,
                "gender": "女",
                "disease": "椎管狭窄",
                "severity": "重度",
                "image_path": "images/case_0002.jpg",
                "report_path": "reports/case_0002_report.txt",
            },
        ]
        with open(processed_dir / "all_cases.json", "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False)

        # Create reports directory with mock reports
        reports_dir = processed_dir / "reports"
        reports_dir.mkdir()

        # Create mock reports
        report_1 = """患者信息:
  年龄: 45岁
  性别: 男
  主诉: 腰痛伴右下肢放射痛3周

影像描述:
  腰椎MRI T2加权矢状位: L4/L5椎间盘向后突出,压迫硬膜囊。

主要发现:
  - 病变节段: L4/L5
  - 病变类型: 椎间盘突出
  - 严重程度: 中度

诊断结论:
  椎间盘突出，程度中度。

治疗建议:
  建议卧床休息2-3周，牵引治疗。口服非甾体抗炎药及神经营养药物。
"""
        with open(reports_dir / "case_0001_report.txt", "w", encoding="utf-8") as f:
            f.write(report_1)

        report_2 = """患者信息:
  年龄: 55岁
  性别: 女
  主诉: 腰痛伴双下肢麻木、无力2月

影像描述:
  腰椎MRI T2加权矢状位: L4/L5椎管狭窄,硬膜囊受压。

主要发现:
  - 病变节段: L4/L5
  - 病变类型: 椎管狭窄
  - 严重程度: 重度

诊断结论:
  椎管狭窄，程度重度。

治疗建议:
  建议尽早手术治疗(椎间盘摘除术或椎管减压术)，以解除神经压迫。
"""
        with open(reports_dir / "case_0002_report.txt", "w", encoding="utf-8") as f:
            f.write(report_2)

        return processed_dir

    def test_load_knowledge_from_mock_dataset(self, mock_data_dir):
        """Test loading knowledge from mock stats.json"""
        config = {"data_path": str(mock_data_dir), "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Should have default knowledge (3) + dataset knowledge (2, excluding "正常")
        topics = [k["topic"] for k in kb.knowledge_base]
        assert "椎间盘突出" in topics
        assert "椎管狭窄" in topics
        assert "正常" not in topics  # "正常" should be filtered out

    def test_load_knowledge_from_mock_reports(self, mock_data_dir):
        """Test loading knowledge from mock report files"""
        config = {"data_path": str(mock_data_dir), "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Check that report knowledge was loaded
        report_knowledge = [k for k in kb.knowledge_base if k.get("source") == "medical_reports"]
        assert len(report_knowledge) >= 1

        # Check content of extracted knowledge
        for knowledge in report_knowledge:
            assert "topic" in knowledge
            assert "content" in knowledge
            assert "treatment" in knowledge

    def test_load_case_database_from_mock(self, mock_data_dir):
        """Test loading case database from mock all_cases.json"""
        config = {"data_path": str(mock_data_dir), "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Should have loaded 2 cases
        assert len(kb.case_database) == 2

        # Check case structure
        for case in kb.case_database:
            assert "case_id" in case
            assert "age" in case
            assert "gender" in case
            assert "diagnosis" in case
            assert "severity" in case

    def test_retrieve_cases_from_mock_database(self, mock_data_dir):
        """Test case retrieval with mock database"""
        config = {"data_path": str(mock_data_dir), "verbose": False}
        kb = MedicalKnowledgeBase(config)

        # Search for cases related to disc herniation
        results = kb.retrieve_similar_cases(query="椎间盘突出", image_features={}, top_k=3)

        assert len(results) >= 1
        # At least one result should be about disc herniation
        assert any("椎间盘突出" in r.get("diagnosis", "") for r in results)

    def test_disable_dataset_loading(self, mock_data_dir):
        """Test that dataset loading can be disabled"""
        config = {
            "data_path": str(mock_data_dir),
            "verbose": False,
            "enable_dataset_knowledge": False,
        }
        kb = MedicalKnowledgeBase(config)

        # Should not have knowledge from dataset_statistics source
        dataset_knowledge = [
            k for k in kb.knowledge_base if k.get("source") == "dataset_statistics"
        ]
        assert len(dataset_knowledge) == 0

    def test_disable_report_loading(self, mock_data_dir):
        """Test that report loading can be disabled"""
        config = {
            "data_path": str(mock_data_dir),
            "verbose": False,
            "enable_report_knowledge": False,
        }
        kb = MedicalKnowledgeBase(config)

        # Should not have knowledge from medical_reports source
        report_knowledge = [k for k in kb.knowledge_base if k.get("source") == "medical_reports"]
        assert len(report_knowledge) == 0

    def test_disable_case_database_loading(self, mock_data_dir):
        """Test that case database loading can be disabled"""
        config = {
            "data_path": str(mock_data_dir),
            "verbose": False,
            "enable_case_database": False,
        }
        kb = MedicalKnowledgeBase(config)

        # Should not have loaded any cases
        assert len(kb.case_database) == 0

    def test_max_reports_limit(self, mock_data_dir):
        """Test max_reports configuration limits report loading"""
        config = {
            "data_path": str(mock_data_dir),
            "verbose": False,
            "max_reports": 1,  # Only read 1 report
        }
        kb = MedicalKnowledgeBase(config)

        # Should have limited number of report knowledge entries
        report_knowledge = [k for k in kb.knowledge_base if k.get("source") == "medical_reports"]
        # With max_reports=1, we should have at most 1 unique disease from reports
        assert len(report_knowledge) <= 1


class TestMedicalKnowledgeUpdateFeatures:
    """Test suite for update_knowledge functionality from Issue #902"""

    @pytest.fixture
    def config(self):
        """Provide test configuration"""
        return {
            "services": {"vector_db": {"collection_name": "test_lumbar_cases", "top_k": 5}},
            "verbose": False,
        }

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
        # With embedding fallback, may return results
        assert len(results) <= 3

    def test_retrieve_knowledge_no_match(self, knowledge_base):
        """Test knowledge retrieval with query that matches nothing"""
        results = knowledge_base.retrieve_knowledge("心脏病", top_k=3)

        assert isinstance(results, list)
        # With embedding fallback, may return semantically similar results
        assert len(results) <= 3

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
