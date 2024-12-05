import logging
import torch
from pycandy import VectorDB
from src.core.embedding.text_preprocessor import TextPreprocessor
from src.core.embedding.multimodal_preprocessor import MultimodalPreprocessor


class BaseMemory:
    """
    Base class for memory layers.
    Provides shared functionality for short-term and long-term memory.
    """

    def __init__(self, vector_dim, search_algorithm, multimodal=False):
        """
        Initialize the memory layer with CANDY VectorDB and embedding preprocessor.
        :param vector_dim: Dimension of the vector representation.
        :param search_algorithm: Search algorithm for vector retrieval.
        :param multimodal: Whether to use multimodal embeddings (text + images).
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = VectorDB(vector_dim, search_algorithm)
        self.text_preprocessor = TextPreprocessor()
        self.multimodal_preprocessor = MultimodalPreprocessor() if multimodal else None

    def _generate_embedding(self, key, value=None):
        """
        Generate an embedding for a given key (and optional value).
        :param key: Text key.
        :param value: Optional additional content (e.g., image path for multimodal embedding).
        :return: Embedding vector.
        """
        if self.multimodal_preprocessor and value:
            return self.multimodal_preprocessor.generate_multimodal_embedding(key, value)
        return self.text_preprocessor.generate_embedding(key)

    def store(self, key, value, additional=None):
        """
        Store a key-value pair in the memory layer.
        :param key: Text or identifier for the value.
        :param value: The content to store.
        :param additional: Optional additional content for multimodal embeddings.
        """
        try:
            embedding = self._generate_embedding(key, additional)
            tensor = torch.from_numpy(embedding)
            self.db.insert_tensor(tensor.clone())
            self.logger.info(f"Stored key-value pair: {key}")
        except Exception as e:
            self.logger.error(f"Error storing key-value pair: {str(e)}")
            raise

    def retrieve(self, query, k=1):
        """
        Retrieve the most relevant value(s) for a given query.
        :param query: Query text to search for.
        :param k: Number of nearest neighbors to retrieve.
        :return: Retrieved value(s).
        """
        try:
            query_embedding = self.text_preprocessor.generate_embedding(query)
            tensor = torch.from_numpy(query_embedding)
            results = self.db.query_nearest_tensors(tensor.clone(), k)
            self.logger.info(f"Retrieved {len(results)} result(s) for query: {query}")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving data for query: {str(e)}")
            raise

    def delete(self, key):
        """
        Delete a key-value pair from the memory layer.
        :param key: Identifier for the value to delete.
        """
        try:
            embedding = self.text_preprocessor.generate_embedding(key)
            tensor = torch.from_numpy(embedding)
            success = self.db.remove_tensor(tensor.clone())
            if success:
                self.logger.info(f"Deleted key-value pair: {key}")
            else:
                self.logger.warning(f"Failed to delete key-value pair: {key}")
        except Exception as e:
            self.logger.error(f"Error deleting key-value pair: {str(e)}")
            raise

    def update(self, old_key, new_key, new_value, additional=None):
        """
        Update an existing key-value pair in the memory layer.
        :param old_key: Old identifier for the value.
        :param new_key: New identifier for the updated value.
        :param new_value: The new content to store.
        :param additional: Optional additional content for multimodal embeddings.
        """
        try:
            old_embedding = self.text_preprocessor.generate_embedding(old_key)
            new_embedding = self._generate_embedding(new_key, additional)
            old_tensor = torch.from_numpy(old_embedding)
            new_tensor = torch.from_numpy(new_embedding)
            self.db.update_tensor(old_tensor.clone(), new_tensor.clone())
            self.logger.info(f"Updated key-value pair: {old_key} -> {new_key}")
        except Exception as e:
            self.logger.error(f"Error updating key-value pair: {str(e)}")
            raise
