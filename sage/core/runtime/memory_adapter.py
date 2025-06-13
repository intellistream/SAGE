# sage/runtime/memory_adapter.py
import ray
import asyncio
from typing import Union, Any, List

class MemoryAdapter:
    """内存集合适配器，统一处理Ray Actor和本地对象的调用"""
    
    def __init__(self):
        pass
    
    async def retrieve(self, memory_collection, query: str = None) -> List[str]:
        """检索方法 - 带详细调试信息"""
        
        # 打印调试信息
        # print(f"=== MemoryAdapter Debug Info ===")
        # print(f"Object type: {type(memory_collection)}")
        # print(f"Object class name: {memory_collection.__class__.__name__}")
        # print(f"Has retrieve method: {hasattr(memory_collection, 'retrieve')}")
        
        # if hasattr(memory_collection, 'retrieve'):
        #     retrieve_method = memory_collection.retrieve
        #     print(f"Retrieve method type: {type(retrieve_method)}")
        #     print(f"Has remote: {hasattr(retrieve_method, 'remote')}")
        #     print(f"Method dir: {[attr for attr in dir(retrieve_method) if not attr.startswith('_')]}")
        
        # # 检查Ray相关属性
        # ray_attrs = [attr for attr in dir(memory_collection) if 'ray' in attr.lower() or 'actor' in attr.lower()]
        # print(f"Ray-related attributes: {ray_attrs}")
        
        # print(f"Is Ray initialized: {ray.is_initialized()}")
        # print(f"================================")
        
        # 尝试检索
        try:
            # 先尝试远程调用
            if hasattr(memory_collection.retrieve, 'remote'):
                # print("Trying Ray remote call...")
                if query is not None:
                    future = memory_collection.retrieve.remote(query)
                else:
                    future = memory_collection.retrieve.remote()
                result = await self._ray_get_async(future)
                # print(f"Ray call successful: {len(result) if result else 0} items")
                return result or []
            else:
                # 尝试本地调用
                # print("Trying local call...")
                if query is not None:
                    if asyncio.iscoroutinefunction(memory_collection.retrieve):
                        result = await memory_collection.retrieve(query)
                    else:
                        result = memory_collection.retrieve(query)
                else:
                    if asyncio.iscoroutinefunction(memory_collection.retrieve):
                        result = await memory_collection.retrieve()
                    else:
                        result = memory_collection.retrieve()
                # print(f"Local call successful: {len(result) if result else 0} items")
                return result or []
                
        except Exception as e:
            print(f"Retrieve failed: {e}")
            return []
    
    def _is_ray_actor(self, obj) -> bool:
        """检查对象是否是Ray Actor"""
        return hasattr(obj, '_actor_id') and hasattr(obj, '_remote')
    
    async def _retrieve_from_ray_actor(self, actor, query: str = None) -> List[str]:
        """从Ray Actor检索"""
        try:
            if query is not None:
                # 有查询参数的检索（如LTM）
                future = actor.retrieve.remote(query)
            else:
                # 无查询参数的检索（如STM、DCM）
                future = actor.retrieve.remote()
            
            # 异步获取结果
            result = await self._ray_get_async(future)
            return result
            
        except Exception as e:
            print(f"Error retrieving from Ray actor: {e}")
            return []
    
    async def _retrieve_from_local_object(self, obj, query: str = None) -> List[str]:
        """从本地对象检索"""
        try:
            if query is not None:
                if asyncio.iscoroutinefunction(obj.retrieve):
                    result = await obj.retrieve(query)
                else:
                    result = obj.retrieve(query)
            else:
                if asyncio.iscoroutinefunction(obj.retrieve):
                    result = await obj.retrieve()
                else:
                    result = obj.retrieve()
            
            return result
            
        except Exception as e:
            print(f"Error retrieving from local object: {e}")
            return []
    
    async def _ray_get_async(self, future):
        """异步版本的ray.get"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ray.get, future)