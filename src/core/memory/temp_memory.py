import torch
from src.core.memory.base_memory import BaseMemory


class SpecialMemory(BaseMemory):
    """
    A simple in-memory global storage for non-persistent use cases.
    """

    def __init__(self):
        super().__init__()
        self.storage = []

    def store(self, embedding):
        """
        Store an embedding in memory.
        :param embedding: Embedding to store.
        """
        self.storage.append(embedding)
        self.logger.info("Successfully stored embedding in special memory.")

    def retrieve(self, embedding, k=1):
        """
        Retrieve embeddings similar to the query embedding.
        :param embedding: Query embedding.
        :param k: Number of nearest embeddings to retrieve.
        :return: List of similar embeddings.
        """
        try:
            # Simple distance-based retrieval for in-memory storage
            distances = [(item, torch.dist(torch.tensor(item), torch.tensor(embedding)).item())
                         for item in self.storage]
            distances.sort(key=lambda x: x[1])
            results = [item[0] for item in distances[:k]]
            self.logger.info(f"Retrieved {len(results)} embedding(s) from special memory.")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving embeddings from special memory: {str(e)}")
            raise

    def delete(self, embedding):
        """
        Delete an embedding from memory.
        :param embedding: Embedding to delete.
        """
        try:
            self.storage.remove(embedding)
            self.logger.info("Successfully deleted embedding from special memory.")
        except ValueError:
            self.logger.warning("Embedding not found in special memory.")
        except Exception as e:
            self.logger.error(f"Error deleting embedding from special memory: {str(e)}")
            raise