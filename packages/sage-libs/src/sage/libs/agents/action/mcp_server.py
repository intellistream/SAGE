# mcp_server.py
# 启动：
#   uvicorn mcp_server:app --host 0.0.0.0 --port 9000
# 依赖：
#   pip install fastapi uvicorn pydantic requests

from __future__ import annotations

import importlib
import time
import uuid
from typing import Any

import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="SAGE MCP Server", version="0.1.0")

# ---------------------------
# In-memory registries
# ---------------------------
TOOLS: dict[
    str, Any
] = {}  # 本地&代理 工具对象：必须有 name/description/input_schema/call(arguments)
REMOTE_ADAPTERS: dict[str, RemoteMCPAdapter] = {}  # 远程 MCP 适配器
MOUNT_MAP: dict[str, dict[str, str]] = {}  # adapter_id -> {local_name: remote_name}


# ---------------------------
# Utilities
# ---------------------------
def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_tool_interface(tool_obj: Any) -> None:
    if not hasattr(tool_obj, "name") or not hasattr(tool_obj, "call"):
        raise TypeError("Tool must have `name` (str) and `call(arguments: dict)`")
    # description / input_schema 建议提供
    if not hasattr(tool_obj, "description"):
        tool_obj.description = ""
    if not hasattr(tool_obj, "input_schema"):
        tool_obj.input_schema = {"type": "object", "properties": {}, "required": []}


def register_tool(tool_obj: Any) -> None:
    _ensure_tool_interface(tool_obj)
    TOOLS[tool_obj.name] = tool_obj


def describe_tools() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "description": getattr(t, "description", ""),
            "input_schema": getattr(t, "input_schema", {}),
        }
        for name, t in TOOLS.items()
    }


def validate_required_args(tool_name: str, arguments: dict[str, Any]) -> str | None:
    schema = getattr(TOOLS[tool_name], "input_schema", {}) or {}
    req = schema.get("required") or []
    missing = [k for k in req if k not in (arguments or {})]
    if missing:
        return f"Missing required arguments: {missing}"
    return None


# ---------------------------
# Remote MCP Adapter
# ---------------------------
class RemoteMCPAdapter:
    """
    把远程 MCP Server 聚合为可调用接口：
      - list_tools() -> {name: {description, input_schema}}
      - call_tool(name, arguments) -> result
    远端约定：HTTP POST {base_url}/jsonrpc
      请求：{"jsonrpc":"2.0","id":"...","method":"list_tools","params":{}}
           {"jsonrpc":"2.0","id":"...","method":"call_tool","params":{"name": "...", "arguments": {...}}}
    """

    def __init__(self, adapter_id: str, base_url: str, timeout: float = 10.0):
        self.id = adapter_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        req = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method,
            "params": params,
        }
        resp = requests.post(f"{self.base_url}/jsonrpc", json=req, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data and data["error"]:
            raise RuntimeError(str(data["error"]))
        return data.get("result", {})

    def list_tools(self) -> dict[str, dict[str, Any]]:
        return self._rpc("list_tools", {})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._rpc("call_tool", {"name": name, "arguments": arguments})


# ---------------------------
# JSON-RPC models
# ---------------------------
class JSONRPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: dict[str, Any] = {}


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Any = None
    error: Any = None


# ---------------------------
# Health
# ---------------------------
@app.get("/health")
def health():
    return {"ok": True, "tools": len(TOOLS), "remotes": len(REMOTE_ADAPTERS)}


# ---------------------------
# JSON-RPC endpoint
# ---------------------------
@app.post("/jsonrpc")
def jsonrpc(req: JSONRPCRequest):
    t0 = _now_ms()
    try:
        # 1) 列出所有工具（本地 + 已挂载的远程代理）
        if req.method == "list_tools":
            return JSONRPCResponse(id=req.id, result=describe_tools())

        # 2) 调用工具
        elif req.method == "call_tool":
            name = req.params.get("name")
            arguments = req.params.get("arguments", {}) or {}
            if name not in TOOLS:
                return JSONRPCResponse(id=req.id, error=f"Tool not found: {name}")
            # 轻校验
            msg = validate_required_args(name, arguments)
            if msg:
                return JSONRPCResponse(id=req.id, error=msg)
            try:
                out = TOOLS[name].call(arguments)
                return JSONRPCResponse(id=req.id, result=out)
            except Exception as e:
                return JSONRPCResponse(id=req.id, error=str(e))

        # 3) 从 python 路径注册本地工具（别人写的 Python 工具类）
        #    params: {"module":"pkg.mod","class":"ToolClass","init_kwargs":{...}}
        elif req.method == "register_tool_from_path":
            module = req.params["module"]
            clsname = req.params["class"]
            init_kwargs = req.params.get("init_kwargs", {})
            mod = importlib.import_module(module)
            cls = getattr(mod, clsname)
            tool_obj = cls(**init_kwargs) if init_kwargs else cls()
            register_tool(tool_obj)
            return JSONRPCResponse(id=req.id, result={"ok": True, "name": tool_obj.name})

        # 4) 挂载远程 MCP：把对方的每个工具映射为本地“代理工具”
        #    params: {"adapter_id":"t1","base_url":"http://host:9001","prefix":"up_"}
        elif req.method == "mount_remote_mcp":
            adapter_id = req.params["adapter_id"]
            base_url = req.params["base_url"]
            prefix = req.params.get("prefix", "")
            adapter = RemoteMCPAdapter(adapter_id=adapter_id, base_url=base_url)
            REMOTE_ADAPTERS[adapter_id] = adapter

            remote_desc = adapter.list_tools()  # {name: {description, input_schema}}
            MOUNT_MAP[adapter_id] = {}

            for rname, meta in remote_desc.items():
                local_name = f"{prefix}{rname}"
                # 为每个远程工具构造一个本地代理对象
                tool = _make_proxy_tool(adapter, adapter_id, local_name, rname, meta)
                register_tool(tool)
                MOUNT_MAP[adapter_id][local_name] = rname

            return JSONRPCResponse(
                id=req.id,
                result={"ok": True, "mounted": list(MOUNT_MAP[adapter_id].keys())},
            )

        # 5) 刷新某个远程 MCP（重新获取远端工具清单，更新代理）
        #    params: {"adapter_id":"t1","prefix":"up_"}
        elif req.method == "refresh_remote_mcp":
            adapter_id = req.params["adapter_id"]
            prefix = req.params.get("prefix", "")
            if adapter_id not in REMOTE_ADAPTERS:
                return JSONRPCResponse(id=req.id, error=f"Remote adapter not found: {adapter_id}")
            adapter = REMOTE_ADAPTERS[adapter_id]

            # 先卸载旧代理
            for local_name in list(MOUNT_MAP.get(adapter_id, {}).keys()):
                TOOLS.pop(local_name, None)
            MOUNT_MAP[adapter_id] = {}

            # 重新挂载
            remote_desc = adapter.list_tools()
            for rname, meta in remote_desc.items():
                local_name = f"{prefix}{rname}"
                tool = _make_proxy_tool(adapter, adapter_id, local_name, rname, meta)
                register_tool(tool)
                MOUNT_MAP[adapter_id][local_name] = rname

            return JSONRPCResponse(
                id=req.id,
                result={"ok": True, "mounted": list(MOUNT_MAP[adapter_id].keys())},
            )

        # 6) 卸载远程 MCP
        #    params: {"adapter_id":"t1"}
        elif req.method == "unmount_remote_mcp":
            adapter_id = req.params["adapter_id"]
            for local_name in list(MOUNT_MAP.get(adapter_id, {}).keys()):
                TOOLS.pop(local_name, None)
            MOUNT_MAP.pop(adapter_id, None)
            REMOTE_ADAPTERS.pop(adapter_id, None)
            return JSONRPCResponse(id=req.id, result={"ok": True})

        else:
            return JSONRPCResponse(id=req.id, error=f"Unknown method: {req.method}")

    except Exception as e:
        return JSONRPCResponse(id=req.id, error=str(e))
    finally:
        # 你可以在这里加简单的访问日志或指标
        _ = _now_ms() - t0


def _make_proxy_tool(
    adapter: RemoteMCPAdapter,
    adapter_id: str,
    local_name: str,
    remote_name: str,
    meta: dict[str, Any],
):
    """
    生成一个“本地代理工具”对象，它满足 name/description/input_schema/call(arguments) 接口，
    实际执行会转发到远程 MCP 的 remote_name。
    """

    class _ProxyTool:
        name = local_name
        description = meta.get("description", f"proxy for {remote_name} via {adapter_id}")
        input_schema = meta.get(
            "input_schema", {"type": "object", "properties": {}, "required": []}
        )

        def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
            result = adapter.call_tool(remote_name, arguments)
            # 统一返回格式建议：{"output": <result>, "meta": {...}}
            return {
                "output": result,
                "meta": {
                    "proxy": True,
                    "adapter_id": adapter_id,
                    "remote": remote_name,
                },
            }

    return _ProxyTool()
