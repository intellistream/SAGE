"""
LLM Integration Test for Agent Tasks

Tests real LLM backends (DeepSeek, Qwen, OpenAI, etc.) with agent planning
and tool selection tasks.

Usage:
    # Run with DeepSeek API
    pytest tests/integration/test_llm_agent_integration.py -v -k deepseek

    # Run with local vLLM
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
from typing import Optional

import pytest

logger = logging.getLogger(__name__)

# Skip entire module in CI - these tests require real API keys or GPU
_IS_CI = os.environ.get("CI") == "true" or os.environ.get("SAGE_TEST_MODE") == "true"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(_IS_CI, reason="LLM integration tests require real API keys or GPU"),
]


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
# LLM Client
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
            # For local vLLM, do a health check since no API key is required
            if not self.config.api_key_env:
                # Try to list models to verify connection
                import httpx

                try:
                    resp = httpx.get(f"{self.config.api_base}/models", timeout=5.0)
                    if resp.status_code != 200:
                        logger.warning(
                            f"{self.config.name}: Health check failed (status {resp.status_code})"
                        )
                        self._available = False
                        return False
                except Exception as e:
                    logger.warning(f"{self.config.name}: Health check failed - {e}")
                    self._available = False
                    return False
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
# Run Tests
# =============================================================================

if __name__ == "__main__":
    # 列出可用后端
    print("Checking available LLM backends...")
    for name, config in LLM_BACKENDS.items():
        client = LLMClient(config)
        status = "✅ Available" if client.is_available else "❌ Not available"
        print(f"  {name}: {status}")

    # 运行测试
    pytest.main([__file__, "-v", "-x", "--tb=short"])
