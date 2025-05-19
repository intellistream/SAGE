# api/ray_actors/composite_actor.py
import ray
from sage.core.neuromem_before.memory_composite import CompositeMemory

@ray.remote
class CompositeMemoryActor:
    def __init__(self, memory_actor_handles):
        self.memory_actors = memory_actor_handles

    def store(self, raw_data, write_func=None):
        for actor in self.memory_actors:
            actor.store.remote(raw_data, write_func)

    def retrieve(self, raw_data, retrieve_func=None):
        result_futures = [actor.retrieve.remote(raw_data, retrieve_func) for actor in self.memory_actors]
        results_nested = ray.get(result_futures)
        flat_results = [item for sublist in results_nested for item in sublist]
        return list(dict.fromkeys(flat_results))

    def flush_kv_to_vdb(self, kv, vdb):
        kv_data = ray.get(kv.retrieve.remote(k=len(kv.collection.memory.storage)))
        print(f"kv_data: {kv_data}")
        if not kv_data:
            return
        for item in kv_data:
            vdb.store.remote(item)
        kv.clean.remote() 
