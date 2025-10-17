"""
SAGE Studio 统一节点接口定义

这是解耦的第一步：定义标准化的节点接口，
让所有节点（包括 SAGE Operator）都通过统一接口工作。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class NodeCategory(str, Enum):
    """节点分类"""
    DATA_SOURCE = "data_source"      # 数据源
    DATA_PROCESSING = "processing"   # 数据处理
    AI_ML = "ai_ml"                 # AI 和机器学习
    CONTROL_FLOW = "control_flow"   # 流程控制
    OUTPUT = "output"               # 输出
    SAGE = "sage"                   # SAGE 特有节点
    CUSTOM = "custom"               # 自定义节点


class DataType(str, Enum):
    """数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DOCUMENT = "document"      # 文档对象
    EMBEDDING = "embedding"    # 向量
    ANY = "any"               # 任意类型


class NodeInput(BaseModel):
    """节点输入定义"""
    name: str = Field(description="输入参数名称")
    type: DataType = Field(description="数据类型")
    required: bool = Field(default=True, description="是否必需")
    description: str = Field(default="", description="参数描述")
    default: Optional[Any] = Field(default=None, description="默认值")
    validation: Optional[Dict[str, Any]] = Field(default=None, description="验证规则")


class NodeOutput(BaseModel):
    """节点输出定义"""
    name: str = Field(description="输出参数名称")
    type: DataType = Field(description="数据类型")
    description: str = Field(default="", description="输出描述")


class NodeMetadata(BaseModel):
    """节点元数据"""
    id: str = Field(description="节点唯一标识")
    name: str = Field(description="节点显示名称")
    category: NodeCategory = Field(description="节点分类")
    description: str = Field(description="节点功能描述")
    version: str = Field(default="1.0.0", description="版本号")
    author: str = Field(default="Unknown", description="作者")
    icon: str = Field(default="⚙️", description="图标")
    color: str = Field(default="#1890ff", description="节点颜色")
    
    # 输入输出定义
    inputs: List[NodeInput] = Field(description="输入参数列表")
    outputs: List[NodeOutput] = Field(description="输出参数列表")
    
    # 扩展信息
    tags: List[str] = Field(default_factory=list, description="标签")
    documentation_url: Optional[str] = Field(default=None, description="文档链接")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")


class ExecutionContext(BaseModel):
    """节点执行上下文"""
    node_id: str = Field(description="节点ID")
    flow_id: Optional[str] = Field(default=None, description="流程ID")
    execution_id: Optional[str] = Field(default=None, description="执行ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置参数")


class ExecutionResult(BaseModel):
    """执行结果"""
    success: bool = Field(description="是否成功")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    duration: float = Field(default=0.0, description="执行耗时（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="执行元数据")


class NodeInterface(ABC):
    """统一的节点接口
    
    所有节点（包括 SAGE Operator 适配器）都必须实现此接口
    """
    
    def __init__(self):
        self._metadata: Optional[NodeMetadata] = None
        self._initialized: bool = False
    
    @property
    @abstractmethod
    def metadata(self) -> NodeMetadata:
        """返回节点元数据"""
        pass
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """执行节点逻辑
        
        Args:
            context: 执行上下文，包含输入数据、配置等
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    async def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """验证输入数据（可选重写）
        
        Args:
            inputs: 输入数据
            
        Returns:
            bool: 验证是否通过
        """
        metadata = self.metadata
        
        # 检查必需参数
        for input_def in metadata.inputs:
            if input_def.required and input_def.name not in inputs:
                raise ValueError(f"Missing required input: {input_def.name}")
        
        # TODO: 更详细的类型检查和验证规则
        # Issue URL: https://github.com/intellistream/SAGE/issues/986
        return True
    
    async def on_initialize(self) -> None:
        """节点初始化钩子（可选重写）"""
        self._initialized = True
    
    async def on_cleanup(self) -> None:
        """节点清理钩子（可选重写）"""
        pass
    
    def is_initialized(self) -> bool:
        """检查节点是否已初始化"""
        return self._initialized


class NodeFactory:
    """节点工厂类
    
    负责创建和管理节点实例
    """
    
    def __init__(self):
        self._node_classes: Dict[str, type] = {}
    
    def register_node_class(self, node_class: type) -> None:
        """注册节点类
        
        Args:
            node_class: 节点类（必须继承 NodeInterface）
        """
        if not issubclass(node_class, NodeInterface):
            raise ValueError(f"Node class {node_class} must inherit from NodeInterface")
        
        # 创建临时实例获取元数据
        temp_instance = node_class()
        metadata = temp_instance.metadata
        
        self._node_classes[metadata.id] = node_class
        print(f"Registered node class: {metadata.name} ({metadata.id})")
    
    def create_node(self, node_id: str) -> NodeInterface:
        """创建节点实例
        
        Args:
            node_id: 节点 ID
            
        Returns:
            NodeInterface: 节点实例
        """
        if node_id not in self._node_classes:
            raise ValueError(f"Node class not found: {node_id}")
        
        node_class = self._node_classes[node_id]
        return node_class()
    
    def list_available_nodes(self) -> List[NodeMetadata]:
        """列出所有可用节点
        
        Returns:
            List[NodeMetadata]: 节点元数据列表
        """
        nodes = []
        for node_class in self._node_classes.values():
            temp_instance = node_class()
            nodes.append(temp_instance.metadata)
        return nodes


# 全局节点工厂实例
node_factory = NodeFactory()


def register_node(node_class: type) -> type:
    """装饰器：注册节点类
    
    Usage:
        @register_node
        class MyNode(NodeInterface):
            ...
    """
    node_factory.register_node_class(node_class)
    return node_class