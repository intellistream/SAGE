"""
测试 sage.middleware.operators.rag.generator 模块
"""

import os
from unittest.mock import Mock, patch

import pytest

# 尝试导入生成器模块
pytest_plugins = []

try:
    from sage.middleware.operators.rag.generator import HFGenerator, OpenAIGenerator

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

        from sage.middleware.operators.rag.generator import OpenAIGenerator

        assert OpenAIGenerator is not None

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_openai_generator_initialization(self, mock_openai_client):
        """测试OpenAIGenerator初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        # Mock OpenAIClient
        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 验证初始化
        assert generator.config == config
        assert generator.enable_profile is False
        assert generator.num == 1

        # 验证OpenAIClient被正确调用
        mock_openai_client.assert_called_once_with(
            model_name="gpt-4o-mini",
            base_url="http://localhost:8000/v1",
            api_key="test_key",  # pragma: allowlist secret
            seed=42,
        )
        assert generator.model == mock_client_instance

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_openai_generator_initialization_with_profile(self, mock_openai_client):
        """测试OpenAIGenerator带profile初始化"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
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

        with patch("os.makedirs"):
            generator = OpenAIGenerator(config=config, enable_profile=True)
            generator.ctx = mock_ctx

            # 重新初始化以设置profile路径
            generator.__init__(config=config, enable_profile=True)

            assert generator.enable_profile is True

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
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
        with patch.dict(os.environ, {"ALIBABA_API_KEY": "env_api_key"}):  # pragma: allowlist secret
            mock_client_instance = Mock()
            mock_openai_client.return_value = mock_client_instance

            OpenAIGenerator(config=config)

            # 验证使用环境变量中的API密钥
            # 注意：某些Mock实现可能会遮蔽敏感信息，所以我们检查调用参数
            assert mock_openai_client.call_count == 1
            call_kwargs = mock_openai_client.call_args[1]
            assert call_kwargs["model_name"] == "gpt-4o-mini"
            assert call_kwargs["base_url"] == "http://localhost:8000/v1"
            # API key 可能被遮蔽显示为 ***，我们只检查它不是 None
            assert call_kwargs["api_key"] is not None
            assert call_kwargs["seed"] == 42

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_string_input(self, mock_openai_client):
        """测试execute方法处理字符串输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
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

        # 新实现：单输入返回字典，包含 generated 与 generate_time
        assert isinstance(result, dict)
        assert result["generated"] == "Generated response"
        expected_messages = [{"role": "user", "content": "Test prompt"}]
        mock_client_instance.generate.assert_called_once_with(expected_messages)

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_two_string_inputs(self, mock_openai_client):
        """测试execute方法处理两个字符串输入（原始query + prompt）"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试两个字符串输入（原始query + prompt）
        input_data = ["What is AI?", "Please explain artificial intelligence."]
        result = generator.execute(input_data)

        # 新实现：返回 dict，包含 query、generated 和 generate_time
        assert isinstance(result, dict)
        assert result["query"] == ""
        assert result["generated"] == "Generated response"

        expected_messages = [{"role": "user", "content": "Please explain artificial intelligence."}]
        mock_client_instance.generate.assert_called_once_with(expected_messages)

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_profile_enabled(self, mock_openai_client):
        """测试启用profile的execute方法"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        with patch("os.makedirs"), patch("builtins.open", create=True), patch("json.dump"):
            generator = OpenAIGenerator(config=config, enable_profile=True)

            # Mock context - 使用统一的SAGE路径管理
            mock_ctx = Mock()
            from sage.common.config.output_paths import get_test_temp_dir

            test_dir = get_test_temp_dir("test_generator")
            mock_ctx.env_base_dir = str(test_dir)
            generator.ctx = mock_ctx
            generator.data_base_path = str(test_dir / ".sage" / "states" / "generator_data")
            generator.data_records = []

            input_data = ["Test prompt"]

            with patch("time.time", return_value=1234567890.0):
                result = generator.execute(input_data)

            # 新实现：单输入返回字典
            assert isinstance(result, dict)
            assert result["generated"] == "Generated response"

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_api_error(self, mock_openai_client):
        """测试execute方法处理API错误"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
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

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_increments_counter(self, mock_openai_client):
        """测试execute方法会递增计数器"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
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

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_dict_input_returns_generate_time(self, mock_openai_client):
        """测试execute方法处理字典输入时返回generate_time字段"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试字典输入 - OpenAIGenerator期望列表输入: [original_data, prompt]
        original_data = {"query": "What is AI?", "other_field": "value"}
        prompt = "Please explain artificial intelligence."
        input_data = [original_data, prompt]

        with patch("time.time", side_effect=[1000.0, 1001.5]):  # start, end times
            result = generator.execute(input_data)

        # 验证结果是字典格式且包含generate_time
        assert isinstance(result, dict)
        assert "generated" in result
        assert result["generated"] == "Generated response"
        assert result["query"] == "What is AI?"
        assert result["other_field"] == "value"

        # 验证调用参数
        expected_messages = [{"role": "user", "content": prompt}]
        mock_client_instance.generate.assert_called_once_with(expected_messages)

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
    def test_execute_with_messages_list_input(self, mock_openai_client):
        """测试execute方法处理消息列表输入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        # Mock OpenAIClient和其响应
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated response"
        mock_openai_client.return_value = mock_client_instance

        generator = OpenAIGenerator(config=config)

        # 测试消息列表输入 - 已格式化的消息
        original_data = {"query": "What is AI?"}
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is artificial intelligence?"},
        ]
        input_data = [original_data, messages]

        with patch("time.time", side_effect=[1000.0, 1002.0]):  # start, end times
            result = generator.execute(input_data)

        # 验证结果
        assert isinstance(result, dict)
        assert "generated" in result
        assert result["generated"] == "Generated response"
        assert result["query"] == "What is AI?"

        # 验证直接传递消息列表
        mock_client_instance.generate.assert_called_once_with(messages)

    @patch("sage.middleware.operators.rag.generator.OpenAIClient")
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

    @pytest.mark.skipif(not GENERATOR_AVAILABLE, reason="Generator module not available")
    def test_generator_with_mock_service(self):
        """测试生成器与mock服务的集成"""
        config = {
            "model_name": "test-model",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        with patch("sage.middleware.operators.rag.generator.OpenAIClient") as mock_openai_client:
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

            # 新实现：返回 dict，包含 query、generated 和 generate_time
            assert isinstance(result, dict)
            assert result["query"] == ""
            assert result["generated"] == "Mocked response"


@pytest.mark.unit
class TestHFGenerator:
    """测试HFGenerator类"""

    def test_hf_generator_import(self):
        """测试HFGenerator导入"""
        if not GENERATOR_AVAILABLE:
            pytest.skip("Generator module not available")

        from sage.middleware.operators.rag.generator import HFGenerator

        assert HFGenerator is not None

    @patch("sage.middleware.operators.rag.generator.HFClient")
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

    @patch("sage.middleware.operators.rag.generator.HFClient")
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

    @patch("sage.middleware.operators.rag.generator.HFClient")
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
        assert (
            user_query == ""
        )  # HFGenerator: data[0] if len(data) > 1 else "" (empty string when single input)
        assert response == "Single response"

        # 验证model.generate被正确调用
        mock_client_instance.generate.assert_called_once_with("Explain machine learning")

    @patch("sage.middleware.operators.rag.generator.HFClient")
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

    @patch("sage.middleware.operators.rag.generator.HFClient")
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

    @pytest.mark.skipif(not GENERATOR_AVAILABLE, reason="Generator module not available")
    def test_multiple_generators_comparison(self):
        """测试多个生成器的比较"""
        openai_config = {
            "model_name": "gpt-4o-mini",
            "base_url": "http://localhost:8000/v1",
            "api_key": "test_key",  # pragma: allowlist secret
            "seed": 42,
        }

        hf_config = {"model_name": "microsoft/DialoGPT-medium"}

        with (
            patch("sage.middleware.operators.rag.generator.OpenAIClient") as mock_openai,
            patch("sage.middleware.operators.rag.generator.HFClient") as mock_hf,
        ):
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

            # 新实现：OpenAI 单输入返回字典；HF 返回元组
            assert isinstance(openai_result, dict)
            assert isinstance(hf_result, tuple)

            # 验证两个生成器都被正确调用
            mock_openai_instance.generate.assert_called_once()
            mock_hf_instance.generate.assert_called_once()
