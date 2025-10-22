"""
流程执行引擎

⚠️ 架构问题 - 待重构/删除 ⚠️
=====================================

当前实现：Studio 有自己的执行引擎
问题：
1. 重复实现 - SAGE 已有完整的 DataStream 引擎
2. 功能缺失 - 缺少容错、分布式、状态管理
3. 架构割裂 - Studio 与 SAGE 核心脱节

正确架构：
Studio (UI) → SAGE DataStream API → SAGE Engine
    描述           调用                执行

重构方案：见 docs/dev-notes/STUDIO_ARCHITECTURE_REFACTOR.md

TODO:
- [ ] 删除 FlowEngine
- [ ] 创建 VisualPipeline 模型（只描述，不执行）
- [ ] 创建 SagePipelineBuilder（转换为 SAGE API）
- [ ] 重构 API 层直接使用 SAGE 执行环境

---

以下是当前的临时实现（将被移除）：
"""

import asyncio
import time
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field

from ..core.node_interface import NodeInterface, ExecutionContext, ExecutionResult
from ..core.plugin_manager import create_node


class FlowStatus(Enum):
    """流程状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeExecutionStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FlowNodeInstance:
    """流程中的节点实例"""
    id: str
    node_id: str  # 节点类型 ID
    name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    error_message: Optional[str] = None
    execution_time: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class FlowConnection:
    """节点间的连接"""
    source_node_id: str
    source_output_key: str
    target_node_id: str
    target_input_key: str


@dataclass
class FlowDefinition:
    """流程定义"""
    id: str
    name: str
    description: str = ""
    nodes: List[FlowNodeInstance] = field(default_factory=list)
    connections: List[FlowConnection] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)  # 入口节点 ID 列表


@dataclass
class FlowExecution:
    """流程执行状态"""
    id: str
    flow_id: str
    status: FlowStatus = FlowStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    node_results: Dict[str, Any] = field(default_factory=dict)  # 节点执行结果


class FlowEngine:
    """流程执行引擎"""
    
    def __init__(self):
        self.running_executions: Dict[str, FlowExecution] = {}
        self.execution_history: List[FlowExecution] = []
    
    async def execute_flow(self, flow: FlowDefinition, initial_inputs: Dict[str, Any] = None) -> FlowExecution:
        """执行流程
        
        Args:
            flow: 流程定义
            initial_inputs: 初始输入数据
            
        Returns:
            FlowExecution: 执行状态
        """
        execution_id = str(uuid.uuid4())
        execution = FlowExecution(
            id=execution_id,
            flow_id=flow.id,
            status=FlowStatus.RUNNING,
            start_time=time.time()
        )
        
        self.running_executions[execution_id] = execution
        
        try:
            print(f"🚀 Starting flow execution: {flow.name} ({execution_id})")
            
            # 构建节点依赖图
            dependency_graph = self._build_dependency_graph(flow)
            
            # 执行流程
            await self._execute_flow_nodes(flow, execution, dependency_graph, initial_inputs or {})
            
            execution.status = FlowStatus.COMPLETED
            execution.end_time = time.time()
            execution.execution_time = execution.end_time - execution.start_time
            
            print(f"✅ Flow execution completed: {flow.name} ({execution.execution_time:.2f}s)")
            
        except Exception as e:
            execution.status = FlowStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = time.time()
            execution.execution_time = execution.end_time - execution.start_time
            
            print(f"❌ Flow execution failed: {flow.name} - {e}")
        
        finally:
            # 移至历史记录
            if execution_id in self.running_executions:
                del self.running_executions[execution_id]
            self.execution_history.append(execution)
            
            # 保留最近 100 条执行记录
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
        
        return execution
    
    def _build_dependency_graph(self, flow: FlowDefinition) -> Dict[str, Set[str]]:
        """构建节点依赖图
        
        Returns:
            Dict[str, Set[str]]: 节点ID -> 依赖的节点ID集合
        """
        dependencies = {node.id: set() for node in flow.nodes}
        
        for connection in flow.connections:
            target_id = connection.target_node_id
            source_id = connection.source_node_id
            dependencies[target_id].add(source_id)
        
        return dependencies
    
    async def _execute_flow_nodes(self, 
                                flow: FlowDefinition, 
                                execution: FlowExecution,
                                dependency_graph: Dict[str, Set[str]],
                                initial_inputs: Dict[str, Any]):
        """执行流程中的所有节点"""
        
        # 建立节点映射
        nodes_by_id = {node.id: node for node in flow.nodes}
        
        # 初始化节点状态
        node_results = {}
        completed_nodes = set()
        
        # 设置入口节点的初始输入
        for entry_node_id in flow.entry_nodes:
            if entry_node_id in nodes_by_id:
                entry_node = nodes_by_id[entry_node_id]
                entry_node.inputs.update(initial_inputs)
        
        # 执行节点，直到所有节点完成
        while len(completed_nodes) < len(flow.nodes):
            # 找到所有可以执行的节点（依赖已满足）
            ready_nodes = []
            for node in flow.nodes:
                if (node.id not in completed_nodes and 
                    node.status == NodeExecutionStatus.PENDING and
                    dependency_graph[node.id].issubset(completed_nodes)):
                    ready_nodes.append(node)
            
            if not ready_nodes:
                # 没有可执行的节点，检查是否有循环依赖
                remaining_nodes = [n for n in flow.nodes if n.id not in completed_nodes]
                if remaining_nodes:
                    raise RuntimeError(f"Circular dependency detected or missing entry nodes. Remaining: {[n.name for n in remaining_nodes]}")
                break
            
            # 并行执行准备好的节点
            tasks = []
            for node in ready_nodes:
                node.status = NodeExecutionStatus.RUNNING
                task = self._execute_single_node(node, node_results, flow.connections, execution)
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(results):
                node = ready_nodes[i]
                if isinstance(result, Exception):
                    node.status = NodeExecutionStatus.FAILED
                    node.error_message = str(result)
                    print(f"❌ Node failed: {node.name} - {result}")
                else:
                    node.status = NodeExecutionStatus.COMPLETED
                    node_results[node.id] = result
                    print(f"✅ Node completed: {node.name}")
                
                completed_nodes.add(node.id)
        
        execution.node_results = node_results
    
    async def _execute_single_node(self, 
                                 node_instance: FlowNodeInstance,
                                 node_results: Dict[str, Any],
                                 connections: List[FlowConnection],
                                 execution: FlowExecution) -> Any:
        """执行单个节点"""
        
        node_instance.start_time = time.time()
        
        try:
            # 创建节点实例
            node = create_node(node_instance.node_id)
            if not node:
                raise ValueError(f"Unknown node type: {node_instance.node_id}")
            
            # 准备输入数据
            inputs = dict(node_instance.inputs)
            
            # 从连接中获取输入数据
            for connection in connections:
                if connection.target_node_id == node_instance.id:
                    source_node_id = connection.source_node_id
                    if source_node_id in node_results:
                        source_result = node_results[source_node_id]
                        if hasattr(source_result, 'outputs') and connection.source_output_key in source_result.outputs:
                            inputs[connection.target_input_key] = source_result.outputs[connection.source_output_key]
            
            # 创建执行上下文
            context = ExecutionContext(
                node_id=node_instance.id,
                flow_id=execution.flow_id,
                execution_id=execution.id,
                inputs=inputs,
                config={}
            )
            
            # 执行节点
            result = await node.execute(context)
            
            # 更新输出
            if result.success and result.outputs:
                node_instance.outputs.update(result.outputs)
            
            node_instance.end_time = time.time()
            node_instance.execution_time = node_instance.end_time - node_instance.start_time
            
            return result
            
        except Exception as e:
            node_instance.end_time = time.time()
            node_instance.execution_time = node_instance.end_time - node_instance.start_time
            raise e
    
    def get_execution_status(self, execution_id: str) -> Optional[FlowExecution]:
        """获取执行状态"""
        if execution_id in self.running_executions:
            return self.running_executions[execution_id]
        
        for execution in self.execution_history:
            if execution.id == execution_id:
                return execution
        
        return None
    
    def list_running_executions(self) -> List[FlowExecution]:
        """列出正在运行的执行"""
        return list(self.running_executions.values())
    
    def get_execution_history(self, limit: int = 50) -> List[FlowExecution]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self.running_executions:
            execution = self.running_executions[execution_id]
            execution.status = FlowStatus.CANCELLED
            execution.end_time = time.time()
            execution.execution_time = execution.end_time - execution.start_time
            
            del self.running_executions[execution_id]
            self.execution_history.append(execution)
            
            print(f"🛑 Flow execution cancelled: {execution_id}")
            return True
        
        return False


# 全局流程引擎实例
flow_engine = FlowEngine()


# 便捷函数

async def execute_flow(flow: FlowDefinition, inputs: Dict[str, Any] = None) -> FlowExecution:
    """执行流程"""
    return await flow_engine.execute_flow(flow, inputs)


def get_execution_status(execution_id: str) -> Optional[FlowExecution]:
    """获取执行状态"""
    return flow_engine.get_execution_status(execution_id)


def list_running_executions() -> List[FlowExecution]:
    """列出正在运行的执行"""
    return flow_engine.list_running_executions()


# 创建简单流程的辅助函数

def create_simple_flow(name: str, node_configs: List[Dict[str, Any]]) -> FlowDefinition:
    """创建简单的顺序流程
    
    Args:
        name: 流程名称
        node_configs: 节点配置列表，格式为 [{"node_id": "xxx", "inputs": {...}}, ...]
    
    Returns:
        FlowDefinition: 流程定义
    """
    flow_id = str(uuid.uuid4())
    flow = FlowDefinition(id=flow_id, name=name)
    
    previous_node_id = None
    
    for i, config in enumerate(node_configs):
        # 创建节点实例
        node_instance = FlowNodeInstance(
            id=f"node_{i}",
            node_id=config["node_id"],
            name=config.get("name", f"Node {i}"),
            inputs=config.get("inputs", {})
        )
        flow.nodes.append(node_instance)
        
        # 如果是第一个节点，设为入口节点
        if i == 0:
            flow.entry_nodes.append(node_instance.id)
        
        # 创建与前一个节点的连接
        if previous_node_id is not None:
            connection = FlowConnection(
                source_node_id=previous_node_id,
                source_output_key="result",  # 默认输出键
                target_node_id=node_instance.id,
                target_input_key="input"     # 默认输入键
            )
            flow.connections.append(connection)
        
        previous_node_id = node_instance.id
    
    return flow


if __name__ == "__main__":
    # 测试流程引擎
    import asyncio
    
    async def test_flow_engine():
        print("🧪 Testing Flow Engine...")
        
        # 创建简单测试流程
        flow = create_simple_flow("Test Flow", [
            {"node_id": "file_reader", "inputs": {"file_path": "/tmp/test.txt"}},
            {"node_id": "text_splitter", "inputs": {"chunk_size": 100}},
            {"node_id": "logger", "inputs": {"level": "info"}}
        ])
        
        print(f"📋 Created flow: {flow.name} with {len(flow.nodes)} nodes")
        
        # 执行流程
        execution = await execute_flow(flow, {"message": "Hello World"})
        
        print(f"📊 Execution result: {execution.status.value}")
        print(f"⏱️  Execution time: {execution.execution_time:.2f}s")
        
        if execution.status == FlowStatus.FAILED:
            print(f"❌ Error: {execution.error_message}")
    
    # 运行测试
    asyncio.run(test_flow_engine())