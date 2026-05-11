from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .dependencies import REPO_ROOT

DEFAULT_RESULTS_ROOT = REPO_ROOT / "evaluation" / "results" / "langchain_rag_shared_workloads"


def _sanitize_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "-" for character in value
    )


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def create_batch_output_directory(base_output_root: str | Path | None = None) -> Path:
    output_root = Path(base_output_root) if base_output_root is not None else DEFAULT_RESULTS_ROOT
    output_root.mkdir(parents=True, exist_ok=True)

    while True:
        timestamp = datetime.now(timezone.utc).strftime("batch-%Y%m%d-%H%M%S-%f")
        batch_dir = output_root / f"{timestamp}-{uuid4().hex[:8]}"
        if batch_dir.exists():
            continue
        (batch_dir / "runs").mkdir(parents=True, exist_ok=False)
        (batch_dir / "comparison").mkdir(parents=True, exist_ok=False)
        return batch_dir


def prepare_run_output_directory(
    batch_dir: Path,
    workload_name: str,
    variant_name: str,
    framework_name: str | None = None,
) -> Path:
    run_dir = batch_dir / "runs" / _sanitize_name(workload_name)
    if framework_name:
        run_dir = run_dir / _sanitize_name(framework_name)
    run_dir = run_dir / _sanitize_name(variant_name)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


__all__ = [
    "DEFAULT_RESULTS_ROOT",
    "create_batch_output_directory",
    "prepare_run_output_directory",
    "write_json",
]
