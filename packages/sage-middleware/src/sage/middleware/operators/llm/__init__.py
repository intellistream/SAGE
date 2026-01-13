"""
LLM Operators - 大语言模型推理算子

这个模块包含 LLM 服务的算子实现。

推荐使用 SageLLMGenerator，支持多种后端：
- backend_type="cuda": NVIDIA GPU (HFCudaEngine)
- backend_type="mock": 测试模式 (MockEngine)
- backend_type="ascend": 华为昇腾 (TODO)

Breaking Change (v0.3.0):
    VLLMGenerator 和 VLLMEmbedding 已移除。
    请迁移到 SageLLMGenerator(backend_type="cuda")。
"""

from sage.middleware.operators.llm.sagellm_generator import SageLLMGenerator

__all__ = ["SageLLMGenerator"]
