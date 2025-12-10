"""
Configuration loader for ICML benchmark experiments.

Supports:
- YAML config loading with validation
- Environment variable substitution
- Default config generation
- Quick mode override
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class HardwareConfig:
    """Hardware configuration."""

    gpus: int = 2
    gpu_type: str = "A100"
    cpu_cores: int = 64
    memory_gb: int = 256


@dataclass
class ModelConfig:
    """Model configuration."""

    name: str
    instances: int = 1
    device: str = "cuda"
    tensor_parallel: int = 1


@dataclass
class WorkloadConfig:
    """Workload configuration."""

    total_requests: int = 1000
    warmup_requests: int = 100
    llm_ratio: float = 0.7
    request_rate: float = 50.0
    input_tokens_min: int = 256
    input_tokens_max: int = 512
    output_tokens_min: int = 64
    output_tokens_max: int = 256
    seed: int = 42


@dataclass
class MetricsConfig:
    """Metrics configuration."""

    latency_percentiles: list[int] = field(default_factory=lambda: [50, 95, 99])
    slo_chat_p99_ms: int = 500
    slo_embedding_p99_ms: int = 100
    report_interval_s: int = 10


@dataclass
class OutputConfig:
    """Output configuration."""

    results_dir: str = "results"
    save_raw_data: bool = True
    generate_plots: bool = True
    export_latex: bool = True


@dataclass
class ExperimentConfig:
    """Complete experiment configuration."""

    name: str
    description: str
    experiment_section: str
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    llm_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(name="Qwen/Qwen2.5-7B-Instruct")
    )
    embedding_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(name="BAAI/bge-m3", device="cpu")
    )
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    baselines: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class ConfigLoader:
    """Configuration loader with validation and defaults."""

    def __init__(self):
        self.config_dir = Path(__file__).parent

    def load(self, path: str) -> ExperimentConfig:
        """Load configuration from YAML file."""
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = self.config_dir / config_path

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            raw_config = yaml.safe_load(f)

        # Substitute environment variables
        raw_config = self._substitute_env_vars(raw_config)

        return self._parse_config(raw_config)

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute ${VAR} with environment variables."""
        if isinstance(obj, str):
            # Handle ${VAR} and ${VAR:-default} patterns
            import re

            pattern = r"\$\{(\w+)(?::-([^}]*))?\}"

            def replacer(match):
                var_name = match.group(1)
                default = match.group(2) or ""
                return os.environ.get(var_name, default)

            return re.sub(pattern, replacer, obj)
        elif isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        return obj

    def _parse_config(self, raw: dict) -> ExperimentConfig:
        """Parse raw config dict into ExperimentConfig."""
        exp = raw.get("experiment", {})

        # Hardware
        hw_raw = raw.get("hardware", {})
        hardware = HardwareConfig(
            gpus=hw_raw.get("gpus", 2),
            gpu_type=hw_raw.get("gpu_type", "A100"),
            cpu_cores=hw_raw.get("cpu_cores", 64),
            memory_gb=hw_raw.get("memory_gb", 256),
        )

        # Models
        models_raw = raw.get("models", {})
        llm_raw = models_raw.get("llm", {})
        llm_model = ModelConfig(
            name=llm_raw.get("name", "Qwen/Qwen2.5-7B-Instruct"),
            instances=llm_raw.get("instances", 2),
            device=llm_raw.get("device", "cuda"),
            tensor_parallel=llm_raw.get("tensor_parallel", 1),
        )

        emb_raw = models_raw.get("embedding", {})
        embedding_model = ModelConfig(
            name=emb_raw.get("name", "BAAI/bge-m3"),
            instances=emb_raw.get("instances", 1),
            device=emb_raw.get("device", "cpu"),
        )

        # Workload
        wl_raw = raw.get("workload", {})
        input_tokens = wl_raw.get("input_tokens", {})
        output_tokens = wl_raw.get("output_tokens", {})
        workload = WorkloadConfig(
            total_requests=wl_raw.get("total_requests", 1000),
            warmup_requests=wl_raw.get("warmup_requests", 100),
            llm_ratio=wl_raw.get("llm_ratio", 0.7),
            request_rate=wl_raw.get("request_rate", 50.0),
            input_tokens_min=input_tokens.get("min", 256),
            input_tokens_max=input_tokens.get("max", 512),
            output_tokens_min=output_tokens.get("min", 64),
            output_tokens_max=output_tokens.get("max", 256),
            seed=wl_raw.get("seed", 42),
        )

        # Metrics
        metrics_raw = raw.get("metrics", {})
        slo_targets = metrics_raw.get("slo_targets", {})
        metrics = MetricsConfig(
            latency_percentiles=metrics_raw.get("latency_percentiles", [50, 95, 99]),
            slo_chat_p99_ms=slo_targets.get("chat_p99_ms", 500),
            slo_embedding_p99_ms=slo_targets.get("embedding_p99_ms", 100),
            report_interval_s=metrics_raw.get("report_interval_s", 10),
        )

        # Output
        output_raw = raw.get("output", {})
        output = OutputConfig(
            results_dir=output_raw.get("results_dir", "results"),
            save_raw_data=output_raw.get("save_raw_data", True),
            generate_plots=output_raw.get("generate_plots", True),
            export_latex=output_raw.get("export_latex", True),
        )

        # Baselines and policies
        baselines = [b["name"] for b in raw.get("baselines", []) if b.get("enabled", True)]
        policies = raw.get("policies", [])

        return ExperimentConfig(
            name=exp.get("name", "unnamed"),
            description=exp.get("description", ""),
            experiment_section=exp.get("section", ""),
            hardware=hardware,
            llm_model=llm_model,
            embedding_model=embedding_model,
            workload=workload,
            metrics=metrics,
            output=output,
            baselines=baselines,
            policies=policies,
            extra=raw.get("extra", {}),
        )

    def get_default_config(self, section: str) -> ExperimentConfig:
        """Get default configuration for a given experiment section."""
        defaults = {
            "5.1": ExperimentConfig(
                name="exp_5_1_control_plane",
                description="Control Plane Unified Scheduling Experiment",
                experiment_section="5.1",
                baselines=["sage_unified", "vllm_only", "separated"],
            ),
            "5.2": ExperimentConfig(
                name="exp_5_2_scheduling",
                description="Scheduling Policy Comparison Experiment",
                experiment_section="5.2",
                policies=["fifo", "priority", "slo_aware", "hybrid"],
            ),
            "5.3": ExperimentConfig(
                name="exp_5_3_e2e",
                description="End-to-End System Evaluation",
                experiment_section="5.3",
            ),
        }
        return defaults.get(
            section,
            ExperimentConfig(name="unknown", description="Unknown", experiment_section=section),
        )

    def apply_quick_mode(self, config: ExperimentConfig) -> ExperimentConfig:
        """Apply quick mode overrides for faster testing."""
        config.workload.total_requests = 100
        config.workload.warmup_requests = 10
        return config

    def save(self, config: ExperimentConfig, path: str) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            "experiment": {
                "name": config.name,
                "description": config.description,
                "section": config.experiment_section,
            },
            "hardware": {
                "gpus": config.hardware.gpus,
                "gpu_type": config.hardware.gpu_type,
                "cpu_cores": config.hardware.cpu_cores,
                "memory_gb": config.hardware.memory_gb,
            },
            "models": {
                "llm": {
                    "name": config.llm_model.name,
                    "instances": config.llm_model.instances,
                    "device": config.llm_model.device,
                    "tensor_parallel": config.llm_model.tensor_parallel,
                },
                "embedding": {
                    "name": config.embedding_model.name,
                    "instances": config.embedding_model.instances,
                    "device": config.embedding_model.device,
                },
            },
            "workload": {
                "total_requests": config.workload.total_requests,
                "warmup_requests": config.workload.warmup_requests,
                "llm_ratio": config.workload.llm_ratio,
                "request_rate": config.workload.request_rate,
                "input_tokens": {
                    "min": config.workload.input_tokens_min,
                    "max": config.workload.input_tokens_max,
                },
                "output_tokens": {
                    "min": config.workload.output_tokens_min,
                    "max": config.workload.output_tokens_max,
                },
                "seed": config.workload.seed,
            },
            "metrics": {
                "latency_percentiles": config.metrics.latency_percentiles,
                "slo_targets": {
                    "chat_p99_ms": config.metrics.slo_chat_p99_ms,
                    "embedding_p99_ms": config.metrics.slo_embedding_p99_ms,
                },
                "report_interval_s": config.metrics.report_interval_s,
            },
            "output": {
                "results_dir": config.output.results_dir,
                "save_raw_data": config.output.save_raw_data,
                "generate_plots": config.output.generate_plots,
                "export_latex": config.output.export_latex,
            },
            "baselines": [{"name": b, "enabled": True} for b in config.baselines],
            "policies": config.policies,
            "extra": config.extra,
        }

        with open(path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
