# tests/lib/agents/test_mcp_server.py
import uuid

import pytest

# 兼容两种导入方式：优先包内路径，找不到则尝试同目录模块
try:
    from sage.libs.agentic.agents.action import mcp_server as mcp
except ImportError:  # pragma: no cover
    import mcp_server as mcp  # type: ignore

from fastapi.testclient import TestClient


# ---------------------------
# 测试用假工具
# ---------------------------
class EchoTool:
    name = "echo"
    description = "echo tool"
    input_schema = {
        "type": "object",
        "properties": {"msg": {"type": "string"}},
        "required": ["msg"],
    }

    def call(self, arguments):
        return {"ok": True, "data": arguments}


class CrashTool:
    name = "crash"
    description = "always raises"
    input_schema = {"type": "object", "properties": {}}

    def call(self, arguments):
        raise RuntimeError("boom")


# 动态导入用：被 register_tool_from_path 使用
class DummyPathTool:
    name = "dummy_path_tool"

    def call(self, arguments):
        return {"hi": "from_path", "args": arguments}


# ---------------------------
# Fixtures
# ---------------------------
@pytest.fixture(autouse=True)
def clean_server_state():
    """每个测试前后清理全局状态，避免交叉污染。"""
    mcp.TOOLS.clear()
    mcp.REMOTE_ADAPTERS.clear()
    mcp.MOUNT_MAP.clear()
    yield
    mcp.TOOLS.clear()
    mcp.REMOTE_ADAPTERS.clear()
    mcp.MOUNT_MAP.clear()


@pytest.fixture()
def client():
    return TestClient(mcp.app)


# ---------------------------
# /health
# ---------------------------
def test_health_initial(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["tools"] == 0
    assert data["remotes"] == 0


# ---------------------------
# 工具注册 + 描述 + 调用
# ---------------------------
def test_register_and_describe_and_call_success(client):
    mcp.register_tool(EchoTool())
    # list_tools
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "list_tools",
        "params": {},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"]["echo"]["description"] == "echo tool"

    # call_tool 成功
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "call_tool",
        "params": {"name": "echo", "arguments": {"msg": "hi"}},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"] == {"ok": True, "data": {"msg": "hi"}}
    assert r["error"] is None


def test_call_tool_missing_required_args_returns_error(client):
    mcp.register_tool(EchoTool())
    # 少了 required 的 msg
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "call_tool",
        "params": {"name": "echo", "arguments": {}},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"] is None
    assert "Missing required arguments" in r["error"]


def test_call_tool_not_found(client):
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "call_tool",
        "params": {"name": "nope", "arguments": {}},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"] is None
    assert r["error"].startswith("Tool not found")


def test_call_tool_internal_exception_wrapped(client):
    mcp.register_tool(CrashTool())
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "call_tool",
        "params": {"name": "crash", "arguments": {}},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"] is None
    assert r["error"] == "boom"


def test_register_tool_sets_defaults_for_missing_fields(client):
    class MinimalTool:
        name = "mini"

        def call(self, arguments):
            return 1

    mcp.register_tool(MinimalTool())
    desc = mcp.describe_tools()
    assert "mini" in desc
    assert isinstance(desc["mini"]["description"], str)
    assert isinstance(desc["mini"]["input_schema"], dict)


# ---------------------------
# register_tool_from_path
# ---------------------------
def test_register_tool_from_path(client):
    # 目标：通过 importlib 导入“当前测试模块”中的 DummyPathTool
    module_name = __name__  # tests.lib.agents.test_mcp_server
    req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "register_tool_from_path",
        "params": {"module": module_name, "class": "DummyPathTool", "init_kwargs": {}},
    }
    r = client.post("/jsonrpc", json=req).json()
    assert r["result"]["ok"] is True
    assert r["result"]["name"] == "dummy_path_tool"

    # 调用一下
    call_req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "call_tool",
        "params": {"name": "dummy_path_tool", "arguments": {"x": 1}},
    }
    cr = client.post("/jsonrpc", json=call_req).json()
    assert cr["result"]["hi"] == "from_path"
    assert cr["result"]["args"] == {"x": 1}


# ---------------------------
# 远程 MCP 挂载/刷新/卸载（mock requests.post）
# ---------------------------
class _MockResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError("HTTP error")

    def json(self):
        return self._payload


def test_mount_remote_mcp_and_proxy_call(monkeypatch, client):
    """模拟远端有工具 sum(a,b)，挂载为本地代理并调用。"""

    def fake_post(url, json, timeout):
        method = json["method"]
        if method == "list_tools":
            return _MockResp(
                {
                    "result": {
                        "sum": {
                            "description": "add two numbers",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "a": {"type": "number"},
                                    "b": {"type": "number"},
                                },
                                "required": ["a", "b"],
                            },
                        }
                    }
                }
            )
        elif method == "call_tool":
            params = json["params"]
            return _MockResp({"result": params["arguments"]["a"] + params["arguments"]["b"]})
        else:
            return _MockResp(
                {"error": {"code": -32601, "message": "method not found"}},
                status_code=400,
            )

    monkeypatch.setattr(mcp.requests, "post", fake_post)

    # 挂载
    mount_req = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "mount_remote_mcp",
        "params": {
            "adapter_id": "r1",
            "base_url": "http://remote:9001",
            "prefix": "up_",
        },
    }
    r = client.post("/jsonrpc", json=mount_req).json()
    assert r["result"]["ok"] is True
    assert r["result"]["mounted"] == ["up_sum"]

    # list_tools 中应包含 up_sum
    lst = client.post(
        "/jsonrpc",
        json={"jsonrpc": "2.0", "id": "1", "method": "list_tools", "params": {}},
    ).json()
    assert "up_sum" in lst["result"]

    # 通过代理调用
    call_req = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "call_tool",
        "params": {"name": "up_sum", "arguments": {"a": 4, "b": 3}},
    }
    cr = client.post("/jsonrpc", json=call_req).json()
    assert cr["error"] is None
    assert cr["result"]["output"] == 7
    assert cr["result"]["meta"]["proxy"] is True
    assert cr["result"]["meta"]["remote"] == "sum"


def test_refresh_remote_mcp(monkeypatch, client):
    """首次远端提供 t1；刷新后变为 t2，验证本地代理更新。"""
    state = {"phase": 0}

    def fake_post(url, json, timeout):
        method = json["method"]
        if method == "list_tools":
            if state["phase"] == 0:
                return _MockResp({"result": {"t1": {"description": "tool1", "input_schema": {}}}})
            else:
                return _MockResp({"result": {"t2": {"description": "tool2", "input_schema": {}}}})
        elif method == "call_tool":
            return _MockResp({"result": "ok"})
        return _MockResp({"error": {"code": -32601}}, status_code=400)

    monkeypatch.setattr(mcp.requests, "post", fake_post)

    # mount（获得 t1）
    mreq = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "mount_remote_mcp",
        "params": {
            "adapter_id": "r1",
            "base_url": "http://remote:9001",
            "prefix": "R_",
        },
    }
    mr = client.post("/jsonrpc", json=mreq).json()
    assert mr["result"]["mounted"] == ["R_t1"]
    assert "R_t1" in mcp.TOOLS

    # refresh → 变为 t2
    state["phase"] = 1
    rreq = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "refresh_remote_mcp",
        "params": {"adapter_id": "r1", "prefix": "R_"},
    }
    rr = client.post("/jsonrpc", json=rreq).json()
    assert rr["result"]["mounted"] == ["R_t2"]
    assert "R_t1" not in mcp.TOOLS
    assert "R_t2" in mcp.TOOLS


def test_unmount_remote_mcp(monkeypatch, client):
    def fake_post(url, json, timeout):
        if json["method"] == "list_tools":
            return _MockResp({"result": {"a": {"description": "", "input_schema": {}}}})
        return _MockResp({"result": "ok"})

    monkeypatch.setattr(mcp.requests, "post", fake_post)

    # mount
    mreq = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "mount_remote_mcp",
        "params": {"adapter_id": "rX", "base_url": "http://remote:9001", "prefix": ""},
    }
    client.post("/jsonrpc", json=mreq)
    assert "a" in mcp.TOOLS
    assert "rX" in mcp.REMOTE_ADAPTERS

    # unmount
    ureq = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "unmount_remote_mcp",
        "params": {"adapter_id": "rX"},
    }
    ur = client.post("/jsonrpc", json=ureq).json()
    assert ur["result"]["ok"] is True
    assert "a" not in mcp.TOOLS
    assert "rX" not in mcp.REMOTE_ADAPTERS
    assert "rX" not in mcp.MOUNT_MAP
