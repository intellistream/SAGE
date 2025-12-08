# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Experiments Module
==================

Predefined experiments for control plane benchmarking.

This module provides standardized experiments:
- BaseExperiment: Abstract base class with lifecycle methods
- ThroughputExperiment: Measure max throughput across request rates
- LatencyExperiment: Analyze latency distribution under fixed load
- SLOComplianceExperiment: Compare SLO compliance across policies
- MixedRatioExperiment: Sweep LLM/Embedding ratios

Example:
    from sage.benchmark.benchmark_control_plane.experiments import (
        ThroughputExperiment,
        LatencyExperiment,
        SLOComplianceExperiment,
        MixedRatioExperiment,
    )

    # Run throughput experiment
    exp = ThroughputExperiment(
        name="throughput_test",
        control_plane_url="http://localhost:8888",
    )
    result = await exp.run_full()

    # Run latency experiment
    exp = LatencyExperiment(
        name="latency_test",
        request_rate=100,
        num_requests=1000,
    )
    result = await exp.run_full()
"""

from .base_experiment import BaseExperiment, ExperimentResult
from .latency_exp import DEFAULT_PERCENTILES, LatencyExperiment
from .mixed_ratio_exp import DEFAULT_LLM_RATIOS, MixedRatioExperiment
from .slo_compliance_exp import DEFAULT_LOAD_LEVELS, SLOComplianceExperiment
from .throughput_exp import DEFAULT_REQUEST_RATES, ThroughputExperiment

__all__ = [
    # Base classes
    "BaseExperiment",
    "ExperimentResult",
    # Experiments
    "ThroughputExperiment",
    "LatencyExperiment",
    "SLOComplianceExperiment",
    "MixedRatioExperiment",
    # Constants
    "DEFAULT_REQUEST_RATES",
    "DEFAULT_PERCENTILES",
    "DEFAULT_LOAD_LEVELS",
    "DEFAULT_LLM_RATIOS",
]
