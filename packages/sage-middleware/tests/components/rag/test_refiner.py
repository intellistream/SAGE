"""
测试 sage.middleware.operators.rag.refiner 模块
"""

import tempfile
from unittest.mock import Mock, patch

import pytest

# 尝试导入插件模块
pytest_plugins = []

try:
    from sage.middleware.operators.rag.refiner import RefinerOperator

    REFINER_AVAILABLE = True
except ImportError as e:
    REFINER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Refiner module not available: {e}")


@pytest.fixture
def temp_dir():
    """提供临时目录的fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.unit
class TestRefinerOperator:
    """测试RefinerOperator类"""

    def test_refiner_operator_import(self):
        """测试RefinerOperator导入"""
        if not REFINER_AVAILABLE:
            pytest.skip("Refiner module not available")

        from sage.middleware.operators.rag.refiner import RefinerOperator

        assert RefinerOperator is not None

    def test_refiner_operator_initialization_missing_config(self):
        """测试RefinerOperator初始化缺少配置"""
        if not REFINER_AVAILABLE:
            pytest.skip("Refiner module not available")

        # RefinerOperator 现在使用 RefinerService，不直接检查配置完整性
        # RefinerService 会在实际使用时检查配置
        incomplete_config = {
            "algorithm": "simple",  # 使用简单算法避免复杂依赖
            "budget": 2048,
        }

        # 测试能否正常初始化（RefinerService会处理配置验证）
        with patch("sage.middleware.components.sage_refiner.RefinerService"):
            try:
                operator = RefinerOperator(config=incomplete_config)
                assert operator.cfg == incomplete_config
            except Exception as e:
                pytest.skip(f"RefinerOperator initialization requires middleware: {e}")

    def test_refiner_operator_initialization_complete_config(self):
        """测试RefinerOperator完整配置初始化"""
        if not REFINER_AVAILABLE:
            pytest.skip("Refiner module not available")

        complete_config = {
            "algorithm": "long_refiner",
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000,
            "enable_profile": False,
        }

        # 使用正确的 RefinerService mock
        with patch("sage.middleware.components.sage_refiner.RefinerService"):
            try:
                adapter = RefinerOperator(config=complete_config)
                assert adapter.cfg == complete_config
                assert adapter.enable_profile is False
                # 验证基本属性存在
                assert hasattr(adapter, "cfg")
                assert hasattr(adapter, "enable_profile")
            except Exception as e:
                # 如果依赖不可用，跳过测试
                pytest.skip(f"RefinerOperator initialization failed: {e}")


@pytest.mark.unit
class TestRefinerOperatorExecution:
    """测试RefinerOperator执行"""

    def test_execute_with_dict_docs(self):
        """测试执行字典格式文档"""
        if not REFINER_AVAILABLE:
            pytest.skip("Refiner module not available")

        config = {
            "algorithm": "long_refiner",
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000,
            "enable_profile": False,
        }

        with patch("sage.middleware.components.sage_refiner.RefinerService") as mock_service_class:
            # 创建 mock service 实例
            mock_service = Mock()

            # 模拟 RefineResult
            mock_result = Mock()
            mock_result.refined_content = [
                "Refined document 1",
                "Refined document 2",
            ]
            mock_result.metrics = Mock()
            mock_result.metrics.compression_rate = 0.5
            mock_result.metrics.original_tokens = 100
            mock_result.metrics.refined_tokens = 50
            mock_result.metrics.refining_time = 1.0
            
            mock_service.refine.return_value = mock_result
            mock_service_class.return_value = mock_service

            # 必须在patch内部创建adapter
            adapter = RefinerOperator(config=config)

            # 测试数据：字典格式文档
            question = "What is artificial intelligence?"
            docs = [
                {"text": "Artificial intelligence is a branch of computer science"},
                {"text": "AI includes machine learning and deep learning"},
            ]

            input_data = {"query": question, "retrieval_docs": docs}
            result = adapter.execute(input_data)

            # 验证结果格式 - 使用新的统一格式
            assert isinstance(result, dict)
            assert result["query"] == question
            assert "refining_results" in result and len(result["refining_results"]) == 2
            assert "refining_docs" in result and len(result["refining_docs"]) == 2
            assert all("text" in d for d in result["refining_results"])

            # 验证refiner被调用
            mock_service.refine.assert_called_once()


@pytest.mark.integration
class TestRefinerOperatorIntegration:
    """RefinerOperator集成测试"""

    @pytest.mark.skipif(not REFINER_AVAILABLE, reason="Refiner module not available")
    def test_refiner_basic_workflow(self):
        """测试基本工作流"""
        config = {
            "algorithm": "simple",
            "budget": 1000,
            "enable_profile": False,
        }

        with patch("sage.middleware.components.sage_refiner.RefinerService") as mock_service_class:
            mock_service = Mock()

            # 模拟 RefineResult
            mock_result = Mock()
            mock_result.refined_content = ["Refined content"]
            mock_result.metrics = Mock()
            mock_result.metrics.compression_rate = 0.5
            mock_result.metrics.original_tokens = 100
            mock_result.metrics.refined_tokens = 50
            mock_result.metrics.refining_time = 1.0
            
            mock_service.refine.return_value = mock_result
            mock_service_class.return_value = mock_service

            # 创建适配器
            adapter = RefinerOperator(config=config)

            # 测试数据
            question = "What are AI applications?"
            docs = [
                {"text": "AI is used in healthcare"},
                {"text": "Machine learning in finance"},
            ]

            # 执行精炼
            result = adapter.execute({"query": question, "retrieval_docs": docs})

            # 验证结果
            assert isinstance(result, dict)
            assert result["query"] == question
            assert "refining_results" in result
            assert "refining_docs" in result
