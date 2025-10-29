"""NVIDIA NIM (OpenAI-compatible) embedding wrapper."""

import os
from typing import Any, Literal

from ..base import BaseEmbedding


class NvidiaOpenAIEmbedding(BaseEmbedding):
    """NVIDIA NIM (OpenAI-compatible) Embedding Wrapper

    支持通过 NVIDIA NIM 访问 NVIDIA 的 embedding 模型（OpenAI 兼容 API）。

    特点:
        - ✅ NVIDIA 优化模型
        - ✅ OpenAI 兼容接口
        - ✅ 高性能
        - ✅ 支持检索优化
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型（示例）:
        - nvidia/llama-3.2-nv-embedqa-1b-v1 (默认）
        - nvidia/nv-embed-v1 (4096维，高性能）

    Args:
        model: 模型名称（默认 'nvidia/llama-3.2-nv-embedqa-1b-v1'）
        base_url: API 地址（默认 'https://integrate.api.nvidia.com/v1'）
        api_key: API 密钥（可选，默认从环境变量 OPENAI_API_KEY 读取）
        input_type: 输入类型（'passage' 或 'query'，默认 'passage'）
        trunc: 截断策略（'NONE', 'START', 'END'，默认 'NONE'）
        encode: 返回格式（'float' 或 'base64'，默认 'float'）

    Examples:
        >>> # 基本使用
        >>> import os
        >>> emb = NvidiaOpenAIEmbedding(
        ...     model="nvidia/llama-3.2-nv-embedqa-1b-v1",
        ...     api_key=os.getenv("OPENAI_API_KEY")
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 检索场景（区分文档和查询）
        >>> # 文档端
        >>> doc_emb = NvidiaOpenAIEmbedding(input_type="passage")
        >>> doc_vec = doc_emb.embed("这是一篇文档")
        >>>
        >>> # 查询端
        >>> query_emb = NvidiaOpenAIEmbedding(input_type="query")
        >>> query_vec = query_emb.embed("查询内容")
    """

    # 常见模型的维度映射（需要根据实际模型更新）
    DIMENSION_MAP = {
        "nvidia/llama-3.2-nv-embedqa-1b-v1": 2048,
        "nvidia/nv-embed-v1": 4096,
    }

    def __init__(
        self,
        model: str = "nvidia/llama-3.2-nv-embedqa-1b-v1",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: str | None = None,
        input_type: str = "passage",
        trunc: str = "NONE",
        encode: Literal["float", "base64"] = "float",
        **kwargs: Any,
    ) -> None:
        """初始化 NVIDIA OpenAI Embedding

        Args:
            model: 模型名称
            base_url: API 地址
            api_key: API 密钥（可选）
            input_type: 输入类型（'passage' 或 'query'）
            trunc: 截断策略
            encode: 返回格式
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            ImportError: 如果未安装 openai 包
            RuntimeError: 如果未提供 API Key
        """
        super().__init__(
            model=model,
            base_url=base_url,
            api_key=api_key,
            input_type=input_type,
            trunc=trunc,
            encode=encode,
            **kwargs,
        )

        # 检查依赖
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError as err:
            raise ImportError(
                "NVIDIA OpenAI embedding 需要 openai 包。\n安装方法: pip install openai"
            ) from err

        self._model = model
        self._base_url = base_url
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._input_type = input_type
        self._trunc = trunc
        self._encode: Literal["float", "base64"] = encode
        self._kwargs = kwargs

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "NVIDIA OpenAI embedding 需要 API Key。\n"  # pragma: allowlist secret
                "解决方案:\n"
                "  1. 设置环境变量: export NVIDIA_API_KEY='your-key'\n"  # pragma: allowlist secret
                "     或: export OPENAI_API_KEY='your-key'\n"  # pragma: allowlist secret
                "  2. 传递参数: NvidiaOpenAIEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                "\n"
                "获取 API Key: https://build.nvidia.com/"  # pragma: allowlist secret
            )

        # 获取维度
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
            from openai import OpenAI

            # 设置环境变量（OpenAI SDK 会读取）
            if self._api_key:
                os.environ["OPENAI_API_KEY"] = self._api_key

            client = OpenAI(base_url=self._base_url)

            response = client.embeddings.create(
                model=self._model,
                input=text,
                encoding_format=self._encode,
                extra_body={
                    "input_type": self._input_type,
                    "truncate": self._trunc,
                },
            )

            return response.data[0].embedding

        except Exception as e:
            raise RuntimeError(
                f"NVIDIA OpenAI embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"端点: {self._base_url}\n"
                f"输入类型: {self._input_type}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        使用 OpenAI 兼容 API 的批量接口（input 参数支持列表）。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表

        Raises:
            RuntimeError: 如果 API 调用失败
        """
        if not texts:
            return []

        try:
            import os

            from openai import OpenAI

            # 设置环境变量
            if self._api_key:
                os.environ["OPENAI_API_KEY"] = self._api_key

            client = OpenAI(base_url=self._base_url)

            # 批量调用
            response = client.embeddings.create(
                model=self._model,
                input=texts,  # 直接传入列表
                encoding_format=self._encode,
                extra_body={
                    "input_type": self._input_type,
                    "truncate": self._trunc,
                },
            )

            # 按照原始顺序返回结果
            return [item.embedding for item in response.data]

        except Exception as e:
            raise RuntimeError(
                f"NVIDIA OpenAI 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"输入类型: {self._input_type}\n"
                f"批量大小: {len(texts)}\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
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
            'nvidia_openai'
        """
        return "nvidia_openai"

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
            return 2048

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "nvidia_openai",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 2048,
            "features": [
                "NVIDIA 优化模型",
                "OpenAI 兼容接口",
                "支持检索优化（passage/query）",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return (
            f"NvidiaOpenAIEmbedding(model='{self._model}', "
            f"input_type='{self._input_type}', dim={self._dim})"
        )
