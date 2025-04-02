
from src.core.embedding import embedding_modelpython -m src.core.embedding.embedding_model
async def _test():
    # huggingface example
    embedding_model = EmbeddingModel("hf", model_name="sentence-transformers/all-MiniLM-L6-v2")
    print(await embedding_model.embed(["123"]))

    # mistralai example "mistral-embed"
    embedding_model2 = EmbeddingModel("openai", model="mistral-embed", base_url="https://api.mistral.ai/v1",
                                      api_key=os.environ.get("MISTRAL_API_KEY"))
    print(await embedding_model2.embed(["123"]))

    # cohere example
    print(os.environ.get("COHERE_API_KEY"))
    embedding_model3 = EmbeddingModel("cohere", model="embed-multilingual-v3.0",
                                      api_key=os.environ.get("COHERE_API_KEY"))
    print(await embedding_model3.embed(["123"]))

    # jina example
    embedding_model4 = EmbeddingModel("jina", api_key=os.environ.get('JINA_API_KEY'))
    print(await embedding_model4.embed(["123"]))

    # siliconcloud example
    api_key = os.environ.get("SILICONCLOUD_API_KEY")
    # print(api_key)
    embedding_model5 = EmbeddingModel("openai", model="BAAI/bge-m3", base_url="https://api.siliconflow.cn/v1",
                                      api_key=api_key)
    print(await embedding_model5.embed(["123"]))


if __name__ == "__main__":
    asyncio.run(_test())