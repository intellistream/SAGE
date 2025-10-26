"""Ollama embedding wrapper."""

from typing import Any

from ..base import BaseEmbedding


class OllamaEmbedding(BaseEmbedding):
    """Ollama Embedding Wrapper

    支持通过 Ollama 访问本地部署的 embedding 模型。

    特点:
        - ✅ 本地部署，数据隐私
        - ✅ 无需 API Key
        - ✅ 支持多种开源模型
        - ✅ 免费使用
        - ❌ 需要安装 Ollama
        - ❌ 需要下载模型
        - 💻 需要本地计算资源

    支持的模型（示例）:
        - nomic-embed-text (默认，768维，高质量英文）
        - mxbai-embed-large (1024维，高性能）
        - all-minilm (384维，轻量级）
        - bge-large (1024维，多语言）

    Args:
        model: 模型名称（默认 'nomic-embed-text'）
        base_url: Ollama API 地址（默认 'http://localhost:11434'）
        api_key: API 密钥（可选，某些部署需要）

    Examples:
        >>> # 基本使用（本地默认端口）
        >>> emb = OllamaEmbedding(model="nomic-embed-text")
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 自定义端口
        >>> emb = OllamaEmbedding(
        ...     model="nomic-embed-text",
        ...     base_url="http://localhost:11434"
        ... )
        >>> vec = emb.embed("你好世界")
        >>>
        >>> # 远程 Ollama 服务（需要 API Key）
        >>> emb = OllamaEmbedding(
        ...     model="nomic-embed-text",
        ...     base_url="https://ollama.example.com",
        ...     api_key="your-key"  # pragma: allowlist secret
        ... )
    """

    # 常见模型的维度映射（需要根据实际模型更新）
    DIMENSION_MAP = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "bge-large": 1024,
    }

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 Ollama Embedding

        Args:
            model: 模型名称
            base_url: Ollama API 地址
            api_key: API 密钥（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            ImportError: 如果未安装 ollama 包
        """
        super().__init__(model=model, base_url=base_url, api_key=api_key, **kwargs)

        # 检查依赖
        try:
            import ollama  # noqa: F401
        except ImportError:
            raise ImportError(
                "Ollama embedding 需要 ollama 包。\n"
                "安装方法: pip install ollama\n"
                "\n"
                "同时需要安装 Ollama 服务:\n"
                "  - macOS/Linux: https://ollama.ai/download\n"
                "  - 安装后运行: ollama pull {model}"
            )

        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._kwargs = kwargs

        # 推断维度
        self._dim = self._infer_dimension()

    def embed(self, text: str) -> list[float]:
        """将文本转换为 embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: 如果 API 调用失败
        """
        try:
            import ollama

            # 构建 headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "SAGE/0.0",
            }
            if self._api_key:
                headers["Authorization"] = self._api_key

            # 创建客户端
            kwargs = {"base_url": self._base_url, "headers": headers}
            client = ollama.Client(**kwargs)

            # 调用 API
            data = client.embed(model=self._model, input=text)
            return data["embedding"]

        except Exception as e:
            raise RuntimeError(
                f"Ollama embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"端点: {self._base_url}\n"
                f"文本: {text[:100]}...\n"
                f"提示:\n"
                f"  1. 检查 Ollama 服务是否运行: ollama list\n"
                f"  2. 拉取模型: ollama pull {self._model}\n"
                f"  3. 检查端口: {self._base_url}"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        当前实现为逐个调用 embed()。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        return [self.embed(text) for text in texts]

    def get_dim(self) -> int:
        """获取向量维度

        Returns:
            维度值
        """
        return self._dim

    @property
    def method_name(self) -> str:
        """返回方法名称

        Returns:
            'ollama'
        """
        return "ollama"

    def _infer_dimension(self) -> int:
        """推断向量维度

        Returns:
            推断的维度值
        """
        # 优先使用已知的维度映射
        if self._model in self.DIMENSION_MAP:
            return self.DIMENSION_MAP[self._model]

        # 尝试通过实际调用推断
        try:
            sample = self.embed("test")
            return len(sample)
        except Exception:
            # 如果推断失败，返回默认维度
            return 768

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "ollama",
            "requires_api_key": False,
            "requires_model_download": True,
            "default_dimension": 768,
            "features": [
                "本地部署，数据隐私",
                "支持多种开源模型",
                "免费使用",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return (
            f"OllamaEmbedding(model='{self._model}', base_url='{self._base_url}', dim={self._dim})"
        )
