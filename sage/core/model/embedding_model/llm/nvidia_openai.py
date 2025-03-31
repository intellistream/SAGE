import asyncio
import sys
import os

if sys.version_info < (3, 9):
    pass
else:
    pass

import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("openai"):
    pm.install("openai")


from openai import AsyncOpenAI

async def nvidia_openai_embed(
    text: str,
    model: str = "nvidia/llama-3.2-nv-embedqa-1b-v1",
    base_url: str = "https://integrate.api.nvidia.com/v1",
    api_key: str = None,
    input_type: str = "passage",  # query for retrieval, passage for embedding
    trunc: str = "NONE",  # NONE or START or END
    encode: str = "float",  # float or base64
) -> list:
    """
    Generate embedding for a single text using NVIDIA NIM-compatible OpenAI API.

    Returns:
        list[float]: The embedding vector.
    """
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    openai_async_client = (
        AsyncOpenAI() if base_url is None else AsyncOpenAI(base_url=base_url)
    )

    response = await openai_async_client.embeddings.create(
        model=model,
        input=text,
        encoding_format=encode,
        extra_body={"input_type": input_type, "truncate": trunc},
    )

    return response.data[0].embedding

# async def main():
#     from dotenv import load_dotenv
#
#     load_dotenv()
#
#     print(await nvidia_openai_embed("123",api_key=os.environ.get('')))
# asyncio.run(main())
