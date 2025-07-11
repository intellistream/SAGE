import os
import threading
import logging
from typing import Dict, Optional, Any, List
from concurrent.futures import ThreadPoolExecutor
from sage_runtime.dagnode.local_dag_node import LocalDAGNode
from sage_runtime.io.local_tcp_server import LocalTcpServer
from sage_utils.custom_logger import CustomLogger
import time
import socket
class LocalThreadPool:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.logger = CustomLogger(
            filename="LocalThreadPool",
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING",
        )

        self._initialized = True
        self.name = "LocalThreadPool"
        self.logger.debug(f"CPU count is {os.cpu_count()}")
        self.thread_pool = ThreadPoolExecutor(
            max_workers=os.cpu_count() * 3,
            thread_name_prefix=None,
            initializer=None,
            initargs=None
        )
        # 节点管理
        # self.running_nodes: Dict[str, LocalDAGNode] = {}  # 正在运行的节点表
        # self.handle_to_node: Dict[str, LocalDAGNode] = {}  # handle到节点的映射


            
    @classmethod
    def get_instance(cls):
        """获取LocalRuntime的唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance



    
    def submit_node(self, node: LocalDAGNode) -> str:

        self.logger.info(f"Submitting node '{node.name}' to {self.name}")
        try:
            future=self.thread_pool.submit(node.run_loop)
        except Exception as e:
            self.logger.error(f"Failed to submit node '{node.name}': {e}", exc_info=True)

    
    def shutdown(self):
        """关闭运行时和所有资源"""
        self.logger.info("Shutting down LocalThreadPool...")
        
        # 停止所有节点
        self.thread_pool.shutdown(wait=True, cancel_futures=True)
        
        # # 关闭TCP服务器
        # if self.tcp_server:
        #     self.tcp_server.stop()
        
        self.logger.info("LocalThreadPool shutdown completed")
    



    
    ########################################################
    #                inactive methods                      #
    ########################################################

    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
                cls._instance = None

    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def __new__(cls, *args, **kwargs):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.shutdown()
        except:
            pass