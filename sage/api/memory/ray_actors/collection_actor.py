# api/serve/collection_actor.py
import ray
from sage.core.neuromem.memory_collection import MemoryCollection

@ray.remote
class CollectionActor:
    def __init__(self, name, embedding_model, backend=None):
        self.collection = MemoryCollection(name, embedding_model, backend)

    def store(self, raw_data, write_func=None):
        return self.collection.store(raw_data, write_func)

    def retrieve(self, raw_data=None, retrieve_func=None):
        return self.collection.retrieve(raw_data, retrieve_func)

    def clean(self):
        return self.collection.clean()

    def get_name(self):
        return self.collection.name
    
    # def retrieve_all(self):
    #     return self.collection.memory.retrieve(k=len(kv.collection.memory.storage))
