import asyncio
import copy
import os
from functools import lru_cache
import asyncio
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("transformers"):
    pm.install("transformers")
if not pm.is_installed("torch"):
    pm.install("torch")
if not pm.is_installed("tenacity"):
    pm.install("tenacity")
if not pm.is_installed("numpy"):
    pm.install("numpy")
if not pm.is_installed("tenacity"):
    pm.install("tenacity")

from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import torch
import numpy as np

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





async def hf_embed(text: str, tokenizer, embed_model) -> list[float]:
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


# async def hf_rerank_score(text: str, tokenizer, embed_model) -> list[float]:
#     device = next(embed_model.parameters()).device
#     inputs = tokenizer(
#         text, return_tensors="pt", padding=True, truncation=True, max_length=512
#     ).to(device)
#     with torch.no_grad():
#         scores = embed_model(
#             **inputs
#         ).logits.view(-1).float()

#     return scores
    #     embeddings = outputs.last_hidden_state.mean(dim=1)
    # if embeddings.dtype == torch.bfloat16:
    #     return embeddings.detach().to(torch.float32).cpu()[0].tolist()
    # else:
    #     return embeddings.detach().cpu()[0].tolist()
    

