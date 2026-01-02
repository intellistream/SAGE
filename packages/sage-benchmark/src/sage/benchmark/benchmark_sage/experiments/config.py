from dataclasses import dataclass, field
from typing import Literal


@dataclass
class HardwareConfig:
    gpus: int = 1
    gpu_type: str = "A100"
    cpu_nodes: int = 0


@dataclass
class ModelConfig:
    name: str


@dataclass
class WorkloadConfig:
    total_requests: int = 1000
    llm_ratio: float = 0.7
    request_rate: float = 10.0
    seed: int = 42
    warmup_requests: int = 100
    input_tokens_min: int = 100
    input_tokens_max: int = 500
    output_tokens_min: int = 50
    output_tokens_max: int = 200
    arrival_pattern: Literal["constant", "poisson", "bursty"] = "poisson"


@dataclass
class MetricsConfig:
    slo_chat_p99_ms: float = 500.0
    slo_embedding_p99_ms: float = 100.0


@dataclass
class OutputConfig:
    generate_plots: bool = True
    save_raw_data: bool = True
    export_latex: bool = True


@dataclass
class ExperimentConfig:
    name: str
    description: str
    experiment_section: str
    gateway_url: str = (
        "http://localhost:8888"  # allow-control-plane-bypass: benchmark configuration
    )
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    llm_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(name="Qwen/Qwen2.5-7B-Instruct")
    )
    embedding_model: ModelConfig = field(default_factory=lambda: ModelConfig(name="BAAI/bge-m3"))
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
