import logging

class BaseMemory:
    """
    Abstract base class for memory layers.
    Provides a common interface for storing, retrieving, and deleting items.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def store(self, embedding):
        raise NotImplementedError("Store method must be implemented in subclasses.")

    def retrieve(self, embedding, k=1):
        raise NotImplementedError("Retrieve method must be implemented in subclasses.")

    def delete(self, embedding):
        raise NotImplementedError("Delete method must be implemented in subclasses.")
