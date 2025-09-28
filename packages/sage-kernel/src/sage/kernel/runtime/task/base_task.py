import threading
import time
from abc import ABC
from queue import Empty as QueueEmpty
from typing import TYPE_CHECKING, Optional

try:
    from ray.util.queue import Empty as RayQueueEmpty
except ImportError:
    RayQueueEmpty = QueueEmpty
from sage.kernel.runtime.communication.router.packet import Packet, StopSignal
from sage.kernel.runtime.context.task_context import TaskContext

if TYPE_CHECKING:
    from sage.core.factory.operator_factory import OperatorFactory
    from sage.core.operator.base_operator import BaseOperator


QUEUE_EMPTY_EXCEPTIONS = (
    (QueueEmpty,) if RayQueueEmpty is QueueEmpty else (QueueEmpty, RayQueueEmpty)
)


class BaseTask(ABC):
    def __init__(self, ctx: "TaskContext", operator_factory: "OperatorFactory") -> None:
        self.ctx = ctx

        # 使用从上下文传入的队列描述符，而不是直接创建队列
        self.input_qd = self.ctx.input_qd

        if self.input_qd:
            self.logger.info(
                f"🎯 Task: Using queue descriptor for input buffer: {self.input_qd.queue_id}"
            )
        else:
            self.logger.info(f"🎯 Task: No input queue (source/spout node)")

        # === 线程控制 ===
        self._worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        # === 性能监控 ===
        self._processed_count = 0
        self._error_count = 0
        try:
            self.operator: BaseOperator = operator_factory.create_operator(self.ctx)
            self.operator.task = self
            # 不再需要inject_router，operator通过ctx.send_packet()进行路由
            # self.operator.inject_router(self.router)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize node {self.name}: {e}", exc_info=True
            )
            raise

    @property
    def router(self):
        return self.ctx.router

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
            target=self._worker_loop, name=f"{self.name}_worker", daemon=True
        )
        self._worker_thread.start()

        self.logger.info(f"Task {self.name} started with worker thread")

    # 连接管理现在由TaskContext在构造时完成，不再需要动态添加连接

    def trigger(self, input_tag: str = None, packet: "Packet" = None) -> None:
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            self.operator.process_packet(packet)
        except Exception as e:
            self.logger.error(
                f"Error processing data in node {self.name}: {e}", exc_info=True
            )
            raise

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if not self.ctx.is_stop_requested():
            self.ctx.set_stop_signal()
            self.logger.info(f"Node '{self.name}' received stop signal.")
            # 立即标记任务为已停止，这样dispatcher就能正确检测到
            self.is_running = False

    def get_object(self):
        return self

    def get_input_buffer(self):
        """
        获取输入缓冲区
        :return: 输入缓冲区对象
        """
        # 通过描述符获取队列实例
        return self.input_qd.queue_instance

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
                        data_packet = self.input_qd.get(timeout=5.0)
                    except QUEUE_EMPTY_EXCEPTIONS:
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    except Exception as e:
                        self.logger.error(
                            f"Unexpected error fetching data for task {self.name}: {e}",
                            exc_info=True,
                        )
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue
                    self.logger.debug(
                        f"Node '{self.name}' received data packet: {data_packet}, type: {type(data_packet)}"
                    )
                    if data_packet is None:
                        self.logger.info(
                            f"Task {self.name}: Received None packet, continuing loop"
                        )
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue

                    # Check if received packet is a StopSignal
                    if isinstance(data_packet, StopSignal):
                        self.logger.info(
                            f"Node '{self.name}' received stop signal: {data_packet}"
                        )

                        # 如果是SinkOperator，在转发停止信号前先调用handle_stop_signal
                        # Comap不能直接套用Join的逻辑，否则会出问题
                        from sage.core.operator.join_operator import \
                            JoinOperator
                        from sage.core.operator.sink_operator import \
                            SinkOperator

                        if isinstance(self.operator, SinkOperator):
                            self.logger.info(
                                f"SinkOperator {self.name} starting graceful shutdown after stop signal"
                            )
                            self._handle_sink_stop_signal(data_packet)
                            break
                        elif isinstance(self.operator, (JoinOperator)):
                            self.logger.info(
                                f"Calling handle_stop_signal for {type(self.operator).__name__} {self.name}"
                            )
                            # 对于Join和CoMap操作，需要传递停止信号的来源信息
                            # 从data_packet中提取input_index信息
                            input_index = getattr(data_packet, "input_index", None)
                            self.operator.handle_stop_signal(
                                stop_signal_name=data_packet.source,
                                input_index=input_index,
                            )
                            # 对于Join和CoMap，不调用ctx.handle_stop_signal，让operator自己决定何时停止
                            # 跳过向下游转发停止信号，让operator自己处理
                            continue

                        # 对于所有操作符，立即向下游转发停止信号
                        # 这确保停止信号能够传播到整个拓扑
                        self.router.send_stop_signal(data_packet)

                        # 在task层统一处理停止信号计数
                        should_stop_pipeline = self.ctx.handle_stop_signal(data_packet)

                        # 停止当前task的worker loop
                        # 但是要特别处理某些操作符
                        from sage.core.operator.filter_operator import \
                            FilterOperator
                        from sage.core.operator.keyby_operator import \
                            KeyByOperator
                        from sage.core.operator.map_operator import MapOperator

                        # 对于中间转换操作符，需要额外的逻辑确保它们不会过早停止
                        if isinstance(
                            self.operator, (KeyByOperator, MapOperator, FilterOperator)
                        ):
                            # 中间操作符应该在收到停止信号后立即停止并转发信号
                            # 这样确保停止信号能够正确传播到下游
                            self.logger.info(
                                f"Intermediate operator {self.name} received stop signal, stopping and forwarding"
                            )
                            # 先通知JobManager该节点完成
                            self.ctx.send_stop_signal_back(self.name)
                            # 然后让中间操作符停止，确保停止信号能传播
                            self.ctx.set_stop_signal()
                            break
                        elif should_stop_pipeline:
                            self.ctx.set_stop_signal()
                            break

                        continue

                    self.operator.receive_packet(data_packet)
            except Exception as e:
                self.logger.error(f"Critical error in node '{self.name}': {str(e)}")
            finally:
                self.is_running = False

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

            # 清理输入队列描述符
            if self.input_qd and hasattr(self.input_qd, "cleanup"):
                self.input_qd.cleanup()
            elif self.input_qd and hasattr(self.input_qd, "close"):
                self.input_qd.close()

            # 清理运行时上下文（包括service_manager）
            if hasattr(self.ctx, "cleanup"):
                self.ctx.cleanup()

            self.logger.debug(f"Task {self.name} cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup of task {self.name}: {e}")

    def _handle_sink_stop_signal(self, stop_signal: "StopSignal"):
        """Gracefully drain in-flight data before finalizing a sink task."""
        drain_timeout = getattr(self.operator, "drain_timeout", 10.0)
        quiet_period = getattr(self.operator, "drain_quiet_period", 0.3)
        drained = self._drain_inflight_messages(
            timeout=drain_timeout,
            quiet_period=quiet_period,
        )

        if drained == -1:
            self.logger.warning(
                f"Sink task {self.name} timed out while draining in-flight data"
            )
        else:
            self.logger.info(
                f"Sink task {self.name} drained {drained} in-flight packets before shutdown"
            )

        # 完成最终的关闭逻辑
        try:
            self.operator.handle_stop_signal()
        except Exception as e:
            self.logger.error(
                f"Error during sink operator finalization for {self.name}: {e}",
                exc_info=True,
            )

        # 通过上下文通知JobManager并传播停止信号
        try:
            self.ctx.handle_stop_signal(stop_signal)
        finally:
            self.ctx.set_stop_signal()

    def _drain_inflight_messages(
        self,
        timeout: float,
        quiet_period: float,
    ) -> int:
        """Drain packets that arrived before the stop signal reached the sink."""
        if not self.input_qd:
            return 0

        start_time = time.time()
        last_packet_time = start_time
        drained_packets = 0
        poll_interval = min(quiet_period, 0.1)

        self.logger.debug(
            f"Sink task {self.name} draining queues with timeout={timeout}s and quiet_period={quiet_period}s"
        )

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return -1

            try:
                packet = self.input_qd.get(timeout=poll_interval)
            except QUEUE_EMPTY_EXCEPTIONS:
                if time.time() - last_packet_time >= quiet_period:
                    break
                continue

            if isinstance(packet, StopSignal):
                # 如果还有其他停止信号，继续等待数据排空
                continue

            try:
                self.operator.receive_packet(packet)
                drained_packets += 1
                last_packet_time = time.time()
            except Exception as e:
                self.logger.error(
                    f"Failed to process in-flight packet during draining for {self.name}: {e}",
                    exc_info=True,
                )

        return drained_packets
