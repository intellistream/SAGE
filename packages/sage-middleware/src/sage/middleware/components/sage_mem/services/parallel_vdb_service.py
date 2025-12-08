"""Parallel VDB Service for high-performance batch insertion.

Layer: L4 (Middleware)

This service provides parallel batch insertion for VDBMemoryCollection,
combining EmbeddingService batch processing with concurrent storage operations.

Design Principles:
1. neuromem remains single-threaded (no internal thread pools)
2. Parallelization happens at the SAGE middleware layer
3. Integrates with existing EmbeddingService for batch embedding
4. Configurable parallelism and batch sizes

Architecture:
    ParallelVDBService
        ↓
    ThreadPoolExecutor (configurable workers)
        ↓
    [Batch 1] [Batch 2] [Batch 3] ... [Batch N]
        ↓         ↓         ↓            ↓
    EmbeddingService.embed() (batch vectors)
        ↓         ↓         ↓            ↓
    VDBCollection (serial storage per batch)

Usage:
    from sage.middleware.components.sage_mem.services import ParallelVDBService

    service = ParallelVDBService(
        collection=vdb_collection,
        embedding_config={
            "method": "hf",
            "model": "BAAI/bge-small-zh-v1.5",
            "batch_size": 64,
        },
        max_workers=4,
    )
    service.setup()

    # Insert 100K documents in parallel
    result = service.parallel_batch_insert(
        texts=texts,
        index_name="my_index",
        batch_size=1000,
    )
    print(f"Inserted {result['total_inserted']} documents")
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from sage.platform.service import BaseService


@dataclass
class ParallelInsertResult:
    """Result of parallel batch insertion."""

    total_texts: int
    total_inserted: int
    total_failed: int
    elapsed_seconds: float
    throughput_per_second: float
    batch_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_texts": self.total_texts,
            "total_inserted": self.total_inserted,
            "total_failed": self.total_failed,
            "elapsed_seconds": self.elapsed_seconds,
            "throughput_per_second": self.throughput_per_second,
            "batch_results": self.batch_results,
        }


class ParallelVDBService(BaseService):
    """High-performance parallel VDB insertion service.

    This service wraps VDBMemoryCollection and EmbeddingService to provide
    parallel batch insertion for large datasets (100K+ documents).

    Features:
    - Parallel batch processing with ThreadPoolExecutor
    - Integrated batch embedding via EmbeddingService
    - Configurable batch size and worker count
    - Progress tracking and statistics
    - Error handling per batch (failures don't stop entire job)

    Example:
        >>> from sage.middleware.components.sage_mem.services import ParallelVDBService
        >>> from sage.middleware.components.sage_mem.neuromem.memory_collection import (
        ...     VDBMemoryCollection
        ... )
        >>>
        >>> # Create collection
        >>> collection = VDBMemoryCollection(config={"name": "my_collection"})
        >>> collection.create_index(config={
        ...     "name": "main_index",
        ...     "dim": 384,
        ...     "backend_type": "FAISS",
        ... })
        >>>
        >>> # Create parallel service
        >>> service = ParallelVDBService(
        ...     collection=collection,
        ...     embedding_config={
        ...         "method": "hf",
        ...         "model": "BAAI/bge-small-zh-v1.5",
        ...     },
        ...     max_workers=4,
        ... )
        >>> service.setup()
        >>>
        >>> # Parallel insert
        >>> texts = ["doc 1", "doc 2", ..., "doc 100000"]
        >>> result = service.parallel_batch_insert(texts, index_name="main_index")
        >>> print(f"Throughput: {result.throughput_per_second:.0f} docs/sec")
    """

    def __init__(
        self,
        collection: Any,  # VDBMemoryCollection
        embedding_config: dict[str, Any],
        max_workers: int = 4,
        default_batch_size: int = 500,
    ):
        """Initialize ParallelVDBService.

        Args:
            collection: VDBMemoryCollection instance
            embedding_config: Configuration for EmbeddingService
                - method: "hf", "openai", "vllm", etc.
                - model: Model name/path
                - batch_size: Embedding batch size (default 64)
                - Other method-specific options
            max_workers: Maximum parallel workers (default 4)
            default_batch_size: Default texts per batch for storage (default 500)
        """
        super().__init__()
        self._collection = collection
        self._embedding_config = embedding_config
        self._max_workers = max_workers
        self._default_batch_size = default_batch_size
        self._embedding_service: Any = None
        self._executor: ThreadPoolExecutor | None = None

    def setup(self) -> None:
        """Initialize the service."""
        from sage.common.components.sage_embedding import EmbeddingService

        self.logger.info(
            f"ParallelVDBService setup: max_workers={self._max_workers}, "
            f"embedding_method={self._embedding_config.get('method')}"
        )

        # Setup embedding service
        self._embedding_service = EmbeddingService(self._embedding_config)
        self._embedding_service.setup()

        # Create thread pool
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

        self.logger.info("ParallelVDBService setup complete")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

        if self._embedding_service is not None:
            self._embedding_service.cleanup()
            self._embedding_service = None

        self.logger.info("ParallelVDBService cleanup complete")

    def parallel_batch_insert(
        self,
        texts: list[str],
        index_name: str,
        metadatas: list[dict[str, Any]] | None = None,
        batch_size: int | None = None,
        show_progress: bool = True,
    ) -> ParallelInsertResult:
        """Insert texts in parallel batches.

        This method:
        1. Splits texts into batches
        2. Submits batches to thread pool
        3. Each batch: embed texts -> insert vectors
        4. Aggregates results

        Args:
            texts: List of texts to insert
            index_name: Target index name in the collection
            metadatas: Optional list of metadata dicts (must match texts length)
            batch_size: Texts per batch (default: self._default_batch_size)
            show_progress: Print progress updates

        Returns:
            ParallelInsertResult with statistics
        """
        if self._embedding_service is None or self._executor is None:
            raise RuntimeError("Service not setup. Call setup() first.")

        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("metadatas length must match texts length")

        batch_size = batch_size or self._default_batch_size
        total_texts = len(texts)

        if total_texts == 0:
            return ParallelInsertResult(
                total_texts=0,
                total_inserted=0,
                total_failed=0,
                elapsed_seconds=0.0,
                throughput_per_second=0.0,
            )

        # Split into batches
        batches = []
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_metadatas = metadatas[i : i + batch_size] if metadatas else None
            batches.append((i, batch_texts, batch_metadatas))

        self.logger.info(
            f"Starting parallel insertion: {total_texts} texts, "
            f"{len(batches)} batches, batch_size={batch_size}"
        )

        start_time = time.time()
        batch_results = []
        total_inserted = 0
        total_failed = 0

        # Submit all batches
        futures = {
            self._executor.submit(
                self._process_batch, batch_idx, batch_texts, batch_metadatas, index_name
            ): batch_idx
            for batch_idx, batch_texts, batch_metadatas in batches
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                result = future.result()
                batch_results.append(result)
                total_inserted += result["inserted"]
                total_failed += result["failed"]
            except Exception as e:
                self.logger.error(f"Batch {batch_idx} failed: {e}")
                batch_results.append(
                    {
                        "batch_idx": batch_idx,
                        "inserted": 0,
                        "failed": batch_size,
                        "error": str(e),
                    }
                )
                total_failed += batch_size

            completed += 1
            if show_progress and completed % max(1, len(batches) // 10) == 0:
                progress = completed / len(batches) * 100
                self.logger.info(f"Progress: {progress:.1f}% ({completed}/{len(batches)} batches)")

        elapsed = time.time() - start_time
        throughput = total_texts / elapsed if elapsed > 0 else 0.0

        self.logger.info(
            f"Parallel insertion complete: {total_inserted}/{total_texts} inserted, "
            f"{total_failed} failed, {elapsed:.2f}s, {throughput:.0f} docs/sec"
        )

        return ParallelInsertResult(
            total_texts=total_texts,
            total_inserted=total_inserted,
            total_failed=total_failed,
            elapsed_seconds=elapsed,
            throughput_per_second=throughput,
            batch_results=batch_results,
        )

    def _process_batch(
        self,
        batch_idx: int,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None,
        index_name: str,
    ) -> dict[str, Any]:
        """Process a single batch: embed texts and insert to collection.

        This runs in a worker thread.

        Args:
            batch_idx: Batch index for tracking
            texts: Batch of texts
            metadatas: Optional batch of metadata dicts
            index_name: Target index name

        Returns:
            Dict with batch results
        """
        inserted = 0
        failed = 0
        errors: list[str] = []

        try:
            # Step 1: Batch embed texts
            embed_result = self._embedding_service.embed(texts, normalize=True)
            vectors = embed_result["vectors"]

            # Step 2: Insert each text+vector to collection (serial within batch)
            # neuromem is single-threaded, so we don't parallelize within batch
            for i, (text, vector) in enumerate(zip(texts, vectors, strict=False)):
                try:
                    metadata = metadatas[i] if metadatas else None
                    vector_np = np.array(vector, dtype=np.float32)

                    result = self._collection.insert(
                        content=text,
                        index_names=index_name,
                        vector=vector_np,
                        metadata=metadata,
                    )

                    if result is not None:
                        inserted += 1
                    else:
                        failed += 1
                        errors.append(f"Insert returned None for text {i}")

                except Exception as e:
                    failed += 1
                    errors.append(f"Insert error for text {i}: {str(e)}")

        except Exception as e:
            # Embedding failed for entire batch
            failed = len(texts)
            errors.append(f"Embedding failed: {str(e)}")

        return {
            "batch_idx": batch_idx,
            "batch_size": len(texts),
            "inserted": inserted,
            "failed": failed,
            "errors": errors[:5] if errors else [],  # Limit error messages
        }

    def get_collection(self) -> Any:
        """Get the underlying VDBMemoryCollection."""
        return self._collection

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "max_workers": self._max_workers,
            "default_batch_size": self._default_batch_size,
            "embedding_method": self._embedding_config.get("method"),
            "embedding_model": self._embedding_config.get("model"),
            "collection_name": getattr(self._collection, "name", "unknown"),
        }


# Convenience function for quick parallel insertion
def parallel_insert_to_vdb(
    texts: list[str],
    collection: Any,  # VDBMemoryCollection
    index_name: str,
    embedding_config: dict[str, Any],
    metadatas: list[dict[str, Any]] | None = None,
    max_workers: int = 4,
    batch_size: int = 500,
) -> ParallelInsertResult:
    """Convenience function for parallel VDB insertion.

    This is a one-shot function that creates a ParallelVDBService,
    performs the insertion, and cleans up.

    Args:
        texts: List of texts to insert
        collection: VDBMemoryCollection instance
        index_name: Target index name
        embedding_config: EmbeddingService configuration
        metadatas: Optional metadata list
        max_workers: Parallel workers
        batch_size: Texts per batch

    Returns:
        ParallelInsertResult with statistics

    Example:
        >>> from sage.middleware.components.sage_mem.services import parallel_insert_to_vdb
        >>> result = parallel_insert_to_vdb(
        ...     texts=["doc1", "doc2", ...],
        ...     collection=my_collection,
        ...     index_name="main_index",
        ...     embedding_config={"method": "hf", "model": "BAAI/bge-small-zh-v1.5"},
        ... )
        >>> print(f"Inserted {result.total_inserted} documents")
    """
    service = ParallelVDBService(
        collection=collection,
        embedding_config=embedding_config,
        max_workers=max_workers,
        default_batch_size=batch_size,
    )

    try:
        service.setup()
        return service.parallel_batch_insert(
            texts=texts,
            index_name=index_name,
            metadatas=metadatas,
            batch_size=batch_size,
        )
    finally:
        service.cleanup()


__all__ = [
    "ParallelVDBService",
    "ParallelInsertResult",
    "parallel_insert_to_vdb",
]
