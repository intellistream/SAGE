from abc import ABC, abstractmethod
from app.index_constructor.base_index_constructor.index_constructor import IndexConstructor

class SparseIndexConstructor(IndexConstructor, ABC):
    """Abstract base class for sparse index construction."""

    def __init__(self, corpus_path, save_dir):
        super().__init__(corpus_path, save_dir)

    @abstractmethod
    def build_index(self):
        """Build the sparse index. To be implemented by subclasses."""
        pass