"""Embedding 生成工具

提供统一的 embedding 生成接口，支持本地和远程 embedding 服务
"""

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model


class EmbeddingGenerator:
    """Embedding 生成器类"""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str = "BAAI/bge-m3",
        api_key: str = "dummy",
    ):
        """初始化 Embedding 生成器

        Args:
            base_url: Embedding 服务器地址 (例如 "http://localhost:8091/v1")
                     如果为 None，则不使用 embedding
            model_name: 模型名称
            api_key: API 密钥 (本地服务使用 "dummy")
        """
        self.base_url = base_url
        self.model_name = model_name

        if base_url:
            # 初始化 embedding 模型
            self.embedding_model = apply_embedding_model(
                name="openai",
                model=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        else:
            self.embedding_model = None

    @classmethod
    def from_config(cls, config) -> "EmbeddingGenerator":
        """从配置对象创建 EmbeddingGenerator

        Args:
            config: RuntimeConfig 对象

        Returns:
            EmbeddingGenerator 实例
        """
        base_url = config.get("runtime.embedding_base_url")
        model_name = config.get("runtime.embedding_model", "BAAI/bge-m3")

        return cls(base_url=base_url, model_name=model_name)

    def embed(self, text: str) -> list[float] | None:
        """对单个文本进行 embedding

        Args:
            text: 输入文本

        Returns:
            embedding 向量，如果未配置 embedding 服务则返回 None
        """
        if self.embedding_model is None:
            return None

        return self.embedding_model.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        """对多个文本进行 embedding

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表，如果未配置 embedding 服务则返回 None
        """
        if self.embedding_model is None:
            return None

        return [self.embedding_model.embed(text) for text in texts]

    def is_available(self) -> bool:
        """检查 embedding 服务是否可用

        Returns:
            True 如果已配置 embedding 服务，否则 False
        """
        return self.embedding_model is not None
