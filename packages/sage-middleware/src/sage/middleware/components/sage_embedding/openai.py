import os
import sys

if sys.version_info < (3, 9):
    pass
else:
    pass


# Dependencies should be installed via requirements.txt
# openai is required for this module

try:
    from openai import AsyncOpenAI, OpenAI  # 确保导入了这个
    from openai.types import CreateEmbeddingResponse
except ImportError:
    raise ImportError(
        "openai package is required for OpenAI embedding functionality. "
        "Please install it via: pip install openai"
    )


async def openai_embed(
    text: str,
    model: str = "text-embedding-3-small",
    base_url: str = None,
    api_key: str = None,
) -> list:
    """
    Generate embedding for a single text using OpenAI Embedding API.

    Args:
        text: Input string
        model: OpenAI embedding model name
        base_url: Optional custom endpoint
        api_key: OpenAI API key

    Returns:
        list[float]: The embedding vector
    """
    if not api_key:
        api_key = os.environ["OPENAI_API_KEY"]

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) SAGE/0.0",
        "Content-Type": "application/json",
    }

    openai_async_client = (
        AsyncOpenAI(default_headers=default_headers, api_key=api_key)
        if base_url is None
        else AsyncOpenAI(
            base_url=base_url, default_headers=default_headers, api_key=api_key
        )
    )

    response = await openai_async_client.embeddings.create(
        model=model, input=text, encoding_format="float"
    )

    return response.data[0].embedding


def openai_embed_sync(
    text: str,
    model: str = "text-embedding-3-small",
    base_url: str = None,
    api_key: str = None,
) -> list[float]:
    """
    同步生成 OpenAI embedding。

    Args:
        text: 输入文本
        model: OpenAI embedding 模型名
        base_url: 可选自定义 API endpoint
        api_key: OpenAI API 密钥

    Returns:
        list[float]: embedding 向量
    """
    if not api_key:
        api_key = os.environ["OPENAI_API_KEY"]

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) SAGE/0.0",
        "Content-Type": "application/json",
    }

    openai_sync_client = (
        OpenAI(default_headers=default_headers, api_key=api_key)
        if base_url is None
        else OpenAI(base_url=base_url, default_headers=default_headers, api_key=api_key)
    )

    response: CreateEmbeddingResponse = openai_sync_client.embeddings.create(
        model=model, input=text, encoding_format="float"
    )

    return response.data[0].embedding
