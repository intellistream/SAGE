# Profile 组件设计文档

!!! note "定位" `BaseProfile`（`packages/sage-libs/src/sage/libs/agentic/agents/profile/profile.py`）定义了
Agent 的“身份卡片”，并可直接映射为 `MapFunction`。它负责描述角色、目标、任务、背景以及输出偏好，可随时渲染为系统提示词。

______________________________________________________________________

## 1. 数据模型

```python title="profile/profile.py"
@dataclass
class BaseProfile(MapFunction):
    name: str = "BaseAgent"
    role: str = "general assistant"
    goals: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    backstory: str = ""
    language: str = "zh"
    tone: str = "concise"

    def render_system_prompt(self) -> str:
        goals_txt = "\n".join(f"- {g}" for g in self.goals) or "- （未指定）"
        tasks_txt = "\n".join(f"- {t}" for t in self.tasks) or "- （未指定）"
        return (
            f"You are **{self.name}**, acting as **{self.role}**.\n"
            f"Language: {self.language}\n"
            f"Tone: {self.tone}\n\n"
            f"Backstory:\n{self.backstory or '(none)'}\n\n"
            f"Goals:\n{goals_txt}\n\n"
            f"Typical Tasks:\n{tasks_txt}\n\n"
            "Guidance:\n"
            "- Stay aligned with the role and goals.\n"
            "- Prefer structured, verifiable outputs.\n"
        )
```

!!! tip "MapFunction 支持" `BaseProfile` 继承自 `MapFunction`，因此可以被流水线或 Agent Runtime
直接调用。`execute(overrides: dict | None)` 会先合并临时覆写，再返回渲染后的系统提示词。

______________________________________________________________________

## 2. 字段说明

| 字段        | 类型      | 默认值                | 说明                                       |
| ----------- | --------- | --------------------- | ------------------------------------------ |
| `name`      | str       | `"BaseAgent"`         | Agent 的名称                               |
| `role`      | str       | `"general assistant"` | 角色定位（planner、analyst 等）            |
| `goals`     | List[str] | `[]`                  | 长期目标列表                               |
| `tasks`     | List[str] | `[]`                  | 常见任务模板                               |
| `backstory` | str       | `""`                  | 背景故事（可空）                           |
| `language`  | str       | `"zh"`                | 默认输出语言                               |
| `tone`      | str       | `"concise"`           | 输出语气（如 concise、detailed、socratic） |

______________________________________________________________________

## 3. 常用方法

- `render_system_prompt()`：生成富文本 System Prompt 字符串
- `to_dict()` / `from_dict()`：便于持久化或序列化配置
- `merged(**overrides)`：复制当前 Profile 并应用字段覆写，常用于一次性调整
- `execute(data: dict | None)`：MapFunction 接口，若提供参数会在渲染前进行一次性覆写

```python
profile = BaseProfile(
    name="ResearchAgent",
    role="planner",
    goals=["分析最新论文"],
    tasks=["筛选相关研究", "输出结构化总结"],
    tone="detailed",
)
print(profile.render_system_prompt())

# 一次性覆写语气
print(profile.execute({"tone": "warm"}))
```

______________________________________________________________________

## 4. 与其它组件的关系

- `AgentRuntime` 使用 `profile.render_system_prompt()` 为 Planner 提供系统提示词
- `LLMPlanner` 接收渲染后的 Prompt 作为上下文，约束计划输出
- 在多 Agent 场景中，可为每个 Agent 定义不同的 Profile，并按需使用 `merged()` 生成派生 persona

______________________________________________________________________

## 5. 现状提示

- 默认语言为中文（`language="zh"`），若需英文回复需显式覆写
- `tone` 字段仅在提示词中说明语气，实际效果由模型决定
- `execute(...)` 返回纯文本，不会修改原始实例的属性
