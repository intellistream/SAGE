import asyncio
import sys
import os
import logging



if sys.version_info < (3, 9):
    from typing import AsyncIterator
else:
    from collections.abc import AsyncIterator
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("openai"):
    pm.install("openai")


from openai import AsyncOpenAI  # 确保导入了这个

async def openai_embed(
    text: str,
    model: str = "text-embedding-3-small",
    base_url: str = None,
    api_key: str = None,
) -> list:
    """
    Generate embedding for a single text using OpenAI Embedding API.

    Args:
        text: Input string
        model: OpenAI embedding model name
        base_url: Optional custom endpoint
        api_key: OpenAI API key

    Returns:
        list[float]: The embedding vector
    """
    if not api_key:
        api_key = os.environ["OPENAI_API_KEY"]

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) SAGE/0.0",
        "Content-Type": "application/json",
    }

    openai_async_client = (
        AsyncOpenAI(default_headers=default_headers, api_key=api_key)
        if base_url is None
        else AsyncOpenAI(
            base_url=base_url, default_headers=default_headers, api_key=api_key
        )
    )

    response = await openai_async_client.embeddings.create(
        model=model,
        input=text,
        encoding_format="float"
    )

    return response.data[0].embedding


# async def main():
#     from dotenv import load_dotenv
#
#     load_dotenv()
#
#     print(await openai_embed("123",base_url="https://api.siliconflow.cn/v1",model="BAAI/bge-m3",api_key=os.environ.get('SILICONCLOUD_API_KEY')))
# asyncio.run(main())