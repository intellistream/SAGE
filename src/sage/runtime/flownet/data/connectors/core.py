from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MAX_JSONL_LINE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_PANDAS_FALLBACK_BYTES = 512 * 1024 * 1024


class ConnectorError(RuntimeError):
    def __init__(self, connector: str, reason: str, message: str):
        self.connector = connector
        self.reason = reason
        super().__init__(f"[{connector}:{reason}] {message}")


@dataclass
class ConnectorQualityStats:
    rows_seen: int = 0
    rows_emitted: int = 0
    invalid_rows: int = 0
    dropped_rows: int = 0
    decode_errors: int = 0
    missing_assets: int = 0
    reader_failures: int = 0
    unsupported_schema: int = 0
    resource_exhausted: int = 0
    compat_fallback_hits: int = 0
    parquet_arrow_fallback_hits: int = 0
    retry_count: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "rows_seen": int(self.rows_seen),
            "rows_emitted": int(self.rows_emitted),
            "invalid_rows": int(self.invalid_rows),
            "dropped_rows": int(self.dropped_rows),
            "decode_errors": int(self.decode_errors),
            "missing_assets": int(self.missing_assets),
            "reader_failures": int(self.reader_failures),
            "unsupported_schema": int(self.unsupported_schema),
            "resource_exhausted": int(self.resource_exhausted),
            "compat_fallback_hits": int(self.compat_fallback_hits),
            "parquet_arrow_fallback_hits": int(self.parquet_arrow_fallback_hits),
            "retry_count": int(self.retry_count),
        }


@dataclass(frozen=True)
class ConnectorCheckpoint:
    connector: str
    path: str
    cursor: int
    rows_seen: int
    rows_emitted: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "path": self.path,
            "cursor": int(self.cursor),
            "rows_seen": int(self.rows_seen),
            "rows_emitted": int(self.rows_emitted),
        }


class _CheckpointTracker:
    def __init__(
        self,
        *,
        connector: str,
        path: str,
        resume_offset: int,
        checkpoint_every: int | None,
        on_checkpoint: Callable[[ConnectorCheckpoint], None] | None,
    ):
        normalized_resume = int(resume_offset)
        if normalized_resume < 0:
            raise ValueError("resume_offset must be >= 0.")

        if checkpoint_every is None:
            normalized_every: int | None = None
        else:
            normalized_every = int(checkpoint_every)
            if normalized_every <= 0:
                raise ValueError("checkpoint_every must be > 0 when provided.")

        self._connector = connector
        self._path = path
        self._resume_offset = normalized_resume
        self._checkpoint_every = normalized_every
        self._on_checkpoint = on_checkpoint
        self._cursor = 0
        self._last_emitted_cursor = -1

    def allow_emit(self, stats: ConnectorQualityStats) -> bool:
        # cursor is the processed-emitted row index for resume semantics.
        self._cursor += 1
        self._emit_if_needed(stats)
        return self._cursor > self._resume_offset

    def finalize(self, stats: ConnectorQualityStats) -> None:
        if self._on_checkpoint is None:
            return
        if self._cursor == self._last_emitted_cursor:
            return
        checkpoint = ConnectorCheckpoint(
            connector=self._connector,
            path=self._path,
            cursor=self._cursor,
            rows_seen=stats.rows_seen,
            rows_emitted=stats.rows_emitted,
        )
        self._on_checkpoint(checkpoint)
        self._last_emitted_cursor = self._cursor

    def _emit_if_needed(self, stats: ConnectorQualityStats) -> None:
        if self._on_checkpoint is None or self._checkpoint_every is None:
            return
        if self._cursor <= 0:
            return
        if self._cursor % self._checkpoint_every != 0:
            return
        checkpoint = ConnectorCheckpoint(
            connector=self._connector,
            path=self._path,
            cursor=self._cursor,
            rows_seen=stats.rows_seen,
            rows_emitted=stats.rows_emitted,
        )
        self._on_checkpoint(checkpoint)
        self._last_emitted_cursor = self._cursor


def _classify_parquet_failure(exc: Exception) -> str:
    message = str(exc).lower()
    resource_markers = (
        "out of memory",
        "oom",
        "cannot allocate",
        "memoryerror",
        "resource exhausted",
    )
    if any(marker in message for marker in resource_markers):
        return "resource_exhausted"
    unsupported_markers = (
        "unsupported",
        "not implemented",
        "incompatible",
        "unable to merge",
        "cannot convert",
        "nested",
        "schema mismatch",
    )
    if any(marker in message for marker in unsupported_markers):
        return "unsupported_schema"
    return "reader_failure"


def _path_total_bytes(path: Path) -> int:
    if path.is_file():
        return int(path.stat().st_size)
    if path.is_dir():
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += int(file_path.stat().st_size)
        return total
    return 0


def chunked(items: Iterable[Any], batch_size: int) -> Iterator[list[Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    buf: list[Any] = []
    for item in items:
        buf.append(item)
        if len(buf) >= batch_size:
            yield buf
            buf = []
    if buf:
        yield buf


def iter_jsonl(
    path: str | Path,
    *,
    quality: ConnectorQualityStats | None = None,
    drop_invalid_rows: bool = False,
    max_line_bytes: int = DEFAULT_MAX_JSONL_LINE_BYTES,
    resume_offset: int = 0,
    checkpoint_every: int | None = None,
    on_checkpoint: Callable[[ConnectorCheckpoint], None] | None = None,
) -> Iterator[dict[str, Any]]:
    if max_line_bytes <= 0:
        raise ValueError("max_line_bytes must be > 0")

    stats = quality if quality is not None else ConnectorQualityStats()
    p = Path(path)
    if not p.exists() or not p.is_file():
        stats.missing_assets += 1
        raise ConnectorError("jsonl", "missing_asset", f"JSONL path not found: {path}")

    tracker = _CheckpointTracker(
        connector="jsonl",
        path=str(path),
        resume_offset=resume_offset,
        checkpoint_every=checkpoint_every,
        on_checkpoint=on_checkpoint,
    )

    try:
        with p.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                stats.rows_seen += 1

                if len(line.encode("utf-8")) > max_line_bytes:
                    stats.invalid_rows += 1
                    stats.dropped_rows += 1
                    if drop_invalid_rows:
                        continue
                    raise ConnectorError(
                        "jsonl",
                        "invalid_row",
                        (
                            f"Line {line_no} in '{path}' exceeds max_line_bytes={max_line_bytes}. "
                            f"len={len(line.encode('utf-8'))}"
                        ),
                    )

                try:
                    payload = json.loads(line)
                except Exception as exc:
                    stats.invalid_rows += 1
                    stats.dropped_rows += 1
                    if drop_invalid_rows:
                        continue
                    raise ConnectorError(
                        "jsonl",
                        "invalid_row",
                        f"Line {line_no} in '{path}' is not valid JSON: {exc}",
                    ) from exc

                if not isinstance(payload, Mapping):
                    stats.invalid_rows += 1
                    stats.dropped_rows += 1
                    if drop_invalid_rows:
                        continue
                    raise ConnectorError(
                        "jsonl",
                        "invalid_row",
                        f"Line {line_no} in '{path}' must decode to an object/dict.",
                    )

                if not tracker.allow_emit(stats):
                    continue
                stats.rows_emitted += 1
                yield dict(payload)
    finally:
        tracker.finalize(stats)


def iter_parquet(
    path: str | Path,
    *,
    batch_size: int = 2048,
    quality: ConnectorQualityStats | None = None,
    max_pandas_fallback_bytes: int | None = DEFAULT_MAX_PANDAS_FALLBACK_BYTES,
    resume_offset: int = 0,
    checkpoint_every: int | None = None,
    on_checkpoint: Callable[[ConnectorCheckpoint], None] | None = None,
) -> Iterator[dict[str, Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    stats = quality if quality is not None else ConnectorQualityStats()
    parquet_path = Path(path)
    if not parquet_path.exists():
        stats.missing_assets += 1
        raise ConnectorError("parquet", "missing_asset", f"Parquet path not found: {path}")
    tracker = _CheckpointTracker(
        connector="parquet",
        path=str(path),
        resume_offset=resume_offset,
        checkpoint_every=checkpoint_every,
        on_checkpoint=on_checkpoint,
    )

    try:
        arrow_failure: Exception | None = None
        try:
            import pyarrow.dataset as ds
        except Exception:
            ds = None  # type: ignore[assignment]

        if ds is not None:
            try:
                dataset = ds.dataset(str(parquet_path), format="parquet")
                scanner = dataset.scanner(batch_size=batch_size)
                for record_batch in scanner.to_batches():
                    rows = record_batch.to_pylist()
                    stats.rows_seen += len(rows)
                    for row in rows:
                        if not tracker.allow_emit(stats):
                            continue
                        stats.rows_emitted += 1
                        yield row
                return
            except Exception as exc:
                classified_reason = _classify_parquet_failure(exc)
                if classified_reason == "unsupported_schema":
                    stats.reader_failures += 1
                    stats.unsupported_schema += 1
                    raise ConnectorError(
                        "parquet",
                        classified_reason,
                        f"Arrow reader failed for '{path}' with unsupported schema: {exc}",
                    ) from exc
                if classified_reason == "resource_exhausted":
                    stats.reader_failures += 1
                    stats.resource_exhausted += 1
                    raise ConnectorError(
                        "parquet",
                        classified_reason,
                        f"Arrow reader failed for '{path}' due to resource limits: {exc}",
                    ) from exc
                arrow_failure = exc

        try:
            import pandas as pd
        except Exception as exc:  # pragma: no cover
            stats.reader_failures += 1
            if arrow_failure is None:
                raise ConnectorError(
                    "parquet",
                    "dependency_missing",
                    "iter_parquet requires either pyarrow or pandas in the runtime environment.",
                ) from exc
            raise ConnectorError(
                "parquet",
                "reader_failure",
                f"Arrow reader failed and pandas is unavailable for '{path}': {arrow_failure}",
            ) from arrow_failure

        stats.compat_fallback_hits += 1
        if arrow_failure is not None:
            stats.parquet_arrow_fallback_hits += 1

        if max_pandas_fallback_bytes is not None:
            limit_bytes = max(0, int(max_pandas_fallback_bytes))
            total_bytes = _path_total_bytes(parquet_path)
            if total_bytes > limit_bytes:
                stats.resource_exhausted += 1
                stats.reader_failures += 1
                raise ConnectorError(
                    "parquet",
                    "resource_exhausted",
                    (
                        f"Pandas fallback blocked for '{path}': input_bytes={total_bytes} "
                        f"exceeds max_pandas_fallback_bytes={limit_bytes}"
                    ),
                )

        try:
            df = pd.read_parquet(path)
        except Exception as exc:
            stats.reader_failures += 1
            classified_reason = _classify_parquet_failure(exc)
            if classified_reason == "resource_exhausted":
                stats.resource_exhausted += 1
                raise ConnectorError(
                    "parquet",
                    classified_reason,
                    f"Pandas reader hit resource limits for '{path}': {exc}",
                ) from exc
            if classified_reason == "unsupported_schema":
                stats.unsupported_schema += 1
                raise ConnectorError(
                    "parquet",
                    classified_reason,
                    f"Pandas reader failed for '{path}' with unsupported schema: {exc}",
                ) from exc
            if arrow_failure is None:
                raise ConnectorError(
                    "parquet",
                    classified_reason,
                    f"Pandas reader failed for '{path}': {exc}",
                ) from exc
            raise ConnectorError(
                "parquet",
                "reader_failure",
                f"Both Arrow and pandas readers failed for '{path}'. "
                f"arrow_error={arrow_failure}; pandas_error={exc}",
            ) from exc

        rows = df.to_dict(orient="records")
        stats.rows_seen += len(rows)
        for row in rows:
            if not tracker.allow_emit(stats):
                continue
            stats.rows_emitted += 1
            yield row
    finally:
        tracker.finalize(stats)


def iter_image_rows(
    path: str | Path,
    mode: str = "RGB",
    *,
    quality: ConnectorQualityStats | None = None,
    drop_bad_rows: bool = True,
    resume_offset: int = 0,
    checkpoint_every: int | None = None,
    on_checkpoint: Callable[[ConnectorCheckpoint], None] | None = None,
) -> Iterator[dict[str, Any]]:
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("iter_image_rows requires pillow and numpy.") from exc

    stats = quality if quality is not None else ConnectorQualityStats()
    p = Path(path)
    if p.is_dir():
        files: Iterable[Path] = (x for x in p.rglob("*") if x.is_file())
    elif p.is_file():
        files = [p]
    else:
        stats.missing_assets += 1
        raise ConnectorError("image", "missing_asset", f"Image path not found: {path}")
    tracker = _CheckpointTracker(
        connector="image",
        path=str(path),
        resume_offset=resume_offset,
        checkpoint_every=checkpoint_every,
        on_checkpoint=on_checkpoint,
    )

    try:
        for image_file in files:
            stats.rows_seen += 1
            try:
                with Image.open(image_file) as img:
                    arr = np.array(img.convert(mode))
                if not tracker.allow_emit(stats):
                    continue
                stats.rows_emitted += 1
                yield {"path": str(image_file), "image": arr}
            except Exception as exc:
                stats.invalid_rows += 1
                stats.decode_errors += 1
                stats.dropped_rows += 1
                if not drop_bad_rows:
                    raise ConnectorError(
                        "image",
                        "decode_error",
                        f"Failed to decode image '{image_file}': {exc}",
                    ) from exc
    finally:
        tracker.finalize(stats)


def iter_tfrecord_rows(
    path: str | Path,
    *,
    quality: ConnectorQualityStats | None = None,
    resume_offset: int = 0,
    checkpoint_every: int | None = None,
    on_checkpoint: Callable[[ConnectorCheckpoint], None] | None = None,
) -> Iterator[dict[str, Any]]:
    try:
        import tensorflow as tf
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("iter_tfrecord_rows requires tensorflow.") from exc

    stats = quality if quality is not None else ConnectorQualityStats()
    p = Path(path)
    if p.is_dir():
        files: Iterable[str] = (str(x) for x in p.rglob("*") if x.is_file())
    elif p.is_file():
        files = [str(p)]
    else:
        stats.missing_assets += 1
        raise ConnectorError("tfrecord", "missing_asset", f"TFRecord path not found: {path}")
    tracker = _CheckpointTracker(
        connector="tfrecord",
        path=str(path),
        resume_offset=resume_offset,
        checkpoint_every=checkpoint_every,
        on_checkpoint=on_checkpoint,
    )

    file_dataset = tf.data.Dataset.from_generator(
        lambda: iter(files),
        output_signature=tf.TensorSpec(shape=(), dtype=tf.string),
    )

    dataset = tf.data.TFRecordDataset(file_dataset)
    try:
        for record in dataset:
            payload = bytes(record.numpy())
            stats.rows_seen += 1
            if not tracker.allow_emit(stats):
                continue
            stats.rows_emitted += 1
            yield {"record": payload}
    except Exception as exc:
        stats.invalid_rows += 1
        stats.dropped_rows += 1
        stats.reader_failures += 1
        raise ConnectorError(
            "tfrecord",
            "reader_failure",
            f"Failed to read TFRecord rows: {exc}",
        ) from exc
    finally:
        tracker.finalize(stats)


def batch_to_format(rows: list[dict[str, Any]], fmt: str) -> Any:
    if fmt == "pandas":
        try:
            import pandas as pd
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("batch_to_format('pandas') requires pandas.") from exc
        return pd.DataFrame(rows)

    if fmt == "pyarrow":
        try:
            import pyarrow as pa
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("batch_to_format('pyarrow') requires pyarrow.") from exc
        return pa.Table.from_pylist(rows)

    if fmt == "numpy":
        try:
            import numpy as np
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("batch_to_format('numpy') requires numpy.") from exc
        if not rows:
            return {}
        keys = sorted(rows[0].keys())
        return {key: np.array([row.get(key) for row in rows], dtype=object) for key in keys}

    raise ValueError(f"Unsupported batch format: {fmt}")


__all__ = [
    "DEFAULT_MAX_JSONL_LINE_BYTES",
    "DEFAULT_MAX_PANDAS_FALLBACK_BYTES",
    "ConnectorError",
    "ConnectorCheckpoint",
    "ConnectorQualityStats",
    "chunked",
    "iter_jsonl",
    "iter_parquet",
    "iter_image_rows",
    "iter_tfrecord_rows",
    "batch_to_format",
]
