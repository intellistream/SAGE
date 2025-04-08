import logging

class BaseMemory:
    """
    Abstract base class for memory layers.
    Provides a consistent interface for memory layers.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def store(self, item, **kwargs):
        """
        Store an item in memory.
        """
        raise NotImplementedError("Store method must be implemented in subclasses.")

    def retrieve(self, query_embedding, k=1, **kwargs):
        """
        Retrieve items from memory.
        """
        raise NotImplementedError("Retrieve method must be implemented in subclasses.")

    def delete(self, item):
        """
        Delete an item from memory.
        """
        raise NotImplementedError("Delete method must be implemented in subclasses.")

    def clean(self):
        """
        Clean all items from memory.
        """
        raise NotImplementedError("Clean method must be implemented in subclasses.")