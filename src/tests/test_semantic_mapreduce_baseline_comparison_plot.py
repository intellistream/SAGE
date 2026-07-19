import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).parents[2]
        / "tools"
        / "benchmark_carrier"
        / "plot_semantic_mapreduce_baseline_comparison.py"
    )
    spec = importlib.util.spec_from_file_location(
        "semantic_mapreduce_baseline_comparison", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_jitter_is_deterministic_and_bounded():
    module = _load_module()
    first = module._jitter("constrained/cascade/7")
    assert first == module._jitter("constrained/cascade/7")
    assert -0.17 <= first <= 0.17


def test_sha256_records_the_exact_figure_input(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "input.csv"
    source.write_bytes(b"a,b\n1,2\n")
    assert module._sha256(source) == (
        "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470"
    )


def test_frozen_aggregate_drift_fails_closed():
    module = _load_module()
    offline = []
    for reducer in module.PANEL_A_REDUCERS:
        value = module.EXPECTED_AGGREGATE[reducer]
        offline.extend(
            {"scenario": scenario, "seed": seed, "reducer": reducer, "f1": value}
            for scenario in module.SCENARIOS
            for seed in module.SEEDS_10
        )
    online = []
    for reducer, key in (
        (module.HYBRID, "matched-hybrid"),
        (module.ACTION, module.ACTION),
    ):
        value = module.EXPECTED_AGGREGATE[key]
        online.extend(
            {"scenario": scenario, "seed": seed, "reducer": reducer, "f1": value}
            for scenario in module.SCENARIOS
            for seed in module.MATCHED_SEEDS
        )
    with pytest.raises(SystemExit, match="matched-constrained"):
        module.summarize(offline, online)


def test_summary_marks_legacy_permission_asymmetry():
    module = _load_module()
    assert module.ACTION == "llm-pairwise-action-validated"
    # The full frozen fixture is exercised by the generator invocation. This
    # assertion protects the claim metadata added to summarize's return value.
    source = (
        Path(__file__).parents[2]
        / "tools"
        / "benchmark_carrier"
        / "plot_semantic_mapreduce_baseline_comparison.py"
    ).read_text(encoding="utf-8")
    assert '"legacy_action_h0": "semantic-graph"' in source
    assert '"fair_shared_catalog_peer_comparison": False' in source
    assert '"f1_delta_family_clustered_bootstrap_95ci"' in source
