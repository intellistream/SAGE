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

class NodeType(Enum):
    LOCAL = "local"
    RAY_ACTOR = "ray_actor"

class DownstreamTarget:
    """下游目标节点的封装"""
    def __init__(self, 
                 node_type: NodeType, 
                 target_object: Any, 
                 target_input_channel: int,
                 node_name: str = None):
        self.node_type = node_type
        self.target_object = target_object
        self.target_input_channel = target_input_channel
        self.node_name = node_name or str(target_object)

class BaseEmitContext(ABC):
    """
    基础Emit Context抽象类
    支持混合环境中本地和Ray Actor之间的通信
    """
    
    def __init__(self, node_name: str, session_folder: str = None):
        self.node_name = node_name
        self.downstream_channels: Dict[int, DownstreamTarget] = {}
        # Dict[自身出口号, DownstreamTarget]
        
        self.logger = CustomLogger(
            object_name=f"EmitContext_{node_name}",
            session_folder=session_folder,
            log_level="DEBUG"
        )
    
    def add_downstream_target(self, 
                            output_channel: int,
                            node_type: NodeType, 
                            target_object: Any, 
                            target_input_channel: int,
                            node_name: str = None) -> None:
        """
        添加下游目标节点
        
        Args:
            output_channel: 自身的输出通道号
            node_type: 下游节点类型
            target_object: 下游节点对象
            target_input_channel: 下游节点的输入通道号
            node_name: 下游节点名称
        """
        target = DownstreamTarget(node_type, target_object, target_input_channel, node_name)
        self.downstream_channels[output_channel] = target
        
        self.logger.debug(f"Added downstream target: {self.node_name}[out:{output_channel}] -> "
                         f"{node_name}[in:{target_input_channel}] (type: {node_type.value})")
    
    def emit(self, channel: int, data: Any) -> None:
        """
        向指定下游通道发送数据
        
        Args:
            channel: 下游通道索引，-1表示广播到所有通道
            data: 要发送的数据
        """
        if channel == -1:
            # 广播到所有下游通道
            for output_channel, target in self.downstream_channels.items():
                self._route_and_send(target, data)
        elif channel in self.downstream_channels:
            target = self.downstream_channels[channel]
            self._route_and_send(target, data)
        else:
            self.logger.warning(f"Channel index {channel} out of range for node {self.node_name}")
    
    def _route_and_send(self, target: DownstreamTarget, data: Any) -> None:
        """
        根据目标类型路由并发送数据
        
        Args:
            target: 目标节点信息
            data: 要发送的数据
        """
        try:
            if target.node_type == NodeType.LOCAL:
                self._send_to_local(target, data)
            elif target.node_type == NodeType.RAY_ACTOR:
                self._send_to_ray_actor(target, data)
            else:
                self.logger.error(f"Unknown target type: {target.node_type}")
        except Exception as e:
            self.logger.error(f"Failed to send data to {target.node_name}: {e}", exc_info=True)
    
    @abstractmethod
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到本地节点"""
        pass
    
    @abstractmethod
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到Ray Actor"""
        pass


class LocalEmitContext(BaseEmitContext):
    """
    本地DAG节点使用的Emit Context
    支持向本地节点的输入缓冲区写入数据，向Ray Actor发送远程调用
    """
    
    def __init__(self, node_name: str, session_folder: str = None):
        super().__init__(node_name, session_folder)
    
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """
        向本地节点的输入缓冲区写入数据包
        
        Args:
            target: 目标本地节点
            data: 数据
        """
        try:
            # 向下游本地节点的输入缓冲区写入 (输入channel, 数据) 包
            data_packet = (target.target_input_channel, data)
            
            # 假设本地节点有input_buffer属性用于接收数据
            if hasattr(target.target_object, 'input_buffer'):
                target.target_object.input_buffer.put(data_packet)
            elif hasattr(target.target_object, 'put'):
                # 或者有put方法
                target.target_object.put(data_packet)
            else:
                raise AttributeError(f"Local node {target.node_name} has no input_buffer or put method")
                
            self.logger.debug(f"Written data packet to local node {target.node_name}[in:{target.target_input_channel}] input buffer")
            
        except Exception as e:
            self.logger.error(f"Error writing data to local node {target.node_name} input buffer: {e}")
            raise
    
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """
        向Ray Actor发送远程调用
        
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


class RayEmitContext(BaseEmitContext):
    """
    Ray Actor使用的Emit Context
    支持向Ray Actor发送远程调用，向本地节点发送TCP包
    """
    
    def __init__(self, node_name: str, ray_node_actor=None,
                 local_tcp_host: str = "localhost", 
                 local_tcp_port: int = 9999, session_folder: str = None):
        super().__init__(node_name, session_folder)
        self.ray_node_actor = ray_node_actor
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
                "timestamp": ray.util.get_current_time_ns()
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


# 为了向后兼容，保留原有的EmitContext作为LocalEmitContext的别名
EmitContext = LocalEmitContext