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


_DEFAULT_ROOT = Path(os.getenv("SAGE_VLLM_MODEL_ROOT", Path.home() / ".sage" / "models" / "vllm"))
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
    """Return the local path for ``model_id`` and optionally download it."""

    try:
        path = get_model_path(model_id, root=root)
        touch_model(model_id, root=root)
        return path
    except ModelNotFoundError:
        if not auto_download:
            raise
    return download_model(model_id, revision=revision, root=root).path


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
            # Directory exists without manifest entry -> treat as stale cache
            shutil.rmtree(target_dir, ignore_errors=True)

    target_dir.mkdir(parents=True, exist_ok=True)

    download_kwargs = dict(
        repo_id=model_id,
        revision=revision,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        **snapshot_kwargs,
    )
    if not progress:
        download_kwargs.setdefault("progress", False)

    resolved_path = Path(snapshot_download(**download_kwargs))  # type: ignore[arg-type]

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
