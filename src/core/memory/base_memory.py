import logging

class BaseMemory:
    """
    Abstract base class for memory layers.
    Provides a common interface for storing, retrieving, and managing states or embeddings.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def store(self, item):
        """
        Store an item in memory. Must be implemented in subclasses.
        :param item: Data or embedding to store.
        """
        raise NotImplementedError("Store method must be implemented in subclasses.")

    def retrieve(self, query=None, k=1):
        """
        Retrieve items from memory. Must be implemented in subclasses.
        :param query: Query for retrieval (optional for some memory types).
        :param k: Number of items to retrieve (if applicable).
        """
        raise NotImplementedError("Retrieve method must be implemented in subclasses.")

    def delete(self, item):
        """
        Delete an item from memory. Must be implemented in subclasses.
        :param item: Data or embedding to delete.
        """
        raise NotImplementedError("Delete method must be implemented in subclasses.")

    def clean(self):
        """
        Clean the memory, removing all items. Must be implemented in subclasses.
        """
        raise NotImplementedError("Clean method must be implemented in subclasses.")