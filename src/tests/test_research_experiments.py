import json
from dataclasses import replace

import pytest

from sage.runtime.research_experiments import (
    InvalidResearchPlan,
    experiment_response_format,
    prepare_experiments,
    render_experiments,
    validate_experiments,
)
from sage.runtime.source_answer_plan import PlanSource, prepare_source_plan


def request():
    source = prepare_source_plan("提出安全性和性能实验", (PlanSource("a", "A", "", "Source text, not measured results."),),
        allow_inferences=True)
    return prepare_experiments(source, ("a",))


def payload(req):
    common = {"mechanism": "state mechanism", "control_value": "off", "treatment_value": "on",
        "shared_conditions": ["same weights", "same precision", "same hardware", "same request trace"],
        "fault_schedule": "identical crash-stop replay in BOTH groups"}
    return {"digest": req.digest, "experiments": [
        {**common, "kind": "invariant", "invariant": "unique state ownership"},
        {**common, "kind": "performance", "metric": "QPS", "direction": "higher",
            "threshold_gain": 0.2, "confidence": 0.95, "target_power": 0.8,
            "sampling_unit": "independent paired request trace"}]}


def test_runtime_owns_distinct_matched_control_and_falsification_rules():
    req = request()
    plan = validate_experiments(req, json.dumps(payload(req)))
    safety, performance = render_experiments(req, plan)
    assert "一次可复现的不变量违反" in safety and "不需要统计显著性" in safety
    assert "性能变慢或没有加速，不是不变量违例" in safety
    assert "处理组指标/对照组指标 − 1" in performance
    assert "单侧置信上界低于" in performance and "0.2" in performance
    assert "单纯差异不显著或样本不足，不构成证伪" in performance
    assert "区间跨越阈值，结果仍不确定" in performance
    assert "先导实验估计方差" in performance
    assert "两组使用完全相同的故障／事件轨迹" in safety and "两组使用完全相同" in performance
    assert "不代表项目当前实现或既有实验" in safety
    assert "对照度量为正" in performance
    assert experiment_response_format(req)["json_schema"]["strict"] is True


def test_lower_is_better_uses_correct_relative_gain_not_inverse_ratio():
    req, data = request(), payload(request())
    data["experiments"][1].update(metric="latency", direction="lower", threshold_gain=0.123456789)
    result = render_experiments(req, validate_experiments(req, json.dumps(data)))[1]
    assert "1 − 处理组指标/对照组指标" in result
    assert "0.123456789" in result


@pytest.mark.parametrize("verdict", ["difference is not significant", "no speedup falsifies safety",
    "no tests were performed", "the mechanism is proven"])
def test_freeform_verdict_and_falsifier_fields_are_not_accepted(verdict):
    req, data = request(), payload(request())
    data["experiments"][1]["falsifier"] = verdict
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(req, json.dumps(data))


@pytest.mark.parametrize("key,value", [("confidence", 1), ("confidence", False),
    ("confidence", float("nan")), ("threshold_gain", float("inf")), ("threshold_gain", 0),
    ("threshold_gain", -0.1), ("target_power", 0), ("target_power", 1),
    ("direction", "unknown"), ("direction", []), ("sampling_unit", "")])
def test_invalid_statistical_design_is_a_terminal_quality_error(key, value):
    req, data = request(), payload(request())
    data["experiments"][1][key] = value
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(req, json.dumps(data))


@pytest.mark.parametrize("change", ["drop_performance", "same_variant", "missing_shared", "no_fault_schedule"])
def test_comparison_cannot_lose_its_required_design_fields(change):
    req, data = request(), payload(request())
    if change == "drop_performance":
        data["experiments"] = data["experiments"][:1]
    elif change == "same_variant":
        data["experiments"][0]["control_value"] = "on"
    elif change == "missing_shared":
        data["experiments"][0]["shared_conditions"] = []
    else:
        data["experiments"][0].pop("fault_schedule")
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(req, json.dumps(data))


def test_binding_rejects_changed_question_and_duplicate_or_stale_receipts():
    req = request()
    data = payload(req)
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(replace(req, payload=req.payload.replace("提出安全性", "不要安全性")), json.dumps(data))
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(req, json.dumps({**data, "digest": "old"}))
    with pytest.raises(InvalidResearchPlan):
        validate_experiments(req, json.dumps(data).replace('"digest":', '"digest":"duplicate","digest":'))
