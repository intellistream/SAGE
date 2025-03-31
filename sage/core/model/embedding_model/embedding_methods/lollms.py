import sys

if sys.version_info < (3, 9):
    from typing import AsyncIterator
else:
    from collections.abc import AsyncIterator
import pipmaster as pm  # Pipmaster for dynamic library install

if not pm.is_installed("aiohttp"):
    pm.install("aiohttp")
if not pm.is_installed("tenacity"):
    pm.install("tenacity")



async def lollms_embed(
    text: str,
    embed_model=None,
    base_url="http://localhost:9600",
    **kwargs,
) -> list:
    """
    Generate embedding for a single text using lollms server.

    Args:
        text: The string to embed
        embed_model: Model name (not used directly as lollms uses configured vectorizer)
        base_url: URL of the lollms server
        **kwargs: Additional arguments passed to the request

    Returns:
        list[float]: The embedding vector
    """
    api_key = kwargs.pop("api_key", None)
    headers = (
        {"Content-Type": "application/json", "Authorization": api_key}
        if api_key
        else {"Content-Type": "application/json"}
    )

    async with aiohttp.ClientSession(headers=headers) as session:
        request_data = {"text": text}

        async with session.post(
            f"{base_url}/lollms_embed",
            json=request_data,
        ) as response:
            result = await response.json()
            return result["vector"]
