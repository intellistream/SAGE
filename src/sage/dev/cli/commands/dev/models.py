"""Typer commands for working with embedding model caches."""

from __future__ import annotations

import typer
from rich.console import Console

from sage.dev.impl.models.cache import (
    DEFAULT_MODEL_NAME,
    cache_embedding_model,
    check_embedding_model,
    clear_embedding_model_cache,
    configure_hf_environment,
)

console = Console()
app = typer.Typer(name="models", help="🤖 Embedding 模型缓存管理")


@app.command()
def configure():
    """仅配置 Hugging Face 下载所需的环境变量。"""

    configure_hf_environment(console)


@app.command()
def cache(
    model: str = typer.Option(DEFAULT_MODEL_NAME, "--model", "-m", help="要缓存的模型标识"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="下载后执行一次推理验证"),
    retries: int = typer.Option(3, "--retries", min=1, max=5, help="下载失败时的最大重试次数"),
):
    """下载并缓存指定的 embedding 模型。"""

    success = cache_embedding_model(model, console=console, verify=verify, retries=retries)
    if not success:
        raise typer.Exit(1)


@app.command()
def check(model: str = typer.Option(DEFAULT_MODEL_NAME, "--model", "-m")):
    """检查模型是否已缓存或可下载。"""

    success = check_embedding_model(model, console=console)
    if not success:
        raise typer.Exit(1)


@app.command()
def clear(model: str = typer.Option(DEFAULT_MODEL_NAME, "--model", "-m")):
    """清理模型缓存。"""

    success = clear_embedding_model_cache(model, console=console)
    if not success:
        raise typer.Exit(1)


__all__ = ["app"]
