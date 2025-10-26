# Agent Minimal Example – 使用文档

!!! info "目标" 本示例演示一个 **不依赖 Memory** 的最小可运行 Agent：读取查询 → 用 LLM 规划（MCP 计划）→ 动态注册并调用 MCP 工具 → 汇总生成回复。

______________________________________________________________________

## 1. 组件与流程

**核心组件**

- **Profile**：以人格/目标/约束生成 system prompt（本示例直接用 `BaseProfile`）。
- **LLMPlanner**：调用 `OpenAIGenerator` 产出 **MCP 风格 JSON 计划**（`tool` / `reply` 步）。
- **MCPRegistry**：按配置**动态 import** 工具并注册，统一 `name/description/input_schema/call()`。
- **AgentRuntime**：驱动一次完整的 `计划 → 执行 → 汇总` 流程。

**执行流程**

1. 从 `source` 加载多条 `query`（本地 JSONL 或 HuggingFace Dataset）。
1. `BaseProfile` 渲染 system prompt（供 Planner 用）。
1. `LLMPlanner` 生成步骤（优先工具调用，最后 `reply`）。
1. `MCPRegistry` 逐步执行工具调用，收集 `observations`。
1. `AgentRuntime` 若无显式 `reply`，则用 `generator` 依据 `observations` 生成最终回答。

______________________________________________________________________

## 2. 运行脚本

保存为：`examples/agent/run_agent_min.py`

```python title="run_agent_min.py"
from __future__ import annotations
import os, sys, json, importlib
from typing import Any, Dict, Iterable

from sage.common.utils.config.loader import load_config
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.action.mcp_registry import MCPRegistry
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.runtime.agent import AgentRuntime
from sage.libs.rag.generator import OpenAIGenerator


# ====== 读取 source ======
def iter_queries(source_cfg: Dict[str, Any]) -> Iterable[str]:
    stype = source_cfg.get("type", "local")
    if stype == "local":
        path = source_cfg["data_path"]
        field = source_cfg.get("field_query", "query")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                q = obj.get(field, "")
                if isinstance(q, str) and q.strip():
                    yield q
    elif stype == "hf":
        from datasets import load_dataset

        name = source_cfg["hf_dataset_name"]
        config = source_cfg.get("hf_dataset_config")
        split = source_cfg.get("hf_split", "dev")
        field = source_cfg.get("field_query", "query")
        ds = load_dataset(name, config, split=split)
        for row in ds:
            q = row.get(field, "")
            if isinstance(q, str) and q.strip():
                yield q
    else:
        raise ValueError(f"Unsupported source.type: {stype}")


def main():
    # ====== 读取配置 ======
    cfg_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "config_agent_min.yaml"
    )
    if not os.path.exists(cfg_path):
        print(f"❌ Configuration file not found: {cfg_path}")
        sys.exit(1)
    config: Dict[str, Any] = load_config(cfg_path)

    # ====== Profile ======
    profile = (
        BaseProfile.from_dict(config["profile"])
        if isinstance(config.get("profile"), dict)
        else BaseProfile()
    )

    # ====== Generator ======
    gen_cfg = config["generator"]["remote"]  # 可改为 "local"/"remote"
    # 环境变量占位符展开：例如 "${OPENAI_API_KEY}"
    api_key = gen_cfg.get("api_key")
    if isinstance(api_key, str) and api_key.startswith("${"):
        gen_cfg = dict(gen_cfg)
        gen_cfg["api_key"] = os.getenv(api_key.strip("${}"), "")
    generator = OpenAIGenerator(gen_cfg)

    # ====== Planner ======
    planner_cfg = config["planner"]
    planner = LLMPlanner(
        generator=generator,
        max_steps=planner_cfg.get("max_steps", 6),
        enable_repair=planner_cfg.get("enable_repair", True),
        topk_tools=planner_cfg.get("topk_tools", 6),
    )

    # ====== MCP 工具注册：按配置动态 import 并注册 ======
    registry = MCPRegistry()
    for item in config.get("tools", []):
        mod = importlib.import_module(item["module"])  # e.g. "sage.tools.arxiv"
        cls = getattr(mod, item["class"])  # e.g. "ArxivSearchTool"
        kwargs = item.get("init_kwargs", {})
        registry.register(cls(**kwargs) if kwargs else cls())

    # ====== Runtime ======
    runtime_cfg = config["runtime"]
    agent = AgentRuntime(
        profile=profile,
        planner=planner,
        tools=registry,
        summarizer=(
            generator if runtime_cfg.get("summarizer") == "reuse_generator" else None
        ),
        # memory=None,  # 如需接入 MemoryServiceAdapter，再按配置打开
        max_steps=runtime_cfg.get("max_steps", 6),
    )

    # ====== 跑一遍 queries ======
    for q in iter_queries(config["source"]):
        print("\n==========================")
        print(f"🧑‍💻 User: {q}")
        ans = agent.execute({"query": q})
        print(f"🤖 Agent:\n{ans}")


if __name__ == "__main__":
    # 和 RAG 示例一致的“测试模式”友好输出
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        try:
            main()
            print("\n✅ Test passed: Agent pipeline structure validated")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)
    else:
        main()
```

______________________________________________________________________

## 3. 配置文件

保存为：`examples/config/config_agent_min.yaml`

```yaml title="config_agent_min.yaml"
pipeline:
  name: "sage-agent-min"
  description: "最小 Agent（无 memory）"
  version: "0.1.0"

source:
  type: "local"                # 或 "hf"
  data_path: "examples/data/agent_queries.jsonl"
  field_query: "query"
  # hf_dataset_name: "RUC-NLPIR/FlashRAG_datasets"
  # hf_dataset_config: "asqa"
  # hf_split: "dev"

profile:
  name: "ResearchOrchestrator"
  role: "planner"
  language: "zh"
  goals:
    - "以最少步骤完成用户意图"
    - "优先使用 MCP 工具"
  constraints:
    - "工具参数必须符合 JSONSchema"
    - "计划步数不超过 6"
  persona:
    style: "concise"

planner:
  max_steps: 6
  enable_repair: true
  topk_tools: 6

# 统一用 OpenAIGenerator，既可连 vLLM/OpenAI 兼容端，也可连公有云
# 这里示例用 remote

generator:
  remote:
    method: "openai"
    model_name: "gpt-4o-mini"
    base_url: "http://localhost:8000/v1"
    api_key: "${OPENAI_API_KEY}"
    temperature: 0.4
    max_tokens: 800

# 需要调用哪些 MCP 工具？按照 "module + class" 动态加载注册
# 你可以把已有工具改成 MCP 规范（name/description/input_schema/call）后填到这里

tools:
  - module: "sage.tools.arxiv"         # 示例：你的工具模块
    class: "ArxivSearchTool"           # 示例：类名
    init_kwargs: { max_results: 2 }     # 可选：构造参数
  - module: "sage.tools.calculator"
    class: "CalculatorTool"

runtime:
  max_steps: 6
  summarizer: "reuse_generator"   # 用上面的 generator 汇总（若 Planner 未给 reply）
```

______________________________________________________________________

## 4. 输入数据

保存为：`examples/data/agent_queries.jsonl`

```json title="agent_queries.jsonl"
{"query": "在 arXiv 搜 2 篇 LLM agents survey，并把 21*2+5 算出来，最后中文总结"}
```

______________________________________________________________________

## 5. 运行

```bash
# 环境变量（示例）
export OPENAI_API_KEY=sk-xxxxx

# 运行
python examples/agent/run_agent_min.py
```

运行日志示例：

```
==========================
🧑‍💻 User: 在 arXiv 搜 2 篇 LLM agents survey，并把 21*2+5 算出来，最后中文总结
🤖 Agent:
{ "final": "...中文总结...", "meta": {"observations": [...]} }
```

______________________________________________________________________

## 6. 工具（MCP）对接约定

**工具最小约定**：

- 属性：`name: str`, `description: str`, `input_schema: dict`
- 方法：`call(arguments: Dict[str, Any]) -> Any`

**注册方式**：

- 在 YAML `tools` 中声明模块与类；
- 运行时通过 `importlib.import_module()` 动态加载并 `registry.register(obj)`。

**Planner 约束**：

- 只允许使用 `describe()` 暴露的工具；
- `arguments` 严格匹配 `input_schema.required`；
- 计划为 **JSON 数组**，步骤为 `{"type":"tool",...}` 或 `{"type":"reply",...}`。

______________________________________________________________________

## 7. 常见问题

??? tip "Planner 输出不是 JSON" 已启用 `enable_repair`：会自动提示模型**返回合法 JSON** 并重试一次；若仍失败，fallback 为直接文本
`reply`。

??? warning "工具参数校验失败" 检查工具的 `input_schema.required` 与 Planner 生成的 `arguments` 是否一致；必要时在
`LLMPlanner` 提示中加入示例。

??? info "没有显式 reply" `runtime.summarizer = reuse_generator` 时，会把 `observations` 打包给 LLM 生成总结。

______________________________________________________________________

## 8. 如何扩展

- **接入 Memory**：

  - 在 `AgentRuntime` 初始化里传入 `MemoryServiceAdapter`；
  - 在 Planner Prompt 拼接 `memory_context`；
  - 在每轮结束后 `store_memory()`。

- **远程 MCP Server**：

  - 在 `MCPRegistry` 增加远端适配器（例如 `mount_remote(registry, base_url, prefix)`）；
  - `LLMPlanner` 工具清单中加入远端工具。

- **自定义汇总器**：

  - 若不想复用 `generator`，可单独配置一个专用 summarizer，并替换 `runtime.summarizer`。

______________________________________________________________________

## 9. 目录建议

```
examples/
  agent/
    run_agent_min.py
  config/
    config_agent_min.yaml
  data/
    agent_queries.jsonl
sage/
  libs/
    agents/
      profile/profile.py              # BaseProfile & ProfileNode（如需）
      planning/llm_planner.py         # LLMPlanner（计划 JSON）
      action/mcp_registry.py          # MCP 工具注册表
      runtime/agent.py                # AgentRuntime（执行主循环）
  tools/
    arxiv.py                          # ArxivSearchTool（MCP 规范）
    calculator.py                     # CalculatorTool（MCP 规范）
```

______________________________________________________________________

## 10. 小结

- 这是一个**最小 Agent 示范**，仅依赖 Profile / Planner / MCP / Runtime；
- 支持本地或远程 LLM（OpenAI 兼容接口），工具按需动态注册；
- 生产化建议逐步引入 Memory、评测、监控与安全策略。
