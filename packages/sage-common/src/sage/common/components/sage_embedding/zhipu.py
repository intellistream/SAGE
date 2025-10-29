pass


# Dependencies should be installed via requirements.txt
# zhipuai is required for this module

try:
    import zhipuai  # noqa: F401
except ImportError:
    raise ImportError(
        "zhipuai package is required for ZhipuAI embedding functionality. "
        "Please install it via: pip install zhipuai"
    )


async def zhipu_embedding(
    text: str, model: str = "embedding-3", api_key: str | None = None, **kwargs
) -> list:
    """
    Generate embedding for a single text using ZhipuAI.

    Args:
        text: Input string
        model: Embedding model name
        api_key: ZhipuAI API key
        **kwargs: Additional arguments to ZhipuAI client

    Returns:
        list[float]: Embedding vector
    """
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        raise ImportError("Please install zhipuai before using this backend.")

    client = ZhipuAI(api_key=api_key) if api_key else ZhipuAI()

    try:
        response = client.embeddings.create(model=model, input=[text], **kwargs)
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Error calling ChatGLM Embedding API: {str(e)}")


def zhipu_embedding_sync(
    text: str, model: str = "embedding-3", api_key: str | None = None, **kwargs
) -> list[float]:
    """
    同步调用 ZhipuAI 生成 embedding 向量。

    Args:
        text: 输入字符串
        model: 使用的 ZhipuAI 模型名称
        api_key: API 密钥（可选）
        **kwargs: 额外参数

    Returns:
        list[float]: 生成的 embedding 向量
    """
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        raise ImportError("Please install zhipuai before using this backend.")

    client = ZhipuAI(api_key=api_key) if api_key else ZhipuAI()

    try:
        response = client.embeddings.create(model=model, input=[text], **kwargs)
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Error calling ChatGLM Embedding API: {str(e)}")
