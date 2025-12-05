"""
Benchmark Refiner Configuration
===============================

配置文件目录，包含各Pipeline的YAML配置。

配置文件:
- config_baseline.yaml: 无压缩基线配置
- config_longrefiner.yaml: LongRefiner配置
- config_reform.yaml: REFORM配置
- config_provence.yaml: Provence配置
- head_analysis_config.yaml: 注意力头分析配置

配置结构:
    pipeline:
      name: str
      description: str
      version: str

    source:
      type: "hf"
      hf_dataset_name: str
      hf_dataset_config: str
      hf_split: str
      max_samples: int

    retriever:
      type: "wiki18_faiss"
      dimension: int
      top_k: int
      faiss:
        index_path: str
        documents_path: str

    generator:
      vllm:
        model_name: str
        base_url: str

    [algorithm]:  # longrefiner / reform / provence
      enabled: bool
      ...algorithm specific config...

    evaluate:
      platform: "local"
"""

__all__: list[str] = []
