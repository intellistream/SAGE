"""
Memory Orchestrator Service - 记忆编排微服务
协调KV和VDB服务，提供统一的记忆管理接口
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
import logging
import time
import uuid

from sage.runtime.service.base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.runtime.factory.service_factory import ServiceFactory
    from sage.runtime.service_context import ServiceContext


@dataclass
class MemoryConfig:
    """Memory服务配置"""
    kv_service_name: str = "kv_service"
    vdb_service_name: str = "vdb_service"
    default_vector_dimension: int = 384
    max_search_results: int = 50
    enable_caching: bool = True


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    session_id: str
    content: str
    vector: List[float]
    metadata: Dict[str, Any]
    timestamp: float
    memory_type: str = "conversation"


class MemoryOrchestratorService(BaseServiceTask):
    """
    记忆编排服务任务
    
    协调KV和VDB服务，提供统一的记忆管理接口
    在SAGE DAG中作为服务节点使用
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        super().__init__(service_factory, ctx)
        
        # 从service_factory获取配置
        self.config: MemoryConfig = getattr(service_factory, 'config', MemoryConfig())
        
        self.logger.info(f"Memory Orchestrator '{self.service_name}' initialized")
        self.logger.info(f"KV Service: {self.config.kv_service_name}")
        self.logger.info(f"VDB Service: {self.config.vdb_service_name}")
    
    def _start_service_instance(self):
        """启动Memory编排服务实例"""
        self.logger.info(f"Memory Orchestrator '{self.service_name}' started")
    
    def _stop_service_instance(self):
        """停止Memory编排服务实例"""
        self.logger.info(f"Memory Orchestrator '{self.service_name}' stopped")
    
    def _get_kv_service(self):
        """获取KV服务的代理"""
        if not hasattr(self, 'ctx') or self.ctx is None:
            raise RuntimeError("Service context not available")
        return self.ctx.service_manager.get_service_proxy(self.config.kv_service_name)
    
    def _get_vdb_service(self):
        """获取VDB服务的代理"""
        if not hasattr(self, 'ctx') or self.ctx is None:
            raise RuntimeError("Service context not available")
        return self.ctx.service_manager.get_service_proxy(self.config.vdb_service_name)
    
    # Memory操作方法 - 这些方法可以通过服务调用机制被调用
    
    def store_memory(
        self,
        session_id: str,
        content: str,
        vector: List[float],
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储记忆
        
        Args:
            session_id: 会话ID
            content: 记忆内容
            vector: 向量表示
            memory_type: 记忆类型
            metadata: 额外元数据
        
        Returns:
            str: 记忆ID
        """
        try:
            # 生成记忆ID
            memory_id = str(uuid.uuid4())
            timestamp = time.time()
            
            # 准备元数据
            full_metadata = {
                "session_id": session_id,
                "memory_type": memory_type,
                "timestamp": timestamp,
                **(metadata or {})
            }
            
            # 创建记忆项
            memory_item = MemoryItem(
                id=memory_id,
                session_id=session_id,
                content=content,
                vector=vector,
                metadata=full_metadata,
                timestamp=timestamp,
                memory_type=memory_type
            )
            
            # 存储到KV服务 (存储完整记忆数据)
            kv_service = self._get_kv_service()
            kv_data = {
                "id": memory_id,
                "session_id": session_id,
                "content": content,
                "memory_type": memory_type,
                "timestamp": timestamp,
                "metadata": full_metadata
            }
            
            kv_success = kv_service.put(f"memory:{memory_id}", kv_data)
            if not kv_success:
                raise RuntimeError("Failed to store memory in KV service")
            
            # 存储到VDB服务 (存储向量用于搜索)
            vdb_service = self._get_vdb_service()
            vdb_data = [{
                "id": memory_id,
                "vector": vector,
                "metadata": full_metadata
            }]
            
            vdb_success = vdb_service.add(vdb_data)
            if not vdb_success:
                # 回滚KV存储
                kv_service.delete(f"memory:{memory_id}")
                raise RuntimeError("Failed to store memory in VDB service")
            
            # 更新会话元数据
            self._update_session_metadata(session_id, memory_id)
            
            self.logger.debug(f"STORE memory: {memory_id} for session {session_id}")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            raise
    
    def search_memories(
        self,
        query_vector: List[float],
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关记忆
        
        Args:
            query_vector: 查询向量
            session_id: 限制在特定会话
            memory_type: 限制记忆类型
            limit: 返回结果数量
            score_threshold: 相似度阈值
        
        Returns:
            List[Dict]: 记忆列表
        """
        try:
            # 构建VDB查询条件
            where_conditions = {}
            if session_id:
                where_conditions["session_id"] = session_id
            if memory_type:
                where_conditions["memory_type"] = memory_type
            
            # 从VDB搜索相似向量
            vdb_service = self._get_vdb_service()
            search_results = vdb_service.search(
                query_vector=query_vector,
                n_results=min(limit, self.config.max_search_results),
                where=where_conditions if where_conditions else None
            )
            
            # 过滤分数
            if score_threshold is not None:
                search_results = [r for r in search_results if r['score'] <= score_threshold]
            
            # 从KV服务获取完整记忆数据
            kv_service = self._get_kv_service()
            memories = []
            
            for result in search_results:
                memory_id = result['id']
                memory_data = kv_service.get(f"memory:{memory_id}")
                
                if memory_data:
                    memory_with_score = {
                        **memory_data,
                        "similarity_score": result['score']
                    }
                    memories.append(memory_with_score)
                else:
                    self.logger.warning(f"Memory {memory_id} found in VDB but not in KV")
            
            self.logger.debug(f"SEARCH memories: found {len(memories)} results")
            return memories
            
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            return []
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取指定记忆"""
        try:
            kv_service = self._get_kv_service()
            memory_data = kv_service.get(f"memory:{memory_id}")
            
            if memory_data:
                self.logger.debug(f"GET memory: {memory_id} found")
                return memory_data
            else:
                self.logger.debug(f"GET memory: {memory_id} not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting memory {memory_id}: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆"""
        try:
            # 从KV服务删除
            kv_service = self._get_kv_service()
            kv_success = kv_service.delete(f"memory:{memory_id}")
            
            # 从VDB服务删除
            vdb_service = self._get_vdb_service()
            vdb_success = vdb_service.delete([memory_id])
            
            success = kv_success and vdb_success
            self.logger.debug(f"DELETE memory: {memory_id}, success: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    def get_session_memories(
        self,
        session_id: str,
        memory_type: Optional[str] = None,
        limit: Optional[int] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取会话的所有记忆"""
        try:
            # 获取会话元数据
            session_metadata = self.get_session_metadata(session_id)
            if not session_metadata:
                return []
            
            memory_ids = session_metadata.get('memory_ids', [])
            
            # 从KV服务获取记忆数据
            kv_service = self._get_kv_service()
            memories = []
            
            for memory_id in memory_ids:
                memory_data = kv_service.get(f"memory:{memory_id}")
                if memory_data:
                    # 应用过滤条件
                    if memory_type and memory_data.get('memory_type') != memory_type:
                        continue
                    
                    timestamp = memory_data.get('timestamp', 0)
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                    
                    memories.append(memory_data)
            
            # 按时间排序
            memories.sort(key=lambda m: m.get('timestamp', 0))
            
            # 应用限制
            if limit:
                memories = memories[-limit:]
            
            self.logger.debug(f"GET session memories: {session_id}, found {len(memories)} memories")
            return memories
            
        except Exception as e:
            self.logger.error(f"Error getting session memories {session_id}: {e}")
            return []
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话元数据"""
        try:
            kv_service = self._get_kv_service()
            metadata = kv_service.get(f"session:{session_id}")
            
            if metadata:
                self.logger.debug(f"GET session metadata: {session_id} found")
                return metadata
            else:
                self.logger.debug(f"GET session metadata: {session_id} not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting session metadata {session_id}: {e}")
            return None
    
    def _update_session_metadata(self, session_id: str, memory_id: str):
        """更新会话元数据"""
        try:
            kv_service = self._get_kv_service()
            
            # 获取现有元数据
            metadata = kv_service.get(f"session:{session_id}") or {
                "session_id": session_id,
                "memory_ids": [],
                "created_at": time.time(),
                "memory_count": 0
            }
            
            # 添加新记忆ID
            if memory_id not in metadata["memory_ids"]:
                metadata["memory_ids"].append(memory_id)
                metadata["memory_count"] = len(metadata["memory_ids"])
                metadata["updated_at"] = time.time()
            
            # 保存元数据
            kv_service.put(f"session:{session_id}", metadata)
            
        except Exception as e:
            self.logger.error(f"Error updating session metadata {session_id}: {e}")
    
    def clear_session(self, session_id: str) -> bool:
        """清空会话的所有记忆"""
        try:
            # 获取会话的所有记忆
            session_memories = self.get_session_memories(session_id)
            
            # 删除所有记忆
            success_count = 0
            for memory in session_memories:
                if self.delete_memory(memory['id']):
                    success_count += 1
            
            # 删除会话元数据
            kv_service = self._get_kv_service()
            kv_service.delete(f"session:{session_id}")
            
            self.logger.debug(f"CLEAR session: {session_id}, deleted {success_count} memories")
            return success_count == len(session_memories)
            
        except Exception as e:
            self.logger.error(f"Error clearing session {session_id}: {e}")
            return False
    
    def stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            base_stats = self.get_statistics()
            
            # 获取KV和VDB服务统计
            kv_service = self._get_kv_service()
            vdb_service = self._get_vdb_service()
            
            kv_stats = kv_service.stats() if hasattr(kv_service, 'stats') else {}
            vdb_stats = vdb_service.stats() if hasattr(vdb_service, 'stats') else {}
            
            memory_stats = {
                "kv_service_name": self.config.kv_service_name,
                "vdb_service_name": self.config.vdb_service_name,
                "vector_dimension": self.config.default_vector_dimension,
                "max_search_results": self.config.max_search_results,
                "kv_service_stats": kv_stats,
                "vdb_service_stats": vdb_stats
            }
            
            base_stats.update(memory_stats)
            return base_stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return self.get_statistics()


# 工厂函数，用于在DAG中创建Memory服务
def create_memory_service_factory(
    service_name: str = "memory_service",
    kv_service_name: str = "kv_service",
    vdb_service_name: str = "vdb_service",
    default_vector_dimension: int = 384,
    max_search_results: int = 50,
    enable_caching: bool = True
):
    """
    创建Memory编排服务工厂
    
    Args:
        service_name: 服务名称
        kv_service_name: KV服务名称
        vdb_service_name: VDB服务名称
        default_vector_dimension: 默认向量维度
        max_search_results: 最大搜索结果数
        enable_caching: 是否启用缓存
    
    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.runtime.factory.service_factory import ServiceFactory
    
    config = MemoryConfig(
        kv_service_name=kv_service_name,
        vdb_service_name=vdb_service_name,
        default_vector_dimension=default_vector_dimension,
        max_search_results=max_search_results,
        enable_caching=enable_caching
    )
    
    factory = ServiceFactory(service_name, MemoryOrchestratorService)
    factory.config = config
    return factory
