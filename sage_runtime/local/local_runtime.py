from sage.core.runtime import BaseRuntime
from sage.core.runtime.local.local_scheduling_strategy import ResourceAwareStrategy
# from sage.core.sage_runtime.local.local_task import StreamingTask,BaseTask
from sage.core.runtime.local.local_slot import Slot
from sage.core.runtime.local.local_dag_node import LocalDAGNode
from sage_utils.custom_logger import CustomLogger
import threading
import socket
import pickle
from typing import Dict, Optional, Any, List

class LocalRuntime(BaseRuntime):
    """本地线程池执行后端"""
    
    _instance = None
    _lock = threading.Lock()


    def __init__(self, max_slots=4, scheduling_strategy=None,  tcp_host: str = "localhost", tcp_port: int = 9999):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.name = "LocalRuntime"
        self.available_slots = [Slot(slot_id=i) for i in range(max_slots)]
        self.tcp_host = tcp_host  # 添加这行
        self.tcp_port = tcp_port  # 添加这行
        # 节点管理
        self.running_nodes: Dict[str, LocalDAGNode] = {}  # 正在运行的节点表
        self.node_to_slot: Dict[LocalDAGNode, int] = {}  # 节点到slot的映射
        self.node_to_handle: Dict[LocalDAGNode, str] = {}  # 节点到handle的映射
        self.handle_to_node: Dict[str, LocalDAGNode] = {}  # handle到节点的映射
        self.next_handle_id = 0



        self.logger = CustomLogger(
            object_name=f"LocalRuntime",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        
        if scheduling_strategy is None:
            self.scheduling_strategy = ResourceAwareStrategy()
        else:
            self.scheduling_strategy = scheduling_strategy
            # 启动TCP服务器
        self._start_tcp_server()

    def __new__(cls, max_slots=4, scheduling_strategy=None, session_folder: str = None,  
                tcp_host: str = "localhost", tcp_port: int = 9999):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")
    
    @classmethod
    def get_instance(cls, max_slots=4, scheduling_strategy=None, 
                     tcp_host: str = "localhost", tcp_port: int = 9999):
        """获取LocalRuntime的唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__(max_slots, scheduling_strategy, tcp_host, tcp_port)
                    cls._instance = instance
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
                cls._instance = None




    def _start_tcp_server(self):
        """启动TCP服务器用于接收Ray Actor的数据"""
        try:
            self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server_socket.bind((self.tcp_host, self.tcp_port))
            self.tcp_server_socket.listen(10)
            
            self.tcp_running = True
            self.tcp_server_thread = threading.Thread(
                target=self._tcp_server_loop,
                name="TCPServerThread"
            )
            self.tcp_server_thread.daemon = True
            self.tcp_server_thread.start()
            
            self.logger.info(f"TCP server started on {self.tcp_host}:{self.tcp_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
            raise
    def _tcp_server_loop(self):
        """TCP服务器主循环"""
        self.logger.debug("TCP server loop started")
        
        while self.tcp_running:
            try:
                client_socket, address = self.tcp_server_socket.accept()
                self.logger.debug(f"New TCP client connected from {address}")
                
                # 在新线程中处理客户端
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, address),
                    name=f"TCPClient-{address}"
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.tcp_running:
                    self.logger.error(f"Error accepting TCP connection: {e}")
        
        self.logger.debug("TCP server loop stopped")

    def _handle_tcp_client(self, client_socket: socket.socket, address):
        """处理TCP客户端连接和消息"""
        try:
            while self.tcp_running:
                # 读取消息长度
                size_data = client_socket.recv(4)
                if not size_data:
                    break
                
                message_size = int.from_bytes(size_data, byteorder='big')
                
                # 读取消息内容
                message_data = b''
                while len(message_data) < message_size:
                    chunk = client_socket.recv(message_size - len(message_data))
                    if not chunk:
                        break
                    message_data += chunk
                
                if len(message_data) != message_size:
                    self.logger.warning(f"Incomplete message received from {address}")
                    continue
                
                # 反序列化并处理消息
                try:
                    message = pickle.loads(message_data)
                    self._process_tcp_message(message, address)
                except Exception as e:
                    self.logger.error(f"Error processing message from {address}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error handling TCP client {address}: {e}")
        finally:
            client_socket.close()
            self.logger.debug(f"TCP client {address} disconnected")
    
    def _process_tcp_message(self, message: Dict[str, Any], client_address):
        """
        处理来自Ray Actor的TCP消息
        
        Args:
            message: 包含消息内容的字典
            client_address: 客户端地址
        """
        try:
            message_type = message.get("type")
            
            if message_type == "ray_to_local":
                # Ray Actor发送给本地节点的数据
                target_node_name = message["target_node"]
                target_channel = message["target_channel"]
                data = message["data"]
                source_actor = message.get("source_actor", "unknown")
                
                # 查找目标节点
                if target_node_name in self.running_nodes:
                    target_node = self.running_nodes[target_node_name]
                    
                    # 将数据放入目标节点的输入缓冲区
                    data_packet = (target_channel, data)
                    target_node.put(data_packet)
                    
                    self.logger.debug(f"Delivered TCP message: {source_actor} -> "
                                    f"{target_node_name}[in:{target_channel}]")
                else:
                    self.logger.warning(f"Target node '{target_node_name}' not found for TCP message from {client_address}")
            else:
                self.logger.warning(f"Unknown TCP message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing TCP message: {e}", exc_info=True)
    
    def submit_node(self, node: LocalDAGNode) -> str:
        """
        提交单个MultiplexerDagNode到本地运行时
        
        Args:
            node: MultiplexerDagNode实例
            
        Returns:
            str: 任务句柄
        """
        if not isinstance(node, LocalDAGNode):
            raise TypeError("Expected LocalDAGNode instance")
        
        self.logger.info(f"Submitting node '{node.name}' to {self.name}")
        
        try:
            # 创建StreamingTask包装节点
            # task = StreamingTask(node, {})
            
            # 选择slot并提交
            slot_id = self.scheduling_strategy.select_slot(node, self.available_slots)
            success = self.available_slots[slot_id].submit_task(node)
            
            if success:
                # 生成handle
                handle = f"local_node_{self.next_handle_id}"
                self.next_handle_id += 1
                
                # 更新映射关系
                self.running_nodes[node.name] = node
                self.node_to_slot[node] = slot_id
                self.node_to_handle[node] = handle
                self.handle_to_node[handle] = node
                
                self.logger.info(f"Node '{node.name}' submitted successfully with handle: {handle}")
                return handle
            else:
                raise RuntimeError(f"Failed to submit node '{node.name}' to slot {slot_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to submit node '{node.name}': {e}")
            raise
    
    def submit_nodes(self, nodes: List[LocalDAGNode]) -> List[str]:
        """
        批量提交多个节点
        
        Args:
            nodes: MultiplexerDagNode列表
            
        Returns:
            List[str]: 任务句柄列表
        """
        handles = []
        for node in nodes:
            try:
                handle = self.submit_node(node)
                handles.append(handle)
            except Exception as e:
                self.logger.error(f"Failed to submit node '{node.name}': {e}")
                # 停止已经提交的节点
                for h in handles:
                    self.stop_node(h)
                raise
        
        self.logger.info(f"Successfully submitted {len(handles)} nodes")
        return handles


    def stop_node(self, node_handle: str):
        """
        停止指定的节点
        
        Args:
            node_handle: 节点句柄
        """
        if node_handle not in self.handle_to_node:
            self.logger.warning(f"Node handle '{node_handle}' not found")
            return
        
        try:
            node = self.handle_to_node[node_handle]
            slot_id = self.node_to_slot[node]
            
            # 停止节点
            node.stop()
            
            # 从slot中移除任务
            # 这里需要找到对应的task
            for task in self.available_slots[slot_id].running_tasks:
                if hasattr(task, 'node') and task.node == node:
                    self.available_slots[slot_id].stop(task)
                    break
            
            # 清理映射关系
            self.running_nodes.pop(node.name, None)
            self.node_to_slot.pop(node, None)
            self.node_to_handle.pop(node, None)
            self.handle_to_node.pop(node_handle, None)
            
            self.logger.info(f"Node '{node.name}' stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping node with handle '{node_handle}': {e}")
    
    def stop_all_nodes(self):
        """停止所有运行中的节点"""
        self.logger.info("Stopping all nodes...")
        
        handles_to_stop = list(self.handle_to_node.keys())
        for handle in handles_to_stop:
            self.stop_node(handle)
        
        self.logger.info(f"Stopped {len(handles_to_stop)} nodes")
    
    def get_node_status(self, node_handle: str) -> Dict[str, Any]:
        """
        获取节点状态
        
        Args:
            node_handle: 节点句柄
            
        Returns:
            Dict: 节点状态信息
        """
        if node_handle not in self.handle_to_node:
            return {"status": "not_found"}
        
        node = self.handle_to_node[node_handle]
        slot_id = self.node_to_slot[node]
        
        return {
            "status": "running",
            "node_name": node.name,
            "is_spout": node.is_spout,
            "slot_id": slot_id,
            "backend": "local",
            "handle": node_handle
        }
    
    def get_running_nodes(self) -> List[str]:
        """获取所有运行中的节点名称"""
        return list(self.running_nodes.keys())
    
    def get_node_by_name(self, node_name: str) -> Optional[LocalDAGNode]:
        """根据名称获取节点"""
        return self.running_nodes.get(node_name)
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """获取运行时信息"""
        return {
            "name": self.name,
            "tcp_server": f"{self.tcp_host}:{self.tcp_port}",
            "running_nodes_count": len(self.running_nodes),
            "running_nodes": list(self.running_nodes.keys()),
            "available_slots": len(self.available_slots),
            "used_slots": len(self.node_to_slot),
            "tcp_running": self.tcp_running
        }
    
    def shutdown(self):
        """关闭运行时和所有资源"""
        self.logger.info("Shutting down LocalRuntime...")
        
        # 停止所有节点
        self.stop_all_nodes()
        
        # 关闭TCP服务器
        self.tcp_running = False
        if self.tcp_server_socket:
            self.tcp_server_socket.close()
        
        # 等待TCP服务器线程结束
        if self.tcp_server_thread and self.tcp_server_thread.is_alive():
            self.tcp_server_thread.join(timeout=2.0)
        
        self.logger.info("LocalRuntime shutdown completed")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.shutdown()
        except:
            pass