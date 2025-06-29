# File: sage/api/memory/memory_api.py

from sage.core.neuromem.memory_manager import MemoryManager
# from sage.core.neuromem.memory_collection import MemoryCollection
# from sage.core.neuromem.memory_composite import CompositeMemory

_default_manager: MemoryManager | None = None

def init_default_manager() -> MemoryManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = MemoryManager()
    return _default_manager


def get_default_manager() -> MemoryManager:
    if _default_manager is None:
        raise RuntimeError("Default manager not initialized. Please call init_default_manager() first.")
    return _default_manager


def create_table():
    pass

def connect():
    pass

def retrieve_func():
    return None

def write_func():
    return None



# def create_table(
#     memory_table_name: str
#     , manager: NeuronMemManager
#     , embedding_model = default_model
#     , memory_table_backend: str | None = None
#     ) -> MemoryCollection:
#     """
#     Create a new memory table/collection and register it with the manager.
#     创建一个新的记忆表/集合并将其注册到管理器
    
#     Args:
#         memory_table_name: Name of the memory table to create
#                           要创建的记忆表名称
#         manager: Memory manager instance that handles registration
#                  处理注册的内存管理器实例
#         embedding_model: Model used for embedding generation (defaults to default_model)
#                         用于生成嵌入向量的模型(默认为default_model)
#         memory_table_backend: Optional backend for the memory table
#                              记忆表的可选后端
                             
#     Returns:
#         The newly created MemoryCollection instance
#         新创建的MemoryCollection实例
#     """
#     memory = MemoryCollection(memory_table_name, embedding_model, memory_table_backend)
#     manager.register(memory_table_name, memory)
#     # ref=manager.register.remote(memory_table_name, memory)
#     # ray.get(ref)
#     return memory

# def connect(manager: NeuronMemManager, *memory_names: str):
#     """
#     Connect to one or more registered memory collections by name.
#     按名称连接到一个或多个已注册的记忆集合
    
#     Args:
#         *memory_names: one or more memory names previously registered.
#                       一个或多个先前注册的记忆名称
                      
#     Returns:
#         A composite object allowing unified memory access (e.g., for retrieval).
#         一个复合对象，允许统一的记忆访问(例如用于检索)
#     """
#     memory_list = [manager.get(name) for name in memory_names]

#     class CompositeMemory:
#         """
#         Composite memory class that combines multiple memory collections
#         组合多个记忆集合的复合记忆类
#         """
        
#         def map(self, raw_data: str, retrieve_func=None):
#             """
#             map data from all connected memory collections
#             从所有连接的记忆集合中检索数据
            
#             Args:
#                 raw_data: Input data to map matches for
#                           用于检索匹配项的输入数据
#                 retrieve_func: Optional custom retrieval function
#                               可选的自定义检索函数
                              
#             Returns:
#                 List of unique results from all memory collections
#                 来自所有记忆集合的唯一结果列表
#             """
#             results = []
#             for mem in memory_list:
#                 results.extend(mem.map(raw_data, retrieve_func)) # type: ignore 
#             return list(dict.fromkeys(results))

#         def store(self, raw_data: str, write_func=None):
#             """
#             Store data to all connected memory collections
#             将数据存储到所有连接的记忆集合中
            
#             Args:
#                 raw_data: Data to be stored
#                           要存储的数据
#                 write_func: Optional custom write function
#                             可选的自定义写入函数
#             """
#             for mem in memory_list:
#                 mem.store(raw_data, write_func) # type: ignore 

#         def flush_kv_to_vdb(self, kv, vdb):
#             """
#             Transfer data from KV to VDB.
#             将数据从KV传输到VDB
            
#             Args:
#                 kv: Key-Value store instance
#                     Key-Value存储实例
#                 vdb: Vector database instance
#                      向量数据库实例
#             """
#             # map all KV data
#             # 检索所有KV数据
#             kv_data = kv.memory.map(k=len(kv.memory.storage))
#             if not kv_data:
#                 return

#             # Convert to embeddings and store in VDB
#             # 转换为嵌入向量并存储到VDB中
#             for item in kv_data:
#                 vdb.store(item)

#             # Clear KV storage after transfer
#             # 传输后清除KV存储
#             kv.clean()
    
#     return CompositeMemory()

# def get_default_manager():
#     return None