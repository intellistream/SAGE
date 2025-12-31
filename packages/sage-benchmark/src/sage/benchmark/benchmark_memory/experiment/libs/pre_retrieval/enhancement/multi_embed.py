"""MultiEmbedAction - 多维embedding策略

使用场景：
- 综合多种相似度维度（语义+情感+实体等）
- 多模态检索（文本+图像+音频）
- 精细化相似度计算

特点：
- 支持多个embedding模型组合
- 可配置各维度权重
- 输出加权平均向量或独立向量
"""

from typing import Any, Optional

from sage.benchmark.benchmark_memory.experiment.utils import EmbeddingGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class MultiEmbedAction(BasePreRetrievalAction):
    """多维embedding Action

    使用多个embedding模型生成多维向量表示。
    """

    def _init_action(self) -> None:
        """初始化多维embedding配置"""
        self.embeddings_config = self._get_config_value(
            "embeddings", required=True, context="action=enhancement.multi_embed"
        )

        if not self.embeddings_config:
            raise ValueError("embeddings config cannot be empty for multi_embed action")

        self.output_format = self._get_config_value("output_format", default="weighted")

        self.match_insert_config = self._get_config_value("match_insert_config", default=True)

        # 初始化embedding生成器（延迟初始化）
        self._embedding_generators: dict[str, tuple[EmbeddingGenerator, float]] = {}
        self._runtime_config: dict[str, Any] = {}

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """生成多维embedding

        Args:
            input_data: 输入数据

        Returns:
            包含多维embedding的输出数据
        """
        question = input_data.question

        if not question:
            return PreRetrievalOutput(
                query=question,
                metadata={"multi_embed_format": self.output_format},
            )

        # 延迟初始化：从config中获取runtime配置并创建多个生成器
        if not self._embedding_generators:
            self._runtime_config = input_data.data.get("_runtime_config", {})
            if not self._runtime_config:
                # 尝试从input_data.config中获取
                self._runtime_config = {
                    "embedding_base_url": input_data.config.get("embedding_base_url")
                }
            self._init_generators()

        # 生成多维embedding
        embeddings_dict: dict[str, list[float]] = {}
        weights_dict: dict[str, float] = {}

        for emb_config in self.embeddings_config:
            name = emb_config.get("name", "default")
            weight = emb_config.get("weight", 1.0)

            if name in self._embedding_generators:
                generator, _ = self._embedding_generators[name]
                try:
                    embedding = generator.embed(question)
                    embeddings_dict[name] = embedding
                    weights_dict[name] = weight
                except Exception as e:
                    print(f"[WARNING] Failed to generate {name} embedding: {e}")

        # 根据output_format处理
        query_embedding: Optional[list[float]] = None
        metadata: dict[str, Any] = {
            "original_query": question,
            "multi_embed_format": self.output_format,
            "embedding_names": list(embeddings_dict.keys()),
        }

        if self.output_format == "weighted":
            # 加权平均
            query_embedding = self._weighted_average(embeddings_dict, weights_dict)
            metadata["embedding_weights"] = weights_dict

        elif self.output_format == "dict":
            # 独立向量字典
            metadata["embeddings"] = embeddings_dict
            metadata["embedding_weights"] = weights_dict
            # 主查询向量使用第一个embedding
            if embeddings_dict:
                query_embedding = next(iter(embeddings_dict.values()))

        elif self.output_format == "concat":
            # 拼接所有向量
            query_embedding = []
            for name in sorted(embeddings_dict.keys()):
                query_embedding.extend(embeddings_dict[name])
            metadata["embedding_dims"] = {name: len(emb) for name, emb in embeddings_dict.items()}

        return PreRetrievalOutput(
            query=question,
            query_embedding=query_embedding,
            metadata=metadata,
            retrieve_mode="active",
            retrieve_params={
                "multi_embed": True,
                "embeddings": embeddings_dict if self.output_format == "dict" else None,
                "weights": weights_dict if self.output_format == "dict" else None,
            },
        )

    def _init_generators(self) -> None:
        """延迟初始化embedding生成器"""
        base_url = self._runtime_config.get("embedding_base_url")

        for emb_config in self.embeddings_config:
            name = emb_config.get("name", "default")
            model = emb_config.get("model", "BAAI/bge-m3")
            weight = emb_config.get("weight", 1.0)

            try:
                generator = EmbeddingGenerator(base_url=base_url, model_name=model)
                self._embedding_generators[name] = (generator, weight)
            except Exception as e:
                print(f"[WARNING] Failed to create {name} embedding generator: {e}")

    def _weighted_average(
        self, embeddings_dict: dict[str, list[float]], weights_dict: dict[str, float]
    ) -> Optional[list[float]]:
        """计算加权平均向量

        Args:
            embeddings_dict: {name: embedding} 字典
            weights_dict: {name: weight} 字典

        Returns:
            加权平均向量
        """
        if not embeddings_dict:
            return None

        # 获取向量维度
        first_embedding = next(iter(embeddings_dict.values()))
        dim = len(first_embedding)

        # 检查所有向量维度是否一致
        if not all(len(emb) == dim for emb in embeddings_dict.values()):
            print("[WARNING] Embedding dimensions mismatch, using first embedding")
            return first_embedding

        # 计算加权和
        weighted_sum = [0.0] * dim
        total_weight = 0.0

        for name, embedding in embeddings_dict.items():
            weight = weights_dict.get(name, 1.0)
            total_weight += weight

            for i, value in enumerate(embedding):
                weighted_sum[i] += value * weight

        # 归一化
        if total_weight > 0:
            weighted_avg = [v / total_weight for v in weighted_sum]
            return weighted_avg

        return first_embedding
