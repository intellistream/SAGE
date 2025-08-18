"""
Memory Service: 将Memory Manager包装成服务进程形式的封装层
"""
from typing import Dict, List, Any, Optional, Union
from sage.middleware.services.neuromem.memory_manager import MemoryManager
from sage.middleware.services.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.common.utils.logging.custom_logger import CustomLogger

class MemoryService:
    """
    Memory服务封装，对外提供统一的服务接口
    主要功能:
    1. 管理collections的创建、删除、重命名等
    2. 对collection进行数据操作(插入、查询、更新、删除)
    3. 对collection进行索引操作(创建、删除、重建)
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        self.manager = MemoryManager(data_dir)
        self.logger = CustomLogger()
        
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
                
            return {
                "status": "success",
                "message": f"Collection '{name}' created successfully",
                "collection_name": name
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def delete_collection(self, name: str) -> Dict[str, Any]:
        """删除指定collection"""
        try:
            self.manager.delete_collection(name)
            return {
                "status": "success",
                "message": f"Collection '{name}' deleted successfully"
            }
        except Exception as e:
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
            return {
                "status": "success",
                "collections": collections
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def rename_collection(self, old_name: str, new_name: str, 
                         new_description: Optional[str] = None) -> Dict[str, Any]:
        """重命名collection"""
        try:
            self.manager.rename(old_name, new_name, new_description)
            return {
                "status": "success",
                "message": f"Collection renamed from '{old_name}' to '{new_name}'"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """获取指定collection的详细信息"""
        try:
            info = self.manager.list_collection(name)
            return {
                "status": "success",
                "collection_info": info
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # Collection数据操作接口
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
            
            return {
                "status": "success",
                "message": "Data inserted successfully",
                "id": stable_id
            }
        except Exception as e:
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
            
            return {
                "status": "success",
                "message": "Data updated successfully",
                "new_id": new_id
            }
        except Exception as e:
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
            return {
                "status": "success",
                "message": "Data deleted successfully"
            }
        except Exception as e:
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
            
            return {
                "status": "success",
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # 索引操作接口
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
            
            return {
                "status": "success",
                "message": f"Index '{index_name}' created successfully"
            }
        except Exception as e:
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
            return {
                "status": "success",
                "message": f"Index '{index_name}' deleted successfully"
            }
        except Exception as e:
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
            return {
                "status": "success",
                "message": f"Index '{index_name}' rebuilt successfully"
            }
        except Exception as e:
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
            return {
                "status": "success",
                "indexes": indexes
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # 存储操作接口
    def store_collection(self, collection_name: str) -> Dict[str, Any]:
        """保存指定collection到磁盘"""
        try:
            collection = self.manager.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found")
                
            self.manager.store_collection(collection_name)
            return {
                "status": "success",
                "message": f"Collection '{collection_name}' stored successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self) -> Dict[str, Any]:
        """保存整个manager的所有信息到磁盘"""
        try:
            self.manager.store_collection()  # 保存所有已加载的collection
            return {
                "status": "success",
                "message": "All manager data stored successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
