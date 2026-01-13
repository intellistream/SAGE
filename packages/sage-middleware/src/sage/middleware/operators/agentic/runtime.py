from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

from sage_libs.sage_agentic.agents.action.mcp_registry import MCPRegistry
from sage_libs.sage_agentic.agents.profile.profile import BaseProfile

from sage.common.core.functions import MapFunction as MapOperator
from sage.middleware.operators.agent.runtime import AgentRuntime
from sage.middleware.operators.rag.generator import HFGenerator, OpenAIGenerator


def _maybe_instantiate(spec: dict[str, Any]):
    module_path = spec["module"]
    class_name = spec["class"]
    kwargs = spec.get("init_kwargs", {})
    module = import_module(module_path)
    ctor = getattr(module, class_name)
    return ctor(**kwargs) if kwargs else ctor()


def _build_generator(config: Any, engine_type: str = "sagellm"):
    """构建 LLM 生成器

    Args:
        config: 生成器配置，可以是已实例化的对象、模块路径配置或参数字典
        engine_type: 引擎类型，支持 "sagellm"（默认）/ "openai" / "hf"
            注意: "vllm" 已废弃，会自动转换为 sagellm 并发出警告

    Returns:
        生成器实例
    """
    if not config:
        raise ValueError("generator config/object is required for AgentRuntimeOperator")

    # 如果已经是生成器实例，直接返回
    if hasattr(config, "execute") or hasattr(config, "generate"):
        return config

    # 模块路径方式实例化
    if isinstance(config, dict) and "module" in config and "class" in config:
        return _maybe_instantiate(config)

    # 从配置中获取 engine_type（如果存在），覆盖参数
    if isinstance(config, dict):
        engine_type = config.get("engine_type", engine_type)

    # 根据 engine_type 选择生成器
    if engine_type == "vllm":
        # vllm 已废弃，自动转换为 sagellm
        warnings.warn(
            "engine_type='vllm' is deprecated for agent generators. "
            "Automatically using engine_type='sagellm' instead. "
            "Please update your configuration.",
            DeprecationWarning,
            stacklevel=3,
        )
        engine_type = "sagellm"  # 转换为 sagellm

    if engine_type == "sagellm":
        # 默认使用 sagellm
        from sage.middleware.operators.llm import SageLLMGenerator

        if isinstance(config, dict):
            return SageLLMGenerator(
                backend_type=config.get("backend_type", "auto"),
                model_path=config.get("model_path", ""),
                device_map=config.get("device_map", "auto"),
                dtype=config.get("dtype", "auto"),
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                top_p=config.get("top_p", 0.95),
                top_k=config.get("top_k", 50),
                timeout=config.get("timeout", 120.0),
                default_options=config.get("default_options", {}),
            )
        return SageLLMGenerator()

    elif engine_type in ("openai", "openai-compatible"):
        return OpenAIGenerator(config if isinstance(config, dict) else {})

    elif engine_type in ("hf", "huggingface"):
        return HFGenerator(config if isinstance(config, dict) else {})

    else:
        # 兼容旧版 method 参数
        method = ""
        if isinstance(config, dict):
            method = (config.get("method") or config.get("type") or "").lower()

        if method.startswith("hf") or method.startswith("huggingface"):
            return HFGenerator(config)
        return OpenAIGenerator(config)


from sage.middleware.operators.agent.planning.router import PlannerRouter


def _build_planner(config: Any, generator):
    if hasattr(config, "plan"):
        return config
    # planner_conf = config or {}

    # Use PlannerRouter instead of direct LLMPlanner
    return PlannerRouter(generator=generator)


def _build_profile(config: Any) -> BaseProfile:
    if isinstance(config, BaseProfile):
        return config
    if isinstance(config, dict) and "module" in config and "class" in config:
        profile_obj = _maybe_instantiate(config)
        if isinstance(profile_obj, BaseProfile):
            return profile_obj
    return BaseProfile.from_dict(config or {})


def _build_tools(config: Any) -> MCPRegistry:
    if isinstance(config, MCPRegistry):
        return config
    registry = MCPRegistry()
    specs: list[Any]
    if isinstance(config, dict):
        specs = [config]
    elif isinstance(config, list):
        specs = config
    else:
        specs = []

    for spec in specs:
        if isinstance(spec, dict) and "module" in spec and "class" in spec:
            tool = _maybe_instantiate(spec)
            registry.register(tool)
        elif hasattr(spec, "call") and hasattr(spec, "name"):
            registry.register(spec)
        else:
            raise ValueError(f"Unsupported tool spec: {spec}")
    return registry


class AgentRuntimeOperator(MapOperator):
    """Wrap AgentRuntime into an L4 operator for drag-and-drop Studio workflows.

    Supports engine_type switching:
    - sagellm (default): Use SageLLMGenerator with configurable backend
    - openai: Use OpenAIGenerator for OpenAI-compatible APIs
    - hf: Use HFGenerator for HuggingFace models

    Backend types for sagellm:
    - auto (default): Automatically select best available backend
    - mock: Mock backend for testing without GPU
    - cuda: NVIDIA CUDA backend
    - ascend: Huawei Ascend NPU backend

    Example:
        ```python
        # Using sagellm with auto backend (default)
        operator = AgentRuntimeOperator(config={
            "generator": {
                "engine_type": "sagellm",
                "backend_type": "auto",
                "model_path": "Qwen/Qwen2.5-7B-Instruct",
            },
            "profile": {"name": "MyAgent"},
            "tools": [],
        })

        # Using sagellm with mock backend (for testing)
        operator = AgentRuntimeOperator(config={
            "generator": {
                "engine_type": "sagellm",
                "backend_type": "mock",
            },
            "profile": {"name": "TestBot"},
            "tools": [],
        })

        # Using OpenAI
        operator = AgentRuntimeOperator(config={
            "generator": {
                "engine_type": "openai",
                "model_name": "gpt-4o-mini",
                "api_key": "sk-xxx",  # pragma: allowlist secret
            },
            "profile": {"name": "MyAgent"},
            "tools": [],
        })
        ```
    """

    def __init__(
        self, config: dict[str, Any] | None = None, enable_profile: bool = False, **kwargs
    ):
        super().__init__(**kwargs)
        self.enable_profile = enable_profile
        self.config = config or {}

        profile_conf = self.config.get("profile", {})
        generator_conf = self.config.get("generator")
        planner_conf = self.config.get("planner", {})
        tools_conf = self.config.get("tools", [])
        runtime_conf = self.config.get("runtime", {})

        # 获取 engine_type（优先从 generator 配置，其次从顶层配置）
        engine_type = "sagellm"  # 默认值
        if isinstance(generator_conf, dict):
            engine_type = generator_conf.get("engine_type", engine_type)
        elif "engine_type" in self.config:
            engine_type = self.config["engine_type"]

        self.engine_type = engine_type
        self.profile = _build_profile(profile_conf)
        self.generator = _build_generator(generator_conf, engine_type=engine_type)
        self.planner = _build_planner(planner_conf, self.generator)
        self.tools = _build_tools(tools_conf)

        summarizer_conf = runtime_conf.get("summarizer")
        if summarizer_conf == "reuse_generator":
            self.summarizer = self.generator
        elif summarizer_conf:
            self.summarizer = _build_generator(summarizer_conf)
        else:
            self.summarizer = None

        self.max_steps = runtime_conf.get("max_steps", 6)
        self.runtime = AgentRuntime(
            profile=self.profile,
            planner=self.planner,
            tools=self.tools,
            summarizer=self.summarizer,
            max_steps=self.max_steps,
        )

    def execute(self, data: Any) -> Any:
        if isinstance(data, dict):
            return self.runtime.execute(data)
        if isinstance(data, str):
            return self.runtime.execute({"query": data})
        raise TypeError("AgentRuntimeOperator expects str or dict payloads")
