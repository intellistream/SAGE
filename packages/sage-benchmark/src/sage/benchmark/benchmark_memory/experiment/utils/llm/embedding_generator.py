"""Embedding 生成工具

提供统一的 embedding 生成接口，支持本地和远程 embedding 服务
"""

import time

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model


class EmbeddingGenerator:
    """Embedding 生成器类"""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str = "BAAI/bge-m3",
        api_key: str = "dummy",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """初始化 Embedding 生成器

        Args:
            base_url: Embedding 服务器地址 (例如 "http://localhost:8091/v1")
                     如果为 None，则不使用 embedding
            model_name: 模型名称
            api_key: API 密钥 (本地服务使用 "dummy")
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url
        self.model_name = model_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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
        max_retries = config.get("runtime.embedding_max_retries", 3)
        retry_delay = config.get("runtime.embedding_retry_delay", 1.0)

        return cls(
            base_url=base_url,
            model_name=model_name,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    def embed(self, text: str) -> list[float] | None:
        """对单个文本进行 embedding（带重试机制）

        Args:
            text: 输入文本

        Returns:
            embedding 向量，如果未配置 embedding 服务则返回 None
        """
        if self.embedding_model is None:
            return None

        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed(text)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    print(
                        f"[EmbeddingGenerator] Retry {attempt + 1}/{self.max_retries} after error: {e}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # 递增延迟

        # 所有重试都失败了
        raise RuntimeError(
            f"Embedding failed after {self.max_retries} retries: {last_error}"
        ) from last_error

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        """对多个文本进行批量 embedding（带重试机制，严格批量）

        严格使用底层模型的原生批量接口，不回退到逐个调用。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表，如果未配置 embedding 服务则返回 None

        Raises:
            RuntimeError: 批量 embedding 失败
            NotImplementedError: 底层模型不支持批量接口
        """
        if self.embedding_model is None:
            return None

        if not texts:
            return []

        # 严格使用批量接口（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_batch(texts)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    print(
                        f"[EmbeddingGenerator] Batch retry {attempt + 1}/{self.max_retries} after error: {e}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))

        raise RuntimeError(
            f"Batch embedding failed after {self.max_retries} retries: {last_error}"
        ) from last_error

    def is_available(self) -> bool:
        """检查 embedding 服务是否可用

        Returns:
            True 如果已配置 embedding 服务，否则 False
        """
        return self.embedding_model is not None
