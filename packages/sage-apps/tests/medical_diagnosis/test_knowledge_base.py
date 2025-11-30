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
