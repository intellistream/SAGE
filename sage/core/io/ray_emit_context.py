from typing import TypeVar, Generic, Callable, Any, List, Dict, Union, Tuple, Literal
from abc import ABC, abstractmethod
from enum import Enum
import ray
from ray.actor import ActorHandle
import socket
import json
import pickle
import threading
from sage.utils.custom_logger import CustomLogger
from sage.core.io.emit_context import BaseEmitContext, DownstreamTarget, NodeType
import time



class RayEmitContext(BaseEmitContext):
    """
    Ray Actor使用的Emit Context
    支持向Ray Actor发送远程调用，向本地节点发送TCP包
    """
    
    def __init__(self, 
                 local_tcp_host: str = "localhost", 
                 local_tcp_port: int = 9999, logger: CustomLogger = None):
        self.local_tcp_host = local_tcp_host
        self.local_tcp_port = local_tcp_port
        self._tcp_socket = None
        self._socket_lock = threading.Lock()

    def _get_tcp_connection(self) -> socket.socket:
        """获取到本地的TCP连接（懒加载）"""
        if self._tcp_socket is None:
            with self._socket_lock:
                if self._tcp_socket is None:
                    try:
                        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self._tcp_socket.connect((self.local_tcp_host, self.local_tcp_port))
                        self.logger.info(f"Ray actor connected to local TCP server at {self.local_tcp_host}:{self.local_tcp_port}")
                    except Exception as e:
                        self.logger.error(f"Failed to connect to local TCP server: {e}")
                        raise
        return self._tcp_socket
    
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """
        向本地节点发送TCP包
        
        Args:
            target: 目标本地节点
            data: 数据
        """
        try:
            # 构造TCP消息包
            message = {
                "type": "ray_to_local",
                "source_actor": self.node_name,
                "target_node": target.node_name,
                "target_channel": target.target_input_channel,
                "data": data,
                "timestamp": time.time_ns()
            }
            
            # 序列化消息
            serialized_data = pickle.dumps(message)
            message_size = len(serialized_data)
            
            # 发送消息长度，然后发送消息内容
            tcp_conn = self._get_tcp_connection()
            tcp_conn.sendall(message_size.to_bytes(4, byteorder='big'))
            tcp_conn.sendall(serialized_data)
            
            self.logger.debug(f"Sent TCP packet to local node {target.node_name}[in:{target.target_input_channel}]")
            
        except Exception as e:
            self.logger.error(f"Error sending TCP packet to local node {target.node_name}: {e}")
            # 重置连接以便下次重试
            with self._socket_lock:
                if self._tcp_socket:
                    self._tcp_socket.close()
                    self._tcp_socket = None
            raise
    
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """
        向其他Ray Actor发送远程调用
        
        Args:
            target: 目标Ray Actor
            data: 数据
        """
        try:
            if isinstance(target.target_object, ActorHandle):
                # 直接调用Ray Actor的remote方法
                target.target_object.receive.remote(target.target_input_channel, data)
                self.logger.debug(f"Sent remote call to Ray actor {target.node_name}[in:{target.target_input_channel}]")
            else:
                raise TypeError(f"Expected ActorHandle for Ray actor, got {type(target.target_object)}")
                
        except Exception as e:
            self.logger.error(f"Error sending remote call to Ray actor {target.node_name}: {e}")
            raise
    
    def close(self):
        """关闭TCP连接"""
        with self._socket_lock:
            if self._tcp_socket:
                self._tcp_socket.close()
                self._tcp_socket = None
                self.logger.info("Closed TCP connection to local server")
