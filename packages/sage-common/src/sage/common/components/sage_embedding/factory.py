"""Factory for creating embedding model instances."""

import os
from typing import Any

from .base import BaseEmbedding
from .registry import EmbeddingRegistry, ModelStatus


class EmbeddingFactory:
    """Embedding 模型工厂

    提供统一的接口来创建各种 embedding 模型实例。

    Examples:
        >>> # 创建 Hash embedding
        >>> emb = EmbeddingFactory.create("hash", dim=384)
        >>>
        >>> # 创建 HuggingFace embedding
        >>> emb = EmbeddingFactory.create(
        ...     "hf",
        ...     model="BAAI/bge-small-zh-v1.5"
        ... )
        >>>
        >>> # 列出所有可用方法
        >>> models = EmbeddingFactory.list_models()
        >>> for method, info in models.items():
        ...     print(f"{method}: {info['description']}")
    """

    @staticmethod
    def create(method: str, **kwargs: Any) -> BaseEmbedding:
        """创建 Embedding 实例

        Args:
            method: embedding 方法名 (hf, openai, hash, mockembedder, ...)
            **kwargs: 方法特定参数
                - model: 模型名称 (hf, openai 等需要)
                - api_key: API 密钥 (openai, jina 等需要)
                - base_url: API 端点 (openai 可选)
                - dim/fixed_dim: 固定维度 (hash, mockembedder 需要)

        Returns:
            BaseEmbedding 实例

        Raises:
            ValueError: 不支持的方法或缺少必要参数
            RuntimeError: 模型不可用或初始化失败

        Examples:
            >>> # HuggingFace 模型
            >>> emb = EmbeddingFactory.create(
            ...     method="hf",
            ...     model="BAAI/bge-small-zh-v1.5"
            ... )
            >>> vec = emb.embed("hello world")
            >>>
            >>> # OpenAI API
            >>> emb = EmbeddingFactory.create(
            ...     method="openai",
            ...     model="text-embedding-3-small",
            ...     api_key=os.getenv("OPENAI_API_KEY")
            ... )
            >>>
            >>> # Mock embedder (测试)
            >>> emb = EmbeddingFactory.create(
            ...     method="mockembedder",
            ...     fixed_dim=384
            ... )
            >>>
            >>> # Hash embedding (快速测试)
            >>> emb = EmbeddingFactory.create(
            ...     method="hash",
            ...     dim=384
            ... )
        """
        # 获取注册信息
        wrapper_class = EmbeddingRegistry.get_wrapper_class(method)
        if not wrapper_class:
            available = ", ".join(EmbeddingRegistry.list_methods())
            raise ValueError(
                f"不支持的 embedding 方法: '{method}'\n"
                f"可用方法: {available}\n"
                f"提示: 请检查方法名拼写，或查看文档了解支持的方法。"
            )

        # 获取模型信息
        model_info = EmbeddingRegistry.get_model_info(method)

        # 检查必要参数
        if model_info:
            if model_info.requires_api_key and "api_key" not in kwargs:
                # 尝试从环境变量获取
                api_key = os.getenv(f"{method.upper()}_API_KEY")
                if not api_key:
                    api_key = os.getenv("OPENAI_API_KEY")  # 通用 fallback
                if api_key:
                    kwargs["api_key"] = api_key

            if model_info.requires_model_download and "model" not in kwargs:
                examples = ", ".join(model_info.example_models[:2])
                raise ValueError(
                    f"{method} 方法需要指定 model 参数。\n"
                    f"示例模型: {examples}\n"
                    f"用法: EmbeddingFactory.create('{method}', model='...')"
                )

        # 检查状态
        status = EmbeddingRegistry.check_status(method, **kwargs)
        if status == ModelStatus.NEEDS_API_KEY:
            raise RuntimeError(
                f"{method} 方法需要 API Key。\n"
                f"解决方案:\n"
                f"  1. 设置环境变量: export {method.upper()}_API_KEY='your-key'\n"  # pragma: allowlist secret
                f"  2. 传递参数: EmbeddingFactory.create('{method}', api_key='your-key', ...)"  # pragma: allowlist secret
            )

        if status == ModelStatus.UNAVAILABLE:
            raise RuntimeError(f"{method} 方法当前不可用。\n请检查是否已正确安装相关依赖。")

        # 创建实例
        try:
            return wrapper_class(**kwargs)
        except TypeError as e:
            # 捕获参数错误，提供友好的提示
            raise ValueError(
                f"创建 {method} embedding 实例时参数错误: {e}\n"
                f"提示: 请检查传入的参数是否正确。\n"
                f"当前参数: {kwargs}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"创建 {method} embedding 实例失败: {e}\n方法: {method}\n参数: {kwargs}"
            ) from e

    @staticmethod
    def list_models() -> dict[str, dict[str, Any]]:
        """列出所有可用的 embedding 方法

        Returns:
            Dict[method_name, model_info]
            每个 model_info 包含:
                - display_name: 显示名称
                - description: 描述
                - requires_api_key: 是否需要 API Key
                - requires_download: 是否需要下载模型
                - default_dimension: 默认维度
                - examples: 示例模型列表

        Examples:
            >>> models = EmbeddingFactory.list_models()
            >>> for method, info in models.items():
            ...     print(f"{method}:")
            ...     print(f"  {info['description']}")
            ...     if info['requires_api_key']:
            ...         print("  ⚠️ 需要 API Key")
            ...     if info['examples']:
            ...         print(f"  示例: {', '.join(info['examples'][:2])}")
            hash:
              轻量级哈希 embedding（测试用）
              示例: hash-384, hash-768
            hf:
              本地 Transformer 模型
              ⚠️ 需要下载模型
              示例: BAAI/bge-small-zh-v1.5, sentence-transformers/all-MiniLM-L6-v2
        """
        result = {}
        for method in EmbeddingRegistry.list_methods():
            info = EmbeddingRegistry.get_model_info(method)
            if info:
                result[method] = {
                    "display_name": info.display_name,
                    "description": info.description,
                    "requires_api_key": info.requires_api_key,
                    "requires_download": info.requires_model_download,
                    "default_dimension": info.default_dimension,
                    "examples": info.example_models,
                }
        return result

    @staticmethod
    def check_availability(method: str, **kwargs: Any) -> dict[str, Any]:
        """检查特定方法的可用性

        Args:
            method: 方法名称
            **kwargs: 方法特定参数

        Returns:
            包含以下键的字典:
                - status: 状态字符串 (available/needs_api_key/needs_download/unavailable)
                - message: 详细说明
                - action: 建议操作

        Examples:
            >>> # 检查 HuggingFace 模型
            >>> status = EmbeddingFactory.check_availability(
            ...     "hf",
            ...     model="BAAI/bge-small-zh-v1.5"
            ... )
            >>> print(status['message'])
            ✅ 已缓存
            >>>
            >>> # 检查 OpenAI（无 API Key）
            >>> status = EmbeddingFactory.check_availability("openai")
            >>> print(status['status'])
            needs_api_key
            >>> print(status['action'])
            设置环境变量: export OPENAI_API_KEY='your-key'  # pragma: allowlist secret
        """
        status = EmbeddingRegistry.check_status(method, **kwargs)

        messages = {
            ModelStatus.AVAILABLE: ("✅ 可用", "可以直接使用"),
            ModelStatus.CACHED: (
                "✅ 已缓存",
                f"模型已下载到本地: {kwargs.get('model', '?')}",
            ),
            ModelStatus.NEEDS_API_KEY: (
                "⚠️ 需要 API Key",
                f"设置环境变量: export {method.upper()}_API_KEY='your-key'",  # pragma: allowlist secret
            ),
            ModelStatus.NEEDS_DOWNLOAD: (
                "⚠️ 需要下载模型",
                f"首次使用将从 HuggingFace 下载模型: {kwargs.get('model', '?')}",
            ),
            ModelStatus.UNAVAILABLE: ("❌ 不可用", f"方法 '{method}' 未注册或不支持"),
        }

        message, action = messages.get(status, ("❓ 未知", "无法确定状态"))

        return {
            "status": status.value,
            "message": message,
            "action": action,
        }


# 便捷函数（包装 Factory 方法）


def get_embedding_model(method: str, **kwargs: Any) -> BaseEmbedding:
    """获取 Embedding 模型实例（推荐使用的便捷函数）

    这是 EmbeddingFactory.create() 的别名，提供更简洁的调用方式。

    Args:
        method: embedding 方法名
        **kwargs: 方法特定参数

    Returns:
        BaseEmbedding 实例

    Examples:
        >>> # 推荐用法
        >>> emb = get_embedding_model("hf", model="BAAI/bge-small-zh-v1.5")
        >>> vec = emb.embed("hello world")
        >>> dim = emb.get_dim()
    """
    return EmbeddingFactory.create(method, **kwargs)


def list_embedding_models() -> dict[str, dict[str, Any]]:
    """列出所有可用的 embedding 方法（便捷函数）

    Returns:
        方法信息字典

    Examples:
        >>> models = list_embedding_models()
        >>> print(list(models.keys()))
        ['hash', 'hf', 'mockembedder', 'openai', ...]
    """
    return EmbeddingFactory.list_models()


def check_model_availability(method: str, **kwargs: Any) -> dict[str, Any]:
    """检查模型可用性（便捷函数）

    Args:
        method: 方法名称
        **kwargs: 方法特定参数

    Returns:
        状态信息字典

    Examples:
        >>> status = check_model_availability("hash")
        >>> print(status['status'])
        available
    """
    return EmbeddingFactory.check_availability(method, **kwargs)
