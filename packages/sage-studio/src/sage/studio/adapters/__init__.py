"""
SAGE Operator 适配器

将现有的 SAGE Operator 适配为统一的 NodeInterface
这是解耦的关键步骤：让 SAGE 功能通过标准接口提供服务
"""

import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.node_interface import (
    NodeInterface, NodeMetadata, NodeCategory, NodeInput, NodeOutput,
    ExecutionContext, ExecutionResult, DataType, register_node
)


class SAGEOperatorAdapter(NodeInterface):
    """SAGE Operator 到 Studio Node 的适配器基类"""
    
    def __init__(self, sage_module_path: str, sage_class_name: str):
        super().__init__()
        self.sage_module_path = sage_module_path
        self.sage_class_name = sage_class_name
        self._sage_operator = None
        self._metadata = None
    
    def _load_sage_operator(self):
        """动态加载 SAGE Operator"""
        if self._sage_operator is None:
            try:
                # 尝试导入 SAGE 模块
                module = importlib.import_module(self.sage_module_path)
                sage_class = getattr(module, self.sage_class_name)
                self._sage_operator = sage_class()
            except ImportError as e:
                # SAGE 未安装或模块不存在
                raise ImportError(f"SAGE module not available: {e}")
            except Exception as e:
                raise RuntimeError(f"Failed to load SAGE operator: {e}")
        
        return self._sage_operator
    
    def _extract_sage_metadata(self) -> NodeMetadata:
        """从 SAGE Operator 提取元数据"""
        try:
            operator = self._load_sage_operator()
            
            # 基础信息
            class_name = operator.__class__.__name__
            doc_string = operator.__class__.__doc__ or f"SAGE {class_name} operator"
            
            # 尝试从源码分析输入输出（简化版）
            inputs = self._infer_inputs(operator)
            outputs = self._infer_outputs(operator)
            
            return NodeMetadata(
                id=f"sage_{class_name.lower()}",
                name=f"SAGE {class_name}",
                category=NodeCategory.SAGE,
                description=doc_string.strip(),
                version="1.0.0",
                author="SAGE Team",
                icon="⚙️",
                color="#52c41a",  # SAGE 绿色
                inputs=inputs,
                outputs=outputs,
                tags=["sage", "operator"]
            )
        
        except Exception as e:
            # 如果无法加载 SAGE，返回占位符元数据
            return NodeMetadata(
                id=f"sage_{self.sage_class_name.lower()}",
                name=f"SAGE {self.sage_class_name}",
                category=NodeCategory.SAGE,
                description=f"SAGE {self.sage_class_name} operator (requires SAGE installation)",
                version="1.0.0",
                author="SAGE Team",
                icon="⚙️",
                color="#ff4d4f",  # 红色表示不可用
                inputs=[],
                outputs=[],
                tags=["sage", "operator", "unavailable"]
            )
    
    def _infer_inputs(self, operator) -> list[NodeInput]:
        """推断输入参数（简化版）"""
        # TODO: 更智能的参数推断
        # Issue URL: https://github.com/intellistream/SAGE/issues/985
        # 可以通过分析 __init__ 方法、process 方法等
        return [
            NodeInput(
                name="input_data",
                type=DataType.ANY,
                required=True,
                description="Input data for processing"
            )
        ]
    
    def _infer_outputs(self, operator) -> list[NodeOutput]:
        """推断输出参数（简化版）"""
        return [
            NodeOutput(
                name="output_data",
                type=DataType.ANY,
                description="Processed output data"
            )
        ]
    
    @property
    def metadata(self) -> NodeMetadata:
        """返回节点元数据"""
        if self._metadata is None:
            self._metadata = self._extract_sage_metadata()
        return self._metadata
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """执行 SAGE Operator"""
        start_time = __import__('time').time()
        
        try:
            # 加载 SAGE Operator
            operator = self._load_sage_operator()
            
            # 转换输入格式
            sage_inputs = self._convert_to_sage_format(context.inputs)
            
            # 执行 SAGE Operator（假设有 process 方法）
            if hasattr(operator, 'process'):
                sage_outputs = await self._async_process(operator, sage_inputs)
            else:
                sage_outputs = operator(sage_inputs)  # 直接调用
            
            # 转换输出格式
            studio_outputs = self._convert_to_studio_format(sage_outputs)
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs=studio_outputs,
                duration=duration,
                metadata={
                    "sage_operator": self.sage_class_name,
                    "sage_module": self.sage_module_path
                }
            )
        
        except ImportError as e:
            return ExecutionResult(
                success=False,
                error=f"SAGE not available: {str(e)}",
                duration=__import__('time').time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"SAGE operator execution failed: {str(e)}",
                duration=__import__('time').time() - start_time
            )
    
    async def _async_process(self, operator, inputs):
        """将同步的 SAGE operator 转为异步"""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, operator.process, inputs
        )
    
    def _convert_to_sage_format(self, studio_inputs: Dict[str, Any]) -> Any:
        """将 Studio 格式转换为 SAGE 格式"""
        # 简化版：直接返回 input_data
        return studio_inputs.get("input_data", studio_inputs)
    
    def _convert_to_studio_format(self, sage_outputs: Any) -> Dict[str, Any]:
        """将 SAGE 格式转换为 Studio 格式"""
        # 简化版：包装为字典
        if isinstance(sage_outputs, dict):
            return sage_outputs
        else:
            return {"output_data": sage_outputs}


# 具体的 SAGE Operator 适配器示例

@register_node
class FileSourceAdapter(SAGEOperatorAdapter):
    """SAGE FileSource 适配器"""
    
    def __init__(self):
        super().__init__(
            sage_module_path="sage.libs.io.file_source",
            sage_class_name="FileSource"
        )
    
    def _infer_inputs(self, operator) -> list[NodeInput]:
        return [
            NodeInput(
                name="file_path",
                type=DataType.STRING,
                required=True,
                description="Path to the file to read"
            ),
            NodeInput(
                name="encoding",
                type=DataType.STRING,
                required=False,
                default="utf-8",
                description="File encoding"
            )
        ]
    
    def _infer_outputs(self, operator) -> list[NodeOutput]:
        return [
            NodeOutput(
                name="content",
                type=DataType.STRING,
                description="File content"
            ),
            NodeOutput(
                name="metadata",
                type=DataType.OBJECT,
                description="File metadata"
            )
        ]


@register_node  
class SimpleRetrieverAdapter(SAGEOperatorAdapter):
    """SAGE SimpleRetriever 适配器"""
    
    def __init__(self):
        super().__init__(
            sage_module_path="sage.libs.rag.retriever",
            sage_class_name="SimpleRetriever"
        )
    
    def _infer_inputs(self, operator) -> list[NodeInput]:
        return [
            NodeInput(
                name="query",
                type=DataType.STRING,
                required=True,
                description="Search query"
            ),
            NodeInput(
                name="top_k",
                type=DataType.INTEGER,
                required=False,
                default=5,
                description="Number of results to return"
            )
        ]
    
    def _infer_outputs(self, operator) -> list[NodeOutput]:
        return [
            NodeOutput(
                name="documents",
                type=DataType.ARRAY,
                description="Retrieved documents"
            ),
            NodeOutput(
                name="scores",
                type=DataType.ARRAY,
                description="Relevance scores"
            )
        ]


# 工具函数：批量创建 SAGE 适配器

def create_sage_adapters_from_config(config_path: str) -> list[NodeInterface]:
    """从配置文件批量创建 SAGE 适配器
    
    Args:
        config_path: SAGE 操作符配置文件路径
        
    Returns:
        list[NodeInterface]: 适配器列表
    """
    import json
    
    adapters = []
    config_dir = Path(config_path).parent
    
    # 读取现有的操作符配置
    for json_file in config_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                operator_config = json.load(f)
            
            # 检查是否有 SAGE 模块信息
            if "module_path" in operator_config and "class_name" in operator_config:
                adapter = SAGEOperatorAdapter(
                    sage_module_path=operator_config["module_path"],
                    sage_class_name=operator_config["class_name"]
                )
                adapters.append(adapter)
                
        except Exception as e:
            print(f"Failed to create adapter from {json_file}: {e}")
    
    return adapters


# 检查 SAGE 可用性的工具函数

def is_sage_available() -> bool:
    """检查 SAGE 是否可用"""
    try:
        import sage.libs
        return True
    except ImportError:
        return False


def get_sage_status() -> Dict[str, Any]:
    """获取 SAGE 环境状态"""
    status = {
        "available": False,
        "version": None,
        "modules": [],
        "operators": []
    }
    
    try:
        import sage
        status["available"] = True
        status["version"] = getattr(sage, "__version__", "unknown")
        
        # 尝试列出可用模块
        try:
            import sage.libs.io
            status["modules"].append("sage.libs.io")
        except ImportError:
            pass
        
        try:
            import sage.libs.rag
            status["modules"].append("sage.libs.rag")
        except ImportError:
            pass
            
    except ImportError:
        pass
    
    return status