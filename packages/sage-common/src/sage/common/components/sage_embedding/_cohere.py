import os

import cohere


async def cohere_embed(
    texts: list[str],
    api_key: str,
    model: str = "embed-multilingual-v3.0",
    input_type: str = "classification",
    embedding_types: list[str] | None = None,
) -> list[list[float]]:
    if embedding_types is None:
        embedding_types = ["float"]
    if api_key is None:
        api_key = os.environ.get("COHERE_API_KEY")
    # print(api_key)
    co = cohere.AsyncClient(api_key=api_key)

    response = await co.embed(
        texts=texts,
        model=model,
        input_type=input_type,
        # embedding_types=embedding_types
    )
    return response.embeddings  # pyright: ignore[reportReturnType]


def cohere_embed_sync(
    texts: list[str],
    api_key: str | None = None,
    model: str = "embed-multilingual-v3.0",
    input_type: str = "classification",
    embedding_types: list[str] | None = None,
) -> list[list[float]]:
    """
    同步版本：使用 Cohere 同步客户端生成文本 embeddings.

    Args:
        texts: 文本列表
        api_key: Cohere API Key
        model: 模型名称
        input_type: 输入类型，如 classification、search_document 等
        embedding_types: 嵌入格式（默认 float）

    Returns:
        list[list[float]]: 每个文本对应的嵌入向量
    """
    if embedding_types is None:
        embedding_types = ["float"]
    if api_key is None:
        api_key = os.environ.get("COHERE_API_KEY")
    if api_key is None:
        raise ValueError("Cohere API key must be provided.")

    co = cohere.Client(api_key=api_key)

    response = co.embed(
        texts=texts,
        model=model,
        input_type=input_type,
        embedding_types=embedding_types,
    )
    return response.embeddings  # pyright: ignore[reportReturnType]
