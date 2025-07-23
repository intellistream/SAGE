from abc import ABC, abstractmethod
from queue import Empty
import threading, copy, time
from typing import Any, TYPE_CHECKING, Union, Optional
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.router.packet import Packet
from ray.util.queue import Empty
if TYPE_CHECKING:
    from sage_runtime.router.base_router import BaseRouter
    from sage_runtime.router.connection import Connection
    from sage_core.operator.base_operator import BaseOperator
    from sage_jobmanager.factory.operator_factory import OperatorFactory

class BaseTask(ABC):
    def __init__(self,runtime_context: 'RuntimeContext',operator_factory: 'OperatorFactory') -> None:
        self.ctx = runtime_context
        # === 继承类设置 ===
        self.router:BaseRouter
        self.input_buffer: Any
        # === 线程控制 ===
        self._worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self._stop_event = threading.Event()
        # === 性能监控 ===
        self._processed_count = 0
        self._error_count = 0
        self._last_activity_time = time.time()
        try:
            self.operator:BaseOperator = operator_factory.create_operator(self.ctx)
            self.operator.task = self
        except Exception as e:
            self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)
            raise


    def start_running(self):
        """启动任务的工作循环"""
        if self.is_running:
            self.logger.warning(f"Task {self.name} is already running")
            return
        
        self.logger.info(f"Starting task {self.name}")
        
        # 设置运行状态
        self.is_running = True
        self._stop_event.clear()
        
        # 启动工作线程
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name=f"{self.name}_worker",
            daemon=True
        )
        self._worker_thread.start()
        
        self.logger.info(f"Task {self.name} started with worker thread")

    def add_connection(self, connection: 'Connection'):
        self.router.add_connection(connection)
        self.logger.debug(f"Connection added to node '{self.name}': {connection}")

    def remove_connection(self, broadcast_index: int, parallel_index: int) -> bool:
        return self.router.remove_connection(broadcast_index, parallel_index)


    def trigger(self, input_tag: str = None, packet:'Packet' = None) -> None:
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            self.operator.process_packet(packet)
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if not self._stop_event.is_set():
            self._stop_event.set()
            self.logger.info(f"Node '{self.name}' received stop signal.")

    def get_input_buffer(self):
        """
        获取输入缓冲区
        :return: 输入缓冲区对象
        """
        return self.input_buffer

    def _worker_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """
        # Main execution loop
        while not self._stop_event.is_set():
            try:
                if self.is_spout:
                    self.logger.debug(f"Running spout node '{self.name}'")
                    self.operator.receive_packet(None)
                    # TODO: 做一个下游缓冲区反压机制，因为引入一个手动延迟实在是太呆了
                    # Issue URL: https://github.com/intellistream/SAGE/issues/335
                    # sleep时间太短对kernel来说就没有意义了。
                    if self.delay > 0.002:
                        time.sleep(self.delay)
                else:
                    
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    try:
                        data_packet = self.input_buffer.get(timeout=0.5)
                    except Empty as e:
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    self.logger.debug(f"Node '{self.name}' received data packet: {data_packet}, type: {type(data_packet)}")
                    if data_packet is None:
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    self.operator.receive_packet(data_packet)
            except Exception as e:
                self.logger.error(f"Critical error in node '{self.name}': {str(e)}")
            finally:
                self._running = False

    @property
    def is_spout(self) -> bool:
        """检查是否为 spout 节点"""
        return self.ctx.is_spout

    @property
    def delay(self) -> float:
        """获取任务的延迟时间"""
        return self.ctx.delay
    
    @property
    def logger(self):
        """获取当前任务的日志记录器"""
        return self.ctx.logger

    @property
    def name(self) -> str:
        """获取任务名称"""
        return self.ctx.name


    def cleanup(self):
        """清理任务资源"""
        self.logger.info(f"Cleaning up task {self.name}")
        
        try:
            # 停止任务
            if self.is_running:
                self.stop()
            
            # # 清理算子资源
            # if hasattr(self.operator, 'cleanup'):
            #     self.operator.cleanup()
            # 这些内容应该会自己清理掉
            # # 清理路由器
            # if hasattr(self.router, 'cleanup'):
            #     self.router.cleanup()
            
            # 清理输入缓冲区
            if hasattr(self.input_buffer, 'cleanup'):
                self.input_buffer.cleanup()
            elif hasattr(self.input_buffer, 'close'):
                self.input_buffer.close()
            
            self.logger.debug(f"Task {self.name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of task {self.name}: {e}")