"""AWS Bedrock embedding wrapper."""

import os
from typing import Any

from ..base import BaseEmbedding


class BedrockEmbedding(BaseEmbedding):
    """AWS Bedrock Embedding Wrapper

    支持通过 AWS Bedrock 访问多种 embedding 模型。

    特点:
        - ✅ AWS 托管服务
        - ✅ 多种模型选择（Amazon Titan、Cohere）
        - ✅ 企业级安全
        - ✅ 灵活的认证方式
        - ❌ 需要 AWS 凭证
        - ❌ 需要开通 Bedrock 服务
        - 💰 按使用量计费

    支持的模型:
        Amazon Titan:
        - amazon.titan-embed-text-v2:0 (默认，1024维)
        - amazon.titan-embed-text-v1 (1536维)

        Cohere:
        - cohere.embed-multilingual-v3 (1024维)
        - cohere.embed-english-v3 (1024维)

    Args:
        model: 模型 ID（默认 'amazon.titan-embed-text-v2:0'）
        aws_access_key_id: AWS Access Key（可选，默认从环境变量读取）
        aws_secret_access_key: AWS Secret Key（可选，默认从环境变量读取）
        aws_session_token: AWS Session Token（可选，用于临时凭证）

    Examples:
        >>> # 使用环境变量认证
        >>> # export AWS_ACCESS_KEY_ID='...'
        >>> # export AWS_SECRET_ACCESS_KEY='...'
        >>> emb = BedrockEmbedding(model="amazon.titan-embed-text-v2:0")
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 显式传递凭证
        >>> emb = BedrockEmbedding(
        ...     model="amazon.titan-embed-text-v2:0",
        ...     aws_access_key_id="your-key-id",  # pragma: allowlist secret
        ...     aws_secret_access_key="your-secret-key"  # pragma: allowlist secret
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 使用 Cohere 模型
        >>> emb = BedrockEmbedding(model="cohere.embed-multilingual-v3")
        >>> vec = emb.embed("你好世界")
    """

    # 模型维度映射
    DIMENSION_MAP = {
        "amazon.titan-embed-text-v2:0": 1024,
        "amazon.titan-embed-text-v1": 1536,
        "cohere.embed-multilingual-v3": 1024,
        "cohere.embed-english-v3": 1024,
    }

    def __init__(
        self,
        model: str = "amazon.titan-embed-text-v2:0",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 Bedrock Embedding

        Args:
            model: 模型 ID
            aws_access_key_id: AWS Access Key（可选）
            aws_secret_access_key: AWS Secret Key（可选）
            aws_session_token: AWS Session Token（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            ImportError: 如果未安装 boto3
            RuntimeError: 如果未配置 AWS 凭证
        """
        super().__init__(
            model=model,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            **kwargs,
        )

        # 检查依赖
        try:
            import boto3  # noqa: F401
        except ImportError:
            raise ImportError("Bedrock embedding 需要 boto3 包。\n安装方法: pip install boto3")

        self._model = model
        self._aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self._aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self._aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        self._kwargs = kwargs

        # 检查凭证
        if not (self._aws_access_key_id and self._aws_secret_access_key):
            raise RuntimeError(
                "Bedrock embedding 需要 AWS 凭证。\n"
                "解决方案:\n"
                "  1. 设置环境变量:\n"
                "     export AWS_ACCESS_KEY_ID='your-key-id'\n"  # pragma: allowlist secret
                "     export AWS_SECRET_ACCESS_KEY='your-secret-key'\n"  # pragma: allowlist secret
                "  2. 传递参数:\n"
                "     BedrockEmbedding(\n"
                "         aws_access_key_id='...',\n"  # pragma: allowlist secret
                "         aws_secret_access_key='...'\n"  # pragma: allowlist secret
                "     )\n"
                "  3. 配置 AWS CLI: aws configure\n"
                "\n"
                "获取凭证: https://console.aws.amazon.com/iam/"
            )

        # 获取维度
        self._dim = self.DIMENSION_MAP.get(model, 1024)

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
            import json

            import boto3

            # 设置环境变量（boto3 会自动读取）
            if self._aws_access_key_id:
                os.environ["AWS_ACCESS_KEY_ID"] = self._aws_access_key_id
            if self._aws_secret_access_key:
                os.environ["AWS_SECRET_ACCESS_KEY"] = self._aws_secret_access_key
            if self._aws_session_token:
                os.environ["AWS_SESSION_TOKEN"] = self._aws_session_token

            bedrock_client = boto3.client("bedrock-runtime")
            model_provider = self._model.split(".")[0]

            if model_provider == "amazon":
                if "v2" in self._model:
                    body = json.dumps(
                        {
                            "inputText": text,
                            "embeddingTypes": ["float"],
                        }
                    )
                elif "v1" in self._model:
                    body = json.dumps({"inputText": text})
                else:
                    raise ValueError(f"不支持的模型: {self._model}")

                response = bedrock_client.invoke_model(
                    modelId=self._model,
                    body=body,
                    accept="application/json",
                    contentType="application/json",
                )
                response_body = json.loads(response["body"].read())
                return response_body["embedding"]

            elif model_provider == "cohere":
                body = json.dumps(
                    {
                        "texts": [text],
                        "input_type": "search_document",
                        "truncate": "NONE",
                    }
                )

                response = bedrock_client.invoke_model(
                    modelId=self._model,
                    body=body,
                    accept="application/json",
                    contentType="application/json",
                )
                response_body = json.loads(response["body"].read())
                return response_body["embeddings"][0]

            else:
                raise ValueError(f"不支持的模型提供商: {model_provider}")

        except Exception as e:
            raise RuntimeError(
                f"Bedrock embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 AWS 凭证、区域设置、Bedrock 服务开通状态"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        当前实现为逐个调用 embed()。
        TODO: 如果模型支持批量接口，可以优化。
        Issue URL: https://github.com/intellistream/SAGE/issues/908

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        # TODO: 检查 Bedrock API 是否支持批量
        # Issue URL: https://github.com/intellistream/SAGE/issues/907
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
            'bedrock'
        """
        return "bedrock"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "bedrock",
            "requires_api_key": True,  # AWS 凭证
            "requires_model_download": False,
            "default_dimension": 1024,
            "features": [
                "AWS 托管服务",
                "多种模型选择（Amazon Titan、Cohere）",
                "企业级安全",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return f"BedrockEmbedding(model='{self._model}', dim={self._dim})"
