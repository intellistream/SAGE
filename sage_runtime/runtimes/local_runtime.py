from sage_runtime.base_runtime import BaseRuntime
from sage_runtime.executor.local_dag_node import LocalDAGNode
from sage_runtime.runtimes.local_tcp_server import LocalTcpServer
from sage_utils.custom_logger import CustomLogger
from concurrent.futures import ThreadPoolExecutor
import os, threading
from typing import Dict, Optional, Any, List

class LocalRuntime(BaseRuntime):
    """本地线程池执行后端"""
    
    _instance = None
    _lock = threading.Lock()


    def __init__(self, tcp_host: str = "localhost", tcp_port: int = 9999):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self.logger = CustomLogger(
            filename=f"LocalRuntime",
            console_output="WARNING",
            file_output="WARNING",
            global_output = "WARNING",
        )
        self._initialized = True
        self.name = "LocalRuntime"
        self.logger.debug(f"cpu count is {os.cpu_count()}")
        self.thread_pool = ThreadPoolExecutor(
            max_workers=os.cpu_count() * 3,
            thread_name_prefix=None,
            initializer=None,
            initargs=None
        )
        # 节点管理
        self.running_nodes: Dict[str, LocalDAGNode] = {}  # 正在运行的节点表
        self.node_to_handle: Dict[LocalDAGNode, str] = {}  # 节点到handle的映射
        self.handle_to_node: Dict[str, LocalDAGNode] = {}  # handle到节点的映射
        self.next_handle_id = 0

        
        # 初始化TCP服务器
        self.tcp_server = LocalTcpServer(
            host=tcp_host,
            port=tcp_port,
            message_handler=self._handle_tcp_message
        )
        self.tcp_server.start()

    def __new__(cls, *args, **kwargs):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")
    
    @classmethod
    def get_instance(cls, tcp_host: str = "localhost", tcp_port: int = 9999):
        """获取LocalRuntime的唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__(tcp_host, tcp_port)
                    cls._instance = instance
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
                cls._instance = None

    def _handle_tcp_message(self, message: Dict[str, Any], client_address: tuple):
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
                input_tag = message["input_tag"]
                data = message["data"]
                source_actor = message.get("source_actor", "unknown")
                
                # 查找目标节点
                if target_node_name in self.running_nodes:
                    target_node = self.running_nodes[target_node_name]
                    
                    # 将数据放入目标节点的输入缓冲区
                    data_packet = (input_tag, data)
                    target_node.put(data_packet)
                    
                    self.logger.debug(f"Delivered TCP message: {source_actor} -> "
                                    f"{target_node_name}[in:{input_tag}]")
                else:
                    self.logger.warning(f"Target node '{target_node_name}' not found for TCP message from {client_address}")
            else:
                self.logger.warning(f"Unknown TCP message type: {message_type} from {client_address}")
                
        except Exception as e:
            self.logger.error(f"Error processing TCP message from {client_address}: {e}", exc_info=True)
    
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
            future=self.thread_pool.submit(node.run_loop)
            #self.task_to_future[node]=future
            # 选择slot并提交
            # slot_id = self.scheduling_strategy.select_slot(node, self.available_slots)
            # success = self.available_slots[slot_id].submit_streaming_task(node)
                
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
        
        return {
            "status": "running",
            "node_name": node.name,
            "is_spout": node.is_spout,
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
        tcp_info = self.tcp_server.get_server_info()
        return {
            "name": self.name,
            "tcp_server": tcp_info["address"],
            "tcp_running": tcp_info["running"],
            "running_nodes_count": len(self.running_nodes),
            "running_nodes": list(self.running_nodes.keys()),
        }
    
    def shutdown(self):
        """关闭运行时和所有资源"""
        self.logger.info("Shutting down LocalRuntime...")
        
        # 停止所有节点
        self.stop_all_nodes()
        
        # 关闭TCP服务器
        if self.tcp_server:
            self.tcp_server.stop()
        
        self.logger.info("LocalRuntime shutdown completed")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.shutdown()
        except:
            pass