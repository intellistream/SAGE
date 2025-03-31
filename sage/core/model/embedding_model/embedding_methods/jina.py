import asyncio
import os
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("lmdeploy"):
    pm.install("lmdeploy")
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

# async def main():
#     from dotenv import load_dotenv
#
#     load_dotenv()
#
#     print(await jina_embed("123",api_key=os.environ.get('JINA_API_KEY')))
# asyncio.run(main())



