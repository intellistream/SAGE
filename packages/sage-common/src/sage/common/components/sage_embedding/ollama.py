pass


# Dependencies should be installed via requirements.txt
# ollama and tenacity are required for this module to work

try:
    import ollama  # noqa: F401
except ImportError:
    raise ImportError(
        "ollama package is required for Ollama embedding functionality. "
        "Please install it via: pip install ollama"
    )

try:
    import tenacity  # noqa: F401
except ImportError:
    raise ImportError(
        "tenacity package is required for Ollama embedding functionality. "
        "Please install it via: pip install tenacity"
    )


async def ollama_embed(text: str, embed_model, **kwargs) -> list:
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


def ollama_embed_sync(text: str, embed_model, **kwargs) -> list[float]:
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
