import os

# flake8: noqa: E402
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from functools import lru_cache

# 延迟导入：transformers, torch, tenacity, numpy 等重量级依赖
# 只在实际调用函数时才导入，避免在模块加载时就加载这些库

os.environ["TOKENIZERS_PARALLELISM"] = "false"


@lru_cache(maxsize=1)
def initialize_hf_model(model_name):
    """初始化 HuggingFace 模型（延迟导入依赖）"""
    # 延迟导入 transformers
    try:
        from transformers import (
            AutoModel,  # noqa: F401
            AutoModelForCausalLM,
            AutoTokenizer,
        )
    except ImportError as e:
        raise ImportError(
            "transformers package is required for HuggingFace embedding functionality. "
            "Please install it via: pip install transformers"
        ) from e

    hf_tokenizer = AutoTokenizer.from_pretrained(
        model_name, device_map="auto", trust_remote_code=True
    )
    hf_model = AutoModelForCausalLM.from_pretrained(
        model_name, device_map="auto", trust_remote_code=True
    )
    if hf_tokenizer.pad_token is None:
        hf_tokenizer.pad_token = hf_tokenizer.eos_token

    return hf_model, hf_tokenizer


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
    # 延迟导入 torch
    try:
        import torch
    except ImportError as e:
        raise ImportError(
            "torch package is required for HuggingFace embedding functionality. "
            "Please install it via: pip install torch"
        ) from e

    device = next(embed_model.parameters()).device
    encoded_texts = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(device)

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


def hf_embed_batch_sync(texts: list[str], tokenizer, embed_model) -> list[list[float]]:
    """
    使用 HuggingFace 模型同步批量生成文本 embedding。

    通过一次前向传播处理多个文本，相比逐个处理显著提高效率。

    Args:
        texts (list[str]): 输入文本列表
        tokenizer: 已加载的 tokenizer
        embed_model: 已加载的 PyTorch embedding 模型

    Returns:
        list[list[float]]: embedding 向量列表
    """
    # 延迟导入 torch
    try:
        import torch
    except ImportError as e:
        raise ImportError(
            "torch package is required for HuggingFace embedding functionality. "
            "Please install it via: pip install torch"
        ) from e

    device = next(embed_model.parameters()).device
    # 批量编码所有文本，tokenizer会自动处理padding
    encoded_texts = tokenizer(texts, return_tensors="pt", padding=True, truncation=True).to(device)

    with torch.no_grad():
        outputs = embed_model(
            input_ids=encoded_texts["input_ids"],
            attention_mask=encoded_texts["attention_mask"],
        )
        # 对每个文本，取其所有token的平均值作为句子embedding
        embeddings = outputs.last_hidden_state.mean(dim=1)

    # 转换为float32并返回CPU上的列表
    if embeddings.dtype == torch.bfloat16:
        return embeddings.detach().to(torch.float32).cpu().tolist()
    else:
        return embeddings.detach().cpu().tolist()
