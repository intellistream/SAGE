"""Index Manifest - Metadata describing a built RAG index

Layer: L4 (sage-middleware/operators/rag)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class IndexManifest:
    """Metadata describing a built knowledge index.

    This dataclass stores comprehensive metadata about a vector index,
    including source information, embedding configuration, and statistics.

    Attributes:
        index_name: Unique identifier for this index
        backend_type: Storage backend ("sagedb", "chromadb", "milvus", etc.)
        persist_path: Path where the index is stored
        source_dir: Original document directory
        embedding_config: Embedding model configuration
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters
        num_documents: Total number of documents indexed
        num_chunks: Total number of text chunks (vectors) stored
        created_at: ISO timestamp of index creation
        metadata: Additional custom metadata

    Example:
        >>> manifest = IndexManifest(
        ...     index_name="docs-public",
        ...     backend_type="chromadb",
        ...     persist_path=Path(".sage/vector_db"),
        ...     source_dir="docs-public/docs_src",
        ...     embedding_config={"method": "hash", "dim": 384},
        ...     chunk_size=800,
        ...     chunk_overlap=160,
        ...     num_documents=124,
        ...     num_chunks=2720,
        ...     created_at=datetime.utcnow().isoformat(),
        ... )
    """

    index_name: str
    backend_type: str
    persist_path: Path
    source_dir: str
    embedding_config: dict[str, Any]
    chunk_size: int
    chunk_overlap: int
    num_documents: int
    num_chunks: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary for serialization."""
        return {
            "index_name": self.index_name,
            "backend_type": self.backend_type,
            "persist_path": str(self.persist_path),
            "source_dir": self.source_dir,
            "embedding_config": self.embedding_config,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "num_documents": self.num_documents,
            "num_chunks": self.num_chunks,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexManifest":
        """Create manifest from dictionary."""
        data_copy = data.copy()
        data_copy["persist_path"] = Path(data_copy["persist_path"])
        return cls(**data_copy)

    @property
    def age_seconds(self) -> float:
        """Get age of index in seconds since creation."""
        created = datetime.fromisoformat(self.created_at)
        return (datetime.utcnow() - created).total_seconds()

    @property
    def is_empty(self) -> bool:
        """Check if index contains any data."""
        return self.num_chunks == 0

    def __repr__(self) -> str:
        """Readable representation of manifest."""
        return (
            f"IndexManifest("
            f"name={self.index_name!r}, "
            f"backend={self.backend_type!r}, "
            f"docs={self.num_documents}, "
            f"chunks={self.num_chunks})"
        )
