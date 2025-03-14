from app.index_constructor.sparse_index_constructor.bm25_index_constructor import BM25IndexConstructor
from app.index_constructor.dense_index_constructor.faiss_index_constructor import FaissIndexConstructor

class IndexFactory:
    """Factory class for creating index constructors."""

    @staticmethod
    def create_index_constructor(model_name, **kwargs):
        """Create an index constructor based on the retrieval method."""
        if model_name == "bm25":
            return BM25IndexConstructor(**kwargs)
        elif model_name == "e5":
            return FaissIndexConstructor(model_name=model_name, **kwargs)
        else:
            raise ValueError(f"Unsupported retrieval method: {model_name}")