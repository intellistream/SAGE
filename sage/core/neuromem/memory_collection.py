from sage.core.neuromem.default_memory import (
    get_default_memory_class,
)

class MemoryCollection:
    """
    A unified memory collection wrapper.
    """

    def __init__(self, name, embedding_model, backend: str | None = None):
        self.name = name
        self.memory = get_default_memory_class(name, backend)
        self.embedding_model = embedding_model

    def retrieve(self, raw_data: str | None = None, retrieve_func = None):
        """
        Retrieve data and support custom retrieval function 'retrievefunc'`
        """
        if self.name == "short_term_memory":
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
        if self.name == "short_term_memory":
            return self.memory.store(raw_data)
        else:
            embedding = self.embedding_model.encode(raw_data)
            if write_func:
                return write_func(raw_data, embedding, self.memory)
            else:
                return self.memory.store(raw_data, embedding)

    def clean(self):
        return self.memory.clean()
    
    
