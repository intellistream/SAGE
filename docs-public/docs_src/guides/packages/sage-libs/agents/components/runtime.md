# Runtime 组件设计文档

!!! note "定位"
`AgentRuntime`（`packages/sage-libs/src/sage/libs/agents/runtime/agent.py`）提供了一个**最小可用的执行循环**：接受用户问题
→ 调用 `LLMPlanner` 生成 MCP 计划 → 逐步调用 `MCPRegistry` 中的工具 → 返回回复或兜底总结。

______________________________________________________________________

## 1. 功能边界

- **核心流程**：`step(user_query: str) -> str`
  1. 基于 `BaseProfile.render_system_prompt()` 和用户输入调用 `LLMPlanner.plan(...)`
  1. 按照计划逐步执行 `tool` 步骤，记录成功/失败 `observations`
  1. 若计划包含 `reply` 步骤则优先返回该文本；否则使用可选 `summarizer` 或内置模板整理观测
- **输入形态**：`execute(...)` 既可以直接传入字符串，也可以传入字典以临时覆写 `max_steps`、`profile_overrides`
- **当前缺省**：源码中未启用 Memory、Reflection、事件总线等扩展；如需记忆能力，可参考 [Memory 组件文档](./memory.md) 在调用端接入
  `MemoryManager` 或自定义服务

______________________________________________________________________

## 2. 核心实现摘录

```python title="runtime/agent.py"
class AgentRuntime(MapFunction):
    def __init__(
        self,
        profile: BaseProfile,
        planner: LLMPlanner,
        tools: MCPRegistry,
        summarizer=None,
        max_steps: int = 6,
    ) -> None:
        self.profile = profile
        self.planner = planner
        self.tools = tools
        self.summarizer = summarizer
        self.max_steps = max_steps

    def step(self, user_query: str) -> str:
        plan = self.planner.plan(
            profile_system_prompt=self.profile.render_system_prompt(),
            user_query=user_query,
            tools=self.tools.describe(),
        )

        observations: List[Dict[str, Any]] = []
        reply_text: Optional[str] = None

        for i, step in enumerate(plan[: self.max_steps]):
            if step.get("type") == "reply":
                reply_text = step.get("text", "").strip()
                break
            if step.get("type") == "tool":
                name = step.get("name")
                arguments = step.get("arguments", {}) or {}
                schema = self.tools.describe().get(name, {}).get("input_schema", {})
                miss = _missing_required(arguments, schema)
                if miss:
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": False,
                            "error": f"Missing required fields: {miss}",
                            "arguments": arguments,
                        }
                    )
                    continue
                t0 = time.time()
                try:
                    out = self.tools.call(name, arguments)
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": True,
                            "latency_ms": int((time.time() - t0) * 1000),
                            "result": out,
                        }
                    )
                except Exception as e:
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": False,
                            "latency_ms": int((time.time() - t0) * 1000),
                            "error": str(e),
                        }
                    )

        if reply_text:
            return reply_text
        if not observations:
            return "（没有可执行的步骤或工具返回空结果）"
        if self.summarizer:
            profile_hint = self.profile.render_system_prompt()
            messages = [
                {"role": "system", "content": "你是一个严谨的助理。只输出中文总结。"},
                {
                    "role": "user",
                    "content": f"[Profile]\n{profile_hint}\n\n[Observations]\n{observations}",
                },
            ]
            _, summary = self.summarizer.execute([None, messages])
            return summary.strip()
        return "\n".join(
            f"#{obs['step'] + 1} 工具 {obs['tool']} {'成功' if obs['ok'] else '失败'}：{obs.get('result') or obs.get('error')}"
            for obs in observations
        )

    def execute(self, data: Any) -> str:
        if isinstance(data, str):
            return self.step(data)
        if isinstance(data, dict):
            ...  # 支持一次性覆写 max_steps / profile_overrides
        raise TypeError("AgentRuntime.execute 仅接受 str 或 dict 两种输入。")
```

!!! info "容错要点" - `_missing_required(...)` 定义在同文件顶部，用于根据工具 `input_schema.required` 做最小必填校验 -
所有工具调用（成功/失败）都会被记录，便于调试或在 summarizer 中使用 - 默认兜底输出会逐行列出每一步执行结果

______________________________________________________________________

## 3. 快速上手

```python
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.action.mcp_registry import MCPRegistry

profile = BaseProfile(name="ResearchAgent", role="planner", language="zh")
planner = LLMPlanner(generator=openai_generator)

registry = MCPRegistry()
registry.register(Calculator())
registry.register(ArxivSearcher())

agent = AgentRuntime(profile, planner, registry, max_steps=4)
print(agent.step("查两篇 LLM agent survey，再算 21*2+5"))

agent.execute(
    {
        "user_query": "输出一句祝福",
        "max_steps": 2,
        "profile_overrides": {"tone": "warm"},
    }
)
```

______________________________________________________________________

## 4. 可扩展点

- **记忆集成**：源码中的 Memory 参数目前注释掉。需要时可以通过继承或装饰器在工具执行后写入记忆。
- **观测事件**：可以在 `observations` 中附加耗时、token 等指标，或推送到外部监控。
- **Re-plan**：若要实现多轮 `observe → replan`，建议在外层根据 `observations` 再次调用 `planner.plan(...)`。

______________________________________________________________________

## 5. 现状提示

- 文件位置：`packages/sage-libs/src/sage/libs/agents/runtime/agent.py`
- 依赖仅限 `BaseProfile`、`LLMPlanner`、`MCPRegistry` 与可选 `summarizer`
- `BaseProfile` 默认语言为 `"zh"`、语气为 `"concise"`，因此默认输出偏中文简洁风格
- `execute(...)` 会在调用结束后恢复原始 `max_steps` 与 Profile 配置
