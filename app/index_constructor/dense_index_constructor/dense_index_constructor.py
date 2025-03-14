from abc import ABC, abstractmethod
import os
from app.index_constructor.base_index_constructor.index_constructor import IndexConstructor

class DenseIndexConstructor(IndexConstructor, ABC):
    """Abstract base class for dense index construction."""

    def __init__(
        self,
        corpus_path,
        save_dir,
        model_path,
        use_fp16,
        pooling_method,
        max_length,
        batch_size,
    ):
        super().__init__(corpus_path, save_dir)
        self.model_path = model_path
        self.max_length = max_length
        self.batch_size = batch_size
        self.use_fp16 = use_fp16
        self.pooling_method = pooling_method

    @abstractmethod
    def encode_all(self):
        """Encode all documents. To be implemented by subclasses."""
        pass

    @abstractmethod
    def save_index(self, all_embeddings, index_save_path):
        """Save the index. To be implemented by subclasses."""
        pass

    def build_index(self):
        """Build the dense index. To be implemented by subclasses."""
        pass