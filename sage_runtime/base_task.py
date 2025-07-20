from abc import ABC, abstractmethod
import threading, copy, time
from typing import Any, TYPE_CHECKING, Union, Optional
from sage_utils.custom_logger import CustomLogger
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.io.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.io.connection import Connection
    from sage_core.operator.base_operator import BaseOperator
    from sage_runtime.operator.factory import OperatorFactory

class BaseTask(ABC):
    def __init__(self,runtime_context: 'RuntimeContext',operator_factory: 'OperatorFactory') -> None:
        self.ctx = runtime_context
        # === 继承类设置 ===
        self.router:Any
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
        except Exception as e:
            self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)


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
        if not self.stop_event.is_set():
            self.stop_event.set()
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
                    self.operator.process_packet(None)
                    # TODO: 做一个下游缓冲区反压机制，因为引入一个手动延迟实在是太呆了
                    time.sleep(self.delay)
                else:
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    data_packet = self.input_buffer.get(timeout=0.5)
                    if data_packet is None:
                        time.sleep(0.01)
                        continue
                    self.operator.process_packet(data_packet)
            except Exception as e:
                self.logger.error(f"Critical error in node '{self.name}': {str(e)}")
                raise RuntimeError(f"Execution failed in node '{self.name}'")
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
    def logger(self) -> CustomLogger:
        """获取当前任务的日志记录器"""
        return self.ctx.logger

    @property
    def name(self) -> str:
        """获取任务名称"""
        return self.ctx.name
