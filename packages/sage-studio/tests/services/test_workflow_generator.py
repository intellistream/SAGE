"""Tests for the workflow generator adapter in Studio services."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sage.studio.services.workflow_generator import WorkflowGenerator, generate_workflow_from_chat


class StubResult(SimpleNamespace):
    success: bool = True
    visual_pipeline: dict | None = None
    raw_plan: dict | None = None
    explanation: str | None = None
    error: str | None = None


class StubGenerator:
    def __init__(self, *, success: bool = True):
        self.success = success
        self.calls: list = []

    def generate(self, context):
        self.calls.append(context)
        if self.success:
            return StubResult(success=True, visual_pipeline={"nodes": []}, raw_plan={})
        return StubResult(success=False, error="boom")


@pytest.fixture()
def workflow(monkeypatch):
    generator = WorkflowGenerator()
    stub_llm = StubGenerator()
    stub_rule = StubGenerator()

    monkeypatch.setattr(
        "sage.libs.agentic.workflow.GenerationContext",
        lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(
        "sage.libs.agentic.workflow.generators.LLMWorkflowGenerator",
        lambda: stub_llm,
    )
    monkeypatch.setattr(
        "sage.libs.agentic.workflow.generators.RuleBasedWorkflowGenerator",
        lambda: stub_rule,
    )

    return generator, stub_llm, stub_rule


def test_generate_uses_llm_by_default(workflow):
    generator, stub_llm, stub_rule = workflow

    result = generator.generate("build a rag pipeline")

    assert result.success is True
    assert len(stub_llm.calls) == 1
    assert stub_rule.calls == []


def test_generate_uses_rule_generator_when_requested(workflow):
    generator, stub_llm, stub_rule = workflow

    result = generator.generate("do deterministic flow", use_llm=False)

    assert result.success is True
    assert len(stub_rule.calls) == 1
    assert stub_llm.calls == []


def test_generate_handles_failed_generation(workflow, monkeypatch):
    generator, stub_llm, _ = workflow
    stub_llm.success = False

    result = generator.generate("bad input")

    assert result.success is False
    assert result.error == "boom"


def test_generate_workflow_from_chat_passthrough(monkeypatch):
    stub = StubGenerator()

    class Wrapper:
        def __init__(self):
            self.calls = []

        def generate(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return stub.generate(kwargs)

    wrapper = Wrapper()

    monkeypatch.setattr(
        "sage.studio.services.workflow_generator.WorkflowGenerator",
        lambda: wrapper,
    )

    result = generate_workflow_from_chat("need pipeline")

    assert result.success is True
    assert wrapper.calls
