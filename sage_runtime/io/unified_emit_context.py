from typing import Any , TYPE_CHECKING
from ray.actor import ActorHandle
import socket
import pickle
import threading
import time
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.connection import Connection, ConnectionType


class UnifiedEmitContext:
    """
    统一的Emit Context，支持所有类型的连接
    根据Connection对象中的配置自动选择合适的发送方式
    """
    
    def __init__(self, session_folder: str = None, name: str = None, **kwargs):
        self.logger = CustomLogger(
            filename=f"Node_{name}",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING",
            name=f"{name}_UnifiedEmitContext"
        )
        self.name = name
        
        # TCP连接管理（用于Ray到Local的连接）
        self._tcp_connections: dict = {}  # host:port -> socket
        self._socket_lock = threading.Lock()

    def send_via_connection(self, connection: 'Connection', data: Any) -> None:
        """
        根据Connection对象的配置发送数据
        
        Args:
            connection: Connection对象，包含完整的连接信息
            data: 要发送的数据
        """
        try:
            connection_type = connection.connection_type
            
            if connection_type == ConnectionType.LOCAL_TO_LOCAL:
                self._send_local_to_local(connection, data)
                
            elif connection_type == ConnectionType.LOCAL_TO_RAY:
                self._send_local_to_ray(connection, data)
                
            elif connection_type == ConnectionType.RAY_TO_LOCAL:
                self._send_ray_to_local(connection, data)
                
            elif connection_type == ConnectionType.RAY_TO_RAY:
                self._send_ray_to_ray(connection, data)
                
            else:
                raise ValueError(f"Unknown connection type: {connection_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to send data via connection {connection.get_summary()}: {e}", exc_info=True)
            raise

    def _send_local_to_local(self, connection: 'Connection', data: Any) -> None:
        """本地到本地：直接调用put方法"""
        try:
            target_node = connection.target_config["dagnode"]
            input_tag = connection.target_input_tag
            
            # 构建数据包
            data_packet = (input_tag, data)
            
            # 发送到目标节点的输入缓冲区
            if hasattr(target_node, 'put'):
                target_node.put(data_packet)
            elif hasattr(target_node, 'input_buffer'):
                target_node.input_buffer.put(data_packet)
            else:
                raise AttributeError(f"Local node {connection.target_name} has no put method or input_buffer")
                
            self.logger.debug(f"Sent local->local: {connection.target_name}[{input_tag}]")
            
        except Exception as e:
            self.logger.error(f"Error in local->local send: {e}")
            raise

    def _send_local_to_ray(self, connection: 'Connection', data: Any) -> None:
        """本地到Ray Actor：远程调用"""
        try:
            actor_handle = connection.target_config["actorhandle"]
            input_tag = connection.target_input_tag
            
            if not isinstance(actor_handle, ActorHandle):
                raise TypeError(f"Expected ActorHandle, got {type(actor_handle)}")
            
            # 调用Ray Actor的process_data方法
            actor_handle.process.remote(input_tag, data)
            
            self.logger.debug(f"Sent local->ray: {connection.target_name}[{input_tag}]")
            
        except Exception as e:
            self.logger.error(f"Error in local->ray send: {e}")
            raise

    def _send_ray_to_local(self, connection: 'Connection', data: Any) -> None:
        """Ray Actor到本地：TCP连接"""
        try:
            tcp_host = connection.target_config["tcp_host"]
            tcp_port = connection.target_config["tcp_port"]
            target_node_name = connection.target_config["node_name"]
            input_tag = connection.target_input_tag
            
            # 构造TCP消息包
            message = {
                "type": "ray_to_local",
                "source_actor": self.name,
                "target_node": target_node_name,
                "input_tag": input_tag,
                "data": data,
                "timestamp": time.time_ns()
            }
            
            # 获取TCP连接并发送
            tcp_connection = self._get_tcp_connection(tcp_host, tcp_port)
            serialized_data = pickle.dumps(message)
            message_size = len(serialized_data)
            
            tcp_connection.sendall(message_size.to_bytes(4, byteorder='big'))
            tcp_connection.sendall(serialized_data)
            
            self.logger.debug(f"Sent ray->local via TCP: {target_node_name}[{input_tag}]")
            
        except Exception as e:
            self.logger.error(f"Error in ray->local TCP send: {e}")
            # 重置TCP连接
            self._reset_tcp_connection(connection.target_config["tcp_host"], 
                                     connection.target_config["tcp_port"])
            raise

    def _send_ray_to_ray(self, connection: 'Connection', data: Any) -> None:
        """Ray Actor到Ray Actor：远程调用"""
        try:
            actor_handle = connection.target_config["actorhandle"]
            input_tag = connection.target_input_tag
            
            if not isinstance(actor_handle, ActorHandle):
                raise TypeError(f"Expected ActorHandle, got {type(actor_handle)}")
            
            # 调用目标Ray Actor的process_data方法
            actor_handle.process.remote(input_tag, data)
            
            self.logger.debug(f"Sent ray->ray: {connection.target_name}[{input_tag}]")
            
        except Exception as e:
            self.logger.error(f"Error in ray->ray send: {e}")
            raise

    def _get_tcp_connection(self, host: str, port: int) -> socket.socket:
        """获取TCP连接（懒加载和重用）"""
        connection_key = f"{host}:{port}"
        
        if connection_key not in self._tcp_connections:
            with self._socket_lock:
                if connection_key not in self._tcp_connections:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((host, port))
                        self._tcp_connections[connection_key] = sock
                        self.logger.info(f"Established TCP connection to {host}:{port}")
                    except Exception as e:
                        self.logger.error(f"Failed to connect to TCP server {host}:{port}: {e}")
                        raise
        
        return self._tcp_connections[connection_key]

    def _reset_tcp_connection(self, host: str, port: int):
        """重置指定的TCP连接"""
        connection_key = f"{host}:{port}"
        with self._socket_lock:
            if connection_key in self._tcp_connections:
                try:
                    self._tcp_connections[connection_key].close()
                except:
                    pass  # 忽略关闭错误
                del self._tcp_connections[connection_key]
                self.logger.debug(f"Reset TCP connection to {host}:{port}")

    def close(self):
        """关闭所有TCP连接"""
        with self._socket_lock:
            for connection_key, sock in self._tcp_connections.items():
                try:
                    sock.close()
                    self.logger.debug(f"Closed TCP connection: {connection_key}")
                except:
                    pass  # 忽略关闭错误
            self._tcp_connections.clear()
            self.logger.info("Closed all TCP connections")

    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        with self._socket_lock:
            return {
                "active_tcp_connections": len(self._tcp_connections),
                "tcp_endpoints": list(self._tcp_connections.keys())
            }