import asyncio
import os
import sys

if sys.version_info < (3, 9):
    pass
else:
    pass
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("lmdeploy"):
    pm.install("lmdeploy")

from openai import (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import numpy as np
import aiohttp
import base64
import struct


# async def siliconcloud_embedding(
#     texts: list[str],
#     model: str = "netease-youdao/bce-embedding-base_v1",
#     base_url: str = "https://api.siliconflow.cn/v1/embeddings",
#     max_token_size: int = 512,
#     api_key: str = None,
# ) -> np.ndarray:
#     if api_key and not api_key.startswith("Bearer "):
#         api_key = "Bearer " + api_key
#     headers = {"Authorization": api_key, "Content-Type": "application/json"}
#
#     truncate_texts = [text[0:max_token_size] for text in texts]
#
#     payload = {"model": model, "input": truncate_texts, "encoding_format": "base64"}
#
#     base64_strings = []
#     async with aiohttp.ClientSession() as session:
#         async with session.post(base_url, headers=headers, json=payload) as response:
#             content = await response.json()
#             if "code" in content:
#                 raise ValueError(content)
#             base64_strings = [item["embedding"] for item in content["data"]]
#
#     embeddings = []
#     for string in base64_strings:
#         decode_bytes = base64.b64decode(string)
#         n = len(decode_bytes) // 4
#         float_array = struct.unpack("<" + "f" * n, decode_bytes)
#         embeddings.append(float_array)
#     return np.array(embeddings)


async def siliconcloud_embedding(
        text: str,
        model: str = "netease-youdao/bce-embedding-base_v1",
        base_url: str = "https://api.siliconflow.cn/v1/embeddings",
        max_token_size: int = 512,
        api_key: str = None,
) -> list:
    """
    Generate embedding for a single text using SiliconCloud (NetEase Youdao).

    Args:
        text: Input string
        model: Embedding model name
        base_url: API endpoint
        max_token_size: Max text length in tokens (cut if needed)
        api_key: Your SiliconCloud API key

    Returns:
        list[float]: The embedding vector
    """
    if api_key and not api_key.startswith("Bearer "):
        api_key = "Bearer " + api_key

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    text = text[:max_token_size]
    payload = {
        "model": model,
        "input": [text],
        "encoding_format": "base64",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(base_url, headers=headers, json=payload) as response:
            content = await response.json()
            if "code" in content:
                raise ValueError(content)
            base64_string = content["data"][0]["embedding"]

    decode_bytes = base64.b64decode(base64_string)
    n = len(decode_bytes) // 4
    float_array = struct.unpack("<" + "f" * n, decode_bytes)
    return list(float_array)

async def main():
    from dotenv import load_dotenv

    load_dotenv()

    print(await siliconcloud_embedding("123",api_key=os.environ.get('SILICONCLOUD_API_KEY')))
asyncio.run(main())
