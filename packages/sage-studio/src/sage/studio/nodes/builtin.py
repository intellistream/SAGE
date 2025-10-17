"""
基础内置节点

这些节点不依赖 SAGE，提供通用的数据处理功能
是独立运行的基础
"""

import json
import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List

from ..core.node_interface import (
    NodeInterface, NodeMetadata, NodeCategory, NodeInput, NodeOutput,
    ExecutionContext, ExecutionResult, DataType, register_node
)


@register_node
class FileReaderNode(NodeInterface):
    """文件读取节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="file_reader",
            name="File Reader",
            category=NodeCategory.DATA_SOURCE,
            description="Read content from local files",
            icon="📁",
            inputs=[
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
            ],
            outputs=[
                NodeOutput(
                    name="content",
                    type=DataType.STRING,
                    description="File content"
                ),
                NodeOutput(
                    name="size",
                    type=DataType.INTEGER,
                    description="File size in bytes"
                ),
                NodeOutput(
                    name="path",
                    type=DataType.STRING,
                    description="Absolute file path"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            file_path = context.inputs["file_path"]
            encoding = context.inputs.get("encoding", "utf-8")
            
            # 转换为绝对路径
            abs_path = Path(file_path).resolve()
            
            # 检查文件是否存在
            if not abs_path.exists():
                raise FileNotFoundError(f"File not found: {abs_path}")
            
            # 读取文件
            with open(abs_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # 获取文件大小
            size = abs_path.stat().st_size
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={
                    "content": content,
                    "size": size,
                    "path": str(abs_path)
                },
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=__import__('time').time() - start_time
            )


@register_node
class FileWriterNode(NodeInterface):
    """文件写入节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="file_writer",
            name="File Writer",
            category=NodeCategory.OUTPUT,
            description="Write content to local files",
            icon="📝",
            inputs=[
                NodeInput(
                    name="content",
                    type=DataType.STRING,
                    required=True,
                    description="Content to write"
                ),
                NodeInput(
                    name="file_path",
                    type=DataType.STRING,
                    required=True,
                    description="Path to write the file"
                ),
                NodeInput(
                    name="encoding",
                    type=DataType.STRING,
                    required=False,
                    default="utf-8",
                    description="File encoding"
                ),
                NodeInput(
                    name="create_dirs",
                    type=DataType.BOOLEAN,
                    required=False,
                    default=True,
                    description="Create parent directories if not exist"
                )
            ],
            outputs=[
                NodeOutput(
                    name="path",
                    type=DataType.STRING,
                    description="Absolute file path"
                ),
                NodeOutput(
                    name="size",
                    type=DataType.INTEGER,
                    description="Written file size in bytes"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            content = context.inputs["content"]
            file_path = context.inputs["file_path"]
            encoding = context.inputs.get("encoding", "utf-8")
            create_dirs = context.inputs.get("create_dirs", True)
            
            abs_path = Path(file_path).resolve()
            
            # 创建父目录
            if create_dirs:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(abs_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            # 获取文件大小
            size = abs_path.stat().st_size
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={
                    "path": str(abs_path),
                    "size": size
                },
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=__import__('time').time() - start_time
            )


@register_node
class HTTPRequestNode(NodeInterface):
    """HTTP 请求节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="http_request",
            name="HTTP Request",
            category=NodeCategory.DATA_SOURCE,
            description="Make HTTP requests to APIs",
            icon="🌐",
            inputs=[
                NodeInput(
                    name="url",
                    type=DataType.STRING,
                    required=True,
                    description="Request URL"
                ),
                NodeInput(
                    name="method",
                    type=DataType.STRING,
                    required=False,
                    default="GET",
                    description="HTTP method (GET, POST, PUT, DELETE)"
                ),
                NodeInput(
                    name="headers",
                    type=DataType.OBJECT,
                    required=False,
                    default={},
                    description="Request headers"
                ),
                NodeInput(
                    name="data",
                    type=DataType.ANY,
                    required=False,
                    description="Request body data"
                ),
                NodeInput(
                    name="timeout",
                    type=DataType.INTEGER,
                    required=False,
                    default=30,
                    description="Request timeout in seconds"
                )
            ],
            outputs=[
                NodeOutput(
                    name="response",
                    type=DataType.STRING,
                    description="Response body"
                ),
                NodeOutput(
                    name="status_code",
                    type=DataType.INTEGER,
                    description="HTTP status code"
                ),
                NodeOutput(
                    name="headers",
                    type=DataType.OBJECT,
                    description="Response headers"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            url = context.inputs["url"]
            method = context.inputs.get("method", "GET").upper()
            headers = context.inputs.get("headers", {})
            data = context.inputs.get("data")
            timeout = context.inputs.get("timeout", 30)
            
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "url": url,
                    "headers": headers,
                    "timeout": aiohttp.ClientTimeout(total=timeout)
                }
                
                if data is not None:
                    if isinstance(data, dict):
                        kwargs["json"] = data
                    else:
                        kwargs["data"] = data
                
                async with session.request(method, **kwargs) as response:
                    response_text = await response.text()
                    response_headers = dict(response.headers)
                    status_code = response.status
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={
                    "response": response_text,
                    "status_code": status_code,
                    "headers": response_headers
                },
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=__import__('time').time() - start_time
            )


@register_node
class JSONParserNode(NodeInterface):
    """JSON 解析节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="json_parser",
            name="JSON Parser",
            category=NodeCategory.DATA_PROCESSING,
            description="Parse JSON strings into objects",
            icon="📋",
            inputs=[
                NodeInput(
                    name="json_string",
                    type=DataType.STRING,
                    required=True,
                    description="JSON string to parse"
                )
            ],
            outputs=[
                NodeOutput(
                    name="data",
                    type=DataType.OBJECT,
                    description="Parsed JSON object"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            json_string = context.inputs["json_string"]
            
            # 解析 JSON
            data = json.loads(json_string)
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={"data": data},
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"JSON parsing failed: {str(e)}",
                duration=__import__('time').time() - start_time
            )


@register_node
class TextSplitterNode(NodeInterface):
    """文本分割节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="text_splitter",
            name="Text Splitter",
            category=NodeCategory.DATA_PROCESSING,
            description="Split text into smaller chunks",
            icon="✂️",
            inputs=[
                NodeInput(
                    name="text",
                    type=DataType.STRING,
                    required=True,
                    description="Text to split"
                ),
                NodeInput(
                    name="chunk_size",
                    type=DataType.INTEGER,
                    required=False,
                    default=500,
                    description="Maximum characters per chunk"
                ),
                NodeInput(
                    name="overlap",
                    type=DataType.INTEGER,
                    required=False,
                    default=50,
                    description="Characters to overlap between chunks"
                ),
                NodeInput(
                    name="separator",
                    type=DataType.STRING,
                    required=False,
                    default="\n\n",
                    description="Text separator"
                )
            ],
            outputs=[
                NodeOutput(
                    name="chunks",
                    type=DataType.ARRAY,
                    description="Text chunks"
                ),
                NodeOutput(
                    name="count",
                    type=DataType.INTEGER,
                    description="Number of chunks"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            text = context.inputs["text"]
            chunk_size = context.inputs.get("chunk_size", 500)
            overlap = context.inputs.get("overlap", 50)
            separator = context.inputs.get("separator", "\n\n")
            
            # 简单的文本分割逻辑
            chunks = []
            
            if separator in text:
                # 按分隔符分割
                parts = text.split(separator)
                current_chunk = ""
                
                for part in parts:
                    if len(current_chunk) + len(part) + len(separator) <= chunk_size:
                        if current_chunk:
                            current_chunk += separator + part
                        else:
                            current_chunk = part
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = part
                
                if current_chunk:
                    chunks.append(current_chunk)
            else:
                # 按字符数分割
                for i in range(0, len(text), chunk_size - overlap):
                    chunk = text[i:i + chunk_size]
                    if chunk:
                        chunks.append(chunk)
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={
                    "chunks": chunks,
                    "count": len(chunks)
                },
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=__import__('time').time() - start_time
            )


@register_node
class LoggerNode(NodeInterface):
    """日志节点"""
    
    @property
    def metadata(self) -> NodeMetadata:
        return NodeMetadata(
            id="logger",
            name="Logger",
            category=NodeCategory.OUTPUT,
            description="Log data to console or file",
            icon="📝",
            inputs=[
                NodeInput(
                    name="data",
                    type=DataType.ANY,
                    required=True,
                    description="Data to log"
                ),
                NodeInput(
                    name="level",
                    type=DataType.STRING,
                    required=False,
                    default="INFO",
                    description="Log level (DEBUG, INFO, WARNING, ERROR)"
                ),
                NodeInput(
                    name="message",
                    type=DataType.STRING,
                    required=False,
                    default="",
                    description="Log message prefix"
                )
            ],
            outputs=[
                NodeOutput(
                    name="logged",
                    type=DataType.BOOLEAN,
                    description="Whether logging was successful"
                )
            ]
        )
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        start_time = __import__('time').time()
        
        try:
            data = context.inputs["data"]
            level = context.inputs.get("level", "INFO").upper()
            message = context.inputs.get("message", "")
            
            # 格式化输出
            timestamp = __import__('datetime').datetime.now().isoformat()
            log_prefix = f"[{timestamp}] [{level}] [{context.node_id}]"
            
            if message:
                log_content = f"{log_prefix} {message}: {data}"
            else:
                log_content = f"{log_prefix} {data}"
            
            # 输出到控制台
            print(log_content)
            
            duration = __import__('time').time() - start_time
            
            return ExecutionResult(
                success=True,
                outputs={"logged": True},
                duration=duration
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=__import__('time').time() - start_time
            )


# 工具函数：获取所有内置节点

def get_builtin_nodes() -> List[NodeMetadata]:
    """获取所有内置节点的元数据"""
    from ..core.node_interface import node_factory
    return node_factory.list_available_nodes()