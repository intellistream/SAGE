"""
Graph Service - 图数据库微服务
提供图存储、知识图谱和图查询功能的服务任务，集成到SAGE DAG中
支持Neo4j和内存图后端
"""
from typing import Dict, Any, Optional, List, Union, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import logging
import time
import uuid

from sage.kernel.runtime.service.base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.kernel.runtime.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.service_context import ServiceContext


@dataclass
class GraphConfig:
    """Graph服务配置"""
    backend_type: str = "memory"  # "memory" 或 "neo4j"
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None
    max_nodes: int = 100000
    max_relationships: int = 500000


@dataclass
class GraphNode:
    """图节点"""
    id: str
    labels: List[str]
    properties: Dict[str, Any]
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class GraphRelationship:
    """图关系"""
    id: str
    from_node: str
    to_node: str
    rel_type: str
    properties: Dict[str, Any]
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class MemoryGraphBackend:
    """内存图数据库后端"""
    
    def __init__(self, max_nodes: int = 100000, max_relationships: int = 500000):
        self.nodes: Dict[str, GraphNode] = {}
        self.relationships: Dict[str, GraphRelationship] = {}
        self.node_relationships: Dict[str, List[str]] = {}  # node_id -> [rel_ids]
        self.max_nodes = max_nodes
        self.max_relationships = max_relationships
        self.logger = logging.getLogger(__name__)
    
    def create_node(self, node: GraphNode) -> str:
        """创建节点"""
        if len(self.nodes) >= self.max_nodes:
            raise RuntimeError(f"Maximum nodes limit reached: {self.max_nodes}")
        
        if not node.id:
            node.id = f"node_{uuid.uuid4()}"
        
        self.nodes[node.id] = node
        if node.id not in self.node_relationships:
            self.node_relationships[node.id] = []
        
        self.logger.debug(f"Created node: {node.id}")
        return node.id
    
    def create_relationship(self, rel: GraphRelationship) -> str:
        """创建关系"""
        if len(self.relationships) >= self.max_relationships:
            raise RuntimeError(f"Maximum relationships limit reached: {self.max_relationships}")
        
        if rel.from_node not in self.nodes or rel.to_node not in self.nodes:
            raise ValueError("Both nodes must exist before creating relationship")
        
        if not rel.id:
            rel.id = f"rel_{uuid.uuid4()}"
        
        self.relationships[rel.id] = rel
        
        # 更新节点关系索引
        if rel.from_node not in self.node_relationships:
            self.node_relationships[rel.from_node] = []
        if rel.to_node not in self.node_relationships:
            self.node_relationships[rel.to_node] = []
        
        self.node_relationships[rel.from_node].append(rel.id)
        self.node_relationships[rel.to_node].append(rel.id)
        
        self.logger.debug(f"Created relationship: {rel.id}")
        return rel.id
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_relationship(self, rel_id: str) -> Optional[GraphRelationship]:
        """获取关系"""
        return self.relationships.get(rel_id)
    
    def find_nodes(self, labels: Optional[List[str]] = None, 
                   properties: Optional[Dict[str, Any]] = None) -> List[GraphNode]:
        """查找节点"""
        results = []
        for node in self.nodes.values():
            # 检查标签
            if labels and not any(label in node.labels for label in labels):
                continue
            
            # 检查属性
            if properties:
                if not all(node.properties.get(k) == v for k, v in properties.items()):
                    continue
            
            results.append(node)
        
        return results
    
    def get_node_relationships(self, node_id: str, direction: str = "both") -> List[GraphRelationship]:
        """获取节点的关系"""
        if node_id not in self.node_relationships:
            return []
        
        rel_ids = self.node_relationships[node_id]
        relationships = []
        
        for rel_id in rel_ids:
            rel = self.relationships.get(rel_id)
            if not rel:
                continue
            
            if direction == "outgoing" and rel.from_node != node_id:
                continue
            elif direction == "incoming" and rel.to_node != node_id:
                continue
            
            relationships.append(rel)
        
        return relationships
    
    def delete_node(self, node_id: str) -> bool:
        """删除节点及其关系"""
        if node_id not in self.nodes:
            return False
        
        # 删除相关的关系
        if node_id in self.node_relationships:
            rel_ids = list(self.node_relationships[node_id])
            for rel_id in rel_ids:
                self.delete_relationship(rel_id)
        
        # 删除节点
        del self.nodes[node_id]
        if node_id in self.node_relationships:
            del self.node_relationships[node_id]
        
        return True
    
    def delete_relationship(self, rel_id: str) -> bool:
        """删除关系"""
        if rel_id not in self.relationships:
            return False
        
        rel = self.relationships[rel_id]
        
        # 从节点关系索引中移除
        if rel.from_node in self.node_relationships:
            self.node_relationships[rel.from_node] = [
                r for r in self.node_relationships[rel.from_node] if r != rel_id
            ]
        
        if rel.to_node in self.node_relationships:
            self.node_relationships[rel.to_node] = [
                r for r in self.node_relationships[rel.to_node] if r != rel_id
            ]
        
        del self.relationships[rel_id]
        return True
    
    def count_nodes(self) -> int:
        """获取节点数量"""
        return len(self.nodes)
    
    def count_relationships(self) -> int:
        """获取关系数量"""
        return len(self.relationships)
    
    def clear(self) -> None:
        """清空图数据"""
        self.nodes.clear()
        self.relationships.clear()
        self.node_relationships.clear()


class Neo4jGraphBackend:
    """Neo4j图数据库后端"""
    
    def __init__(self, uri: str, user: str, password: str):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.logger = logging.getLogger(__name__)
            
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.logger.info(f"Connected to Neo4j: {uri}")
        except ImportError:
            raise ImportError("Neo4j package not installed. Run: pip install neo4j")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def create_node(self, node: GraphNode) -> str:
        """创建节点"""
        with self.driver.session() as session:
            labels_str = ":".join(node.labels) if node.labels else ""
            query = f"CREATE (n:{labels_str} $properties) RETURN n"
            
            if not node.id:
                node.id = f"node_{uuid.uuid4()}"
            
            properties = {**node.properties, "id": node.id, "created_at": node.created_at}
            result = session.run(query, properties=properties)
            
            self.logger.debug(f"Created Neo4j node: {node.id}")
            return node.id
    
    def create_relationship(self, rel: GraphRelationship) -> str:
        """创建关系"""
        with self.driver.session() as session:
            if not rel.id:
                rel.id = f"rel_{uuid.uuid4()}"
            
            query = """
            MATCH (a {id: $from_node}), (b {id: $to_node})
            CREATE (a)-[r:%s $properties]->(b)
            RETURN r
            """ % rel.rel_type
            
            properties = {**rel.properties, "id": rel.id, "created_at": rel.created_at}
            session.run(query, 
                       from_node=rel.from_node, 
                       to_node=rel.to_node, 
                       properties=properties)
            
            self.logger.debug(f"Created Neo4j relationship: {rel.id}")
            return rel.id
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """获取节点"""
        with self.driver.session() as session:
            query = "MATCH (n {id: $node_id}) RETURN n, labels(n) as labels"
            result = session.run(query, node_id=node_id)
            
            record = result.single()
            if not record:
                return None
            
            node_data = dict(record["n"])
            labels = record["labels"]
            
            return GraphNode(
                id=node_data.pop("id"),
                labels=labels,
                properties=node_data,
                created_at=node_data.get("created_at", time.time())
            )
    
    def find_nodes(self, labels: Optional[List[str]] = None, 
                   properties: Optional[Dict[str, Any]] = None) -> List[GraphNode]:
        """查找节点"""
        with self.driver.session() as session:
            where_clauses = []
            params = {}
            
            if labels:
                label_str = ":".join(labels)
                query = f"MATCH (n:{label_str})"
            else:
                query = "MATCH (n)"
            
            if properties:
                for i, (k, v) in enumerate(properties.items()):
                    param_name = f"prop_{i}"
                    where_clauses.append(f"n.{k} = ${param_name}")
                    params[param_name] = v
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " RETURN n, labels(n) as labels"
            
            result = session.run(query, **params)
            nodes = []
            
            for record in result:
                node_data = dict(record["n"])
                labels = record["labels"]
                
                nodes.append(GraphNode(
                    id=node_data.pop("id"),
                    labels=labels,
                    properties=node_data,
                    created_at=node_data.get("created_at", time.time())
                ))
            
            return nodes
    
    def clear(self) -> None:
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            self.logger.debug("Cleared Neo4j database")


class GraphService(BaseServiceTask):
    """
    Graph服务任务
    
    提供图存储、知识图谱和图查询功能，可以在SAGE DAG中作为服务节点使用
    支持内存和Neo4j后端
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        super().__init__(service_factory, ctx)
        
        # 从service_factory获取配置
        self.config: GraphConfig = getattr(service_factory, 'config', GraphConfig())
        
        # 初始化后端
        if self.config.backend_type == "neo4j":
            if not all([self.config.neo4j_uri, self.config.neo4j_user, self.config.neo4j_password]):
                raise ValueError("Neo4j URI, user and password required for Neo4j backend")
            self.backend = Neo4jGraphBackend(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password
            )
            self.logger.info(f"Graph Service '{self.service_name}' initialized with Neo4j backend")
        else:
            self.backend = MemoryGraphBackend(
                self.config.max_nodes,
                self.config.max_relationships
            )
            self.logger.info(f"Graph Service '{self.service_name}' initialized with memory backend")
    
    def _start_service_instance(self):
        """启动Graph服务实例"""
        self.logger.info(f"Graph Service '{self.service_name}' started")
    
    def _stop_service_instance(self):
        """停止Graph服务实例"""
        self.logger.info(f"Graph Service '{self.service_name}' stopped")
    
    # Graph操作方法 - 这些方法可以通过服务调用机制被调用
    
    def create_node(self, labels: List[str], properties: Dict[str, Any], 
                   node_id: Optional[str] = None) -> str:
        """创建节点"""
        self.logger.debug(f"Creating node with labels: {labels}")
        
        node = GraphNode(
            id=node_id or "",
            labels=labels,
            properties=properties
        )
        
        result = self.backend.create_node(node)
        self.logger.debug(f"Created node: {result}")
        return result
    
    def create_relationship(self, from_node: str, to_node: str, rel_type: str,
                          properties: Optional[Dict[str, Any]] = None,
                          rel_id: Optional[str] = None) -> str:
        """创建关系"""
        self.logger.debug(f"Creating relationship: {from_node} -[{rel_type}]-> {to_node}")
        
        rel = GraphRelationship(
            id=rel_id or "",
            from_node=from_node,
            to_node=to_node,
            rel_type=rel_type,
            properties=properties or {}
        )
        
        result = self.backend.create_relationship(rel)
        self.logger.debug(f"Created relationship: {result}")
        return result
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点"""
        self.logger.debug(f"Getting node: {node_id}")
        
        node = self.backend.get_node(node_id)
        if node:
            return {
                "id": node.id,
                "labels": node.labels,
                "properties": node.properties,
                "created_at": node.created_at
            }
        return None
    
    def find_nodes(self, labels: Optional[List[str]] = None,
                  properties: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """查找节点"""
        self.logger.debug(f"Finding nodes with labels: {labels}, properties: {properties}")
        
        nodes = self.backend.find_nodes(labels, properties)
        results = []
        for node in nodes:
            results.append({
                "id": node.id,
                "labels": node.labels,
                "properties": node.properties,
                "created_at": node.created_at
            })
        
        self.logger.debug(f"Found {len(results)} nodes")
        return results
    
    def get_node_relationships(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """获取节点的关系"""
        self.logger.debug(f"Getting relationships for node: {node_id}, direction: {direction}")
        
        if hasattr(self.backend, 'get_node_relationships'):
            relationships = self.backend.get_node_relationships(node_id, direction)
            results = []
            for rel in relationships:
                results.append({
                    "id": rel.id,
                    "from_node": rel.from_node,
                    "to_node": rel.to_node,
                    "rel_type": rel.rel_type,
                    "properties": rel.properties,
                    "created_at": rel.created_at
                })
            return results
        return []
    
    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        self.logger.debug(f"Deleting node: {node_id}")
        result = self.backend.delete_node(node_id)
        self.logger.debug(f"Delete node result: {result}")
        return result
    
    def delete_relationship(self, rel_id: str) -> bool:
        """删除关系"""
        self.logger.debug(f"Deleting relationship: {rel_id}")
        result = self.backend.delete_relationship(rel_id)
        self.logger.debug(f"Delete relationship result: {result}")
        return result
    
    def count_nodes(self) -> int:
        """获取节点数量"""
        result = self.backend.count_nodes()
        self.logger.debug(f"Node count: {result}")
        return result
    
    def count_relationships(self) -> int:
        """获取关系数量"""
        result = self.backend.count_relationships()
        self.logger.debug(f"Relationship count: {result}")
        return result
    
    def clear(self) -> None:
        """清空图数据"""
        self.logger.debug("Clearing graph data")
        self.backend.clear()
    
    def stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        base_stats = self.get_statistics()
        graph_stats = {
            "backend_type": self.config.backend_type,
            "node_count": self.backend.count_nodes(),
            "relationship_count": self.backend.count_relationships(),
            "max_nodes": getattr(self.config, 'max_nodes', None),
            "max_relationships": getattr(self.config, 'max_relationships', None)
        }
        base_stats.update(graph_stats)
        return base_stats


# 工厂函数，用于在DAG中创建Graph服务
def create_graph_service_factory(
    service_name: str = "graph_service",
    backend_type: str = "memory",
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    max_nodes: int = 100000,
    max_relationships: int = 500000
):
    """
    创建Graph服务工厂
    
    Args:
        service_name: 服务名称
        backend_type: 后端类型 ("memory" 或 "neo4j")
        neo4j_uri: Neo4j连接URI
        neo4j_user: Neo4j用户名
        neo4j_password: Neo4j密码
        max_nodes: 最大节点数 (仅内存后端)
        max_relationships: 最大关系数 (仅内存后端)
    
    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.kernel.runtime.factory.service_factory import ServiceFactory
    
    config = GraphConfig(
        backend_type=backend_type,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        max_nodes=max_nodes,
        max_relationships=max_relationships
    )
    
    factory = ServiceFactory(service_name, GraphService)
    factory.config = config
    return factory
