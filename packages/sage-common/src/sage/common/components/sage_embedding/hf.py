import os

# flake8: noqa: E402
# Auto-detect network region and configure HuggingFace mirror
from sage.common.config import ensure_hf_mirror_configured

ensure_hf_mirror_configured()

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

    使用 masked mean pooling 确保只对有效 token 取平均。

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
        # 使用 masked mean pooling：只对非 padding token 取平均
        last_hidden_state = outputs.last_hidden_state  # (1, seq_len, hidden_dim)
        attention_mask = encoded_texts["attention_mask"]  # (1, seq_len)

        # 扩展 attention_mask 到 hidden_dim 维度
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()

        # 对有效 token 求和然后取平均
        sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        embeddings = sum_embeddings / sum_mask

    if embeddings.dtype == torch.bfloat16:
        return embeddings.detach().to(torch.float32).cpu()[0].tolist()
    else:
        return embeddings.detach().cpu()[0].tolist()


def hf_embed_batch_sync(texts: list[str], tokenizer, embed_model) -> list[list[float]]:
    """
    使用 HuggingFace 模型同步批量生成文本 embedding。

    通过一次前向传播处理多个文本，相比逐个处理显著提高效率。
    使用 masked mean pooling 确保 padding token 不影响结果。

    Args:
        texts (list[str]): 输入文本列表
        tokenizer: 已加载的 tokenizer
        embed_model: 已加载的 PyTorch embedding 模型

    Returns:
        list[list[float]]: embedding 向量列表
    """
    # 处理空列表情况
    if not texts:
        return []

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
        # 使用 masked mean pooling：只对非 padding token 取平均
        # 这确保批处理结果与单独处理结果一致
        last_hidden_state = outputs.last_hidden_state  # (batch_size, seq_len, hidden_dim)
        attention_mask = encoded_texts["attention_mask"]  # (batch_size, seq_len)

        # 扩展 attention_mask 到 hidden_dim 维度: (batch_size, seq_len, hidden_dim)
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()

        # 对每个文本，只对有效 token 求和然后取平均
        sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)  # 防止除零
        embeddings = sum_embeddings / sum_mask

    # 转换为float32并返回CPU上的列表
    if embeddings.dtype == torch.bfloat16:
        return embeddings.detach().to(torch.float32).cpu().tolist()
    else:
        return embeddings.detach().cpu().tolist()
