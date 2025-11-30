"""ChromaDB VectorStore Adapter

Adapter that wraps ChromaBackend to implement the VectorStore protocol,
enabling it to work with IndexBuilder.

Layer: L3 (sage-libs/integrations)
Dependencies: sage.middleware.operators.rag.index_builder (L4 Protocol only - runtime_checkable)
"""

import json
from pathlib import Path
from typing import Any

from sage.libs.integrations.chroma import ChromaBackend


class ChromaVectorStoreAdapter:
    """Adapter wrapping ChromaBackend to implement VectorStore Protocol.

    This adapter enables ChromaBackend to work with IndexBuilder by
    implementing the VectorStore interface.

    Note: We don't formally implement the Protocol here (that would create
    L3→L4 dependency). Instead, we provide duck-typing compatibility.
    The Protocol is only for type checking at runtime.

    Args:
        persist_path: Directory to store ChromaDB data
        dim: Vector dimension (unused for Chroma, but required by Protocol)
        collection_name: Name of the Chroma collection
    """

    def __init__(
        self,
        persist_path: Path,
        dim: int,
        collection_name: str = "sage_index",
    ):
        """Initialize ChromaDB adapter.

        Args:
            persist_path: Path to persist ChromaDB data
            dim: Vector dimension (recorded but not enforced by Chroma)
            collection_name: Name of collection to use
        """
        self.persist_path = persist_path
        self.dim = dim
        self.collection_name = collection_name

        # Create parent directory
        persist_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaBackend with local persistence
        config = {
            "persistence_path": str(persist_path),
            "collection_name": collection_name,
            "metadata": {"hnsw:space": "cosine"},
        }

        self.backend = ChromaBackend(config)

        # Track documents for count
        self._doc_count = 0

    def add(self, vector: list[float], metadata: dict[str, Any]) -> None:
        """Add a single vector with metadata.

        Args:
            vector: Vector embedding
            metadata: Metadata dictionary
        """
        # ChromaBackend.add_documents expects batch format
        # We'll accumulate and flush periodically, or add one at a time
        doc_id = f"doc_{self._doc_count}"

        self.backend.add_documents(
            ids=[doc_id],
            embeddings=[vector],
            metadatas=[metadata],
            documents=[metadata.get("text", "")],  # Use 'text' field if available
        )

        self._doc_count += 1

    def build_index(self) -> None:
        """Build/optimize the index.

        ChromaDB builds indices automatically, so this is a no-op.
        """
        # ChromaDB automatically maintains indices
        pass

    def save(self, path: str) -> None:
        """Persist the vector store to disk.

        Args:
            path: Path to save (unused for Chroma - uses persistence_path from config)
        """
        # ChromaDB with PersistentClient automatically persists
        # Save metadata about the index
        manifest_path = Path(path).parent / "chroma_manifest.json"
        manifest = {
            "collection_name": self.collection_name,
            "persistence_path": str(self.persist_path),
            "dim": self.dim,
            "count": self._doc_count,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    def load(self, path: str) -> None:
        """Load vector store from disk.

        Args:
            path: Path to load from
        """
        # ChromaDB automatically loads from persistence_path
        # Try to load manifest for metadata
        manifest_path = Path(path).parent / "chroma_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
                self._doc_count = manifest.get("count", 0)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of result dictionaries with 'id', 'score', 'metadata'
        """
        # Use ChromaBackend.query
        results = self.backend.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=filter_dict,  # ChromaDB uses 'where' for metadata filtering
        )

        # Convert ChromaDB results to standard format
        formatted_results = []
        if results and "ids" in results:
            ids = results["ids"][0] if results["ids"] else []
            distances = results["distances"][0] if results["distances"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []

            for i, doc_id in enumerate(ids):
                formatted_results.append(
                    {
                        "id": doc_id,
                        "score": float(distances[i]) if i < len(distances) else 0.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                    }
                )

        return formatted_results

    def get_dim(self) -> int:
        """Get vector dimension.

        Returns:
            Vector dimension
        """
        return self.dim

    def count(self) -> int:
        """Get number of vectors in store.

        Returns:
            Number of stored vectors
        """
        # ChromaDB collection has a count method
        try:
            return self.backend.collection.count()
        except Exception:
            return self._doc_count
