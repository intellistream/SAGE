# File: sage/api/memory/memory_api.py

# from sage.core.neuronmem.collection import MemoryCollection
# from sage.core.neuronmem.manager import NeuronMemManager


def create_table(memory_table_name: str, memory_table_backend: str, embedding_model=None):
    """
    Create a new memory collection with specified backend and optional embedding_model model.

    Args:
        memory_table_name: unique name for the memory instance.
        memory_table_backend: backend identifier (e.g., "kv_store.rocksdb", "vector_db.candy").
        embedding_model: embedding_model model used for vector memory; only required for vector backends.

    Returns:
        A MemoryCollection instance.
    """
    # if embedding_model is None and memory_table_backend.startswith("vector_db"):
    #     raise ValueError("Vector memory backend requires an embedding_model model.")
    #
    # memory = MemoryCollection(name=memory_table_name, backend=memory_table_backend, embedding_model=embedding_model)
    # NeuronMemManager.register(memory_table_name, memory)
    # return memory
    return None

def connect(*memory_names: str):
    """
    Connect to one or more registered memory collections by name.

    Args:
        *memory_names: one or more memory names previously registered.

    Returns:
        A composite object allowing unified memory access (e.g., for retrieval).
    """
    # memory_list = [NeuronMemManager.get(name) for name in memory_names]
    #
    # class CompositeMemory:
    #     def retrieve(self, embedding, retrieval_func):
    #         results = []
    #         for mem in memory_list:
    #             results.extend(mem.retrieve(embedding, retrieval_func))
    #         return results
    #
    #     def write(self, data, write_func):
    #         for mem in memory_list:
    #             mem.write(data, write_func)

    # return CompositeMemory()
    return None


def retrieve_func():
    return None

def write_func():
    return None