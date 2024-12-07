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

    def store(self, item):
        """
        Store an embedding in the database.
        :param item: Embedding or tensor to store.
        """
        try:
            tensor = torch.from_numpy(item) if isinstance(item, (list, tuple)) else item
            self.db.insert_tensor(tensor.clone())
            self.logger.info("Successfully stored item in CANDY database.")
        except Exception as e:
            self.logger.error(f"Error storing item: {str(e)}")
            raise

    def retrieve(self, query, k=1):
        """
        Retrieve items based on a query embedding.
        :param query: Query embedding.
        :param k: Number of nearest neighbors to retrieve.
        :return: Retrieved embeddings or items.
        """
        try:
            tensor = torch.from_numpy(query) if isinstance(query, (list, tuple)) else query
            results = self.db.query_nearest_tensors(tensor.clone(), k)
            self.logger.info(f"Retrieved {len(results)} item(s) from CANDY database.")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving items: {str(e)}")
            raise

    def delete(self, item):
        """
        Delete an embedding from the database.
        :param item: Embedding or tensor to delete.
        """
        try:
            tensor = torch.from_numpy(item) if isinstance(item, (list, tuple)) else item
            success = self.db.remove_tensor(tensor.clone())
            if success:
                self.logger.info("Successfully deleted item from CANDY database.")
            else:
                self.logger.warning("Failed to delete item from CANDY database.")
        except Exception as e:
            self.logger.error(f"Error deleting item: {str(e)}")
            raise

    def clean(self):
        """
        Clean the entire CANDY database.
        """
        self.logger.error("CANDY database does not support bulk delete. Consider removing items individually.")
