import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = Path(__file__).parents[2] / "tools/benchmark_carrier/plot_semantic_mapreduce_quality_cost.py"
    spec = importlib.util.spec_from_file_location("semantic_mapreduce_quality_cost", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_values_and_tikz_panel_are_deterministic():
    module = _load_module()
    points = [
        {key: values[index] for key, values in module.EXPECTED.items()}
        for index in range(3)
    ]
    module.assert_frozen(points)
    kwargs = dict(
        x0=1.0,
        label="a",
        ylabel="Quality",
        ymax=1.0,
        yticks=[0.0, 0.5, 1.0],
        series=[("Action F1", module.EXPECTED["f1"], "black", "solid")],
        legend_x=2.0,
        legend_y=2.0,
    )
    assert module.panel(**kwargs) == module.panel(**kwargs)


def test_frozen_value_drift_fails_closed():
    module = _load_module()
    points = [
        {key: values[index] for key, values in module.EXPECTED.items()}
        for index in range(3)
    ]
    points[1]["f1"] += 0.001
    with pytest.raises(SystemExit, match="frozen-value mismatch for f1"):
        module.assert_frozen(points)
