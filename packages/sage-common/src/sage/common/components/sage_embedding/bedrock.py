import json
import os

import boto3

# Dependencies are managed via pyproject.toml [project.optional-dependencies.embedding]
# Install with: pip install isage-common[embedding]
# Required: aioboto3, boto3, tenacity

try:
    import aioboto3
except ImportError:
    raise ImportError(
        "aioboto3 package is required for AWS Bedrock embedding functionality. "
        "Please install it via: pip install isage-common[embedding]"
    )

try:
    from tenacity import (
        retry,  # noqa: F401
        retry_if_exception_type,  # noqa: F401
        stop_after_attempt,  # noqa: F401
        wait_exponential,  # noqa: F401
    )
except ImportError:
    raise ImportError(
        "tenacity package is required for AWS Bedrock embedding functionality. "
        "Please install it via: pip install isage-common[embedding]"
    )


class BedrockError(Exception):
    """Generic error for issues related to Amazon Bedrock"""


async def bedrock_embed(
    text: str,
    model: str = "amazon.titan-embed-text-v2:0",
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
) -> list:
    # 只在提供了值时才设置环境变量
    if aws_access_key_id is not None:
        os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    if aws_secret_access_key is not None:
        os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    if aws_session_token is not None:
        os.environ["AWS_SESSION_TOKEN"] = aws_session_token

    session = aioboto3.Session()
    async with session.client("bedrock-runtime") as bedrock_async_client:  # type: ignore[attr-defined]
        model_provider = model.split(".")[0]

        if model_provider == "amazon":
            if "v2" in model:
                body = json.dumps(
                    {
                        "inputText": text,
                        "embeddingTypes": ["float"],
                    }
                )
            elif "v1" in model:
                body = json.dumps({"inputText": text})
            else:
                raise ValueError(f"Model {model} is not supported!")

            response = await bedrock_async_client.invoke_model(
                modelId=model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )

            response_body = await response.get("body").json()
            return response_body["embedding"]

        elif model_provider == "cohere":
            body = json.dumps(
                {
                    "texts": [text],
                    "input_type": "search_document",
                    "truncate": "NONE",
                }
            )

            response = await bedrock_async_client.invoke_model(
                model=model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response.get("body").read())
            return response_body["embeddings"][0]

        else:
            raise ValueError(f"Model provider '{model_provider}' is not supported!")


def bedrock_embed_sync(
    text: str,
    model: str = "amazon.titan-embed-text-v2:0",
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
) -> list[float]:
    """
    同步版本：使用 AWS Bedrock 生成 embedding。

    Args:
        text: 输入文本
        model: 模型 ID，例如 "amazon.titan-embed-text-v2:0"
        aws_access_key_id / secret / session_token: 可选 AWS 认证信息

    Returns:
        list[float]: embedding 向量
    """
    # 设置 AWS 环境变量（优先从参数取）
    if aws_access_key_id:
        os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    if aws_secret_access_key:
        os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    if aws_session_token:
        os.environ["AWS_SESSION_TOKEN"] = aws_session_token

    bedrock_client = boto3.client("bedrock-runtime")

    model_provider = model.split(".")[0]

    if model_provider == "amazon":
        if "v2" in model:
            body = json.dumps(
                {
                    "inputText": text,
                    "embeddingTypes": ["float"],
                }
            )
        elif "v1" in model:
            body = json.dumps({"inputText": text})
        else:
            raise ValueError(f"Model {model} is not supported!")

        response = bedrock_client.invoke_model(
            modelId=model,
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
            modelId=model,
            body=body,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response["body"].read())
        return response_body["embeddings"][0]

    else:
        raise ValueError(f"Model provider '{model_provider}' is not supported!")
