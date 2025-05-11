class CompositeMemory:
    def __init__(self, memory_list: list):
        self.memory_list = memory_list

    def retrieve(self, raw_data: str, retrieve_func=None):
        results = []
        for mem in self.memory_list:
            results.extend(mem.retrieve(raw_data, retrieve_func))
        return list(dict.fromkeys(results))

    def store(self, raw_data: str, write_func=None):
        for mem in self.memory_list:
            mem.store(raw_data, write_func)

    # def flush_kv_to_vdb(self, kv, vdb):
    #     kv_data = kv.memory.retrieve(k=len(kv.memory.storage))
    #     if not kv_data:
    #         return
    #     for item in kv_data:
    #         vdb.store(item)
    #     kv.clean()
