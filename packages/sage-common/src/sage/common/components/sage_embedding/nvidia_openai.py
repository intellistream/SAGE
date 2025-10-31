import os

pass


# Dependencies should be installed via requirements.txt
# openai is required for this module

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    raise ImportError(
        "openai package is required for NVIDIA OpenAI embedding functionality. "
        "Please install it via: pip install openai"
    )


async def nvidia_openai_embed(
    text: str,
    model: str = "nvidia/llama-3.2-nv-embedqa-1b-v1",
    base_url: str = "https://integrate.api.nvidia.com/v1",
    api_key: str | None = None,
    input_type: str = "passage",  # query for retrieval, passage for embedding
    trunc: str = "NONE",  # NONE or START or END
    encode: str = "float",  # float or base64
) -> list[float]:
    """
    Generate embedding for a single text using NVIDIA NIM-compatible OpenAI API.

    Returns:
        list[float]: The embedding vector.
    """
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    openai_async_client = AsyncOpenAI() if base_url is None else AsyncOpenAI(base_url=base_url)

    response = await openai_async_client.embeddings.create(
        model=model,
        input=text,
        encoding_format=encode,  # pyright: ignore[reportArgumentType]
        extra_body={"input_type": input_type, "truncate": trunc},
    )

    return response.data[0].embedding


def nvidia_openai_embed_sync(
    text: str,
    model: str = "nvidia/llama-3.2-nv-embedqa-1b-v1",
    base_url: str = "https://integrate.api.nvidia.com/v1",
    api_key: str | None = None,
    input_type: str = "passage",  # query for retrieval, passage for embedding
    trunc: str = "NONE",  # NONE or START or END
    encode: str = "float",  # float or base64
) -> list[float]:
    """
    同步版本：使用 NVIDIA NIM 接口生成文本 embedding。

    Args:
        text: 输入文本
        model: 使用的模型 ID
        base_url: 接口地址（默认为 NVIDIA 接口）
        api_key: API 密钥（使用 OPENAI_API_KEY 环境变量）
        input_type: 输入类型（passage / query）
        trunc: 截断策略
        encode: 返回格式（float / base64）

    Returns:
        list[float]: 嵌入向量
    """
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    client = OpenAI(base_url=base_url)

    response = client.embeddings.create(
        model=model,
        input=text,
        encoding_format=encode,  # pyright: ignore[reportArgumentType]
        extra_body={"input_type": input_type, "truncate": trunc},
    )

    return response.data[0].embedding
