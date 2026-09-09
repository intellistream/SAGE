"""Bounded local spool transport for TraceLoom's inference trace v1 importer."""

from __future__ import annotations

import os
import secrets
import threading
import time
from pathlib import Path


class NDJSONExporter:
    """Write private, bounded segments; TraceLoom is never on the inference path.

    A dedicated directory is required. Rotation only touches trace-*.ndjson files.
    Expiration is enforced during export/purge, not by an unattended daemon.
    """

    def __init__(
        self,
        directory,
        *,
        segment_bytes=16 * 1024**2,
        total_bytes=64 * 1024**2,
        retention_seconds=86400,
    ):
        if not 16384 <= segment_bytes <= 16 * 1024**2:
            raise ValueError("segment_bytes must be 16 KiB..16 MiB")
        if not segment_bytes <= total_bytes <= 64 * 1024**2:
            raise ValueError("total_bytes must be segment_bytes..64 MiB")
        if not 0 < retention_seconds <= 86400:
            raise ValueError("retention must be positive and at most 24 hours")
        self.directory = Path(directory)
        self.segment_bytes = segment_bytes
        self.total_bytes = total_bytes
        self.retention_seconds = retention_seconds
        self._path = None
        self._session = secrets.token_hex(16)
        self._segment = 0
        self._lock = threading.Lock()

    def _purge(self, reserve=0):
        files = sorted(
            (p for p in self.directory.glob("trace-*.ndjson") if not p.is_symlink()),
            key=lambda p: p.stat().st_mtime_ns,
        )
        retained = []
        for path in files:
            if time.time() - path.stat().st_mtime > self.retention_seconds:
                path.unlink(missing_ok=True)
            else:
                retained.append(path)
        size = sum(p.stat().st_size for p in retained)
        for path in retained:
            if size + reserve <= self.total_bytes:
                break
            size -= path.stat().st_size
            path.unlink(missing_ok=True)

    def purge(self):
        with self._lock:
            if self.directory.exists():
                self._purge()

    def export(self, record: bytes):
        if len(record) > 16384 or not record.endswith(b"\n"):
            raise ValueError("invalid trace record size/framing")
        with self._lock:
            self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
            self._purge(reserve=len(record))
            if (
                self._path is None
                or not self._path.exists()
                or self._path.stat().st_size + len(record) > self.segment_bytes
            ):
                self._segment += 1
                self._path = self.directory / f"trace-{self._session}-{self._segment:06d}.ndjson"
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self._path, flags, 0o600)
            with os.fdopen(descriptor, "ab") as stream:
                stream.write(record)
