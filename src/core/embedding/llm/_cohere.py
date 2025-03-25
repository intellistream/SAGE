import os
import cohere
import asyncio

import numpy as np


async def cohere_embed(
        texts: [str], api_key: str, model: str = "embed-multilingual-v3.0", input_type: str = "classification",
        embedding_types: [str] = ["float"]
) -> np.ndarray:
    if api_key is None:
        api_key = os.environ.get("COHERE_API_KEY")
    # print(api_key)
    co = cohere.AsyncClient(api_key=api_key)

    response = await co.embed(
        texts=texts,
        model=model,
        input_type=input_type,
        # embedding_types=embedding_types
    )
    return np.array(response.embeddings)


# async def main():
#     from dotenv import load_dotenv
#
#     load_dotenv()
#     print(await cohere_embed(["123"], api_key=os.environ.get("COHERE_API_KEY")))
#
#
# asyncio.run(main())




