from __future__ import annotations

from importlib import import_module
from typing import Any

from sage.common.core.functions import MapFunction as MapOperator
from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.profile.profile import BaseProfile
from sage.middleware.operators.agent.runtime import AgentRuntime
from sage.middleware.operators.rag.generator import HFGenerator, OpenAIGenerator


def _maybe_instantiate(spec: dict[str, Any]):
    module_path = spec["module"]
    class_name = spec["class"]
    kwargs = spec.get("init_kwargs", {})
    module = import_module(module_path)
    ctor = getattr(module, class_name)
    return ctor(**kwargs) if kwargs else ctor()


def _build_generator(config: Any):
    if not config:
        raise ValueError("generator config/object is required for AgentRuntimeOperator")
    if hasattr(config, "execute") or hasattr(config, "generate"):
        return config
    if isinstance(config, dict) and "module" in config and "class" in config:
        return _maybe_instantiate(config)
    method = (config.get("method") or config.get("type") or "openai").lower()
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
    """Wrap AgentRuntime into an L4 operator for drag-and-drop Studio workflows."""

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

        self.profile = _build_profile(profile_conf)
        self.generator = _build_generator(generator_conf)
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
