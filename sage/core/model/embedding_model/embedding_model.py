# sage/core/model/embedding_model/embedding_model.py

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

import time
import hashlib
from typing import Optional

import torch
import numpy as np
from dotenv import load_dotenv
from transformers import AutoModel, AutoTokenizer

load_dotenv()

from sage.core.model.embedding_model.embedding_methods import (
    hf, ollama, jina, zhipu, nvidia_openai, bedrock,
    _cohere, openai, siliconcloud, lollms
)


class _MockTextEmbedderImpl:
    """内部用的 Mock 嵌入实现，生成确定性随机向量"""
    def __init__(self, fixed_dim: int = 128):
        self.fixed_dim = fixed_dim
        self.seed = int(hashlib.sha256(b"mock-model").hexdigest()[:8], 16)

    def encode(self, text: str, max_length: int = 512, stride: Optional[int] = None) -> torch.Tensor:
        """生成固定维度的伪嵌入（相同文本输出相同）"""
        if not text.strip():
            return torch.zeros(self.fixed_dim)

        text_seed = self.seed + int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        torch.manual_seed(text_seed)

        # 生成随机向量（与原有代码维度逻辑一致）
        if stride is None or len(text.split()) <= max_length:
            return self._embed_single()
        else:
            return self._embed_with_sliding_window()

    def _embed_single(self) -> torch.Tensor:
        """模拟单文本嵌入"""
        embedding = torch.randn(384)
        return self._adjust_dimension(embedding)

    def _embed_with_sliding_window(self) -> torch.Tensor:
        """模拟长文本滑动窗口嵌入"""
        embeddings = torch.stack([torch.randn(384) for _ in range(3)])
        return self._adjust_dimension(embeddings.mean(dim=0))

    def _adjust_dimension(self, embedding: torch.Tensor) -> torch.Tensor:
        """保持与原代码一致的维度调整逻辑"""
        if embedding.size(0) > self.fixed_dim:
            return embedding[:self.fixed_dim]
        elif embedding.size(0) < self.fixed_dim:
            padding = torch.zeros(self.fixed_dim - embedding.size(0))
            return torch.cat((embedding, padding))
        return embedding


class EmbeddingModel:
    # def __init__(self, method: str = "openai", model: str = "mistral-embed",
    #              base_url: str = None, api_key: str = None):
    def __init__(self, method: str = "openai", **kwargs):
        """
        初始化 embedding table
        :param method: 指定使用的 embedding 方法名称，例如 "openai" 或 "cohere" 或“hf"等
        """
        self.dim = None

        if method == "mock":
            fixed_dim = kwargs.get("fixed_dim", 128)
            self.dim = fixed_dim
            self._mock_impl = _MockTextEmbedderImpl(fixed_dim=fixed_dim)
            # 在 mock 模式下也要初始化 kwargs，避免后续调用失败
            self.kwargs = {}
            # embed_fn 接口统一返回 list[float]
            self.embed_fn = lambda text, **_: self._mock_impl.encode(text).tolist()
            return

        if method == "default":
            method = "hf"
            kwargs["model"] = "sentence-transformers/all-MiniLM-L6-v2"

        self.set_dim(kwargs["model"])
        self.method = method
        self.kwargs = kwargs

        if method == "hf":
            if "model" not in kwargs:
                raise ValueError("hf method need model")
            model_name = kwargs["model"]
            self.kwargs["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
            self.kwargs["embed_model"] = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            self.kwargs.pop("model")

        # 保留原有的 embed_fn 赋值方式
        self.embed_fn = self._get_embed_function(method)

    def set_dim(self, model_name: str):
        """
        :param model_name:
        :return:
        """
        dimension_mapping = {
            "mistral_embed": 1024,
            "embed-multilingual-v3.0": 1024,
            "embed-english-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "embed-multilingual-light-v3.0": 384,
            "embed-english-v2.0": 4096,
            "embed-english-light-v2.0": 1024,
            "embed-multilingual-v2.0": 768,
            "jina-embeddings-v3": 1024,
            "BAAI/bge-m3": 1024,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
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
    直接继承 EmbeddingModel 的 mock 分支，
    构造时只需传 fixed_dim
    """
    def __init__(self, fixed_dim: int = 128):
        super().__init__(method="mock", fixed_dim=fixed_dim)
