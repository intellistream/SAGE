import torch
from pycandy import VectorDB

from src.core.memory.base_memory import BaseMemory


class PersistentMemory(BaseMemory):
    """
    Persistent memory layer that interfaces with the CANDY VectorDB backend.
    """

    def __init__(self, vector_dim, search_algorithm):
        super().__init__()
        self.db = VectorDB(vector_dim, search_algorithm)
        self.logger.info("Persistent memory initialized with CANDY database.")

    def store(self, embedding):
        """
        Store an embedding in the database.
        :param embedding: Precomputed embedding to store.
        """
        try:
            tensor = torch.from_numpy(embedding)
            self.db.insert_tensor(tensor.clone())
            self.logger.info("Successfully stored embedding in CANDY database.")
        except Exception as e:
            self.logger.error(f"Error storing embedding: {str(e)}")
            raise

    def retrieve(self, embedding, k=1):
        """
        Retrieve the most relevant embeddings based on a query embedding.
        :param embedding: Precomputed embedding to use as the query.
        :param k: Number of nearest neighbors to retrieve.
        :return: Retrieved embeddings.
        """
        try:
            tensor = torch.from_numpy(embedding)
            results = self.db.query_nearest_tensors(tensor.clone(), k)
            self.logger.info(f"Retrieved {len(results)} embedding(s) from CANDY database.")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving embeddings: {str(e)}")
            raise

    def delete(self, embedding):
        """
        Delete an embedding from the database.
        :param embedding: Precomputed embedding to delete.
        """
        try:
            tensor = torch.from_numpy(embedding)
            success = self.db.remove_tensor(tensor.clone())
            if success:
                self.logger.info("Successfully deleted embedding from CANDY database.")
            else:
                self.logger.warning("Failed to delete embedding from CANDY database.")
        except Exception as e:
            self.logger.error(f"Error deleting embedding: {str(e)}")
            raise
