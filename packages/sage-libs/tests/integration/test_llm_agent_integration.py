"""
LLM Integration Test for Agent Tasks

Tests real LLM backends (DeepSeek, Qwen, OpenAI, etc.) with agent planning
and tool selection tasks.

**NEW**: Supports embedded VLLMService when GPU is available, no external
API required for local testing.

Usage:
    # Run with embedded vLLM (requires GPU)
    pytest tests/integration/test_llm_agent_integration.py -v -k embedded

    # Run with DeepSeek API
    pytest tests/integration/test_llm_agent_integration.py -v -k deepseek

    # Run with local vLLM server
    pytest tests/integration/test_llm_agent_integration.py -v -k vllm

    # Run all available backends
    pytest tests/integration/test_llm_agent_integration.py -v

Environment Variables:
    DEEPSEEK_API_KEY: DeepSeek API key
    OPENAI_API_KEY: OpenAI API key
    SAGE_VLLM_ENDPOINT: Local vLLM endpoint (default: http://localhost:8000)
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import pytest

logger = logging.getLogger(__name__)


# =============================================================================
# GPU/vLLM Availability Checks
# =============================================================================


def check_gpu_available() -> bool:
    """Check if GPU is available."""
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


def check_vllm_available() -> bool:
    """Check if vLLM is installed and GPU is available."""
    if not check_gpu_available():
        return False
    try:
        import vllm  # noqa: F401

        return True
    except ImportError:
        return False


HAS_GPU = check_gpu_available()
HAS_VLLM = check_vllm_available()


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class LLMBackendConfig:
    """LLM 后端配置"""

    name: str
    api_base: str
    api_key_env: str
    model_id: str
    supports_function_calling: bool = True
    supports_json_mode: bool = True
    max_tokens: int = 2048
    temperature: float = 0.1


# 支持的 LLM 后端
LLM_BACKENDS = {
    "deepseek": LLMBackendConfig(
        name="DeepSeek",
        api_base="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",  # pragma: allowlist secret
        model_id="deepseek-chat",  # 或 deepseek-coder
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "deepseek-reasoner": LLMBackendConfig(
        name="DeepSeek-R1",
        api_base="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",  # pragma: allowlist secret
        model_id="deepseek-reasoner",
        supports_function_calling=False,  # R1 不支持 function calling
        supports_json_mode=True,
    ),
    "openai": LLMBackendConfig(
        name="OpenAI",
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",  # pragma: allowlist secret
        model_id="gpt-4o-mini",
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "qwen-cloud": LLMBackendConfig(
        name="Qwen (Aliyun)",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",  # pragma: allowlist secret
        model_id="qwen-plus",
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "vllm-local": LLMBackendConfig(
        name="vLLM Local",
        api_base=os.getenv("SAGE_VLLM_ENDPOINT", "http://localhost:8000/v1"),
        api_key_env="",  # 本地不需要 key
        model_id="",  # 由 vLLM 服务决定
        supports_function_calling=False,  # 取决于部署的模型
        supports_json_mode=True,
    ),
    "siliconflow": LLMBackendConfig(
        name="SiliconFlow",
        api_base="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",  # pragma: allowlist secret
        model_id="deepseek-ai/DeepSeek-V3",
        supports_function_calling=True,
        supports_json_mode=True,
    ),
}


# =============================================================================
# Embedded LLM Client (GPU-based, no external API needed)
# =============================================================================


class EmbeddedLLMClient:
    """
    内嵌 LLM 客户端，使用 VLLMService 直接在进程内加载模型。

    无需外部 API，只需 GPU 和 vLLM 安装。
    """

    DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._service: Any = None
        self._available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """Check if embedded LLM is available (GPU + vLLM)."""
        if self._available is not None:
            return self._available

        self._available = HAS_VLLM
        if not self._available:
            logger.info("Embedded LLM not available: vLLM or GPU not found")
        return self._available

    def setup(self) -> None:
        """Initialize VLLMService and load model."""
        if self._service is not None:
            return

        from sage.common.components.sage_llm import VLLMService

        config = {
            "model_id": self.model_id,
            "auto_download": True,
            "sampling": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            "engine": {
                "gpu_memory_utilization": 0.5,  # Conservative for testing
                "max_model_len": 4096,
            },
        }

        logger.info(f"Loading embedded LLM: {self.model_id}")
        self._service = VLLMService(config)
        self._service.setup()
        logger.info("Embedded LLM ready")

    def teardown(self) -> None:
        """Release GPU resources."""
        if self._service is not None:
            self._service.cleanup()
            self._service = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text response."""
        if self._service is None:
            self.setup()

        # Build prompt with system message
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = f"User: {prompt}\n\nAssistant:"

        results = self._service.generate(
            full_prompt,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        if results and results[0].get("generations"):
            return results[0]["generations"][0]["text"]
        return ""

    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Generate with tools (simulated via prompt engineering).

        Note: Most small models don't support native function calling,
        so we use prompt-based tool selection.
        """
        # Build tool descriptions
        tool_descs = []
        for t in tools:
            func = t.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            tool_descs.append(f"- {name}: {desc}")

        tools_str = "\n".join(tool_descs)

        enhanced_prompt = f"""You have access to these tools:
{tools_str}

User request: {prompt}

If you need to use a tool, respond with JSON: {{"tool": "tool_name", "arguments": {{...}}}}
If no tool is needed, respond normally."""

        response = self.generate(
            enhanced_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        # Try to parse tool call from response
        tool_calls = []
        try:
            # Look for JSON in response
            import re

            json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response)
            if json_match:
                tool_data = json.loads(json_match.group())
                if "tool" in tool_data:
                    tool_calls.append(
                        {
                            "id": "embedded_call_1",
                            "function": {
                                "name": tool_data["tool"],
                                "arguments": json.dumps(tool_data.get("arguments", {})),
                            },
                        }
                    )
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "content": response,
            "tool_calls": tool_calls,
            "finish_reason": "stop",
        }


# =============================================================================
# LLM Client (API-based)
# =============================================================================


class LLMClient:
    """
    统一的 LLM 客户端接口

    支持 OpenAI-compatible APIs (DeepSeek, Qwen, vLLM 等)
    """

    def __init__(self, config: LLMBackendConfig):
        self.config = config
        self._client = None
        self._available = None

    @property
    def is_available(self) -> bool:
        """检查后端是否可用"""
        if self._available is not None:
            return self._available

        # 检查 API key
        if self.config.api_key_env:
            api_key = os.getenv(self.config.api_key_env)
            if not api_key:
                logger.warning(f"{self.config.name}: Missing {self.config.api_key_env}")
                self._available = False
                return False

        # 尝试连接
        try:
            self._init_client()
            self._available = True
        except Exception as e:
            logger.warning(f"{self.config.name}: Connection failed - {e}")
            self._available = False

        return self._available

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai")

        api_key = (
            os.getenv(self.config.api_key_env, "dummy") if self.config.api_key_env else "dummy"
        )

        self._client = OpenAI(
            api_key=api_key,
            base_url=self.config.api_base,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """生成文本响应"""
        if not self._client:
            self._init_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.config.model_id,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        if json_mode and self.config.supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: Optional[str] = None,
    ) -> dict:
        """使用 function calling 生成响应"""
        if not self.config.supports_function_calling:
            raise NotImplementedError(f"{self.config.name} does not support function calling")

        if not self._client:
            self._init_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.config.model_id,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        message = response.choices[0].message

        return {
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (message.tool_calls or [])
            ],
            "finish_reason": response.choices[0].finish_reason,
        }


# =============================================================================
# Test Fixtures
# =============================================================================


def get_available_backends() -> list[str]:
    """获取所有可用的后端"""
    available = []
    for name, config in LLM_BACKENDS.items():
        client = LLMClient(config)
        if client.is_available:
            available.append(name)
    return available


@pytest.fixture(scope="module")
def available_backends():
    """可用后端列表"""
    backends = get_available_backends()
    if not backends:
        pytest.skip("No LLM backends available")
    return backends


@pytest.fixture(params=list(LLM_BACKENDS.keys()))
def llm_client(request):
    """参数化的 LLM 客户端"""
    backend_name = request.param
    config = LLM_BACKENDS[backend_name]
    client = LLMClient(config)

    if not client.is_available:
        pytest.skip(f"{backend_name} not available")

    return client


# =============================================================================
# Test Data
# =============================================================================

# Agent 工具定义 (OpenAI function calling 格式)
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "weather_query",
            "description": "Query current weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g., 'Beijing', 'Shanghai'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate, e.g., '2 + 3 * 4'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# 测试用例
AGENT_TEST_CASES = [
    {
        "id": "weather_simple",
        "instruction": "What's the weather like in Beijing today?",
        "expected_tool": "weather_query",
        "expected_args": {"location": "Beijing"},
        "difficulty": "easy",
    },
    {
        "id": "calculator_simple",
        "instruction": "Calculate 15 * 8 + 42",
        "expected_tool": "calculator",
        "expected_args": {"expression": "15 * 8 + 42"},
        "difficulty": "easy",
    },
    {
        "id": "search_simple",
        "instruction": "Search for the latest news about AI",
        "expected_tool": "web_search",
        "expected_args": {"query": "latest AI news"},
        "difficulty": "easy",
    },
    {
        "id": "multi_step",
        "instruction": "I need to know the weather in Shanghai and then calculate how many layers of clothes I should wear if it's below 10 degrees",
        "expected_tools": ["weather_query", "calculator"],
        "difficulty": "medium",
    },
    {
        "id": "planning",
        "instruction": "Plan a trip to Tokyo: 1) search for flight prices, 2) check the weather forecast, 3) calculate the total budget if flights cost $500 and hotel is $150/night for 5 nights",
        "expected_tools": ["web_search", "weather_query", "calculator"],
        "difficulty": "hard",
    },
]

# Agent 系统提示
AGENT_SYSTEM_PROMPT = """You are an intelligent assistant that can use tools to help users.

Available tools:
1. weather_query: Get weather information for a location
2. calculator: Perform mathematical calculations
3. web_search: Search the web for information

When you need to use a tool, respond with the appropriate function call.
Think step by step and use tools when necessary."""


# =============================================================================
# Test Cases
# =============================================================================


class TestLLMAgentIntegration:
    """LLM Agent 集成测试"""

    @pytest.mark.integration
    def test_basic_generation(self, llm_client: LLMClient):
        """测试基础文本生成"""
        response = llm_client.generate(
            prompt="Say 'Hello, SAGE!' and nothing else.",
            temperature=0.0,
        )

        assert response is not None
        assert len(response) > 0
        assert "SAGE" in response or "sage" in response.lower()

        logger.info(f"[{llm_client.config.name}] Basic generation: {response[:100]}")

    @pytest.mark.integration
    def test_json_generation(self, llm_client: LLMClient):
        """测试 JSON 格式生成"""
        response = llm_client.generate(
            prompt='Generate a JSON object with keys "name" and "age" for a person named "Alice" who is 25.',
            json_mode=True,
            temperature=0.0,
        )

        assert response is not None

        # 验证是有效 JSON
        try:
            data = json.loads(response)
            assert "name" in data or "Alice" in response
        except json.JSONDecodeError:
            # 有些模型不完美遵循 JSON 模式
            logger.warning(f"[{llm_client.config.name}] Non-strict JSON: {response[:200]}")

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "test_case", [tc for tc in AGENT_TEST_CASES if tc["difficulty"] == "easy"]
    )
    def test_tool_selection_easy(self, llm_client: LLMClient, test_case: dict):
        """测试简单工具选择"""
        if not llm_client.config.supports_function_calling:
            pytest.skip(f"{llm_client.config.name} does not support function calling")

        result = llm_client.generate_with_tools(
            prompt=test_case["instruction"],
            tools=AGENT_TOOLS,
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        logger.info(f"[{llm_client.config.name}] {test_case['id']}: {result}")

        # 验证调用了正确的工具
        tool_calls = result.get("tool_calls", [])

        if tool_calls:
            called_tool = tool_calls[0]["function"]["name"]
            assert called_tool == test_case["expected_tool"], (
                f"Expected {test_case['expected_tool']}, got {called_tool}"
            )

    @pytest.mark.integration
    def test_agent_planning_prompt(self, llm_client: LLMClient):
        """测试 Agent 规划（不使用 function calling）"""
        planning_prompt = """You are a planning agent. Given the user's request, create a step-by-step plan.

User request: Book a flight from Beijing to Shanghai for tomorrow, and find a hotel near the airport.

Output your plan as a JSON array of steps, where each step has:
- "step_number": integer
- "action": string describing the action
- "tool": name of tool to use (one of: flight_search, hotel_search, calendar_check)
- "parameters": object with tool parameters

Output only the JSON array, no other text."""

        response = llm_client.generate(
            prompt=planning_prompt,
            temperature=0.0,
        )

        logger.info(f"[{llm_client.config.name}] Planning response: {response[:500]}")

        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            import re

            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                plan = json.loads(json_match.group())
                assert isinstance(plan, list)
                assert len(plan) >= 2, "Plan should have at least 2 steps"

                # 检查步骤结构
                for step in plan:
                    assert "action" in step or "tool" in step, f"Invalid step: {step}"

                logger.info(f"[{llm_client.config.name}] Valid plan with {len(plan)} steps")
        except (json.JSONDecodeError, AssertionError) as e:
            logger.warning(f"[{llm_client.config.name}] Plan parsing issue: {e}")


class TestDeepSeekSpecific:
    """DeepSeek 特定测试"""

    @pytest.fixture
    def deepseek_client(self):
        config = LLM_BACKENDS["deepseek"]
        client = LLMClient(config)
        if not client.is_available:
            pytest.skip("DeepSeek not available")
        return client

    @pytest.mark.integration
    def test_deepseek_function_calling(self, deepseek_client: LLMClient):
        """测试 DeepSeek function calling"""
        result = deepseek_client.generate_with_tools(
            prompt="What's the weather in Tokyo?",
            tools=AGENT_TOOLS,
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        assert result["tool_calls"], "DeepSeek should generate tool calls"
        assert result["tool_calls"][0]["function"]["name"] == "weather_query"

        # 验证参数
        args = json.loads(result["tool_calls"][0]["function"]["arguments"])
        assert "location" in args
        assert "Tokyo" in args["location"] or "tokyo" in args["location"].lower()

    @pytest.mark.integration
    def test_deepseek_chinese_agent(self, deepseek_client: LLMClient):
        """测试 DeepSeek 中文 Agent 任务"""
        result = deepseek_client.generate_with_tools(
            prompt="帮我查一下北京今天的天气怎么样",
            tools=AGENT_TOOLS,
            system_prompt="你是一个智能助手，可以使用工具帮助用户完成任务。",
        )

        logger.info(f"DeepSeek Chinese: {result}")

        if result["tool_calls"]:
            assert result["tool_calls"][0]["function"]["name"] == "weather_query"


class TestModelComparison:
    """多模型对比测试"""

    @pytest.mark.integration
    def test_compare_tool_selection_accuracy(self, available_backends: list[str]):
        """对比不同模型的工具选择准确率"""
        results = {}

        for backend_name in available_backends:
            config = LLM_BACKENDS[backend_name]
            client = LLMClient(config)

            if not client.config.supports_function_calling:
                continue

            correct = 0
            total = 0

            for test_case in AGENT_TEST_CASES:
                if test_case["difficulty"] != "easy":
                    continue
                if "expected_tool" not in test_case:
                    continue

                try:
                    result = client.generate_with_tools(
                        prompt=test_case["instruction"],
                        tools=AGENT_TOOLS,
                        system_prompt=AGENT_SYSTEM_PROMPT,
                    )

                    total += 1
                    if result["tool_calls"]:
                        called_tool = result["tool_calls"][0]["function"]["name"]
                        if called_tool == test_case["expected_tool"]:
                            correct += 1

                except Exception as e:
                    logger.warning(f"{backend_name} failed on {test_case['id']}: {e}")
                    total += 1

            if total > 0:
                results[backend_name] = {
                    "accuracy": correct / total,
                    "correct": correct,
                    "total": total,
                }

        # 输出对比结果
        logger.info("\n=== Tool Selection Accuracy Comparison ===")
        for name, stats in sorted(results.items(), key=lambda x: x[1]["accuracy"], reverse=True):
            logger.info(f"{name}: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")

        assert len(results) > 0, "At least one backend should be tested"


# =============================================================================
# Embedded LLM Tests (GPU-based, no external API)
# =============================================================================


@pytest.mark.integration
class TestEmbeddedLLM:
    """
    内嵌 LLM 测试 - 使用本地 GPU，无需外部 API。

    这些测试在有 GPU 和 vLLM 时自动启用，无需配置 API keys。
    """

    @pytest.fixture(scope="class")
    def embedded_client(self):
        """创建内嵌 LLM 客户端 fixture"""
        if not HAS_VLLM:
            pytest.skip("vLLM or GPU not available")

        client = EmbeddedLLMClient(
            model_id="Qwen/Qwen2.5-0.5B-Instruct",
            max_tokens=256,
            temperature=0.1,
        )
        yield client
        # Cleanup after all tests in class
        client.teardown()

    def test_embedded_availability(self):
        """测试内嵌 LLM 可用性检测"""
        client = EmbeddedLLMClient()
        is_available = client.is_available

        if HAS_VLLM:
            assert is_available, "Should be available when vLLM and GPU are present"
        else:
            assert not is_available, "Should not be available without vLLM/GPU"

    @pytest.mark.skipif(not HAS_VLLM, reason="vLLM or GPU not available")
    def test_embedded_basic_generation(self, embedded_client: EmbeddedLLMClient):
        """测试内嵌 LLM 基础文本生成"""
        response = embedded_client.generate(
            prompt="What is 2 + 2? Answer with just the number.",
            temperature=0.0,
            max_tokens=32,
        )

        assert response is not None
        assert len(response) > 0
        # The response should contain "4" somewhere
        assert "4" in response, f"Expected '4' in response, got: {response}"

        logger.info(f"[Embedded] Basic generation: {response[:100]}")

    @pytest.mark.skipif(not HAS_VLLM, reason="vLLM or GPU not available")
    def test_embedded_with_system_prompt(self, embedded_client: EmbeddedLLMClient):
        """测试内嵌 LLM 系统提示"""
        response = embedded_client.generate(
            prompt="What color is the sky?",
            system_prompt="You are a helpful assistant. Always answer briefly.",
            temperature=0.0,
        )

        assert response is not None
        assert len(response) > 0
        # Should mention blue or sky-related color
        response_lower = response.lower()
        assert any(word in response_lower for word in ["blue", "sky", "color"]), (
            f"Unexpected response: {response}"
        )

        logger.info(f"[Embedded] System prompt test: {response[:100]}")

    @pytest.mark.skipif(not HAS_VLLM, reason="vLLM or GPU not available")
    def test_embedded_tool_selection(self, embedded_client: EmbeddedLLMClient):
        """测试内嵌 LLM 工具选择（通过 prompt）"""
        result = embedded_client.generate_with_tools(
            prompt="What's the weather in Beijing?",
            tools=AGENT_TOOLS,
            system_prompt="You are an assistant that can use tools.",
        )

        logger.info(f"[Embedded] Tool selection result: {result}")

        # Should have some response
        assert result is not None
        assert "content" in result

        # Tool calls are optional (depends on model capability)
        if result.get("tool_calls"):
            tool_call = result["tool_calls"][0]
            logger.info(f"[Embedded] Detected tool call: {tool_call['function']['name']}")

    @pytest.mark.skipif(not HAS_VLLM, reason="vLLM or GPU not available")
    def test_embedded_chinese(self, embedded_client: EmbeddedLLMClient):
        """测试内嵌 LLM 中文支持"""
        response = embedded_client.generate(
            prompt="请用中文回答：1加1等于几？",
            temperature=0.0,
            max_tokens=64,
        )

        assert response is not None
        assert len(response) > 0
        # Should contain "2" or Chinese numeral
        assert "2" in response or "二" in response, f"Unexpected response: {response}"

        logger.info(f"[Embedded] Chinese test: {response[:100]}")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    # 列出可用后端
    print("Checking available LLM backends...")
    for name, config in LLM_BACKENDS.items():
        client = LLMClient(config)
        status = "Available" if client.is_available else "Not available"
        print(f"  {name}: {status}")

    # Check embedded availability
    embedded = EmbeddedLLMClient()
    embedded_status = "Available (GPU + vLLM)" if embedded.is_available else "Not available"
    print(f"  embedded: {embedded_status}")

    # 运行测试
    pytest.main([__file__, "-v", "-x", "--tb=short"])
