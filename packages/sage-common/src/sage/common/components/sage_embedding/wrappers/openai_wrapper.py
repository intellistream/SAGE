"""OpenAI embedding wrapper.

支持 OpenAI 官方 API、兼容 API 以及本地 sagellm 推理引擎（占位实现）。
"""

import logging
import os
from typing import TYPE_CHECKING, Any

from ..base import BaseEmbedding

if TYPE_CHECKING:
    pass  # Reserved for future type hints

# 抑制 httpx 的 INFO 日志（每次 HTTP 请求都会打印）
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding API Wrapper

    支持 OpenAI 官方 API、兼容的第三方 API（如 vLLM、DeepSeek 等）
    以及本地 sagellm 推理引擎。

    特点:
        - ✅ 高质量 embedding
        - ✅ 支持多种模型
        - ✅ 兼容第三方 API
        - ✅ 支持本地 sagellm 引擎（无需网络）
        - ❌ 需要 API Key（仅 openai provider）
        - ❌ 需要网络连接（仅 openai provider）
        - 💰 按使用量计费（仅 openai provider）

    支持的模型:
        - text-embedding-3-small (1536维，性价比高)
        - text-embedding-3-large (3072维，最高质量)
        - text-embedding-ada-002 (1536维，旧版本)
        - 任意 HuggingFace 模型（通过 sagellm provider）

    Args:
        model: 模型名称（默认 'text-embedding-3-small'）
        api_key: API 密钥（可选，默认从环境变量 OPENAI_API_KEY 读取）
        base_url: API 端点（可选，用于兼容 API）
        provider: 后端提供者，'openai'（默认）或 'sagellm'（本地推理）
        sagellm_config: sagellm 推理配置（仅 provider='sagellm' 时有效）

    Examples:
        >>> # OpenAI 官方 API
        >>> import os
        >>> emb = OpenAIEmbedding(
        ...     model="text-embedding-3-small",
        ...     api_key=os.getenv("OPENAI_API_KEY")
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 兼容 API（自定义端点）
        >>> emb = OpenAIEmbedding(
        ...     model="text-embedding-v1",
        ...     api_key=os.getenv("OPENAI_API_KEY"),
        ...     base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:8090/v1")
        ... )
        >>> vec = emb.embed("你好世界")
        >>>
        >>> # vLLM 部署的模型
        >>> emb = OpenAIEmbedding(
        ...     model="BAAI/bge-base-en-v1.5",
        ...     base_url="http://localhost:8000/v1"
        ... )
        >>>
        >>> # 本地 sagellm 推理（当前使用 sentence-transformers 作为占位实现，无需 API Key 和网络）
        >>> emb = OpenAIEmbedding(
        ...     model="BAAI/bge-small-zh-v1.5",
        ...     provider="sagellm",
        ...     sagellm_config={"device": "cuda"}
        ... )
        >>> vec = emb.embed("你好世界")
    """

    # 常见模型的维度映射
    DIMENSION_MAP = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "text-embedding-v1": 1536,
        # Common HuggingFace models for sagellm
        "BAAI/bge-small-zh-v1.5": 512,
        "BAAI/bge-base-zh-v1.5": 768,
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "BAAI/bge-m3": 1024,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
    }

    # 支持的 provider
    SUPPORTED_PROVIDERS = ("openai", "sagellm")

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str | None = None,
        provider: str = "openai",
        sagellm_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 OpenAI Embedding

        Args:
            model: 模型名称
            api_key: API 密钥（可选，仅 openai provider）
            base_url: API 端点（可选，仅 openai provider）
            provider: 后端提供者，'openai' 或 'sagellm'
            sagellm_config: sagellm 推理配置（仅 provider='sagellm' 时有效）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            RuntimeError: 如果 openai provider 未提供 API Key
            ValueError: 如果 provider 不支持
        """
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)

        self._model = model
        self._provider = provider.lower()
        self._sagellm_config = sagellm_config or {}
        self._sagellm_engine: Any = None  # Lazy-loaded sagellm engine

        # 验证 provider
        if self._provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"不支持的 provider: {self._provider}\n"
                f"支持的 provider: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )

        if self._provider == "openai":
            # OpenAI API 模式
            self._api_key = api_key or os.getenv("OPENAI_API_KEY")
            self._base_url = base_url

            # 检查 API Key
            if not self._api_key:
                raise RuntimeError(
                    "OpenAI embedding 需要 API Key。\n"
                    "解决方案:\n"
                    "  1. 设置环境变量: export OPENAI_API_KEY='your-key'\n"  # pragma: allowlist secret
                    "  2. 传递参数: OpenAIEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                    "\n"
                    "如果使用兼容 API:\n"
                    "  export OPENAI_API_KEY='your-api-key'\n"  # pragma: allowlist secret
                    "  并指定 base_url 参数\n"
                    "\n"
                    "或者使用本地推理:\n"
                    "  OpenAIEmbedding(model='BAAI/bge-small-zh-v1.5', provider='local')"
                )
        else:
            # 本地推理模式（当前占位实现：sentence-transformers）
            self._api_key = None
            self._base_url = None
            logger.info(
                f"使用 sagellm 本地推理占位实现: model={model}, config={self._sagellm_config}"
            )

        # 推断或获取维度
        self._dim = self._infer_dimension()

    def embed(self, text: str) -> list[float]:
        """将文本转换为 embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: 如果 API 调用或本地推理失败
        """
        if self._provider == "sagellm":
            return self._embed_with_sagellm(text)
        return self._embed_with_openai(text)

    def _embed_with_openai(self, text: str) -> list[float]:
        """使用 OpenAI API 生成 embedding

        Args:
            text: 输入文本

        Returns:
            embedding 向量
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            response = client.embeddings.create(
                model=self._model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(
                f"OpenAI embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def _embed_with_sagellm(self, text: str) -> list[float]:
        """使用 sagellm（占位：sentence-transformers）生成 embedding

        Args:
            text: 输入文本

        Returns:
            embedding 向量
        """
        engine = self._get_sagellm_engine()
        try:
            # sentence-transformers 返回 numpy array
            result = engine.encode(text)
            # 确保返回 list[float]
            if hasattr(result, "tolist"):
                return result.tolist()
            return list(result)
        except Exception as e:
            raise RuntimeError(
                f"sagellm embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查模型是否已下载，设备是否可用"
            ) from e

    def _get_sagellm_engine(self) -> Any:
        """获取或创建 sagellm embedding 引擎（懒加载）

        注意：当前 sagellm 仓库尚未提供 embedding 引擎，这里以
        sentence-transformers 作为占位实现。完成 sagellm 的 EmbeddingEngine
        实现后，可直接替换为正式引擎。

        Returns:
            占位的 sentence-transformers 模型实例

        Raises:
            RuntimeError: 如果无法加载 sentence-transformers
        """
        if self._sagellm_engine is not None:
            return self._sagellm_engine

        try:
            # 使用 sentence-transformers 作为占位（待 sagellm 原生 EmbeddingEngine 完成后替换）
            from sentence_transformers import SentenceTransformer

            device = self._sagellm_config.get("device", "cpu")
            logger.info(
                f"使用 sentence-transformers 占位推理: model={self._model}, device={device}"
            )
            self._sagellm_engine = SentenceTransformer(
                self._model,
                device=device,
            )
            return self._sagellm_engine

        except ImportError as e:
            raise RuntimeError(
                "本地 embedding 需要 sentence-transformers。\n"
                "请安装: pip install sentence-transformers"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"无法初始化 sagellm embedding 占位引擎: {e}\n"
                f"模型: {self._model}\n"
                f"配置: {self._sagellm_config}"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        使用 OpenAI API 的批量接口或 sagellm 的批量编码。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表

        Raises:
            RuntimeError: 如果 API 调用或本地推理失败
        """
        if not texts:
            return []

        if self._provider == "sagellm":
            return self._embed_batch_with_sagellm(texts)
        return self._embed_batch_with_openai(texts)

    def _embed_batch_with_openai(self, texts: list[str]) -> list[list[float]]:
        """使用 OpenAI API 批量生成 embedding

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        try:
            from openai import OpenAI

            # 设置环境变量
            if self._api_key:
                import os

                os.environ["OPENAI_API_KEY"] = self._api_key

            client = OpenAI(base_url=self._base_url)

            # OpenAI API 支持批量：input 可以是字符串列表
            response = client.embeddings.create(
                model=self._model,
                input=texts,  # 直接传入列表
            )

            # 按照原始顺序返回结果
            return [item.embedding for item in response.data]

        except Exception as e:
            raise RuntimeError(
                f"OpenAI 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"批量大小: {len(texts)}\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def _embed_batch_with_sagellm(self, texts: list[str]) -> list[list[float]]:
        """使用 sagellm（占位：sentence-transformers）批量生成 embedding

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        engine = self._get_sagellm_engine()
        try:
            # sentence-transformers 支持批量编码
            results = engine.encode(texts)
            # 确保返回 list[list[float]]
            if hasattr(results, "tolist"):
                return results.tolist()
            return [list(r) if hasattr(r, "__iter__") else [r] for r in results]
        except Exception as e:
            raise RuntimeError(
                f"sagellm 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"批量大小: {len(texts)}\n"
                f"提示: 检查模型是否已下载，设备是否可用"
            ) from e

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
            'openai' 或 'sagellm'（取决于 provider）
        """
        return self._provider

    @property
    def provider(self) -> str:
        """返回后端提供者

        Returns:
            'openai' 或 'sagellm'
        """
        return self._provider

    def _infer_dimension(self) -> int:
        """推断或获取维度

        Returns:
            推断的维度值
        """
        # 优先使用已知的维度映射
        if self._model in self.DIMENSION_MAP:
            return self.DIMENSION_MAP[self._model]

        # 如果是未知模型，尝试通过实际调用推断
        try:
            sample = self.embed("test")
            return len(sample)
        except Exception:
            # 如果推断失败，返回默认维度
            return 1536

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "openai",
            "requires_api_key": True,  # Only for openai provider
            "requires_model_download": True,  # sagellm 需要本地模型
            "default_dimension": 1536,
            "supported_providers": list(cls.SUPPORTED_PROVIDERS),
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        base_info = f"OpenAIEmbedding(model='{self._model}', dim={self._dim}, provider='{self._provider}'"
        if self._provider == "openai" and self._base_url:
            base_info += f", base_url='{self._base_url}'"
        elif self._provider == "sagellm" and self._sagellm_config:
            config_str = ", ".join(f"{k}={v!r}" for k, v in self._sagellm_config.items())
            base_info += f", config={{{config_str}}}"
        return base_info + ")"

    def close(self) -> None:
        """释放资源

        清理本地引擎占用的 GPU 内存等资源。
        """
        if self._sagellm_engine is not None:
            # 尝试释放资源
            if hasattr(self._sagellm_engine, "close"):
                self._sagellm_engine.close()
            elif hasattr(self._sagellm_engine, "stop"):
                self._sagellm_engine.stop()
            self._sagellm_engine = None
            logger.debug("sagellm embedding 引擎占位已释放")

    def __del__(self) -> None:
        """析构函数"""
        try:
            self.close()
        except Exception:
            pass  # 忽略析构时的错误
