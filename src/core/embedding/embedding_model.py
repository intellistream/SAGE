import asyncio
import os
from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from src.core.embedding.llm import hf, ollama, jina, zhipu, nvidia_openai, bedrock, _cohere, openai, \
    siliconcloud, lollms  # , instructor
from transformers import AutoModel, AutoTokenizer





class EmbeddingModel:
    # def __init__(self, method: str = "openai", model: str = "mistral-embed",
    #              base_url: str = None, api_key: str = None):
    def __init__(self, method: str = "openai", **kwargs):
        """
        初始化 embedding table
        :param method: 指定使用的 embedding 方法名称，例如 "openai" 或 "cohere" 或“hf"等
        """
        self.method = method
        self.embed_fn = self._get_embed_function(method)
        # self.kwargs = {}
        self.kwargs = kwargs
        if method == "hf":
            if "model_name" not in kwargs:
                raise ValueError("hf method need model_name")
            model_name = kwargs["model_name"]
            self.kwargs["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
            self.kwargs["embed_model"] = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            self.kwargs.pop("model_name")


    def _get_embed_function(self, method: str):
        """根据方法名返回对应的 embedding 函数"""
        mapping = {
            "openai": openai.openai_embed,
            "zhipu": zhipu.zhipu_embedding,
            "bedrock": bedrock.bedrock_embed,
            "hf": hf.hf_embed,
            "jina": jina.jina_embed,
            # "llama_index_impl": llama_index_impl.llama_index_embed,
            "lollms": lollms.lollms_embed,
            "nvidia_openai": nvidia_openai.nvidia_openai_embed,
            "ollama": ollama.ollama_embed,
            "siliconcloud": siliconcloud.siliconcloud_embedding,
            "cohere": cohere.cohere_embed,
            # "instructor": instructor.instructor_embed
        }
        if method not in mapping:
            raise ValueError(f"不支持的 embedding 方法：{method}")

        embed_fn = mapping[method]

        return embed_fn

    async def embed(self, texts: [str], **kwargs):
        """
        异步执行 embedding 操作
        :param texts: 要 embedding 的文本列表
        :param kwargs: embedding 方法可能需要的额外参数
        :return: embedding 后的结果
        """
        return await self.embed_fn(texts, **self.kwargs)  # 确保异步调用







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
