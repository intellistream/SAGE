"""
Refiner配置管理
===============

定义Refiner的配置类和枚举类型。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RefinerAlgorithm(str, Enum):
    """支持的Refiner算法"""

    LONG_REFINER = "long_refiner"  # LongRefiner算法
    ECORAG = "ecorag"  # ECoRAG算法 (待实现)
    XRAG = "xrag"  # xRAG算法 (待实现)
    SIMPLE = "simple"  # 简单截断算法
    NONE = "none"  # 不压缩

    @classmethod
    def list_available(cls):
        """列出所有可用算法"""
        return [e.value for e in cls]


@dataclass
class RefinerConfig:
    """Refiner配置类"""

    # ===== 基础配置 =====
    algorithm: RefinerAlgorithm = RefinerAlgorithm.LONG_REFINER
    """使用的压缩算法"""

    budget: int = 2048
    """token预算，控制压缩后的最大长度"""

    compression_ratio: float | None = None
    """压缩比例（可选，与budget二选一）"""

    # ===== 缓存配置 =====
    enable_cache: bool = False
    """是否启用缓存"""

    cache_size: int = 1000
    """缓存大小（条目数）"""

    cache_ttl: int = 3600
    """缓存TTL（秒）"""

    # ===== 性能配置 =====
    gpu_device: int = 0
    """GPU设备ID"""

    max_model_len: int = 25000
    """模型最大输入长度"""

    gpu_memory_utilization: float = 0.7
    """GPU显存利用率"""

    batch_size: int = 1
    """批处理大小"""

    # ===== LongRefiner特定配置 =====
    base_model_path: str = "Qwen/Qwen2.5-3B-Instruct"
    """基础模型路径"""

    query_analysis_module_lora_path: str = ""
    """查询分析模块LoRA路径"""

    doc_structuring_module_lora_path: str = ""
    """文档结构化模块LoRA路径"""

    global_selection_module_lora_path: str = ""
    """全局选择模块LoRA路径"""

    score_model_name: str = "bge-reranker-v2-m3"
    """评分模型名称"""

    score_model_path: str = "BAAI/bge-reranker-v2-m3"
    """评分模型路径"""

    score_gpu_device: int | None = None
    """评分模型GPU设备（None则使用gpu_device）"""

    # ===== 监控配置 =====
    enable_metrics: bool = True
    """是否启用性能监控"""

    enable_profiling: bool = False
    """是否启用详细性能分析"""

    metrics_output_path: str | None = None
    """性能指标输出路径"""

    # ===== 其他配置 =====
    algorithm_params: dict[str, Any] = field(default_factory=dict)
    """算法特定的额外参数"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "algorithm": (
                self.algorithm.value
                if isinstance(self.algorithm, RefinerAlgorithm)
                else self.algorithm
            ),
            "budget": self.budget,
            "compression_ratio": self.compression_ratio,
            "enable_cache": self.enable_cache,
            "cache_size": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "gpu_device": self.gpu_device,
            "max_model_len": self.max_model_len,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "batch_size": self.batch_size,
            "base_model_path": self.base_model_path,
            "query_analysis_module_lora_path": self.query_analysis_module_lora_path,
            "doc_structuring_module_lora_path": self.doc_structuring_module_lora_path,
            "global_selection_module_lora_path": self.global_selection_module_lora_path,
            "score_model_name": self.score_model_name,
            "score_model_path": self.score_model_path,
            "score_gpu_device": self.score_gpu_device,
            "enable_metrics": self.enable_metrics,
            "enable_profiling": self.enable_profiling,
            "metrics_output_path": self.metrics_output_path,
            "algorithm_params": self.algorithm_params,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "RefinerConfig":
        """从字典创建配置"""
        # 处理algorithm枚举
        if "algorithm" in config_dict and isinstance(config_dict["algorithm"], str):
            config_dict["algorithm"] = RefinerAlgorithm(config_dict["algorithm"])

        return cls(**config_dict)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "RefinerConfig":
        """从YAML文件加载配置"""
        import yaml

        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    def save_yaml(self, yaml_path: str) -> None:
        """保存配置到YAML文件"""
        import yaml

        with open(yaml_path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
