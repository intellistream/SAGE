"""Recommended LLM model catalog helpers."""

from __future__ import annotations

import json
import os
from importlib import resources
from typing import Any

import requests

from sage.common.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_INDEX_CANDIDATES = [
    "https://raw.githubusercontent.com/intellistream/SAGE/main/docs/assets/model-registry/recommended_llm_models.json",
    "https://raw.githubusercontent.com/intellistream/SAGE/main-dev/docs/assets/model-registry/recommended_llm_models.json",
]

_FALLBACK_MODELS: list[dict[str, Any]] = [
    {
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "display_name": "Qwen2.5 0.5B Instruct",
        "size_billion": 0.5,
        "disk_gb": 2.8,
        "min_gpu_memory_gb": 6,
        "recommended_gpu": "Single 8GB",
        "throughput_tps": 35,
        "tags": ["default", "chat", "cn"],
        "description": "默认开发模型，体积小、加载快，适合本地开发与单 GPU 环境。",
    },
    {
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "display_name": "Qwen2.5 7B Instruct",
        "size_billion": 7,
        "disk_gb": 14,
        "min_gpu_memory_gb": 16,
        "recommended_gpu": "Single 24GB",
        "throughput_tps": 12,
        "tags": ["chat", "general"],
        "description": "平衡质量与成本，适合中等规模中文/英文应用。",
    },
    {
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "display_name": "Llama 3.1 8B Instruct",
        "size_billion": 8,
        "disk_gb": 16,
        "min_gpu_memory_gb": 18,
        "recommended_gpu": "Single 24GB",
        "throughput_tps": 10,
        "tags": ["chat", "english"],
        "description": "面向英语任务的主流 8B 模型，社区生态成熟。",
    },
    {
        "model_id": "google/gemma-2-9b-it",
        "display_name": "Gemma 2 9B IT",
        "size_billion": 9,
        "disk_gb": 18,
        "min_gpu_memory_gb": 20,
        "recommended_gpu": "Single 24GB",
        "throughput_tps": 9,
        "tags": ["chat", "lightweight"],
        "description": "谷歌轻量指令模型，多语种支持，推理成本低。",
    },
    {
        "model_id": "BAAI/bge-m3",
        "display_name": "BGE M3 (Embedding)",
        "size_billion": 1.8,
        "disk_gb": 1.9,
        "min_gpu_memory_gb": 4,
        "recommended_gpu": "Single 8GB",
        "throughput_tps": 120,
        "tags": ["embedding", "retrieval"],
        "description": "通用多语种 Embedding 模型，适合 RAG/搜索。",
    },
]


def _iter_candidate_urls(index_url: str | None = None) -> list[str]:
    """Compose ordered list of URLs to try for the catalog."""

    urls: list[str] = []
    if index_url:
        urls.append(index_url)
    env_url = os.environ.get("SAGE_LLM_MODEL_INDEX_URL")
    if env_url:
        urls.append(env_url)
    urls.extend(_DEFAULT_INDEX_CANDIDATES)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url and url not in seen:
            ordered.append(url)
            seen.add(url)
    return ordered


def fetch_recommended_models(
    index_url: str | None = None, timeout: float = 5.0
) -> list[dict[str, Any]]:
    """Return recommended model catalog, preferring the bundled index."""

    prefer_remote = bool(index_url or os.environ.get("SAGE_LLM_MODEL_INDEX_URL"))
    if not prefer_remote:
        local_models = _load_local_models()
        if local_models:
            return local_models

    failures: list[str] = []
    for url in _iter_candidate_urls(index_url):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()

            if isinstance(payload, dict) and "models" in payload:
                models = payload["models"]
            elif isinstance(payload, list):
                models = payload
            else:
                failures.append(f"{url}: unexpected payload")
                logger.debug("Unexpected model index payload from %s", url)
                continue

            normalized = _normalize_models(models)
            if normalized:
                return normalized
            failures.append(f"{url}: empty model list")
        except Exception as exc:  # pragma: no cover - network failures
            failures.append(f"{url}: {exc}")
            logger.debug("无法从 %s 拉取模型索引", url, exc_info=exc)

    if failures:
        joined = "; ".join(failures[:3])
        if len(failures) > 3:
            joined = f"{joined}; ..."
        logger.warning("无法拉取远程模型索引，将使用内置推荐列表。原因：%s", joined)

    return _FALLBACK_MODELS


def _normalize_models(models: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        model_id = item.get("model_id")
        if not isinstance(model_id, str):
            continue
        normalized.append(
            {
                "model_id": model_id,
                "display_name": item.get("display_name", model_id),
                "size_billion": item.get("size_billion"),
                "disk_gb": item.get("disk_gb"),
                "min_gpu_memory_gb": item.get("min_gpu_memory_gb"),
                "recommended_gpu": item.get("recommended_gpu"),
                "throughput_tps": item.get("throughput_tps"),
                "tags": item.get("tags", []),
                "description": item.get("description", ""),
            }
        )
    return normalized


def _load_local_models() -> list[dict[str, Any]] | None:
    """Load bundled JSON index shipped with sage-common."""

    try:
        data = resources.files(__package__).joinpath("recommended_llm_models.json")
    except FileNotFoundError:
        return None

    if not data.is_file():  # type: ignore[attr-defined]
        return None

    try:
        with data.open("r", encoding="utf-8") as fp:  # type: ignore[attr-defined]
            payload = json.load(fp)
    except Exception as exc:  # pragma: no cover - IO failure
        logger.debug("无法加载本地推荐模型索引", exc_info=exc)
        return None

    if isinstance(payload, dict) and "models" in payload:
        models = payload["models"]
    elif isinstance(payload, list):
        models = payload
    else:
        logger.debug("本地推荐模型索引格式异常: %s", payload)
        return None

    return _normalize_models(models)
