"""Utilities for persisting FileSource dialog queries to disk so that
SAGE pipelines can consume them via ``FileSource``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict

__all__ = ["FileSourceQueryStorage"]


class FileSourceQueryStorage:
    """Persist FileSource dialog queries to per-job files.

    Two artifacts are maintained under ``~/.sage/studio/queries/<jobId>/``:

    ``queries.jsonl``
        JSON Lines file containing rich metadata for each query.

    ``filesource_input.txt``
        Plain-text file with one sanitized query per line. Configure the
        pipeline's :class:`~sage.libs.io_utils.source.FileSource` to read from
        this file (set ``data_path`` to the path returned by :meth:`save_query`) so
        that the RAG pipeline picks up the newly submitted queries automatically.
    """

    METADATA_FILENAME = "queries.jsonl"
    PIPELINE_FILENAME = "filesource_input.txt"

    def __init__(self) -> None:
        self._base_dir = self._get_base_dir()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_base_dir(self) -> Path:
        """Resolve ``~/.sage`` directory (or custom ``SAGE_OUTPUT_DIR``).

        Keeps the logic aligned with the backend API without introducing
        circular imports.
        """
        env_dir = os.environ.get("SAGE_OUTPUT_DIR")
        if env_dir:
            sage_dir = Path(env_dir)
        else:
            current_dir = Path.cwd()
            if (current_dir / "packages" / "sage-common").exists():
                sage_dir = current_dir / ".sage"
            else:
                sage_dir = Path.home() / ".sage"

        studio_queries_dir = sage_dir / "studio" / "queries"
        return studio_queries_dir

    def save_query(
        self, job_id: str, node_id: str, query: str, query_id: str
    ) -> Dict[str, str]:
        """Append a query to the metadata and pipeline files.

        Parameters
        ----------
        job_id:
            Identifier of the pipeline/job the query belongs to.
        node_id:
            Identifier of the FileSource node.
        query:
            The question text submitted by the user.
        query_id:
            Unique identifier generated for the query.

        Returns
        -------
        Dict[str, str]
            Paths of the metadata JSONL file and the pipeline text file.
        """
        timestamp = time.time()
        job_dir = self._base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = job_dir / self.METADATA_FILENAME
        pipeline_path = job_dir / self.PIPELINE_FILENAME

        record = {
            "query_id": query_id,
            "job_id": job_id,
            "node_id": node_id,
            "query": query,
            "timestamp": timestamp,
        }

        # Append metadata as JSON line (UTF-8, keep unicode characters intact)
        with metadata_path.open("a", encoding="utf-8") as meta_fp:
            meta_fp.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Append plain text line for FileSource consumption
        sanitized_query = query.replace("\n", " ").strip()
        with pipeline_path.open("a", encoding="utf-8") as pipe_fp:
            pipe_fp.write(sanitized_query + "\n")

        return {
            "metadata_path": str(metadata_path.resolve()),
            "pipeline_path": str(pipeline_path.resolve()),
        }
