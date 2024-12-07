import torch
from src.core.memory.base_memory import BaseMemory

class StateMemory(BaseMemory):
    """
    A simple in-memory storage for non-persistent use cases, maintaining states.
    """

    def __init__(self):
        super().__init__()
        self.storage = []

    def store(self, item):
        """
        Store an item in memory.
        :param item: Data or state to store.
        """
        self.storage.append(item)
        self.logger.info("Successfully stored item in state memory.")

    def retrieve(self, query=None, k=1):
        """
        Retrieve items from memory.
        :param query: Query for retrieval (optional for some use cases).
        :param k: Number of items to retrieve.
        :return: List of retrieved items.
        """
        if query is None:
            self.logger.info("Retrieved all items from state memory.")
            return self.storage[:k]
        else:
            self.logger.warning("Query-based retrieval not supported in StateMemory.")
            return self.storage[:k]

    def delete(self, item):
        """
        Delete an item from memory.
        :param item: Item to delete.
        """
        try:
            self.storage.remove(item)
            self.logger.info("Successfully deleted item from state memory.")
        except ValueError:
            self.logger.warning("Item not found in state memory.")
        except Exception as e:
            self.logger.error(f"Error deleting item from state memory: {str(e)}")
            raise

    def clean(self):
        """
        Clean the memory, removing all items.
        """
        try:
            self.storage.clear()
            self.logger.info("Successfully cleaned state memory.")
        except Exception as e:
            self.logger.error(f"Error cleaning state memory: {str(e)}")
            raise

    def get_all_states(self):
        """
        Return all stored states as a list.
        :return: List of all stored states.
        """
        self.logger.info("Returning all stored states from state memory.")
        return self.storage