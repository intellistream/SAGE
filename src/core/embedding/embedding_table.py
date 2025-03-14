import asyncio
import os
from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv
load_dotenv()

from src.core.embedding.llm import hf, ollama, jina, zhipu, llama_index_impl, nvidia_openai, bedrock, cohere, openai, \
    siliconcloud, lollms, instructor
from transformers import AutoModel, AutoTokenizer


@dataclass
class EmbeddingFunc:
    embedding_dim: int
    max_token_size: int
    func: callable

    # concurrent_limit: int = 16

    async def __call__(self, *args, **kwargs) -> np.ndarray:
        return await self.func(*args, **kwargs)


class EmbeddingTable:
    def __init__(self, method: str = "openai"):
        """
        初始化 embedding table
        :param method: 指定使用的 embedding 方法名称，例如 "openai" 或 "zhipu"
        """
        self.method = method
        self.embed_fn = self._get_embed_function(method)

    def _get_embed_function(self, method: str):
        """根据方法名返回对应的 embedding 函数"""
        mapping = {
            "openai": openai.openai_embed,
            "zhipu": zhipu.zhipu_embedding,
            "bedrock": bedrock.bedrock_embed,
            "hf": hf.hf_embed,
            "jina": jina.jina_embed,
            "llama_index_impl": llama_index_impl.llama_index_embed,
            "lollms": lollms.lollms_embed,
            "nvidia_openai": nvidia_openai.nvidia_openai_embed,
            "ollama": ollama.ollama_embed,
            "siliconcloud": siliconcloud.siliconcloud_embedding,
            "cohere": cohere.cohere_embed,
            "instructor": instructor.instructor_embed
        }
        if method not in mapping:
            raise ValueError(f"不支持的 embedding 方法：{method}")

        embed_fn = mapping[method]

        return embed_fn

    async def embed(self, texts: [str], **kwargs):
        """
        异步执行 embedding 操作
        :param text: 要 embedding 的文本
        :param kwargs: embedding 方法可能需要的额外参数
        :return: embedding 后的结果
        """
        return await self.embed_fn(texts, **kwargs)  # 确保异步调用


async def embedding(method, **kwargs):
    """
    异步执行 embedding 操作
    :param text: 要 embedding 的文本
    :param kwargs: embedding 方法可能需要的额外参数
    :return: embedding 后的结果
    """
    return EmbeddingFunc(
        embedding_dim=768,
        max_token_size=5120,
        func=lambda texts: EmbeddingTable(method).embed(texts, **kwargs)
    )


async def main():

    #huggingface example
    #huggingface  model = {"sentence-transformers/all-MiniLM-L6-v2","BAAI/bge-m3", "naver/splade-v3","bert-base-uncased"，“Alibaba-NLP/gte-multilingual-base”，"nomic-ai/nomic-embed-text-v2-moe","nomic-ai/nomic-embed-text-v1"}
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name,trust_remote_code=True)
    model.eval()
    embedding_func = await embedding("hf", tokenizer=tokenizer, embed_model=model)
    texts = [["hello world", "hello "], ["apple", "red aplle"]]
    for t in texts:
        print(await embedding_func(t))

    #mistralai example
    api_key = os.environ.get("MISTRAL_API_KEY")
    # print(api_key)
    embedding_func2 = await embedding("openai",model="mistral-embed",base_url="https://api.mistral.ai/v1",api_key=api_key)
    for t in texts:
        print(await embedding_func2(t))

    #cohere example
    api_key = os.environ.get("COHERE_API_KEY")
    embedding_func3 = await embedding("cohere",model="embed-multilingual-v3.0",api_key=api_key)
    for t in texts:
        v = await embedding_func3(t)
        print(v)
        print(v.shape)

    #instructor example
    embedding_func4 = await embedding("instructor",model="hkunlp/instructor-large")
    for t in texts:
        v = await embedding_func4(t)
        print(v)
        print(v.shape)


if __name__ == "__main__":
    asyncio.run(main())
