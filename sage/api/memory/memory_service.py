# api/serve/manager_service.py
from ray import serve
import ray
# from sage.api.memory.ray_actors.collection_actor import CollectionActor
# from sage.api.memory.ray_actors.composite_actor import CompositeMemoryActor

@serve.deployment
class MemoryManagerService:
    pass 
    # def __init__(self):
    #     # 初始化空集合字典 | Initialize empty collections dictionary
    #     self.collections = {}

    # async def create_table(self, name, embedding_model, backend=None):
    #     # 如果表存在，重置它 | Reset table if it exists
    #     if name in self.collections:
    #         await self.collections[name].clean.remote()  # 可选重置 | Optional reset
    #     # 创建新的CollectionActor | Create new CollectionActor
    #     actor = CollectionActor.remote(name, embedding_model, backend)
    #     # 存储到collections | Store in collections
    #     self.collections[name] = actor
    #     return actor

    # async def get_table(self, name):
    #     # 获取指定表 | Get specified table
    #     return self.collections.get(name)

    # async def connect(self, *names):
    #     # 筛选存在的表 | Filter existing tables
    #     actors = [self.collections[n] for n in names if n in self.collections]
    #     # 创建复合内存actor | Create composite memory actor
    #     composite = CompositeMemoryActor.remote(actors)
    #     return composite

    # async def list_collections(self):
    #     # 返回所有表名 | Return all table names
    #     return list(self.collections.keys())