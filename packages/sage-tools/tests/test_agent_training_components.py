"""Unit tests for agent training utilities."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

# Import SIAS components from middleware
from sage.middleware.components.sage_sias import CoresetSelector, OnlineContinualLearner
from sage.tools.agent_training.data_formatter import AgentSFTFormatter
from sage.tools.agent_training.dialog_processor import AgentDialogProcessor, ProcessedDialog


def _make_turn(role: str, **kwargs):
    payload = {"role": role}
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _make_dialog(turns, **kwargs):
    return SimpleNamespace(
        dialog_id=kwargs.get("dialog_id", "dlg-test"),
        goal=kwargs.get("goal", "test tool call"),
        target_tools=kwargs.get("target_tools", ["web_search"]),
        metadata=kwargs.get("metadata", {}),
        turns=turns,
    )


def _make_sample(dialog_id: str, loss: float) -> ProcessedDialog:
    return ProcessedDialog(
        dialog_id=dialog_id,
        task_type="tool_selection",
        text=f"dialog {dialog_id}",
        metadata={"loss": loss},
        target_tools=["tool"],
        split="train",
        source="agent_sft",
    )


@pytest.mark.unit
def test_formatter_emits_qwen_tool_payloads():
    assistant_turn = _make_turn(
        "assistant",
        content="call web_search tool with plan first",
    )
    tool_turn = _make_turn(
        "tool",
        tool_id="web_search",
        content='{"query": "weather in hangzhou"}',
        result={"hits": 3},
    )
    user_turn = _make_turn("user", content="查一下杭州天气")

    dialog = _make_dialog(
        [user_turn, assistant_turn, tool_turn],
        dialog_id="dlg-qwen",
    )

    formatter = AgentSFTFormatter(
        output_format="alpaca",
        include_tool_descriptions=False,
        tool_call_style="qwen",
    )

    formatted = formatter.format_dialog(dialog)
    output = formatted["output"]

    assert "<tool_call>" in output
    assert "<tool_response>" in output

    call_payload = json.loads(output.split("<tool_call>\n", 1)[1].split("\n</tool_call>", 1)[0])
    assert call_payload["name"] == "web_search"
    assert call_payload["arguments"]["query"] == "weather in hangzhou"

    response_payload = json.loads(
        output.split("<tool_response>\n", 1)[1].split("\n</tool_response>", 1)[0]
    )
    assert response_payload["name"] == "web_search"
    assert response_payload["result"] == {"hits": 3}


@pytest.mark.unit
def test_coreset_selector_picks_highest_loss_samples():
    samples = [
        _make_sample("dlg1", 0.1),
        _make_sample("dlg2", 0.7),
        _make_sample("dlg3", 0.4),
    ]

    selector = CoresetSelector(strategy="loss_topk", metric_key="loss", random_seed=0)
    selected = selector.select(samples, target_size=2, metrics=None)

    assert {sample.dialog_id for sample in selected} == {"dlg2", "dlg3"}


@pytest.mark.unit
def test_online_continual_learner_replays_buffer_samples():
    samples = [
        _make_sample("dlg1", 0.1),
        _make_sample("dlg2", 0.8),
        _make_sample("dlg3", 0.5),
        _make_sample("dlg4", 0.9),
    ]

    selector = CoresetSelector(strategy="loss_topk", metric_key="loss", random_seed=0)
    learner = OnlineContinualLearner(
        buffer_size=3,
        replay_ratio=0.5,
        selector=selector,
        random_seed=0,
    )

    batch1 = learner.update_buffer(samples[:2], metrics={"dlg1": 0.1, "dlg2": 0.8})
    assert {dialog.dialog_id for dialog in batch1} == {"dlg1", "dlg2"}
    assert {dialog.dialog_id for dialog in learner.buffer_snapshot()} == {"dlg1", "dlg2"}

    batch2 = learner.update_buffer(
        samples[2:],
        metrics={"dlg1": 0.1, "dlg2": 0.8, "dlg3": 0.5, "dlg4": 0.9},
    )

    # replay_ratio=0.5 => expect 1 replay when two new samples are provided
    assert len(batch2) == 3
    new_ids = {dialog.dialog_id for dialog in samples[2:]}
    replay_ids = {dialog.dialog_id for dialog in batch2 if dialog.dialog_id not in new_ids}
    assert len(replay_ids) == 1

    # Buffer should keep the top-3 loss dialogs (dlg2, dlg3, dlg4)
    assert {dialog.dialog_id for dialog in learner.buffer_snapshot()} == {"dlg2", "dlg3", "dlg4"}


@pytest.mark.unit
def test_dialog_processor_emits_metrics_for_coreset():
    processor = AgentDialogProcessor()
    sample = ProcessedDialog(
        dialog_id="dlg-metrics",
        task_type="tool_selection",
        text="plan tool call plan tool call",
        metadata={"loss": 0.5},
        target_tools=["web_search"],
        split="train",
        source="agent_sft",
    )

    metrics = processor._compute_dialog_metrics(sample)  # pylint: disable=protected-access
    assert metrics["loss"] == pytest.approx(0.5)
    assert metrics["token_length"] > 0
    assert 0 < metrics["lexical_diversity"] <= 1
