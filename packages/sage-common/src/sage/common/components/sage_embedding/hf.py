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
        from transformers import AutoModel  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer
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
