# Action 组件设计文档 —— `MCPRegistry`

> 模块路径：`packages/sage-libs/src/sage/libs/agents/action/mcp_registry.py`

!!! note "定位" `MCPRegistry` 是 **MCP 风格工具** 的**进程内注册与调用**中心。Planner
产出的步骤（`{"type":"tool", ...}`）会交给它执行。

```
- **输入**：符合 MCP 约定的工具对象（至少包含 `name/description/input_schema/call(arguments)`）
- **能力**：注册、列举（供 Planner 使用）、按名调用
- **不包含**：远程传输协议（如 JSON-RPC over stdio/websocket）与权限/沙箱；若需远程工具，需写 **Adapter** 封装成同一接口
```

______________________________________________________________________

## 1. 设计目标

- **MCP 约定**：对齐 `name / description / input_schema / call(arguments)` 四要素
- **低耦合**：不关心工具内部实现（本地函数/HTTP/外部 MCP Server 均可）
- **面向 Planner**：`describe()` 提供简洁的工具清单给 LLM 使用
- **简洁稳定**：最小 API，便于扩展（校验、权限、遥测后续再加）

______________________________________________________________________

## 2. 接口简介

```python title="mcp_registry.py"
class MCPRegistry(MapFunction):
    def __init__(self) -> None: ...

    def register(self, tool_obj: Any) -> None:
        """注册一个工具对象。要求至少有 `name` 与 `call(arguments)`；
        若有 `description` 与 `input_schema` 则会被 `describe()` 暴露给 Planner。"""

    def describe(self) -> Dict[str, Dict[str, Any]]:
        """返回 `{name: {description, input_schema}}`，供 Planner 构造计划时参考。"""

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """按名调用工具：`tools[name].call(arguments)`。未注册则抛 `KeyError`。"""

    def execute(self, data: Any = None) -> Any:
        """支持 None/"describe"/dict 形式的统一入口。"""
```

______________________________________________________________________

## 3. 工具对象的最小约定（MCP 风格）

一个可被注册的工具至少需要：

- `name: str` —— 工具唯一名
- `description: str` —— 用于 Planner 挑选工具（可选，但强烈建议）
- `input_schema: dict` —— **JSON Schema** 的入参契约（可选但建议，Planner 会据此组装参数）
- `call(arguments: Dict[str, Any]) -> Any` —— 执行入口

```python title="示例：本地 Calculator 工具"
class Calculator:
    name = "calculator"
    description = "Evaluate a simple arithmetic expression"
    input_schema = {
        "type": "object",
        "properties": {"expr": {"type": "string"}},
        "required": ["expr"],
    }

    def call(self, arguments: dict) -> dict:
        expr = arguments["expr"]
        out = str(eval(expr, {"__builtins__": {}}))  # 演示用：实际请加沙箱
        return {"output": out}
```

!!! tip "能否直接调用其它 MCP 规范的工具？" **可以**，只要你把它们**适配**成上述接口就能 `register()`。对于**进程内 Python 工具**，直接实现
`call()` 即可；对于**远程 MCP Server**，可写一个 **Adapter**，把远程调用封装进 `call(arguments)`。

______________________________________________________________________

## 4. 进程内注册与调用（本地工具）

```python
from sage.libs.agents.action.mcp_registry import MCPRegistry

# 1) 实例化注册表
reg = MCPRegistry()

# 2) 注册工具
reg.register(Calculator())

# 3) 提供给 Planner 的工具清单（MCP 三要素）
print(reg.describe())
# {
#   "calculator": {
#       "description": "Evaluate a simple arithmetic expression",
#       "input_schema": { ... }
#   }
# }

# 4) 运行时按计划调用
res = reg.call("calculator", {"expr": "21*2+5"})
print(res)  # {"output": "47"}
```

______________________________________________________________________

## 5. 适配“远程 MCP 服务”的通用 Adapter（可选）

> 如果你的工具运行在**独立的 MCP Server**（例如走 JSON-RPC over stdio / WebSocket），你可以写一个 **Adapter**：
>
> - 对外暴露 `name/description/input_schema/call()`；
> - 在 `call()` 内部完成远程 JSON-RPC 请求/响应；
> - 这样就能与本地工具在 `MCPRegistry` 中**同构**。

```python title="示例：远程 MCP 工具适配器（伪实现）"
import json, subprocess, uuid


class RemoteMCPAdapter:
    def __init__(
        self, name: str, description: str, input_schema: dict, server_cmd: list[str]
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self._server_cmd = (
            server_cmd  # 例如 ["node", "server.js"] 或任意可启动的 MCP server
        )

    def _rpc(self, method: str, params: dict) -> dict:
        # 这里仅示意：真实实现应维护长连接（stdio/websocket）并做并发/错误处理
        req = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method,
            "params": params,
        }
        proc = subprocess.run(
            self._server_cmd, input=json.dumps(req).encode(), capture_output=True
        )
        resp = json.loads(proc.stdout.decode() or "{}")
        if "error" in resp:
            raise RuntimeError(resp["error"])  # 同步抛错
        return resp.get("result", {})

    def call(self, arguments: dict) -> dict:
        return self._rpc(method=self.name, params=arguments)


# 用法：
# remote = RemoteMCPAdapter(
#     name="web_search",
#     description="Search the web",
#     input_schema={"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},
#     server_cmd=["python", "web_search_server.py"]
# )
# reg.register(remote)
```

!!! warning "关于传输层" `MCPRegistry` 本身**不实现** MCP 的传输层（如 JSON-RPC over stdio/websocket）；
它只负责**对象注册与调用**。若要连接**外部** MCP Server，请用上面的 **Adapter** 或集成你现有的传输客户端。

______________________________________________________________________

## 6. 与 Planner/Runtime 的协作

```python
# Planner 侧：
# tools_for_planner = reg.describe()
# -> 传给 LLM 以生成 {"type":"tool","name":"...","arguments":{...}}

# Runtime 侧：
# for step in plan_steps:
#     if step["type"] == "tool":
#         result = reg.call(step["name"], step.get("arguments", {}))
#     elif step["type"] == "reply":
#         ...
```

______________________________________________________________________

## 7. 错误处理与返回约定

- `register()`：若工具缺少 `name` 或 `call`，抛 `TypeError`
- `call(name, ...)`：未注册工具抛 `KeyError`
- 工具内部错误：由工具自身抛出异常；上层 Runtime 可捕获并触发 **重规划** 或 **用户澄清**

!!! tip "统一返回结构（建议）" 为了便于记录与展示，建议工具返回 `{"output": Any, "meta": {...}}` 的结构； 不强制，但能帮助 Runtime/Memory
记录 `meta`（耗时、代价、命中缓存等）。

______________________________________________________________________

## 8. 单元测试建议（pytest）

```python
import pytest
from sage.libs.agents.action.mcp_registry import MCPRegistry


class EchoTool:
    name = "echo"
    description = "echo back"
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def call(self, args):
        return {"output": args["text"]}


class BadTool:
    pass


def test_register_and_describe():
    reg = MCPRegistry()
    reg.register(EchoTool())
    desc = reg.describe()
    assert "echo" in desc and "input_schema" in desc["echo"]


def test_call_success():
    reg = MCPRegistry()
    reg.register(EchoTool())
    assert reg.call("echo", {"text": "hi"}) == {"output": "hi"}


def test_call_missing_tool():
    reg = MCPRegistry()
    with pytest.raises(KeyError):
        reg.call("nope", {})


def test_register_invalid():
    reg = MCPRegistry()
    with pytest.raises(TypeError):
        reg.register(BadTool())
```

______________________________________________________________________

## 9. 未来扩展

- **参数校验**：基于 `input_schema` 做严格 JSONSchema 验证与默认值合并
- **权限控制**：工具白名单/黑名单，最小权限（最重要的安全基线）
- **超时与重试**：在注册表层面提供统一超时/重试策略
- **遥测与日志**：统一记录 `call` 的耗时/错误码/代价（便于评估与回放）
- **并发与队列**：对慢工具提供异步接口或队列化
