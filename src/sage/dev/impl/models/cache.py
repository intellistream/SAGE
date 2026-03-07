"""Utilities for managing embedding model caches used in CI flows."""

from __future__ import annotations

import os
import time
from pathlib import Path

from rich.console import Console

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _get_console(console: Console | None) -> Console:
    return console or Console()


def configure_hf_environment(console: Console | None = None) -> dict[str, str]:
    """Configure environment variables that improve Hugging Face downloads."""

    console = _get_console(console)
    cache_dir = os.environ.get("TRANSFORMERS_CACHE") or os.path.expanduser(
        "~/.cache/huggingface/transformers"
    )
    suggested_env = {
        "HF_ENDPOINT": os.environ.get("HF_ENDPOINT") or "https://hf-mirror.com",
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "HF_HUB_DOWNLOAD_TIMEOUT": os.environ.get("HF_HUB_DOWNLOAD_TIMEOUT") or "60",
        "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE") or "0",
        "TRANSFORMERS_CACHE": cache_dir,
    }

    for key, value in suggested_env.items():
        os.environ[key] = value

    console.print("🔧 [bold]已配置 Hugging Face 下载环境变量[/bold]")
    for key, value in suggested_env.items():
        console.print(f"  • {key} = {value}")

    return suggested_env


def clear_embedding_model_cache(
    model_name: str = DEFAULT_MODEL_NAME, console: Console | None = None
) -> bool:
    """Remove cached files for *model_name* if they exist."""

    console = _get_console(console)
    try:
        from transformers import TRANSFORMERS_CACHE
    except ImportError as exc:  # pragma: no cover - optional dependency
        console.print(f"⚠️ 未安装 transformers，无法清理缓存: {exc}")
        return False

    cache_dir = Path(TRANSFORMERS_CACHE)
    if not cache_dir.exists():
        console.print("ℹ️ 尚未创建 transformers 缓存目录")
        return True

    pattern = model_name.split("/")[-1]
    matches = [p for p in cache_dir.glob("**/*") if pattern in p.name]
    if not matches:
        console.print("ℹ️ 未找到对应模型缓存")
        return True

    import shutil

    removed = 0
    for path in matches:
        if path.is_dir():
            console.print(f"🗑️ 删除缓存目录: {path}")
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    console.print(f"✅ 已清理 {removed} 个缓存条目")
    return True


def _prepare_requests_session():
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        try:
            import huggingface_hub

            huggingface_hub.constants.DEFAULT_REQUEST_TIMEOUT = 60
        except Exception:  # pragma: no cover - best effort tweak
            pass

        return session
    except ImportError:  # pragma: no cover - optional dependency
        return None


def cache_embedding_model(
    model_name: str = DEFAULT_MODEL_NAME,
    *,
    console: Console | None = None,
    verify: bool = True,
    retries: int = 3,
) -> bool:
    """Download and cache the specified embedding model."""

    console = _get_console(console)
    configure_hf_environment(console)
    _prepare_requests_session()

    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - optional dependency
        console.print(f"❌ 未安装 transformers: {exc}")
        return False

    tokenizer = None
    for attempt in range(retries):
        try:
            console.print(f"📥 下载 tokenizer (尝试 {attempt + 1}/{retries})")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            break
        except Exception as exc:  # pragma: no cover - network dependent
            console.print(f"  ❌ 下载失败: {exc}")
            if attempt < retries - 1:
                delay = 2**attempt
                console.print(f"  ⏳ {delay} 秒后重试")
                time.sleep(delay)
            else:
                return False

    model = None
    for attempt in range(retries):
        try:
            console.print(f"📥 下载模型 (尝试 {attempt + 1}/{retries})")
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            break
        except Exception as exc:  # pragma: no cover - network dependent
            console.print(f"  ❌ 下载失败: {exc}")
            if attempt < retries - 1:
                delay = 2**attempt
                console.print(f"  ⏳ {delay} 秒后重试")
                time.sleep(delay)
            else:
                return False

    if verify and tokenizer is not None and model is not None:
        try:
            console.print("🧪 验证模型输出...")
            inputs = tokenizer("测试文本", return_tensors="pt", padding=True, truncation=True)
            outputs = model(**inputs)
            console.print(f"  ✅ 输出维度: {tuple(outputs.last_hidden_state.shape)}")
        except Exception as exc:  # pragma: no cover - runtime dependent
            console.print(f"❌ 模型验证失败: {exc}")
            return False

    cache_dir = os.environ.get("TRANSFORMERS_CACHE", "~/.cache/huggingface/transformers")
    console.print(f"✅ 模型缓存完成，位置: {cache_dir}")
    return True


def check_embedding_model(
    model_name: str = DEFAULT_MODEL_NAME, *, console: Console | None = None
) -> bool:
    """Return ``True`` when the embedding model is available locally or remotely."""

    console = _get_console(console)
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - optional dependency
        console.print(f"❌ 未安装 transformers: {exc}")
        return False

    console.print(f"🔍 检查模型 {model_name} 是否就绪")
    try:
        AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        AutoModel.from_pretrained(model_name, local_files_only=True, trust_remote_code=True)
        console.print("✅ 模型已在本地缓存")
        return True
    except Exception:
        console.print("ℹ️ 本地缓存未找到，尝试远程下载验证")

    for attempt in range(3):
        try:
            AutoTokenizer.from_pretrained(model_name)
            AutoModel.from_pretrained(model_name, trust_remote_code=True)
            console.print("✅ 远程验证成功")
            return True
        except Exception as exc:
            console.print(f"  ❌ 尝试 {attempt + 1} 失败: {exc}")
            if attempt < 2:
                delay = 2**attempt
                console.print(f"  ⏳ {delay} 秒后重试")
                time.sleep(delay)

    console.print("❌ 模型不可用")
    return False


__all__ = [
    "DEFAULT_MODEL_NAME",
    "cache_embedding_model",
    "check_embedding_model",
    "clear_embedding_model_cache",
    "configure_hf_environment",
]
