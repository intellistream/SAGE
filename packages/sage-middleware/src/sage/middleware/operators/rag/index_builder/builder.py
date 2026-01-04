"""Index Builder - Service for building RAG vector indices

Layer: L4 (sage-middleware/operators/rag)
"""

import logging
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from sage.middleware.operators.rag.index_builder.manifest import IndexManifest
from sage.middleware.operators.rag.index_builder.storage import VectorStore

logger = logging.getLogger(__name__)


@contextmanager
def _optional_progress(show: bool, description: str, total: int | None = None):
    """Context manager for optional Rich progress bar.

    Args:
        show: Whether to show progress bar (False = silent mode)
        description: Task description
        total: Total number of items (None for indeterminate)

    Yields:
        Progress task update function: update(advance=1)
    """
    if not show:
        # Silent mode - yield a no-op update function
        def noop(**kwargs):
            pass

        yield noop
        return

    try:
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            transient=True,  # Clear after completion
        ) as progress:
            task = progress.add_task(description, total=total)

            def update(advance: int = 1, **kwargs):
                progress.update(task, advance=advance, **kwargs)

            yield update

    except ImportError:
        # Fallback if rich is not available
        logger.info(f"[Progress] {description}")

        def fallback_update(**kwargs):
            pass

        yield fallback_update


class IndexBuilder:
    """Service for building RAG vector indices with pluggable backends.

    This class orchestrates the complete index building workflow, using
    dependency injection to decouple from specific vector storage backends.

    Architecture Pattern:
        - L4 defines this builder (orchestration logic)
        - L4 provides SageDB backend (sage.middleware.components.sage_db)
        - L3 provides ChromaDB backend (sage.libs.integrations.chroma)
        - L6 uses IndexBuilder with injected backend factory

    Args:
        backend_factory: Function creating VectorStore instances
            Signature: (persist_path: Path, dim: int) -> VectorStore

    Example:
        >>> # In sage-cli (L6)
        >>> from sage.middleware.operators.rag.index_builder import IndexBuilder
        >>> from sage.middleware.components.sage_db import SageVDBBackend
        >>>
        >>> def factory(path: Path, dim: int):
        ...     return SageVDBBackend(path, dim)
        >>>
        >>> builder = IndexBuilder(backend_factory=factory)
        >>> manifest = builder.build_from_docs(
        ...     source_dir=Path("docs"),
        ...     persist_path=Path(".sage/db"),
        ...     embedding_model=embedder,
        ...     chunk_size=800,
        ...     chunk_overlap=160,
        ... )
    """

    def __init__(self, backend_factory: Callable[[Path, int], VectorStore]):
        """Initialize builder with backend factory.

        Args:
            backend_factory: Factory function for creating VectorStore instances
        """
        self.backend_factory = backend_factory

    def build_from_docs(
        self,
        source_dir: Path,
        persist_path: Path,
        embedding_model: Any,
        index_name: str = "default",
        chunk_size: int = 800,
        chunk_overlap: int = 160,
        document_processor: Callable[[Path], list[dict[str, Any]]] | None = None,
        max_documents: int | None = None,
        show_progress: bool = True,
    ) -> IndexManifest:
        """Build vector index from document directory.

        This method orchestrates the complete index building process:
        1. Create vector store backend
        2. Process documents (via document_processor or default)
        3. Chunk text content
        4. Generate embeddings
        5. Store vectors with metadata
        6. Build/optimize index
        7. Persist to disk
        8. Return manifest

        Args:
            source_dir: Directory containing source documents
            persist_path: Path to save the built index
            embedding_model: Model with embed() and get_dim() methods
            index_name: Unique identifier for this index
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between consecutive chunks
            document_processor: Optional custom document processing function
                If None, uses simple text extraction
                Signature: (source_dir: Path) -> list[dict] where dict has:
                    - "content": str (text content)
                    - "metadata": dict (doc_path, title, heading, etc.)
            max_documents: Optional limit on number of documents to process
            show_progress: Show Rich progress bar (False = quiet mode)

        Returns:
            IndexManifest with build statistics and metadata

        Raises:
            FileNotFoundError: If source_dir doesn't exist
            RuntimeError: If index building fails

        Example:
            >>> # Custom document processor for Markdown
            >>> def process_markdown(source_dir: Path):
            ...     chunks = []
            ...     for file in source_dir.glob("**/*.md"):
            ...         text = file.read_text()
            ...         chunks.append({
            ...             "content": text,
            ...             "metadata": {"doc_path": str(file.relative_to(source_dir))}
            ...         })
            ...     return chunks
            >>>
            >>> manifest = builder.build_from_docs(
            ...     source_dir=Path("docs"),
            ...     persist_path=Path(".sage/db"),
            ...     embedding_model=embedder,
            ...     document_processor=process_markdown,
            ... )
        """
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        logger.debug(f"Building index from {source_dir}")
        logger.debug(f"Backend: {self.backend_factory}")
        logger.debug(f"Chunk size: {chunk_size}, overlap: {chunk_overlap}")

        # Create vector store backend
        dim = embedding_model.get_dim()
        store = self.backend_factory(persist_path, dim)
        logger.debug(f"Created vector store with dimension {dim}")

        # Process documents
        if document_processor is None:
            # Default: simple text file processing
            logger.debug(
                "No document_processor provided, using default text extraction. "
                "For better results, provide a custom processor."
            )
            processed_docs = self._default_document_processor(source_dir, max_documents)
        else:
            processed_docs = document_processor(source_dir)
            if max_documents:
                processed_docs = processed_docs[:max_documents]

        logger.debug(f"Processed {len(processed_docs)} document sections")

        # Import chunking utility
        try:
            from sage.common.utils.document_processing import (
                chunk_text,
                sanitize_metadata_value,
                truncate_text,
            )
        except ImportError:
            logger.debug("Cannot import chunking utilities from sage.common, using simple split")

            def chunk_text(text: str, size: int, overlap: int) -> list[str]:
                # Fallback: simple fixed-size chunking
                chunks = []
                start = 0
                while start < len(text):
                    end = min(len(text), start + size)
                    chunks.append(text[start:end])
                    start += size - overlap
                return chunks

            def sanitize_metadata_value(val: str) -> str:
                # Remove problematic chars for JSON/C++ parser
                return (
                    val.replace("\\", "")
                    .replace("\n", " ")
                    .replace('"', "'")
                    .replace("{", "(")
                    .replace("}", ")")
                )

            def truncate_text(text: str, limit: int = 480) -> str:
                return text[:limit] if len(text) > limit else text

        # Embed and store (with chunking)
        # First pass: count total chunks for accurate progress
        all_chunks_data = []  # List of (chunk_text, base_metadata)
        unique_docs = set()

        for doc in processed_docs:
            content = doc["content"]
            base_metadata = doc["metadata"]

            # Track unique documents
            if "doc_path" in base_metadata:
                unique_docs.add(base_metadata["doc_path"])

            # Chunk the content
            content_chunks = chunk_text(content, chunk_size, chunk_overlap)

            for chunk_idx, chunk in enumerate(content_chunks):
                all_chunks_data.append((chunk, base_metadata, chunk_idx))

        total_chunks = len(all_chunks_data)
        logger.debug(f"Total chunks to embed: {total_chunks}")

        # Second pass: embed with accurate progress
        with _optional_progress(show_progress, "Embedding", total=total_chunks) as progress_update:
            for idx, (chunk, base_metadata, chunk_idx) in enumerate(all_chunks_data, start=1):
                # Generate embedding
                vector = embedding_model.embed(chunk)

                # Create metadata for this chunk
                metadata = {
                    **base_metadata,
                    "chunk": str(chunk_idx),
                    "text": sanitize_metadata_value(truncate_text(chunk, limit=1200)),
                }

                # Sanitize all string values
                metadata = {
                    k: sanitize_metadata_value(str(v)) if isinstance(v, str) else str(v)
                    for k, v in metadata.items()
                }

                # Store vector with metadata
                store.add(vector, metadata)
                progress_update(advance=1)

                if idx % 500 == 0:
                    logger.debug(f"Embedded {idx}/{total_chunks} chunks")

        logger.debug(f"Added {total_chunks} vectors from {len(unique_docs)} documents")

        # Build index
        logger.debug("Building vector index...")
        store.build_index()

        # Persist to disk
        logger.debug(f"Saving index to {persist_path}")
        store.save(str(persist_path))

        # Create manifest
        manifest = IndexManifest(
            index_name=index_name,
            backend_type=type(store).__name__,
            persist_path=persist_path,
            source_dir=str(source_dir),
            embedding_config={
                "model": type(embedding_model).__name__,
                "dim": dim,
            },
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            num_documents=len(unique_docs),
            num_chunks=total_chunks,
            created_at=datetime.utcnow().isoformat(),
        )

        logger.debug(f"Index built successfully: {manifest}")
        return manifest

    def _default_document_processor(
        self,
        source_dir: Path,
        max_documents: int | None = None,
    ) -> list[dict[str, Any]]:
        """Default document processor for plain text files.

        This is a fallback processor that simply reads text files.
        For production use, provide a custom processor that:
        - Handles specific formats (Markdown, PDF, etc.)
        - Implements smart chunking
        - Preserves document structure

        Args:
            source_dir: Directory to scan
            max_documents: Optional limit

        Returns:
            List of processed chunks with metadata
        """
        chunks = []
        text_files = list(source_dir.glob("**/*.txt")) + list(source_dir.glob("**/*.md"))

        if max_documents:
            text_files = text_files[:max_documents]

        for file_path in text_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = file_path.relative_to(source_dir)

                chunks.append(
                    {
                        "content": content,
                        "metadata": {
                            "doc_path": str(rel_path),
                            "title": file_path.stem,
                            "text": content[:1000],  # Preview
                        },
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")

        return chunks
