"""HuggingFace embedding wrapper."""

from typing import Any, Dict, List, Optional

from ..base import BaseEmbedding
from ..hf import hf_embed_sync  # 复用现有实现


class HFEmbedding(BaseEmbedding):
    """HuggingFace Transformer Embedding Wrapper

    使用本地 HuggingFace Transformer 模型生成 embedding。
    首次使用时会自动从 HuggingFace Hub 下载模型。

    特点:
        - ✅ 高质量语义 embedding
        - ✅ 本地运行，数据隐私
        - ✅ 支持多种语言
        - ❌ 需要下载模型（首次使用）
        - ❌ 可能需要 GPU 加速（大模型）

    推荐模型:
        - BAAI/bge-small-zh-v1.5 (中文，512维)
        - BAAI/bge-base-zh-v1.5 (中文，768维)
        - BAAI/bge-large-zh-v1.5 (中文，1024维)
        - sentence-transformers/all-MiniLM-L6-v2 (英文，384维)
        - sentence-transformers/all-mpnet-base-v2 (英文，768维)

    Args:
        model: 模型名称（HuggingFace Hub）

    Examples:
        >>> # 中文 embedding
        >>> emb = HFEmbedding(model="BAAI/bge-small-zh-v1.5")
        >>> vec = emb.embed("你好世界")
        >>> len(vec)
        512
        >>>
        >>> # 英文 embedding
        >>> emb = HFEmbedding(model="sentence-transformers/all-MiniLM-L6-v2")
        >>> vec = emb.embed("hello world")
        >>> len(vec)
        384
        >>>
        >>> # 批量处理
        >>> vecs = emb.embed_batch(["文本1", "文本2", "文本3"])
        >>> len(vecs)
        3
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        """初始化 HuggingFace Embedding

        Args:
            model: 模型名称（如 'BAAI/bge-small-zh-v1.5'）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            RuntimeError: 如果模型加载失败
        """
        super().__init__(model=model, **kwargs)

        try:
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "HuggingFace embedding 需要 transformers 库。\n"
                "请安装: pip install transformers torch"
            ) from e

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.embed_model = AutoModel.from_pretrained(model, trust_remote_code=True)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load HuggingFace model '{model}': {e}\n"
                f"提示:\n"
                f"  1. 检查模型名称是否正确\n"
                f"  2. 检查网络连接（首次使用需要下载）\n"
                f"  3. 设置镜像: export HF_ENDPOINT=https://hf-mirror.com"
            ) from e

        # 推断维度
        self._dim = self._infer_dimension()
        self._model_name = model

    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: 如果 embedding 失败
        """
        try:
            return hf_embed_sync(text, self.tokenizer, self.embed_model)
        except Exception as e:
            raise RuntimeError(
                f"HuggingFace embedding 失败: {e}\n" f"文本: {text[:100]}..."
            ) from e

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为 embedding 向量

        当前实现为逐个调用 embed()。
        TODO: 实现真正的批量处理以提高效率。
        Issue URL: https://github.com/intellistream/SAGE/issues/910

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        # TODO: 优化为真正的批量处理
        # Issue URL: https://github.com/intellistream/SAGE/issues/909
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
            'hf'
        """
        return "hf"

    def _infer_dimension(self) -> int:
        """通过 embedding 一个示例文本推断维度

        Returns:
            推断的维度值（如果失败则返回默认值 768）
        """
        try:
            sample = self.embed("test")
            return len(sample)
        except Exception:
            # 如果推断失败，返回常见的默认维度
            return 768

    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "hf",
            "requires_api_key": False,
            "requires_model_download": True,
            "default_dimension": None,  # 动态推断
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return f"HFEmbedding(model='{self._model_name}', dim={self._dim})"
