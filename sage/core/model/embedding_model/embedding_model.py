#sage/core/model/embedding_model/embedding_model.py

import asyncio
import os
import sys
import torch
import hashlib
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

import time
from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from sage.core.model.embedding_model.embedding_methods import hf, ollama, jina, zhipu, nvidia_openai, bedrock, _cohere, openai, \
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
 
        self.dim = None
        if method == "default":
            method = "hf"
            kwargs["model"] = "sentence-transformers/all-MiniLM-L6-v2"
        self.set_dim(kwargs["model"] )
        self.method = method

        # self.kwargs = {}
        self.kwargs = kwargs
        if method == "hf":
            if "model" not in kwargs:
                raise ValueError("hf method need model")
            model_name = kwargs["model"]
            self.kwargs["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
            self.kwargs["embed_model"] = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            self.kwargs.pop("model")
        self.embed_fn = self._get_embed_function(method)

    def set_dim(self,model_name):
        """
        :param model_name:
        :return:
        """
        dimension_mapping = {
            "mistral_embed": 1024,
            "embed-multilingual-v3.0":1024,
            "embed-english-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "embed-multilingual-light-v3.0": 384,
            "embed-english-v2.0": 4096,
            "embed-english-light-v2.0": 1024,
            "embed-multilingual-v2.0": 768,
            "jina-embeddings-v3":1024,
            "BAAI/bge-m3":1024,
            "sentence-transformers/all-MiniLM-L6-v2":384
        }
        if model_name in dimension_mapping:
            self.dim = dimension_mapping[model_name]
        else:
            raise ValueError(f"<UNK> embedding <UNK>{model_name}")

    def get_dim(self):
        return self.dim

    def _get_embed_function(self, method: str):
        """根据方法名返回对应的 embedding 函数"""
        mapping = {
            "openai": openai.openai_embed_sync,
            "zhipu": zhipu.zhipu_embedding_sync,
            "bedrock": bedrock.bedrock_embed_sync,
            "hf": hf.hf_embed_sync,
            "jina": jina.jina_embed_sync,
            # "llama_index_impl": llama_index_impl.llama_index_embed,
            "lollms": lollms.lollms_embed_sync,
            "nvidia_openai": nvidia_openai.nvidia_openai_embed_sync,
            "ollama": ollama.ollama_embed_sync,
            "siliconcloud": siliconcloud.siliconcloud_embedding_sync,
            "cohere": _cohere.cohere_embed_sync,
            # "instructor": instructor.instructor_embed
        }
        if method not in mapping:
            raise ValueError(f"不支持的 embedding 方法：{method}")

        embed_fn = mapping[method]

        return embed_fn

    def _embed(self, text: str) -> list[float]:
        """
        异步执行 embedding 操作
        :param text: 要 embedding 的文本
        :param kwargs: embedding 方法可能需要的额外参数
        :return: embedding 后的结果
        """
        return self.embed_fn(text, **self.kwargs)

    def embed(self, text: str) -> list[float]:
        
        return self._embed(text)
    
    def encode(self, text: str) -> list[float]:
        
        return self._embed(text)

class MockTextEmbedder(EmbeddingModel):
    """
    Mock 嵌入模型，输出固定维度的确定性随机向量。
    继承自 EmbeddingModel，method 固定为 'mock'。
    """
    def __init__(
        self,
        model_name: str = 'mock-model',
        fixed_dim: int = 128
    ):
        # 不调用 EmbeddingModel.__init__ 以避免向上依赖 API
        self.method = 'mock'
        self.fixed_dim = fixed_dim
        # 根据模型名设置固定随机种子
        self.seed = int(hashlib.sha256(model_name.encode()).hexdigest()[:8], 16)

    def embed(self, text: str, max_length: int = 512, stride: Optional[int] = None) -> torch.Tensor:
        """
        生成固定维度的伪嵌入（相同文本输出一致）。
        """
        if not text.strip():
            return torch.zeros(self.fixed_dim)

        text_seed = self.seed + int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        torch.manual_seed(text_seed)

        if stride is None or len(text.split()) <= max_length:
            return self._embed_single()
        return self._embed_with_sliding_window()

    def _embed_single(self) -> torch.Tensor:
        # 直接生成与固定维度一致的随机张量
        return torch.randn(self.fixed_dim)

    def _embed_with_sliding_window(self) -> torch.Tensor:
        # 模拟长文本滑动窗口平均
        parts = [torch.randn(self.fixed_dim) for _ in range(3)]
        return torch.stack(parts).mean(dim=0)

def main():
    embedding_model = EmbeddingModel(method="hf",model = "sentence-transformers/all-MiniLM-L6-v2")
    for i in range(10):
        start = time.time()
        v = embedding_model.embed(f"{i} times ")
        print(v)
        end = time.time()
        print(f"embedding time :{end-start}")
if __name__ =="__main__":
    main()
