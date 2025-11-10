# tests/test_mcp_registry.py
import pytest

# 尽量直接导入；如果你的工程路径未就绪，可在运行pytest时用 PYTHONPATH 指向项目根
from sage.libs.agents.action.mcp_registry import MCPRegistry


class EchoTool:
    """一个最小可用的Tool：原样返回arguments，并带有可选的描述与schema。"""

    name = "echo"
    description = "echo back arguments"
    input_schema = {"type": "object", "properties": {"x": {"type": "number"}}}

    def call(self, arguments):
        return {"ok": True, "echo": arguments}


class AddTool:
    """简单计算用的Tool。"""

    name = "add"
    description = "sum a and b"
    input_schema = {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    }

    def call(self, arguments):
        return arguments["a"] + arguments["b"]


def test_register_and_call_success():
    reg = MCPRegistry()
    reg.register(EchoTool())
    reg.register(AddTool())

    # 直接用 call()
    assert reg.call("add", {"a": 1, "b": 2}) == 3
    assert reg.call("echo", {"k": "v"}) == {"ok": True, "echo": {"k": "v"}}


def test_register_requires_name_and_call():
    class NoName:
        def call(self, arguments):
            return None

    class NoCall:
        name = "no_call"

    reg = MCPRegistry()
    with pytest.raises(TypeError):
        reg.register(NoName())
    with pytest.raises(TypeError):
        reg.register(NoCall())


def test_register_overwrite_same_name():
    class T1:
        name = "same"

        def call(self, arguments):
            return 1

    class T2:
        name = "same"

        def call(self, arguments):
            return 2

    reg = MCPRegistry()
    reg.register(T1())
    assert reg.call("same", {}) == 1
    # 再次注册同名应覆盖
    reg.register(T2())
    assert reg.call("same", {}) == 2


def test_describe_contains_description_and_schema():
    reg = MCPRegistry()
    reg.register(EchoTool())
    reg.register(AddTool())

    desc = reg.describe()
    assert set(desc.keys()) == {"echo", "add"}
    assert desc["echo"]["description"] == "echo back arguments"
    assert "type" in desc["echo"]["input_schema"]
    assert desc["add"]["description"] == "sum a and b"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "describe",
        {"op": "describe"},
        {
            "op": "describe",
            "foo": 1,
        },  # 即便有其它键，只要op是describe且没有name，也应走describe分支
    ],
)
def test_execute_describe_variants(payload):
    reg = MCPRegistry()
    reg.register(EchoTool())
    out = reg.execute(payload)
    assert "echo" in out
    assert isinstance(out["echo"]["input_schema"], dict)


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"name": "add", "arguments": {"a": 10, "b": 5}}, 15),
        ({"op": "call", "name": "add", "arguments": {"a": 2, "b": 3}}, 5),
    ],
)
def test_execute_call_variants(payload, expected):
    reg = MCPRegistry()
    reg.register(AddTool())
    assert reg.execute(payload) == expected


def test_execute_call_invalid_name():
    reg = MCPRegistry()
    reg.register(EchoTool())
    with pytest.raises(KeyError):
        reg.execute({"name": "not_exist", "arguments": {}})


def test_execute_invalid_op_raises():
    reg = MCPRegistry()
    reg.register(EchoTool())
    with pytest.raises(ValueError) as ei:
        reg.execute({"op": "delete", "name": "echo", "arguments": {}})
    assert "Unsupported op" in str(ei.value)


@pytest.mark.parametrize(
    "bad_payload, exc_type, msg_part",
    [
        ([], TypeError, "expects None/'describe' or a dict"),
        ({"op": "call", "arguments": {}}, ValueError, "Missing or invalid 'name'"),
        ({"name": ""}, ValueError, "Missing or invalid 'name'"),
        ({"name": "echo", "arguments": 123}, TypeError, "'arguments' must be a dict"),
    ],
)
def test_execute_input_validation_errors(bad_payload, exc_type, msg_part):
    reg = MCPRegistry()
    reg.register(EchoTool())
    with pytest.raises(exc_type) as ei:
        reg.execute(bad_payload)
    assert msg_part in str(ei.value)


def test_call_direct_type_and_key_errors():
    reg = MCPRegistry()
    reg.register(EchoTool())

    # 未注册名称
    with pytest.raises(KeyError):
        reg.call("nope", {})

    # arguments 类型不对时：call 本身把参数直接传给 tool，类型校验在 execute 中做；
    # 这里补充一个最简单的 tool 内部容错（EchoTool可以接受任意类型），因此不抛错：
    assert reg.call("echo", {"value": 123}) == {"ok": True, "echo": {"value": 123}}
