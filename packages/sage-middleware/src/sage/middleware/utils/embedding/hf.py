import asyncio
import copy
import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import asyncio
from functools import lru_cache

import pipmaster as pm  # Pipmaster for dynamic library install

# Dependencies should be installed via requirements.txt
# transformers, torch, tenacity, and numpy are required for this module

try:
    from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
except ImportError:
    raise ImportError(
        "transformers package is required for HuggingFace embedding functionality. "
        "Please install it via: pip install transformers"
    )

try:
    import torch
except ImportError:
    raise ImportError(
        "torch package is required for HuggingFace embedding functionality. "
        "Please install it via: pip install torch"
    )

try:
    import tenacity
except ImportError:
    raise ImportError(
        "tenacity package is required for HuggingFace embedding functionality. "
        "Please install it via: pip install tenacity"
    )

try:
    import numpy
except ImportError:
    raise ImportError(
        "numpy package is required for HuggingFace embedding functionality. "
        "Please install it via: pip install numpy"
    )

os.environ["TOKENIZERS_PARALLELISM"] = "false"


@lru_cache(maxsize=1)
def initialize_hf_model(model_name):
    hf_tokenizer = AutoTokenizer.from_pretrained(
        model_name, device_map="auto", trust_remote_code=True
    )
    hf_model = AutoModelForCausalLM.from_pretrained(
        model_name, device_map="auto", trust_remote_code=True
    )
    if hf_tokenizer.pad_token is None:
        hf_tokenizer.pad_token = hf_tokenizer.eos_token

    return hf_model, hf_tokenizer


import torch


def hf_embed_sync(text: str, tokenizer, embed_model) -> list[float]:
    """
    使用 HuggingFace 模型同步生成文本 embedding。

    Args:
        text (str): 输入文本
        tokenizer: 已加载的 tokenizer
        embed_model: 已加载的 PyTorch embedding 模型

    Returns:
        list[float]: embedding 向量
    """
    device = next(embed_model.parameters()).device
    encoded_texts = tokenizer(
        text, return_tensors="pt", padding=True, truncation=True
    ).to(device)

    with torch.no_grad():
        outputs = embed_model(
            input_ids=encoded_texts["input_ids"],
            attention_mask=encoded_texts["attention_mask"],
        )
        embeddings = outputs.last_hidden_state.mean(dim=1)

    if embeddings.dtype == torch.bfloat16:
        return embeddings.detach().to(torch.float32).cpu()[0].tolist()
    else:
        return embeddings.detach().cpu()[0].tolist()
