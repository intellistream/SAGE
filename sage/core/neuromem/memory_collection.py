from sage.core.neuromem.memory_backend import MemoryBackend

class MemoryCollection:
    """
    A unified memory collection wrapper.
    """
    def __init__(self, name, embedding_model, backend: str | None = None):
        self.name = name
        self.memory, self.backend_type = MemoryBackend.create_table(name, backend)
        self.embedding_model = embedding_model

    def retrieve(self, raw_data: str | None = None, retrieve_func = None):
        """
        Retrieve data and support custom retrieval function 'retrievefunc'`
        """
        if self.backend_type == "kv_backend":
            return self.memory.retrieve()
        else:
            embedding = self.embedding_model.encode(raw_data)
            if retrieve_func:
                return retrieve_func(embedding, self.memory)
            else:
                return self.memory.retrieve(embedding)

    def store(self, raw_data, write_func = None):
        """
        Store data and support custom storage function 'write _func'
        """
        if self.backend_type == "kv_backend":
            return self.memory.store(raw_data)
        else:
            embedding = self.embedding_model.encode(raw_data)
            if write_func:
                return write_func(raw_data, embedding, self.memory)
            else:
                return self.memory.store(raw_data, embedding)

    def clean(self):
        return self.memory.clean()
    
    
