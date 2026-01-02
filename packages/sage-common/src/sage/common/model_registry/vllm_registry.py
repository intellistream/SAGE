"""Shared helpers for managing local vLLM-compatible model assets.

The CLI (``sage llm``) and middleware services share this module to keep model
lifecycle logic in one place.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

try:  # Optional dependency – resolved lazily where needed
    from huggingface_hub import snapshot_download
except ImportError:  # pragma: no cover - defer failure until download call
    snapshot_download = None  # type: ignore


_DEFAULT_ROOT = Path(os.getenv("SAGE_LLM_MODEL_ROOT", Path.home() / ".sage" / "models" / "vllm"))
_MANIFEST_NAME = "metadata.json"


@dataclass(order=True)
class ModelInfo:
    """Metadata describing a locally cached model."""

    sort_index: float = field(init=False, repr=False)
    model_id: str
    path: Path
    revision: str | None = None
    size_bytes: int = 0
    last_used: float = field(default_factory=lambda: 0.0)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Negative for descending sort on ``last_used``
        self.sort_index = -float(self.last_used or 0.0)

    @property
    def size_mb(self) -> float:
        return self.size_bytes / 1024**2

    @property
    def last_used_iso(self) -> str | None:
        if not self.last_used:
            return None
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.last_used))


class ModelRegistryError(RuntimeError):
    """Base class for registry exceptions."""


class ModelNotFoundError(ModelRegistryError):
    """Raised when the requested model does not exist locally."""


def _ensure_root(root: Path | None = None) -> Path:
    resolved = Path(root) if root is not None else _DEFAULT_ROOT
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _manifest_path(root: Path) -> Path:
    return root / _MANIFEST_NAME


def _load_manifest(root: Path) -> dict[str, dict]:
    manifest_path = _manifest_path(root)
    if not manifest_path.exists():
        return {}
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected corruption
        raise ModelRegistryError(f"Corrupted manifest at {manifest_path}: {exc}") from exc


def _save_manifest(root: Path, manifest: dict[str, dict]) -> None:
    manifest_path = _manifest_path(root)
    tmp_path = manifest_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(manifest_path)


def _safe_dir_name(model_id: str, revision: str | None) -> str:
    slug = model_id.replace("/", "__")
    if revision:
        slug = f"{slug}__{revision}"
    return slug


def _compute_size_bytes(path: Path) -> int:
    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            total += file_path.stat().st_size
    return total


def _purge_missing_entries(root: Path, manifest: dict[str, dict]) -> dict[str, dict]:
    changed = False
    to_delete = []
    for model_id, entry in manifest.items():
        path = Path(entry.get("path", ""))
        if not path.exists():
            to_delete.append(model_id)
    if to_delete:
        for model_id in to_delete:
            manifest.pop(model_id, None)
        changed = True
    if changed:
        _save_manifest(root, manifest)
    return manifest


def list_models(root: Path | None = None) -> list[ModelInfo]:
    """List locally available models sorted by last-used timestamp."""

    root = _ensure_root(root)
    manifest = _purge_missing_entries(root, _load_manifest(root))
    infos: list[ModelInfo] = []
    for model_id, entry in manifest.items():
        infos.append(
            ModelInfo(
                model_id=model_id,
                path=Path(entry["path"]),
                revision=entry.get("revision"),
                size_bytes=int(entry.get("size_bytes", 0)),
                last_used=float(entry.get("last_used", 0.0)),
                tags=list(entry.get("tags", [])),
            )
        )
    return sorted(infos)


def get_model_path(model_id: str, root: Path | None = None) -> Path:
    """Return the local path for ``model_id`` or raise ``ModelNotFoundError``."""

    root = _ensure_root(root)
    manifest = _load_manifest(root)
    entry = manifest.get(model_id)
    if not entry:
        raise ModelNotFoundError(
            f"Model '{model_id}' is not downloaded. Run 'sage llm model download'."
        )
    path = Path(entry["path"])
    if not path.exists():
        raise ModelNotFoundError(
            f"Model '{model_id}' manifest points to missing path '{path}'. Consider re-downloading."
        )
    return path


def touch_model(model_id: str, root: Path | None = None) -> None:
    """Update ``last_used`` timestamp for ``model_id`` if it exists."""

    root = _ensure_root(root)
    manifest = _load_manifest(root)
    if model_id not in manifest:
        return
    manifest[model_id]["last_used"] = time.time()
    _save_manifest(root, manifest)


def ensure_model_available(
    model_id: str,
    *,
    revision: str | None = None,
    auto_download: bool = False,
    root: Path | None = None,
) -> Path:
    """Return the local path for ``model_id`` and optionally download it.

    If the model directory exists but is incomplete (missing key files),
    it will be re-downloaded automatically.

    Args:
        model_id: HuggingFace model ID (e.g., "Qwen/Qwen2.5-1.5B-Instruct")
                  or local path (e.g., "/path/to/model")
    """

    # Check if model_id is a local path (absolute or relative)
    model_path = Path(model_id)
    if model_path.exists() and model_path.is_dir():
        # It's a local path, verify completeness and return directly
        if _is_model_complete(model_path):
            return model_path
        else:
            raise ModelRegistryError(f"本地模型目录 '{model_id}' 存在但不完整（缺少关键文件）。")

    try:
        path = get_model_path(model_id, root=root)

        # Validate model completeness
        if not _is_model_complete(path):
            # Model exists but is incomplete - continue download (NOT force=True)
            if auto_download:
                print(f"⚠️  检测到模型 '{model_id}' 下载不完整，继续下载...")
                # Do NOT use force=True - let huggingface_hub resume the download
                return download_model(model_id, revision=revision, root=root, force=False).path
            else:
                raise ModelRegistryError(
                    f"模型 '{model_id}' 下载不完整（缺少关键文件）。"
                    f"请使用 'sage llm model download {model_id}' 继续下载。"
                )

        touch_model(model_id, root=root)
        return path
    except ModelNotFoundError:
        if not auto_download:
            raise
    return download_model(model_id, revision=revision, root=root).path


def _is_model_complete(model_path: Path) -> bool:
    """Check if a model directory contains the expected files.

    A complete model should have at least one of:
    - *.safetensors files (PyTorch safe tensors format)
    - *.bin files (legacy PyTorch format)
    - config.json (model configuration)

    Note: With huggingface_hub's blob storage, we check both:
    1. Symlinks in snapshots directory
    2. Actual blob files (no .incomplete suffix)
    """
    if not model_path.exists() or not model_path.is_dir():
        return False

    # Check for config.json
    has_config = (model_path / "config.json").exists()
    if not has_config:
        return False

    # Check for weight files (safetensors or bin)
    # These might be symlinks pointing to blobs
    has_safetensors = any(model_path.glob("*.safetensors"))
    has_bin = any(model_path.glob("*.bin"))

    if not (has_safetensors or has_bin):
        # No weight files found - check if there are incomplete downloads
        # in the parent blobs directory
        blobs_dir = model_path.parent.parent / "blobs"
        if blobs_dir.exists():
            # Check if there are .incomplete files (ongoing downloads)
            incomplete_files = list(blobs_dir.glob("*.incomplete"))
            if incomplete_files:
                # Has incomplete downloads - model is not complete
                return False

        # No weight files and no incomplete downloads - model is incomplete
        return False

    # Has config.json and at least one weight file
    return True


def download_model(
    model_id: str,
    *,
    revision: str | None = None,
    root: Path | None = None,
    tags: Iterable[str] | None = None,
    force: bool = False,
    progress: bool = True,
    **snapshot_kwargs,
) -> ModelInfo:
    """Download ``model_id`` into the registry and return its metadata."""

    if snapshot_download is None:  # pragma: no cover - import guard
        raise ModelRegistryError(
            "huggingface_hub is required to download models. Install the 'isage-tools[cli]' extra or add huggingface_hub."
        )

    root = _ensure_root(root)
    manifest = _load_manifest(root)

    target_dir = root / _safe_dir_name(model_id, revision)
    if target_dir.exists() and force:
        shutil.rmtree(target_dir, ignore_errors=True)

    if target_dir.exists() and not force:
        manifest_entry = manifest.get(model_id)
        if manifest_entry:
            # refresh last-used and return existing info
            touch_model(model_id, root=root)
            return ModelInfo(
                model_id=model_id,
                path=Path(manifest_entry["path"]),
                revision=manifest_entry.get("revision"),
                size_bytes=int(manifest_entry.get("size_bytes", 0)),
                last_used=float(manifest_entry.get("last_used", 0.0)),
                tags=list(manifest_entry.get("tags", [])),
            )
        else:
            # Directory exists without manifest entry
            # DO NOT DELETE - huggingface_hub will resume incomplete downloads
            # Just continue to download, it will handle .incomplete files
            if progress:
                print("⚠️  发现未完成的下载，继续从断点恢复...")

    target_dir.mkdir(parents=True, exist_ok=True)

    download_kwargs = dict(
        repo_id=model_id,
        revision=revision,
        local_dir=str(target_dir),
        # resume_download is deprecated - huggingface_hub now resumes by default
        # local_dir_use_symlinks is deprecated - downloads are direct by default
        **snapshot_kwargs,
    )
    if not progress:
        download_kwargs.setdefault("progress", False)

    # Retry download with exponential backoff
    # Note: huggingface_hub automatically resumes incomplete downloads
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            resolved_path = Path(snapshot_download(**download_kwargs))  # type: ignore[arg-type]
            break  # Success
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # 1s, 2s, 4s
                if progress:
                    print(f"⚠️  下载中断，{wait_time}秒后重试 (尝试 {attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            else:
                # Final attempt failed
                raise ModelRegistryError(
                    f"下载失败 (已重试 {max_retries} 次): {last_error}\n"
                    f"提示：使用 --force 清理并重新下载，或检查网络连接"
                ) from last_error

    size_bytes = _compute_size_bytes(resolved_path)
    now = time.time()
    manifest[model_id] = {
        "path": str(resolved_path),
        "revision": revision,
        "size_bytes": size_bytes,
        "last_used": now,
        "tags": list(tags or []),
    }
    _save_manifest(root, manifest)

    return ModelInfo(
        model_id=model_id,
        path=resolved_path,
        revision=revision,
        size_bytes=size_bytes,
        last_used=now,
        tags=list(tags or []),
    )


def delete_model(model_id: str, *, root: Path | None = None) -> None:
    """Remove ``model_id`` from the registry (manifest + files)."""

    root = _ensure_root(root)
    manifest = _load_manifest(root)
    entry = manifest.pop(model_id, None)
    if entry:
        path = Path(entry.get("path", ""))
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    _save_manifest(root, manifest)


__all__ = [
    "ModelInfo",
    "ModelRegistryError",
    "ModelNotFoundError",
    "list_models",
    "download_model",
    "delete_model",
    "get_model_path",
    "touch_model",
    "ensure_model_available",
]
