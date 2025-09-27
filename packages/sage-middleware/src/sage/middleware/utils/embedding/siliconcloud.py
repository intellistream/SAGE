import asyncio
import os
import sys

if sys.version_info < (3, 9):
    pass
else:
    pass
import base64
import struct

import aiohttp
import numpy as np
from openai import APIConnectionError, APITimeoutError, RateLimitError
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)


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


import base64
import struct

import requests


def siliconcloud_embedding_sync(
    text: str,
    model: str = "netease-youdao/bce-embedding-base_v1",
    base_url: str = "https://api.siliconflow.cn/v1/embeddings",
    max_token_size: int = 512,
    api_key: str = None,
) -> list[float]:
    """
    同步版本：使用 SiliconCloud (NetEase Youdao) 接口获取文本 embedding。

    Args:
        text: 输入文本
        model: 模型名称
        base_url: 接口地址
        max_token_size: 截断长度（按字符）
        api_key: API 密钥（可选，带或不带 "Bearer "）

    Returns:
        list[float]: embedding 向量
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

    try:
        response = requests.post(base_url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()

        if "code" in content:
            raise ValueError(f"SiliconCloud API error: {content}")

        base64_string = content["data"][0]["embedding"]
        decode_bytes = base64.b64decode(base64_string)
        n = len(decode_bytes) // 4
        float_array = struct.unpack("<" + "f" * n, decode_bytes)
        return list(float_array)

    except Exception as e:
        raise RuntimeError(f"SiliconCloud embedding failed: {str(e)}")
