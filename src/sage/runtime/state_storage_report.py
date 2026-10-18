"""Content-free, read-only accounting for SAGE SQLite state.

This is an observation, not a retention policy or capacity reservation. Never
unpickle values, checkpoint, vacuum, prune, or open a missing database for write.
SQLite counters share a read transaction; filesystem counters are advisory and
may change independently while writers continue. Payload bytes are serialized
blob bytes, not filesystem usage and not the size of individual logical events.
"""

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StateStorageReport:
    entries: int
    payload_bytes: int
    largest_payload_bytes: int
    allocated_page_bytes: int
    reusable_page_bytes: int
    observed_wal_bytes: int
    filesystem_free_bytes: int


def inspect_sqlite_state(path: str | Path) -> StateStorageReport:
    """Inspect an existing SAGE state database without exposing keys or values.

    Missing/invalid/inaccessible databases fail explicitly, never report an empty
    healthy store. No retention action or change to admission limits is implied.
    """
    path = Path(path).resolve(strict=True)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        entries, payload_bytes, largest = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(length(value_blob)), 0), "
            "COALESCE(MAX(length(value_blob)), 0) FROM state_entries"
        ).fetchone()
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        pages = connection.execute("PRAGMA page_count").fetchone()[0]
        free_pages = connection.execute("PRAGMA freelist_count").fetchone()[0]
    finally:
        connection.close()
    try:
        wal_bytes = Path(str(path) + "-wal").stat().st_size
    except FileNotFoundError:
        wal_bytes = 0
    return StateStorageReport(entries, payload_bytes, largest, pages * page_size,
                              free_pages * page_size, wal_bytes,
                              shutil.disk_usage(path.parent).free)
