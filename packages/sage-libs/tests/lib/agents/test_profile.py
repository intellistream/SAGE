# refactor_wxh/MemoRAG/packages/sage-libs/tests/lib/agents/test_profile.py

import pytest
# 如果你已经配置好了 pythonpath（见第2节），下面这行导入能直接成功：
from sage.libs.agents.profile.profile import BaseProfile


def test_defaults_and_types():
    p = BaseProfile()
    assert p.name == "BaseAgent"
    assert p.role == "general assistant"
    assert isinstance(p.goals, list) and p.goals == []
    assert isinstance(p.tasks, list) and p.tasks == []
    assert p.backstory == ""
    assert p.language == "zh"
    assert p.tone == "concise"


def test_render_system_prompt_with_defaults():
    p = BaseProfile()
    s = p.render_system_prompt()
    assert "BaseAgent" in s
    assert "general assistant" in s
    assert "- （未指定）" in s  # 空 goals/tasks 的占位符


def test_render_system_prompt_with_content():
    p = BaseProfile(
        name="ResearchAnalyst",
        role="literature review agent",
        goals=["检索高质量论文", "提供可引用总结"],
        tasks=["列出关键论文", "构建对比表"],
        backstory="专注信息提炼与可追溯性。",
        language="zh",
        tone="concise",
    )
    s = p.render_system_prompt()
    assert "ResearchAnalyst" in s
    assert "literature review agent" in s
    for g in p.goals:
        assert f"- {g}" in s
    for t in p.tasks:
        assert f"- {t}" in s
    assert "Backstory:" in s and "专注信息提炼与可追溯性" in s
    assert "Language: zh" in s
    assert "Tone: concise" in s


def test_to_dict_and_from_dict_roundtrip():
    p = BaseProfile(
        name="Coder",
        role="software bug fixer",
        goals=["复现问题", "最小修复", "补测试"],
        tasks=["阅读堆栈", "定位故障点", "写变更说明"],
        backstory="工程实战导向",
        language="zh",
        tone="concise",
    )
    d = p.to_dict()
    p2 = BaseProfile.from_dict(d)
    assert p2.to_dict() == d


def test_from_dict_with_missing_fields_uses_defaults():
    d = {"name": "OnlyNameProvided"}
    p = BaseProfile.from_dict(d)
    assert p.name == "OnlyNameProvided"
    assert p.role == "general assistant"
    assert p.goals == [] and p.tasks == []
    assert p.backstory == ""
    assert p.language == "zh" and p.tone == "concise"


def test_merged_override_without_mutating_original():
    base = BaseProfile(name="Base", role="helper", goals=["G1"], tasks=["T1"])
    derived = base.merged(name="Derived", role="teacher", goals=["G2"], tone="detailed")

    assert derived is not base
    assert derived.name == "Derived"
    assert derived.role == "teacher"
    assert derived.goals == ["G2"]
    assert derived.tone == "detailed"

    assert base.name == "Base"
    assert base.role == "helper"
    assert base.goals == ["G1"]
    assert base.tone == "concise"


def test_lists_are_independent_instances():
    p1 = BaseProfile()
    p2 = BaseProfile()
    p1.goals.append("A")
    p1.tasks.append("B")
    assert p1.goals == ["A"] and p2.goals == []
    assert p1.tasks == ["B"] and p2.tasks == []


def test_prompt_is_reasonably_structured():
    p = BaseProfile(name="X", role="Y", goals=["g1", "g2"], tasks=["t1"])
    s = p.render_system_prompt()
    assert "You are **X**, acting as **Y**." in s
    assert "Backstory:" in s
    assert "Goals:" in s
    assert "Typical Tasks:" in s
    assert "- g1" in s and "- g2" in s and "- t1" in s


def test_non_ascii_and_english_language_toggle():
    p = BaseProfile(
        name="测试Agent",
        role="teacher",
        language="en",
        tone="detailed",
        goals=["讲清关键概念"],
        tasks=["举例说明"],
    )
    s = p.render_system_prompt()
    assert "Language: en" in s
    assert "Tone: detailed" in s
    assert "讲清关键概念" in s
    assert "举例说明" in s
