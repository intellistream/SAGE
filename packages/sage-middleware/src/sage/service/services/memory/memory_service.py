"""
Memory Service - 记忆编排微服务
协调KV、VDB和Graph服务，提供统一的高级记忆管理接口
不再包含底层存储实现，而是通过服务调用机制协调其他微服务
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
    graph_service_name: str = "graph_service"
    default_vector_dimension: int = 384
    max_search_results: int = 50
    enable_caching: bool = True
    enable_knowledge_graph: bool = True


class MemoryService(BaseServiceTask):
    """
    记忆编排服务任务
    
    提供高级的记忆管理功能，协调KV、VDB和Graph微服务
    在SAGE DAG中作为服务节点使用
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        super().__init__(service_factory, ctx)
        
        # 从service_factory获取配置
        self.config: MemoryConfig = getattr(service_factory, 'config', MemoryConfig())
        
        self.logger.info(f"Memory Service '{self.service_name}' initialized")
        self.logger.info(f"KV Service: {self.config.kv_service_name}")
        self.logger.info(f"VDB Service: {self.config.vdb_service_name}")
        self.logger.info(f"Graph Service: {self.config.graph_service_name}")
    
    def _start_service_instance(self):
        """启动Memory服务实例"""
        self.logger.info(f"Memory Service '{self.service_name}' started")
    
    def _stop_service_instance(self):
        """停止Memory服务实例"""
        self.logger.info(f"Memory Service '{self.service_name}' stopped")
    
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
    
    def _get_graph_service(self):
        """获取Graph服务的代理"""
        if not hasattr(self, 'ctx') or self.ctx is None:
            raise RuntimeError("Service context not available")
        return self.ctx.service_manager.get_service_proxy(self.config.graph_service_name)
    
    # 高级记忆操作方法
    
    def store_memory(
        self,
        content: str,
        vector: List[float],
        session_id: Optional[str] = None,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        create_knowledge_graph: bool = False
    ) -> str:
        """
        存储记忆（高级API）
        
        Args:
            content: 记忆内容
            vector: 向量表示
            session_id: 会话ID
            memory_type: 记忆类型
            metadata: 额外元数据
            create_knowledge_graph: 是否创建知识图谱关系
        
        Returns:
            str: 记忆ID
        """
        try:
            memory_id = str(uuid.uuid4())
            timestamp = time.time()
            
            # 准备完整元数据
            full_metadata = {
                "session_id": session_id,
                "memory_type": memory_type,
                "timestamp": timestamp,
                "content_preview": content[:100],
                **(metadata or {})
            }
            
            # 存储到KV服务
            kv_service = self._get_kv_service()
            kv_data = {
                "id": memory_id,
                "content": content,
                "session_id": session_id,
                "memory_type": memory_type,
                "timestamp": timestamp,
                "metadata": full_metadata
            }
            
            kv_success = kv_service.put(f"memory:{memory_id}", kv_data)
            if not kv_success:
                raise RuntimeError("Failed to store memory in KV service")
            
            # 存储到VDB服务
            vdb_service = self._get_vdb_service()
            vdb_data = [{
                "id": memory_id,
                "vector": vector,
                "text": content,
                "metadata": full_metadata
            }]
            
            vdb_ids = vdb_service.add_vectors(vdb_data)
            if not vdb_ids:
                # 回滚KV存储
                kv_service.delete(f"memory:{memory_id}")
                raise RuntimeError("Failed to store memory in VDB service")
            
            # 如果启用知识图谱，创建节点和关系
            if create_knowledge_graph and self.config.enable_knowledge_graph:
                try:
                    graph_service = self._get_graph_service()
                    
                    # 创建记忆节点
                    node_data = {
                        "id": memory_id,
                        "labels": ["Memory", memory_type.capitalize()],
                        "properties": {
                            "content": content,
                            "timestamp": timestamp,
                            "session_id": session_id
                        }
                    }
                    graph_service.add_node(node_data)
                    
                    # 如果有会话ID，创建会话关系
                    if session_id:
                        # 确保会话节点存在
                        session_node = {
                            "id": f"session:{session_id}",
                            "labels": ["Session"],
                            "properties": {"session_id": session_id}
                        }
                        graph_service.add_node(session_node)
                        
                        # 创建关系
                        relationship = {
                            "from_node": f"session:{session_id}",
                            "to_node": memory_id,
                            "rel_type": "CONTAINS",
                            "properties": {"created_at": timestamp}
                        }
                        graph_service.add_relationship(relationship)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to create knowledge graph for memory {memory_id}: {e}")
            
            self.logger.debug(f"STORE memory: {memory_id}")
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
        similarity_threshold: Optional[float] = None,
        include_graph_context: bool = False
    ) -> List[Dict[str, Any]]:
        """
        搜索相关记忆（高级API）
        
        Args:
            query_vector: 查询向量
            session_id: 限制在特定会话
            memory_type: 限制记忆类型
            limit: 返回结果数量
            similarity_threshold: 相似度阈值
            include_graph_context: 是否包含图上下文信息
        
        Returns:
            List[Dict]: 增强的记忆列表
        """
        try:
            # 构建VDB查询条件
            metadata_filter = {}
            if session_id:
                metadata_filter["session_id"] = session_id
            if memory_type:
                metadata_filter["memory_type"] = memory_type
            
            # 从VDB搜索相似向量
            vdb_service = self._get_vdb_service()
            search_results = vdb_service.search_vectors(
                query_vector=query_vector,
                top_k=min(limit, self.config.max_search_results),
                metadata_filter=metadata_filter if metadata_filter else None
            )
            
            # 过滤相似度
            if similarity_threshold is not None:
                search_results = [r for r in search_results if r['distance'] <= similarity_threshold]
            
            # 从KV服务获取完整记忆数据
            kv_service = self._get_kv_service()
            memories = []
            
            for result in search_results:
                memory_id = result['id']
                memory_data = kv_service.get(f"memory:{memory_id}")
                
                if memory_data:
                    enhanced_memory = {
                        **memory_data,
                        "similarity_score": result['distance'],
                        "vector_text": result.get('text', ''),
                    }
                    
                    # 如果启用图上下文，获取相关的图信息
                    if include_graph_context and self.config.enable_knowledge_graph:
                        try:
                            graph_service = self._get_graph_service()
                            # 获取该记忆的图上下文（相邻节点和关系）
                            graph_context = graph_service.get_node_context(memory_id, depth=1)
                            enhanced_memory["graph_context"] = graph_context
                        except Exception as e:
                            self.logger.warning(f"Failed to get graph context for {memory_id}: {e}")
                            enhanced_memory["graph_context"] = {}
                    
                    memories.append(enhanced_memory)
                else:
                    self.logger.warning(f"Memory {memory_id} found in VDB but not in KV")
            
            self.logger.debug(f"SEARCH memories: found {len(memories)} results")
            return memories
            
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            return []
    
    def get_memory(self, memory_id: str, include_graph_context: bool = False) -> Optional[Dict[str, Any]]:
        """获取指定记忆（高级API）"""
        try:
            kv_service = self._get_kv_service()
            memory_data = kv_service.get(f"memory:{memory_id}")
            
            if memory_data:
                # 如果启用图上下文，获取相关信息
                if include_graph_context and self.config.enable_knowledge_graph:
                    try:
                        graph_service = self._get_graph_service()
                        graph_context = graph_service.get_node_context(memory_id, depth=1)
                        memory_data["graph_context"] = graph_context
                    except Exception as e:
                        self.logger.warning(f"Failed to get graph context for {memory_id}: {e}")
                        memory_data["graph_context"] = {}
                
                self.logger.debug(f"GET memory: {memory_id} found")
                return memory_data
            else:
                self.logger.debug(f"GET memory: {memory_id} not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting memory {memory_id}: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆（高级API）"""
        try:
            success = True
            
            # 从KV服务删除
            kv_service = self._get_kv_service()
            kv_success = kv_service.delete(f"memory:{memory_id}")
            if not kv_success:
                success = False
            
            # 从VDB服务删除
            vdb_service = self._get_vdb_service()
            vdb_success = vdb_service.delete_vectors([memory_id])
            if vdb_success == 0:
                success = False
            
            # 从图服务删除（如果启用）
            if self.config.enable_knowledge_graph:
                try:
                    graph_service = self._get_graph_service()
                    graph_service.delete_node(memory_id)
                except Exception as e:
                    self.logger.warning(f"Failed to delete graph node for {memory_id}: {e}")
            
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
        include_graph_analysis: bool = False
    ) -> Dict[str, Any]:
        """获取会话记忆（高级API）"""
        try:
            # 构建查询条件
            metadata_filter = {"session_id": session_id}
            if memory_type:
                metadata_filter["memory_type"] = memory_type
            
            # 从VDB获取会话中的所有记忆
            vdb_service = self._get_vdb_service()
            session_vectors = vdb_service.list_vectors(metadata_filter=metadata_filter)
            
            # 从KV获取完整数据
            kv_service = self._get_kv_service()
            memories = []
            
            for vector_data in session_vectors:
                memory_id = vector_data['id']
                memory_data = kv_service.get(f"memory:{memory_id}")
                if memory_data:
                    memories.append(memory_data)
            
            # 按时间排序
            memories.sort(key=lambda m: m.get('timestamp', 0))
            
            # 应用限制
            if limit:
                memories = memories[-limit:]
            
            result = {
                "session_id": session_id,
                "memory_count": len(memories),
                "memories": memories
            }
            
            # 如果启用图分析，提供会话的图分析
            if include_graph_analysis and self.config.enable_knowledge_graph:
                try:
                    graph_service = self._get_graph_service()
                    session_graph = graph_service.get_session_graph(session_id)
                    result["graph_analysis"] = session_graph
                except Exception as e:
                    self.logger.warning(f"Failed to get session graph analysis: {e}")
                    result["graph_analysis"] = {}
            
            self.logger.debug(f"GET session memories: {session_id}, found {len(memories)} memories")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting session memories {session_id}: {e}")
            return {"session_id": session_id, "memory_count": 0, "memories": []}
    
    def stats(self) -> Dict[str, Any]:
        """获取综合服务统计信息"""
        try:
            base_stats = self.get_statistics()
            
            # 获取各个服务的统计
            service_stats = {}
            
            try:
                kv_service = self._get_kv_service()
                service_stats["kv"] = kv_service.stats() if hasattr(kv_service, 'stats') else {}
            except Exception as e:
                service_stats["kv"] = {"error": str(e)}
            
            try:
                vdb_service = self._get_vdb_service()
                service_stats["vdb"] = vdb_service.stats() if hasattr(vdb_service, 'stats') else {}
            except Exception as e:
                service_stats["vdb"] = {"error": str(e)}
            
            if self.config.enable_knowledge_graph:
                try:
                    graph_service = self._get_graph_service()
                    service_stats["graph"] = graph_service.stats() if hasattr(graph_service, 'stats') else {}
                except Exception as e:
                    service_stats["graph"] = {"error": str(e)}
            
            memory_stats = {
                "config": {
                    "kv_service_name": self.config.kv_service_name,
                    "vdb_service_name": self.config.vdb_service_name,
                    "graph_service_name": self.config.graph_service_name,
                    "enable_knowledge_graph": self.config.enable_knowledge_graph,
                    "enable_caching": self.config.enable_caching
                },
                "services": service_stats
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
    graph_service_name: str = "graph_service",
    default_vector_dimension: int = 384,
    max_search_results: int = 50,
    enable_caching: bool = True,
    enable_knowledge_graph: bool = True
):
    """
    创建Memory服务工厂
    
    Args:
        service_name: 服务名称
        kv_service_name: KV服务名称
        vdb_service_name: VDB服务名称
        graph_service_name: Graph服务名称
        default_vector_dimension: 默认向量维度
        max_search_results: 最大搜索结果数
        enable_caching: 是否启用缓存
        enable_knowledge_graph: 是否启用知识图谱
    
    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.runtime.factory.service_factory import ServiceFactory
    
    config = MemoryConfig(
        kv_service_name=kv_service_name,
        vdb_service_name=vdb_service_name,
        graph_service_name=graph_service_name,
        default_vector_dimension=default_vector_dimension,
        max_search_results=max_search_results,
        enable_caching=enable_caching,
        enable_knowledge_graph=enable_knowledge_graph
    )
    
    factory = ServiceFactory(service_name, MemoryService)
    factory.config = config
    return factory
