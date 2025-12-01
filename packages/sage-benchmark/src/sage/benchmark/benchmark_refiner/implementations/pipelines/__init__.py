"""
Refiner RAG Pipelines
=====================

各种Refiner算法的RAG评测Pipeline。

每个Pipeline包含:
1. 数据源 (HFDatasetBatch)
2. 检索器 (Wiki18FAISSRetriever)
3. Refiner (可选，baseline无此步骤)
4. Promptor (QAPromptor)
5. 生成器 (OpenAIGenerator / vLLM)
6. 评估器 (F1, TokenCount, Latency, CompressionRate)

评测指标:
- F1 Score: 答案质量
- Token Count: 压缩后token数
- Latency: 端到端延迟
- Compression Rate: 压缩率
"""

__all__: list[str] = []
