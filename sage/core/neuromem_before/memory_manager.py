import logging
from sage.core.neuromem_before.memory_composite import CompositeMemory
from sage.core.neuromem_before.memory_collection import MemoryCollection

class NeuronMemManager:
    """
    STM LTM DCM Manager
    """

    def __init__(self, memory_layers = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_layers = memory_layers or {}

    def register(self, memory_table_name, memory_collection):
        """
        Register a MemoryCollection instance.
        """
        if memory_table_name in self.memory_layers:
            self.logger.warning(f"Memory table {memory_table_name} already exists, overwriting.")

        self.memory_layers[memory_table_name] = memory_collection
        return memory_collection

    def list_collections(self):
        return list(self.memory_layers.values())

    def get(self, memory_table_name):
        return self.memory_layers.get(memory_table_name)

    def create_table(self, name, embedding_model, backend=None):
        mem = MemoryCollection(name, embedding_model, backend)
        self.register(name, mem)
        return mem

    def connect(self, *names) -> CompositeMemory:
        mem_list = [self.get(name) for name in names if self.get(name)]
        return CompositeMemory(mem_list)