class MemoryBackend:
    def retrieve(self, embedding, retrieval_func):
        raise NotImplementedError

    def write(self, data, write_func):
        raise NotImplementedError
