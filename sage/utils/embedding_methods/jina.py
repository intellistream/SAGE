import asyncio
import os
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("tenacity"):
    pm.install("tenacity")


import numpy as np
import aiohttp


async def fetch_data(url, headers, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            response_json = await response.json()
            data_list = response_json.get("data", [])
            return data_list


async def jina_embed(
    text: str,
    dimensions: int = 1024,
    late_chunking: bool = False,
    base_url: str = None,
    api_key: str = None,
    model:str="jina-embeddings-v3"
) -> list[float]:
    if api_key:
        os.environ["JINA_API_KEY"] = api_key
    url = "https://api.jina.ai/v1/embeddings" if not base_url else base_url
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['JINA_API_KEY']}",
    }
    data = {
        "model": f"{model}",
        "normalized": True,
        "embedding_type": "float",
        "dimensions": f"{dimensions}",
        "late_chunking": late_chunking,
        "input": text,
    }
    data_list = await fetch_data(url, headers, data)
    print(data_list)
    return data_list[0]['embedding']

import os
import requests

def jina_embed_sync(
    text: str,
    dimensions: int = 1024,
    late_chunking: bool = False,
    base_url: str = None,
    api_key: str = None,
    model: str = "jina-embeddings-v3"
) -> list[float]:
    """
    同步版本：调用 Jina AI embedding API 获取嵌入向量

    Args:
        text: 待嵌入的文本
        dimensions: 嵌入维度
        late_chunking: 是否开启 late chunking
        base_url: 自定义 API 地址（可选）
        api_key: Jina API 密钥
        model: 使用的模型名

    Returns:
        list[float]: 嵌入向量
    """
    if api_key:
        os.environ["JINA_API_KEY"] = api_key

    url = base_url or "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['JINA_API_KEY']}",
    }
    payload = {
        "model": model,
        "normalized": True,
        "embedding_type": "float",
        "dimensions": dimensions,
        "late_chunking": late_chunking,
        "input": text,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except Exception as e:
        raise RuntimeError(f"Jina API call failed: {str(e)}")





