import itertools
from pathlib import Path
from typing import Any

import pytest
from sage.tools.cli.commands import chat as chat_module
from sage.tools.cli.commands import pipeline as pipeline_builder


def test_looks_like_pipeline_request_detection():
    assert chat_module._looks_like_pipeline_request("请帮我构建一个大模型应用")
    assert chat_module._looks_like_pipeline_request(
        "build an LLM pipeline for retrieval"
    )
    assert not chat_module._looks_like_pipeline_request("SAGE 是什么？")


@pytest.fixture()
def fake_generator(monkeypatch):
    plan = {
        "pipeline": {
            "name": "demo",
            "description": "test",
            "version": "1.0.0",
            "type": "local",
        },
        "source": {
            "class": "sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleQuestionSource",
            "params": {"questions": ["hi"]},
        },
        "stages": [
            {
                "id": "generator",
                "kind": "map",
                "class": "sage.benchmark.benchmark_rag.implementations.rag_simple.SimplePromptor",
                "params": {},
            }
        ],
        "sink": {
            "class": "sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleTerminalSink",
            "params": {},
        },
        "services": [],
        "monitors": [],
    }

    instances = []

    class DummyGenerator:
        def __init__(self, config):
            self.config = config
            self.calls: list[
                tuple[dict[str, Any], dict[str, Any] | None, str | None]
            ] = []

        def generate(
            self,
            requirements: dict[str, Any],
            previous_plan: dict[str, Any] | None = None,
            feedback: str | None = None,
        ) -> dict[str, Any]:
            self.calls.append((requirements, previous_plan, feedback))
            return plan

    def factory(config):
        instance = DummyGenerator(config)
        instances.append(instance)
        return instance

    monkeypatch.setattr(pipeline_builder, "PipelinePlanGenerator", factory)
    monkeypatch.setattr(pipeline_builder, "render_pipeline_plan", lambda plan: None)
    monkeypatch.setattr(pipeline_builder, "preview_pipeline_plan", lambda plan: None)

    executed: dict[str, Any] = {}

    def fake_execute(
        plan_obj, autostop=True, host=None, port=None, console_override=None
    ):
        executed.update(
            {
                "plan": plan_obj,
                "autostop": autostop,
                "host": host,
                "port": port,
            }
        )
        return "job-1234"

    saves = []

    def fake_save(plan_obj, output, overwrite):
        target = output or Path("demo.yaml")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("pipeline: demo\n", encoding="utf-8")
        saves.append((plan_obj, target, overwrite))
        return target

    monkeypatch.setattr(pipeline_builder, "execute_pipeline_plan", fake_execute)
    monkeypatch.setattr(pipeline_builder, "save_pipeline_plan", fake_save)

    monkeypatch.setattr(
        chat_module, "load_domain_contexts", lambda limit=4: ("默认上下文",)
    )
    monkeypatch.setattr(chat_module, "get_default_knowledge_base", lambda: None)

    return {
        "plan": plan,
        "instances": instances,
        "saves": saves,
        "executed": executed,
    }


def test_pipeline_chat_coordinator_handles_flow(monkeypatch, tmp_path, fake_generator):
    prompts = itertools.chain(
        [
            # 场景模板相关
            # "qa",  # 模板选择（由 confirm 返回 False 跳过）
            # 需求收集
            "DemoPipeline",  # 名称
            "构建一个问答应用",  # 目标
            "文档知识库",  # 数据来源
            "实时",  # 延迟
            "",  # 约束
            # 保存路径
            str(tmp_path / "demo.yaml"),
        ]
    )
    prompt_iter = iter(prompts)

    def fake_prompt(message, default=None, **kwargs):
        try:
            return next(prompt_iter)
        except StopIteration:
            return default or ""

    # 调整 confirm 顺序：不使用模板、配置满意、保存文件、立即运行、autostop
    confirms = iter([False, True, True, True])

    def fake_confirm(message, default=False, **kwargs):
        try:
            return next(confirms)
        except StopIteration:
            return default

    monkeypatch.setattr(chat_module.typer, "prompt", fake_prompt)
    monkeypatch.setattr(chat_module.typer, "confirm", fake_confirm)

    coordinator = chat_module.PipelineChatCoordinator("mock", "mock-model", None, None)
    handled = coordinator.handle("请帮我构建一个大模型应用，包含知识检索")

    assert handled is True
    assert fake_generator["instances"], "Generator should be instantiated"
    instance = fake_generator["instances"][0]
    assert instance.calls, "generate should be invoked"
    requirements = instance.calls[0][0]
    assert requirements["data_sources"] == ["文档知识库"]
    assert fake_generator["saves"], "plan should be saved"
    saved_path = fake_generator["saves"][0][1]
    assert saved_path.exists()
    assert fake_generator["executed"].get("plan") == fake_generator["plan"]
    assert fake_generator["executed"].get("autostop") is True


def test_scenario_templates():
    """测试场景模板功能"""
    # 测试获取模板
    qa_template = chat_module._get_scenario_template("qa")
    assert qa_template is not None
    assert qa_template["name"] == "问答助手"
    assert "data_sources" in qa_template

    # 测试不存在的模板
    invalid = chat_module._get_scenario_template("nonexistent")
    assert invalid is None


def test_validate_pipeline_config():
    """测试配置验证功能"""
    # 有效配置
    valid_plan = {
        "pipeline": {
            "name": "test",
            "type": "local",
        },
        "source": {
            "class": "test.Source",
            "params": {},
        },
        "sink": {
            "class": "test.Sink",
            "params": {},
        },
        "stages": [
            {
                "id": "stage1",
                "kind": "map",
                "class": "test.Stage",
            }
        ],
    }
    is_valid, errors = chat_module._validate_pipeline_config(valid_plan)
    assert is_valid
    assert len(errors) == 0

    # 无效配置 - 缺少必需字段
    invalid_plan = {
        "pipeline": {"name": "test"},  # 缺少 type
        "source": {},  # 缺少 class
    }
    is_valid, errors = chat_module._validate_pipeline_config(invalid_plan)
    assert not is_valid
    assert len(errors) > 0
    assert any("type" in err for err in errors)
    assert any("class" in err for err in errors)


def test_normalize_list_field():
    """测试列表字段规范化"""
    # 逗号分隔
    result = chat_module._normalize_list_field("a,b,c")
    assert result == ["a", "b", "c"]

    # 中文逗号
    result = chat_module._normalize_list_field("文档，数据库，API")
    assert result == ["文档", "数据库", "API"]

    # 混合分隔符
    result = chat_module._normalize_list_field("a,b;c/d")
    assert result == ["a", "b", "c", "d"]

    # 空字符串
    result = chat_module._normalize_list_field("")
    assert result == []

    # 带空格
    result = chat_module._normalize_list_field("  a  ,  b  ")
    assert result == ["a", "b"]
