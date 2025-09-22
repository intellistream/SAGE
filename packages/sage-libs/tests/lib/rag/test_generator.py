"""
测试 sage.libs.rag.generator 模块
"""

import json
import os
import tempfile
import time
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# 尝试导入生成器模块
pytest_plugins = []

try:
    from sage.libs.rag.generator import HFGenerator, OpenAIGenerator

    GENERATOR_AVAILABLE = True
except ImportError as e:
    GENERATOR_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Generator module not available: {e}")


@pytest.mark.unit
class TestOpenAIGenerator:
    """测试OpenAIGenerator类"""

    def test_openai_generator_import(self):
        """测试OpenAIGenerator导入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        from sage.libs.rag.generator import OpenAIGenerator

        assert OpenAIGenerator is not None

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_openai_generator_initialization(self, mock_openai_client):
        """测试OpenAIGenerator初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient
        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 验证初始化
        assert generator.config == config
        assert generator.enable_profile == False
        assert generator.num == 1

        # 验证OpenAIClient被正确调用
        mock_openai_client.assert_called_once_with(
            model_name="gpt-4o-mini",
            base_url="http://localhost:8000/v1",
            api_key="test_key",
            seed=42,
        )
        assert generator.model == mock_client_instance

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_openai_generator_initialization_with_profile(self, mock_openai_client):
        """测试OpenAIGenerator带profile初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient
        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        # Mock context with env_base_dir - 使用统一的SAGE路径管理
        mock_ctx = Mock()
        from sage.common.config.output_paths import get_test_temp_dir

        test_dir = get_test_temp_dir("test_generator")
        mock_ctx.env_base_dir = str(test_dir)

        with patch("os.makedirs") as mock_makedirs:
            generator = OpenAIGenerator(config=config, enable_profile=True)
            generator.ctx = mock_ctx

            # 重新初始化以设置profile路径
            generator.__init__(config=config, enable_profile=True)

            assert generator.enable_profile == True

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_openai_generator_initialization_no_api_key(self, mock_openai_client):
        """测试OpenAIGenerator无API密钥初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": None,
            "seed": 42,
        }

        # Mock环境变量
        with patch.dict(os.environ, {"ALIBABA_API_KEY": "env_api_key"}):
            mock_client_instance = Mock()
            mock_openai_client.return_value = mock_client_instance

            generator = OpenAIGenerator(config=config)

            # 验证使用环境变量中的API密钥
            mock_openai_client.assert_called_once_with(
                model_name="gpt-4o-mini",
                base_url="http://localhost:8000/v1",
                api_key="env_api_key",
                seed=42,
            )

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_execute_with_string_input(self, mock_openai_client):
        """测试execute方法处理字符串输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试字符串输入 - OpenAIGenerator期望列表输入
        input_data = ["Test prompt"]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query is None  # 因为只有一个输入
        assert response == "Generated response"
        mock_client_instance.generate.assert_called_once_with("Test prompt")

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_execute_with_dict_input(self, mock_openai_client):
        """测试execute方法处理字典输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试字典输入 - OpenAIGenerator期望列表输入
        input_data = ["What is AI?", "Please explain artificial intelligence."]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query == "What is AI?"
        assert response == "Generated response"

        mock_client_instance.generate.assert_called_once_with(
            "Please explain artificial intelligence."
        )

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_execute_with_profile_enabled(self, mock_openai_client):
        """测试启用profile的execute方法"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        with patch("os.makedirs"), patch(
            "builtins.open", create=True
        ) as mock_open, patch("json.dump") as mock_json_dump:

            generator = OpenAIGenerator(config=config, enable_profile=True)

            # Mock context - 使用统一的SAGE路径管理
            mock_ctx = Mock()
            from sage.common.config.output_paths import get_test_temp_dir

            test_dir = get_test_temp_dir("test_generator")
            mock_ctx.env_base_dir = str(test_dir)
            generator.ctx = mock_ctx
            generator.data_base_path = str(
                test_dir / ".sage" / "states" / "generator_data"
            )
            generator.data_records = []

            input_data = ["Test prompt"]

            with patch("time.time", return_value=1234567890.0):
                result = generator.execute(input_data)

            # 验证结果
            assert isinstance(result, tuple)
            assert len(result) == 2
            user_query, response = result
            assert user_query is None
            assert response == "Generated response"

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_execute_with_api_error(self, mock_openai_client):
        """测试execute方法处理API错误"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient抛出异常
        mock_client_instance = Mock()
        mock_client_instance.generate.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试异常处理
        with pytest.raises(Exception) as exc_info:
            generator.execute(["Test prompt"])

        assert "API Error" in str(exc_info.value)

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_execute_increments_counter(self, mock_openai_client):
        """测试execute方法会递增计数器"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.chat_completion.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 验证初始计数器
        assert generator.num == 1

        # 执行多次调用
        generator.execute(["Test prompt 1"])
        assert generator.num == 2

        generator.execute(["Test prompt 2"])
        assert generator.num == 3

    @patch("sage.libs.rag.generator.OpenAIClient")
    def test_configuration_validation(self, mock_openai_client):
        """测试配置验证"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        # 测试缺少必需配置字段
        incomplete_configs = [
            {},  # 空配置
            {"model_name": "gpt-4o-mini"},  # 缺少base_url
            {"base_url": "http://localhost:8000/v1"},  # 缺少model_name
        ]

        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        for config in incomplete_configs:
            with pytest.raises(KeyError):
                OpenAIGenerator(config=config)


@pytest.mark.integration
class TestOpenAIGeneratorIntegration:
    """OpenAIGenerator集成测试"""

    @pytest.mark.skipif(
        not GENERATOR_AVAILABLE, reason="Generator module not available"
    )
    def test_generator_with_mock_service(self):
        """测试生成器与mock服务的集成"""
        config = {
            "model_name": "test-model",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        with patch("sage.libs.rag.generator.OpenAIClient") as mock_openai_client:
            mock_client_instance = Mock()
            mock_client_instance.generate.return_value = "Mocked response"
            mock_openai_client.return_value = mock_client_instance

            generator = OpenAIGenerator(config=config)

            # 测试完整的数据流
            test_data = [
                "Analyze the following context and answer the question.",
                "What is machine learning?",
            ]

            result = generator.execute(test_data)

            # 验证结果结构
            assert isinstance(result, tuple)
            assert len(result) == 2
            user_query, response = result
            assert (
                user_query == "Analyze the following context and answer the question."
            )
            assert response == "Mocked response"


@pytest.mark.unit
class TestHFGenerator:
    """测试HFGenerator类"""

    def test_hf_generator_import(self):
        """测试HFGenerator导入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        from sage.libs.rag.generator import HFGenerator

        assert HFGenerator is not None

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_initialization(self, mock_hf_client):
        """测试HFGenerator初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient
        mock_client_instance = Mock()
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 验证初始化
        assert generator.config == config

        # 验证HFClient被正确调用
        mock_hf_client.assert_called_once_with(model_name="microsoft/DialoGPT-medium")
        assert generator.model == mock_client_instance

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_list_input(self, mock_hf_client):
        """测试HFGenerator处理列表输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试列表输入 [user_query, prompt]
        input_data = ["What is AI?", "Please explain artificial intelligence."]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query == "What is AI?"
        assert response == "Generated response"

        # 验证model.generate被正确调用
        mock_client_instance.generate.assert_called_once_with(
            "Please explain artificial intelligence."
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_single_input(self, mock_hf_client):
        """测试HFGenerator处理单个输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Single response"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试单个输入
        input_data = ["Explain machine learning"]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query is None  # HFGenerator: data[0] if len(data) > 1 else None
        assert response == "Single response"

        # 验证model.generate被正确调用
        mock_client_instance.generate.assert_called_once_with(
            "Explain machine learning"
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_kwargs(self, mock_hf_client):
        """测试HFGenerator处理额外参数"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Response with params"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试带有额外参数的调用
        input_data = ["Generate text"]
        kwargs = {"temperature": 0.7, "max_length": 100}

        result = generator.execute(input_data, **kwargs)

        # 验证结果
        assert isinstance(result, tuple)
        user_query, response = result
        assert response == "Response with params"

        # 验证model.generate被正确调用，包含kwargs
        mock_client_instance.generate.assert_called_once_with(
            "Generate text", temperature=0.7, max_length=100
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_error_handling(self, mock_hf_client):
        """测试HFGenerator错误处理"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient抛出异常
        mock_client_instance = Mock()
        mock_client_instance.generate.side_effect = Exception("HF API Error")
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试异常处理
        with pytest.raises(Exception) as exc_info:
            generator.execute(["Test input"])

        assert "HF API Error" in str(exc_info.value)


@pytest.mark.integration
class TestGeneratorIntegration:
    """Generator集成测试"""

    @pytest.mark.skipif(
        not GENERATOR_AVAILABLE, reason="Generator module not available"
    )
    def test_multiple_generators_comparison(self):
        """测试多个生成器的比较"""
        openai_config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",
            "seed": 42,
        }

        hf_config = {"model_name": "microsoft/DialoGPT-medium"}

        with patch("sage.libs.rag.generator.OpenAIClient") as mock_openai, patch(
            "sage.libs.rag.generator.HFClient"
        ) as mock_hf:

            # Mock两个客户端
            mock_openai_instance = Mock()
            mock_openai_instance.generate.return_value = "OpenAI response"
            mock_openai.return_value = mock_openai_instance

            mock_hf_instance = Mock()
            mock_hf_instance.generate.return_value = "HF response"
            mock_hf.return_value = mock_hf_instance

            # 创建生成器
            openai_gen = OpenAIGenerator(config=openai_config)
            hf_gen = HFGenerator(config=hf_config)

            # 测试相同输入
            test_input = ["What is artificial intelligence?"]

            openai_result = openai_gen.execute(test_input)
            hf_result = hf_gen.execute(test_input)

            # 验证结果格式一致性
            assert isinstance(openai_result, tuple)
            assert isinstance(hf_result, tuple)
            assert len(openai_result) == 2
            assert len(hf_result) == 2

            # 验证两个生成器都被正确调用
            mock_openai_instance.generate.assert_called_once()
            mock_hf_instance.generate.assert_called_once()


@pytest.mark.unit
class TestHFGenerator:
    """测试HFGenerator类"""

    def test_hf_generator_import(self):
        """测试HFGenerator导入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        from sage.libs.rag.generator import HFGenerator

        assert HFGenerator is not None

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_initialization(self, mock_hf_client):
        """测试HFGenerator初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient
        mock_client_instance = Mock()
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 验证初始化
        assert generator.config == config

        # 验证HFClient被正确调用
        mock_hf_client.assert_called_once_with(model_name="microsoft/DialoGPT-medium")
        assert generator.model == mock_client_instance

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_tuple_input(self, mock_hf_client):
        """测试HFGenerator execute方法处理元组输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "HF Generated response"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试元组输入 (user_query, prompt)
        input_data = ["What is AI?", "Answer the following question: What is AI?"]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query == "What is AI?"
        assert response == "HF Generated response"
        mock_client_instance.generate.assert_called_once_with(
            "Answer the following question: What is AI?"
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_single_input(self, mock_hf_client):
        """测试HFGenerator execute方法处理单一输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "HF Generated response"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试单一输入 - 需要作为列表传入
        input_data = ["Generate a response for this prompt"]
        result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, tuple)
        assert len(result) == 2
        user_query, response = result
        assert user_query is None  # 当只有一个输入时，user_query为None
        assert response == "HF Generated response"

        # 验证model.generate被正确调用 - 传入整个列表
        mock_client_instance.generate.assert_called_once_with(
            ["Generate a response for this prompt"]
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_kwargs(self, mock_hf_client):
        """测试HFGenerator execute方法传递额外参数"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "HF Generated response"
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试带额外参数的调用 - 需要作为列表传入
        input_data = ["Test prompt"]
        result = generator.execute(input_data, temperature=0.7, max_tokens=100)

        # 验证结果和参数传递
        assert isinstance(result, tuple)
        mock_client_instance.generate.assert_called_once_with(
            ["Test prompt"],  # HFGenerator传递整个列表作为prompt
            temperature=0.7,
            max_tokens=100,
        )

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_execute_with_error(self, mock_hf_client):
        """测试HFGenerator execute方法处理错误"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {"model_name": "microsoft/DialoGPT-medium"}

        # Mock HFClient抛出异常
        mock_client_instance = Mock()
        mock_client_instance.generate.side_effect = Exception("HF Model Error")
        mock_hf_client.return_value = mock_client_instance

        generator = HFGenerator(config=config)

        # 测试异常处理
        with pytest.raises(Exception) as exc_info:
            generator.execute("Test prompt")

        assert "HF Model Error" in str(exc_info.value)

    @patch("sage.libs.rag.generator.HFClient")
    def test_hf_generator_configuration_validation(self, mock_hf_client):
        """测试HFGenerator配置验证"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        # 测试缺少必需配置字段
        incomplete_config = {}  # 缺少model_name

        mock_client_instance = Mock()
        mock_hf_client.return_value = mock_client_instance

        with pytest.raises(KeyError):
            HFGenerator(config=incomplete_config)


@pytest.mark.integration
class TestHFGeneratorIntegration:
    """HFGenerator集成测试"""

    @pytest.mark.skipif(
        not GENERATOR_AVAILABLE, reason="Generator module not available"
    )
    def test_hf_generator_with_mock_service(self):
        """测试HFGenerator与mock服务的集成"""
        config = {"model_name": "microsoft/DialoGPT-medium"}

        with patch("sage.libs.rag.generator.HFClient") as mock_hf_client:
            mock_client_instance = Mock()
            mock_client_instance.generate.return_value = "Mocked HF response"
            mock_hf_client.return_value = mock_client_instance

            generator = HFGenerator(config=config)

            # 测试完整的数据流
            test_data = ["What is deep learning?", "Explain deep learning concepts"]

            result = generator.execute(test_data)

            # 验证结果结构
            assert isinstance(result, tuple)
            assert len(result) == 2
            user_query, response = result
            assert user_query == "What is deep learning?"
            assert response == "Mocked HF response"
