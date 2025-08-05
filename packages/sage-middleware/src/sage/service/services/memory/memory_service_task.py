"""
Memory Service - 改造版本
继承BaseServiceTask，保留原有功能，适配SAGE框架
"""
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
from sage.service.memory.memory_manager import MemoryManager
from sage.service.memory.memory_collection.base_collection import BaseMemoryCollection
from sage.utils.logging.custom_logger import CustomLogger
from sage.runtime.service.base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.runtime.factory.service_factory import ServiceFactory
    from sage.runtime.service_context import ServiceContext


class MemoryServiceTask(BaseServiceTask):
    """
    Memory服务任务 - 继承BaseServiceTask
    
    保留原有MemoryService的完整功能，同时适配SAGE框架
    主要功能:
    1. 管理collections的创建、删除、重命名等
    2. 对collection进行数据操作(插入、查询、更新、删除)
    3. 对collection进行索引操作(创建、删除、重建)
    4. 作为SAGE DAG中的服务任务节点
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        super().__init__(service_factory, ctx)
        
        # 从service_factory获取配置
        config = getattr(service_factory, 'config', {})
        data_dir = config.get('data_dir', None)
        
        # 初始化原有的memory manager
        self.manager = MemoryManager(data_dir)
        
        self.logger.info(f"Memory Service '{self.service_name}' initialized with data_dir: {data_dir}")
    
    def _start_service_instance(self):
        """启动Memory服务实例"""
        self.logger.info(f"Memory Service '{self.service_name}' started")
    
    def _stop_service_instance(self):
        """停止Memory服务实例"""
        # 保存所有collection到磁盘
        try:
            self.manager.store_collection()
            self.logger.info(f"Memory Service '{self.service_name}' saved all collections")
        except Exception as e:
            self.logger.error(f"Error saving collections during shutdown: {e}")
        
        self.logger.info(f"Memory Service '{self.service_name}' stopped")
    
    # ============ Collection管理方法 ============
    
    def create_collection(self, name: str, backend_type: str, description: str = "", 
                         embedding_model: Optional[Any] = None, dim: Optional[int] = None) -> Dict[str, Any]:
        """创建新的collection"""
        try:
            collection = self.manager.create_collection(
                name=name,
                backend_type=backend_type,
                description=description,
                embedding_model=embedding_model,
                dim=dim
            )
            # 预先注册常用的元数据字段
            if hasattr(collection, "add_metadata_field"):
                # 注册基础字段
                collection.add_metadata_field("type")
                collection.add_metadata_field("date")
                collection.add_metadata_field("source")
                collection.add_metadata_field("index")
                collection.add_metadata_field("timestamp")
                
            self.logger.debug(f"Created collection: {name}")
            return {
                "status": "success",
                "message": f"Collection '{name}' created successfully",
                "collection_name": name
            }
        except Exception as e:
            self.logger.error(f"Error creating collection {name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def delete_collection(self, name: str) -> Dict[str, Any]:
        """删除指定collection"""
        try:
            self.manager.delete_collection(name)
            self.logger.debug(f"Deleted collection: {name}")
            return {
                "status": "success",
                "message": f"Collection '{name}' deleted successfully"
            }
        except Exception as e:
            self.logger.error(f"Error deleting collection {name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def list_collections(self) -> Dict[str, Any]:
        """列出所有collections及其信息"""
        try:
            collections = []
            for name, info in self.manager.collection_metadata.items():
                collections.append({
                    "name": name,
                    "description": info.get("description", ""),
                    "backend_type": info.get("backend_type", ""),
                    "status": self.manager.collection_status.get(name, "unknown")
                })
            
            self.logger.debug(f"Listed {len(collections)} collections")
            return {
                "status": "success",
                "collections": collections
            }
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def rename_collection(self, old_name: str, new_name: str, 
                         new_description: Optional[str] = None) -> Dict[str, Any]:
        """重命名collection"""
        try:
            self.manager.rename(old_name, new_name, new_description)
            self.logger.debug(f"Renamed collection: {old_name} -> {new_name}")
            return {
                "status": "success",
                "message": f"Collection renamed from '{old_name}' to '{new_name}'"
            }
        except Exception as e:
            self.logger.error(f"Error renaming collection {old_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """获取指定collection的详细信息"""
        try:
            info = self.manager.list_collection(name)
            self.logger.debug(f"Got collection info: {name}")
            return {
                "status": "success",
                "collection_info": info
            }
        except Exception as e:
            self.logger.error(f"Error getting collection info {name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    # ============ Collection数据操作方法 ============
    
    def insert_data(self, collection_name: str, text: str, 
                    metadata: Optional[Dict[str, Any]] = None,
                    index_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """向指定collection插入数据"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            index_names = index_names or []
            stable_id = collection.insert(text, metadata, *index_names)
            
            self.logger.debug(f"Inserted data into {collection_name}: {stable_id}")
            return {
                "status": "success",
                "message": "Data inserted successfully",
                "id": stable_id
            }
        except Exception as e:
            self.logger.error(f"Error inserting data into {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def update_data(self, collection_name: str, old_text: str, new_text: str,
                    new_metadata: Optional[Dict[str, Any]] = None,
                    index_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """更新指定collection中的数据"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            index_names = index_names or []
            new_id = collection.update(old_text, new_text, new_metadata, *index_names)
            
            self.logger.debug(f"Updated data in {collection_name}: {new_id}")
            return {
                "status": "success",
                "message": "Data updated successfully",
                "new_id": new_id
            }
        except Exception as e:
            self.logger.error(f"Error updating data in {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def delete_data(self, collection_name: str, text: str) -> Dict[str, Any]:
        """从指定collection删除数据"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            collection.delete(text)
            self.logger.debug(f"Deleted data from {collection_name}")
            return {
                "status": "success",
                "message": "Data deleted successfully"
            }
        except Exception as e:
            self.logger.error(f"Error deleting data from {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def retrieve_data(self, collection_name: str, query_text: str,
                      topk: Optional[int] = None,
                      index_name: Optional[str] = None,
                      with_metadata: bool = False,
                      metadata_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """从指定collection检索数据"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
            
            metadata_conditions = metadata_filter or {}
            results = collection.retrieve(
                query_text,
                topk=topk,
                index_name=index_name,
                with_metadata=with_metadata,
                **metadata_conditions
            )
            
            self.logger.debug(f"Retrieved {len(results)} items from {collection_name}")
            return {
                "status": "success",
                "results": results
            }
        except Exception as e:
            self.logger.error(f"Error retrieving data from {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    # ============ 索引操作方法 ============
    
    def create_index(self, collection_name: str, index_name: str,
                     description: Optional[str] = None,
                     metadata_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """为指定collection创建索引"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
            
            metadata_conditions = metadata_conditions or {}
            collection.create_index(
                index_name=index_name,
                description=description,
                **metadata_conditions
            )
            
            self.logger.debug(f"Created index {index_name} for {collection_name}")
            return {
                "status": "success",
                "message": f"Index '{index_name}' created successfully"
            }
        except Exception as e:
            self.logger.error(f"Error creating index {index_name} for {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def delete_index(self, collection_name: str, index_name: str) -> Dict[str, Any]:
        """删除指定collection的索引"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            collection.delete_index(index_name)
            self.logger.debug(f"Deleted index {index_name} from {collection_name}")
            return {
                "status": "success",
                "message": f"Index '{index_name}' deleted successfully"
            }
        except Exception as e:
            self.logger.error(f"Error deleting index {index_name} from {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def rebuild_index(self, collection_name: str, index_name: str) -> Dict[str, Any]:
        """重建指定collection的索引"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            collection.rebuild_index(index_name)
            self.logger.debug(f"Rebuilt index {index_name} for {collection_name}")
            return {
                "status": "success",
                "message": f"Index '{index_name}' rebuilt successfully"
            }
        except Exception as e:
            self.logger.error(f"Error rebuilding index {index_name} for {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def list_indexes(self, collection_name: str) -> Dict[str, Any]:
        """列出指定collection的所有索引"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            indexes = collection.list_index()
            self.logger.debug(f"Listed {len(indexes)} indexes for {collection_name}")
            return {
                "status": "success",
                "indexes": indexes
            }
        except Exception as e:
            self.logger.error(f"Error listing indexes for {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    # ============ 存储操作方法 ============
    
    def store_collection(self, collection_name: str) -> Dict[str, Any]:
        """保存指定collection到磁盘"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            self.manager.store_collection(collection_name)
            self.logger.debug(f"Stored collection {collection_name} to disk")
            return {
                "status": "success",
                "message": f"Collection '{collection_name}' stored successfully"
            }
        except Exception as e:
            self.logger.error(f"Error storing collection {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def store_all(self) -> Dict[str, Any]:
        """保存整个manager的所有信息到磁盘"""
        try:
            self.manager.store_collection()  # 保存所有已加载的collection
            self.logger.debug("Stored all collections to disk")
            return {
                "status": "success",
                "message": "All manager data stored successfully"
            }
        except Exception as e:
            self.logger.error(f"Error storing all collections: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        base_stats = self.get_statistics()
        
        memory_stats = {
            "collections_count": len(self.manager.collection_metadata),
            "loaded_collections": len(self.manager.collections),
            "data_dir": self.manager.data_dir,
            "collections": list(self.manager.collection_metadata.keys())
        }
        
        base_stats.update(memory_stats)
        return base_stats


# 工厂函数，用于在DAG中创建Memory服务
def create_memory_service_factory(
    service_name: str = "memory_service",
    data_dir: Optional[str] = None
):
    """
    创建Memory服务工厂
    
    Args:
        service_name: 服务名称
        data_dir: 数据目录路径
    
    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.runtime.factory.service_factory import ServiceFactory
    
    config = {
        "data_dir": data_dir
    }
    
    factory = ServiceFactory(service_name, MemoryServiceTask)
    factory.config = config
    return factory


# 保持向后兼容性的别名
MemoryService = MemoryServiceTask
