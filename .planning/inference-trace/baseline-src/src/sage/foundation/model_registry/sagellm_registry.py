"""Shared helpers for managing local sageLLM-compatible model assets."""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from sage.foundation.config.user_paths import get_user_paths

try:
    from huggingface_hub import snapshot_download
except ImportError:  # pragma: no cover
    snapshot_download = None  # type: ignore


_MANIFEST_NAME = "metadata.json"


@dataclass(order=True)
class ModelInfo:
    """Metadata describing one locally cached model."""

    sort_index: float = field(init=False, repr=False)
    model_id: str
    path: Path
    revision: str | None = None
    size_bytes: int = 0
    last_used: float = field(default_factory=lambda: 0.0)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
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
    """Raised when a requested model does not exist locally."""


def _default_root() -> Path:
    return get_user_paths().sagellm_models_dir


def _ensure_root(root: Path | None = None) -> Path:
    resolved = Path(root) if root is not None else _default_root()
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
    except json.JSONDecodeError as exc:  # pragma: no cover
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
    """List locally cached models sorted by last access time."""
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


def get_model_path(model_id: str, root: Path | None = None) -> Path | None:
    """Return local path for ``model_id`` or ``None``."""
    root = _ensure_root(root)
    manifest = _load_manifest(root)
    entry = manifest.get(model_id)
    if not entry:
        return None
    path = Path(entry["path"])
    return path if path.exists() else None


def touch_model(model_id: str, root: Path | None = None) -> None:
    """Refresh the last-used timestamp if a model exists in the registry."""
    root = _ensure_root(root)
    manifest = _load_manifest(root)
    if model_id not in manifest:
        return
    manifest[model_id]["last_used"] = time.time()
    _save_manifest(root, manifest)


def download_model(
    model_id: str,
    revision: str | None = None,
    root: Path | None = None,
    tags: Iterable[str] | None = None,
    force: bool = False,
    progress: bool = True,
    **snapshot_kwargs,
) -> ModelInfo:
    """Download a model into the local registry."""
    if snapshot_download is None:  # pragma: no cover
        raise ModelRegistryError(
            "huggingface_hub is required to download models. "
            "Install with: pip install huggingface_hub"
        )

    root = _ensure_root(root)
    manifest = _load_manifest(root)
    target_dir = root / _safe_dir_name(model_id, revision)

    if target_dir.exists() and force:
        shutil.rmtree(target_dir, ignore_errors=True)

    if target_dir.exists() and not force:
        manifest_entry = manifest.get(model_id)
        if manifest_entry:
            touch_model(model_id, root=root)
            return ModelInfo(
                model_id=model_id,
                path=Path(manifest_entry["path"]),
                revision=manifest_entry.get("revision"),
                size_bytes=int(manifest_entry.get("size_bytes", 0)),
                last_used=float(manifest_entry.get("last_used", 0.0)),
                tags=list(manifest_entry.get("tags", [])),
            )
        if progress:
            print("⚠️  发现未完成的下载，继续从断点恢复...")

    target_dir.mkdir(parents=True, exist_ok=True)
    download_kwargs = {
        "repo_id": model_id,
        "revision": revision,
        "local_dir": str(target_dir),
        **snapshot_kwargs,
    }
    if not progress:
        download_kwargs.setdefault("progress", False)

    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            resolved_path = Path(snapshot_download(**download_kwargs))  # type: ignore[arg-type]
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                if progress:
                    print(f"⚠️  下载中断，{wait_time}秒后重试 (尝试 {attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise ModelRegistryError(
                    f"下载失败 (已重试 {max_retries} 次): {last_error}\n"
                    "提示：使用 --force 清理并重新下载，或检查网络连接"
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


def delete_model(model_id: str, root: Path | None = None) -> bool:
    """Delete a model from the registry and local filesystem."""
    root = _ensure_root(root)
    manifest = _load_manifest(root)
    entry = manifest.pop(model_id, None)
    if not entry:
        return False
    path = Path(entry.get("path", ""))
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    _save_manifest(root, manifest)
    return True


def ensure_model_available(
    model_id: str,
    revision: str | None = None,
    root: Path | None = None,
    auto_download: bool = True,
) -> Path:
    """Ensure a model exists locally, downloading it when allowed."""
    path = get_model_path(model_id, root=root)
    if path is not None:
        touch_model(model_id, root=root)
        return path

    if not auto_download:
        raise ModelNotFoundError(
            f"Model '{model_id}' not found locally. "
            "Set auto_download=True or download it with the SAGE model registry API "
            "(for example `ensure_model_available()` / `download_model()`)."
        )

    info = download_model(model_id, revision=revision, root=root)
    return info.path


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
