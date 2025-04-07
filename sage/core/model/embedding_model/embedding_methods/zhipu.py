import sys
import re
import json


if sys.version_info < (3, 9):
    pass
else:
    pass
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("zhipuai"):
    pm.install("zhipuai")


async def zhipu_embedding(
    text: str,
    model: str = "embedding-3",
    api_key: str = None,
    **kwargs
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
