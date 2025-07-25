#!/usr/bin/env python3
"""
SAGE Remote Environment - Simplified Version
简化版远程环境，专注于序列化和发送环境对象
"""

import socket
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# 导入SAGE序列化工具
try:
    from sage.utils.serialization.dill_serializer import serialize_object, deserialize_object
    has_serializer = True
except ImportError:
    import pickle
    has_serializer = False

logger = logging.getLogger(__name__)

class SimpleRemoteEnvironment:
    """
    简化的远程环境类
    专注于序列化环境对象并发送给JobManager服务
    """
    
    def __init__(self, name: str = "remote_env", config: Optional[Dict[str, Any]] = None,
                 jobmanager_host: str = "127.0.0.1", jobmanager_port: int = 19002):
        """
        初始化远程环境
        
        Args:
            name: 环境名称
            config: 环境配置
            jobmanager_host: JobManager服务主机
            jobmanager_port: JobManager服务端口
        """
        self.name = name
        self.config = config or {}
        self.platform = "remote"
        self.pipeline = []
        
        # JobManager连接配置
        self.jobmanager_host = jobmanager_host
        self.jobmanager_port = jobmanager_port
        
        # 客户端相关属性设为None（避免序列化问题）
        self._engine_client = None
        self._jobmanager = None
        
        logger.info(f"Initialized SimpleRemoteEnvironment: {name}")
    
    @property
    def client(self):
        """客户端属性（为兼容性保留）"""
        return self._engine_client
    
    @property
    def jobmanager(self):
        """JobManager属性（为兼容性保留）"""
        return self._jobmanager
    
    def add_to_pipeline(self, component):
        """添加组件到流水线"""
        self.pipeline.append(component)
        logger.info(f"Added component to pipeline: {component}")
    
    def serialize_environment(self, include: Optional[list] = None, 
                            exclude: Optional[list] = None) -> bytes:
        """
        序列化环境对象
        
        Args:
            include: 包含的属性列表
            exclude: 排除的属性列表
            
        Returns:
            序列化后的字节数据
        """
        try:
            if has_serializer:
                # 使用SAGE的dill序列化器
                return serialize_object(self, include=include, exclude=exclude)
            else:
                # 备用pickle序列化
                import pickle
                return pickle.dumps(self)
        except Exception as e:
            logger.error(f"Failed to serialize environment: {e}")
            raise
    
    def send_to_jobmanager(self, include: Optional[list] = None, 
                          exclude: Optional[list] = None) -> Dict[str, Any]:
        """
        序列化环境并发送给JobManager服务
        
        Args:
            include: 包含的属性列表
            exclude: 排除的属性列表
            
        Returns:
            服务器响应
        """
        try:
            # 序列化环境
            serialized_data = self.serialize_environment(include=include, exclude=exclude)
            logger.info(f"Serialized environment ({len(serialized_data)} bytes)")
            
            # 发送到JobManager
            response = self._send_data_to_server(serialized_data)
            logger.info(f"Sent environment to JobManager: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send environment to JobManager: {e}")
            raise
    
    def _send_data_to_server(self, data: bytes) -> Dict[str, Any]:
        """
        发送数据到服务器
        
        Args:
            data: 要发送的字节数据
            
        Returns:
            服务器响应
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                # 连接到JobManager服务
                client_socket.connect((self.jobmanager_host, self.jobmanager_port))
                
                # 发送数据长度
                data_length = len(data)
                client_socket.send(data_length.to_bytes(4, byteorder='big'))
                
                # 发送数据
                client_socket.send(data)
                
                # 接收响应长度
                response_length_data = client_socket.recv(4)
                if len(response_length_data) != 4:
                    raise RuntimeError("Invalid response length header")
                
                response_length = int.from_bytes(response_length_data, byteorder='big')
                
                # 接收响应数据
                response_data = b""
                while len(response_data) < response_length:
                    chunk = client_socket.recv(min(4096, response_length - len(response_data)))
                    if not chunk:
                        break
                    response_data += chunk
                
                # 解析JSON响应
                response = json.loads(response_data.decode('utf-8'))
                return response
                
        except Exception as e:
            logger.error(f"Failed to send data to server: {e}")
            raise
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "name": self.name,
            "config": self.config,
            "platform": self.platform,
            "pipeline_length": len(self.pipeline),
            "jobmanager_host": self.jobmanager_host,
            "jobmanager_port": self.jobmanager_port
        }
    
    def __repr__(self):
        return f"SimpleRemoteEnvironment(name='{self.name}', platform='{self.platform}')"
