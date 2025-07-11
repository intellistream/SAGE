import sys

if sys.version_info < (3, 9):
    from typing import AsyncIterator
else:
    from collections.abc import AsyncIterator

import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("ollama"):
    pm.install("ollama")
if not pm.is_installed("tenacity"):
    pm.install("tenacity")


import ollama



import numpy as np
from typing import Union




async def ollama_embed(
    text: str,
    embed_model,
    **kwargs
) -> list:
    """
    Generate embedding for a single text using Ollama.

    Args:
        text: A single input string
        embed_model: The name of the Ollama embedding model
        **kwargs: Optional arguments (e.g. base_url, api_key)

    Returns:
        list[float]: The embedding vector
    """
    import ollama

    api_key = kwargs.pop("api_key", None)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SAGE/0.0",
    }
    if api_key:
        headers["Authorization"] = api_key
    kwargs["headers"] = headers

    ollama_client = ollama.Client(**kwargs)
    data = ollama_client.embed(model=embed_model, input=text)
    return data["embedding"]

def ollama_embed_sync(
    text: str,
    embed_model,
    **kwargs
) -> list[float]:
    """
    同步版本：使用 Ollama 客户端生成 embedding 向量。

    Args:
        text: 输入文本
        embed_model: 使用的模型名
        **kwargs: 额外参数（可包含 base_url、api_key）

    Returns:
        list[float]: embedding 向量
    """
    import ollama

    api_key = kwargs.pop("api_key", None)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SAGE/0.0",
    }
    if api_key:
        headers["Authorization"] = api_key
    kwargs["headers"] = headers

    ollama_client = ollama.Client(**kwargs)
    data = ollama_client.embed(model=embed_model, input=text)
    return data["embedding"]
