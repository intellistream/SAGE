from abc import ABC, abstractmethod
from queue import Empty
import threading, copy, time
from typing import Any, TYPE_CHECKING, Union, Optional
from sage.runtime.runtime_context import RuntimeContext
from sage.runtime.router.packet import Packet
from ray.util.queue import Empty

from sage.utils.queue_adapter import create_queue
from sage.runtime.router.router import BaseRouter
from sage.core.function.source_function import StopSignal
if TYPE_CHECKING:
    from sage.runtime.router.connection import Connection
    from sage.core.operator.base_operator import BaseOperator
    from sage.runtime.factory.operator_factory import OperatorFactory

class BaseTask(ABC):
    def __init__(self,runtime_context: 'RuntimeContext',operator_factory: 'OperatorFactory') -> None:
        self.ctx = runtime_context
        
        # 初始化task层的context属性，避免序列化问题
        self.ctx.initialize_task_context()
        
        self.logger.info(f"🎯 Task: Creating input_buffer with name='{self.ctx.name}'")
        self.input_buffer = create_queue(name=self.ctx.name)
        if hasattr(self.input_buffer, 'logger'):
            self.input_buffer.logger = self.ctx.logger
        # === 线程控制 ===
        self._worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        # 使用ctx中的共享stop_event，不再自己维护
        # === 性能监控 ===
        self._processed_count = 0
        self._error_count = 0
        self._last_activity_time = time.time()
        self.router = BaseRouter(runtime_context)
        try:
            self.operator:BaseOperator = operator_factory.create_operator(self.ctx)
            self.operator.task = self
            self.operator.inject_router(self.router)
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
        self.ctx.clear_stop_signal()
        
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

    # def remove_connection(self, broadcast_index: int, parallel_index: int) -> bool:
    #     return self.router.remove_connection(broadcast_index, parallel_index)


    def trigger(self, input_tag: str = None, packet:'Packet' = None) -> None:
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            self.operator.process_packet(packet)
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if not self.ctx.is_stop_requested():
            self.ctx.set_stop_signal()
            self.logger.info(f"Node '{self.name}' received stop signal.")

    def get_object(self):
        return self

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
        while not self.ctx.is_stop_requested():
            try:
                if self.is_spout:
                        
                    self.logger.debug(f"Running spout node '{self.name}'")
                    self.operator.receive_packet(None)
                    self.logger.debug(f"self.delay: {self.delay}")
                    if self.delay > 0.002:
                        time.sleep(self.delay)
                else:
                    
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    try:
                        self.logger.info(f"Task {self.name}: Attempting to get packet from input_buffer (timeout=5.0s)")
                        data_packet = self.input_buffer.get(timeout=5.0)

                        self.logger.info(f"Task {self.name}: Successfully got packet from input_buffer: {data_packet}")
                    except Exception as e:
                        self.logger.error(f"Task {self.name}: No packet received from input_buffer (timeout/exception): {e}")
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    self.logger.debug(f"Node '{self.name}' received data packet: {data_packet}, type: {type(data_packet)}")
                    if data_packet is None:
                        self.logger.info(f"Task {self.name}: Received None packet, continuing loop")
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    
                    # Check if received packet is a StopSignal
                    if isinstance(data_packet, StopSignal):
                        self.logger.info(f"Node '{self.name}' received stop signal: {data_packet}")
                        
                        # 在task层统一处理停止信号计数
                        should_stop_pipeline = self.ctx.handle_stop_signal(data_packet)
                        
                        # 向下游转发停止信号
                        self.router.send_stop_signal(data_packet)
                        
                        # 停止当前task的worker loop
                        if should_stop_pipeline:
                            self.ctx.set_stop_signal()
                            break
                        
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
            
            # 清理运行时上下文（包括service_manager）
            if hasattr(self.ctx, 'cleanup'):
                self.ctx.cleanup()
            
            self.logger.debug(f"Task {self.name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of task {self.name}: {e}")