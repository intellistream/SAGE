import threading
import time
from abc import ABC
from queue import Empty as QueueEmpty
from typing import TYPE_CHECKING

try:
    from ray.util.queue import Empty as RayQueueEmpty  # type: ignore
except ImportError:
    RayQueueEmpty = QueueEmpty  # type: ignore
from sage.kernel.runtime.communication.packet import Packet, StopSignal
from sage.kernel.runtime.context.task_context import TaskContext
from sage.kernel.runtime.monitoring import (
    RESOURCE_MONITOR_AVAILABLE,
    MetricsCollector,
    MetricsReporter,
    ResourceMonitor,
    TaskPerformanceMetrics,
)

if TYPE_CHECKING:
    from sage.kernel.api.operator.base_operator import BaseOperator
    from sage.kernel.runtime.factory.operator_factory import OperatorFactory


QUEUE_EMPTY_EXCEPTIONS = (
    (QueueEmpty,) if RayQueueEmpty is QueueEmpty else (QueueEmpty, RayQueueEmpty)
)


class BaseTask(ABC):  # noqa: B024
    def __init__(self, ctx: "TaskContext", operator_factory: "OperatorFactory") -> None:
        self.ctx = ctx

        # 使用从上下文传入的队列描述符
        self.input_qd = self.ctx.input_qd

        if self.input_qd:
            self.logger.info(
                f"🎯 Task: Using queue descriptor for input buffer: {self.input_qd.queue_id}"
            )
        else:
            self.logger.info("🎯 Task: No input queue (source/spout node)")

        # === 线程控制 ===
        self._worker_thread: threading.Thread | None = None
        self.is_running = False

        # === 性能监控 ===
        self._processed_count = 0
        self._error_count = 0

        # ✅ 添加 checkpoint 相关属性
        self._checkpoint_counter = 0
        self._last_checkpoint_time = 0.0

        # 检查是否启用性能监控
        self._enable_monitoring = getattr(ctx, "enable_monitoring", False)
        self.metrics_collector: MetricsCollector | None = None
        self.resource_monitor: ResourceMonitor | None = None
        self.metrics_reporter: MetricsReporter | None = None

        self.fault_handler = None  # Will be set by dispatcher if applicable

        if self._enable_monitoring:
            try:
                self.metrics_collector = MetricsCollector(
                    name=self.ctx.name,
                    window_size=getattr(ctx, "metrics_window_size", 10000),
                    enable_detailed_tracking=getattr(ctx, "enable_detailed_tracking", True),
                )

                # 尝试启动资源监控（需要psutil）
                if RESOURCE_MONITOR_AVAILABLE:
                    try:
                        self.resource_monitor = ResourceMonitor(
                            sampling_interval=getattr(ctx, "resource_sampling_interval", 1.0),
                            enable_auto_start=True,
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to start resource monitoring for task {self.name}: {e}"
                        )
                else:
                    self.logger.debug(
                        f"psutil not available, resource monitoring disabled for task {self.name}"
                    )

                # 可选：启动性能汇报器
                if getattr(ctx, "enable_auto_report", False):
                    self.metrics_reporter = MetricsReporter(
                        metrics_collector=self.metrics_collector,
                        resource_monitor=self.resource_monitor,
                        report_interval=getattr(ctx, "report_interval", 60),
                        enable_auto_report=True,
                        report_callback=lambda report: self.logger.info(f"\n{report}"),
                    )

                self.logger.info(f"Performance monitoring enabled for task {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize monitoring for task {self.name}: {e}")
                self._enable_monitoring = False

        try:
            self.operator: BaseOperator = operator_factory.create_operator(self.ctx)
            if hasattr(self.operator, "task"):
                self.operator.task = self  # type: ignore
        except Exception as e:
            self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)
            raise

    def get_state(self) -> dict:
        """
        获取任务完整状态用于 checkpoint

        包括：
        1. Task 层的状态（processed_count, error_count 等）
        2. Operator 层的状态（通过 operator.get_state()）
        3. Function 层的状态（通过 function.get_state()，已包含在 operator 中）

        Returns:
            任务完整状态字典
        """
        state = {
            # === Task 元数据 ===
            "task_id": self.name,
            "task_type": self.__class__.__name__,
            "is_spout": self.is_spout,
            "timestamp": time.time(),
            # === Task 性能指标 ===
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "checkpoint_counter": self._checkpoint_counter,
            "last_checkpoint_time": self._last_checkpoint_time,
            # === Task 配置 ===
            "delay": self.delay,
        }

        # === Operator 和 Function 状态 ===
        if hasattr(self.operator, "get_state"):
            try:
                operator_state = self.operator.get_state()
                state["operator_state"] = operator_state

                self.logger.debug(
                    f"Captured operator state for {self.name}: {list(operator_state.keys())}"
                )

                # 如果 operator_state 包含 function_state，也记录
                if "function_state" in operator_state:
                    function_attrs = list(operator_state["function_state"].keys())
                    self.logger.debug(f"Function state includes: {function_attrs}")

            except Exception as e:
                self.logger.warning(
                    f"Failed to get operator state for {self.name}: {e}", exc_info=True
                )
                state["operator_state"] = None
        else:
            self.logger.warning(
                f"Operator {self.operator.__class__.__name__} does not support get_state()"
            )
            state["operator_state"] = None

        # === Context 配置信息（只保存配置，不保存运行时对象）===
        try:
            state["context_config"] = {
                "name": self.ctx.name,
                "is_spout": self.ctx.is_spout,
                "delay": self.ctx.delay,
                # 不保存 queue, router 等运行时对象
            }
        except Exception as e:
            self.logger.warning(f"Failed to capture context config: {e}")

        # 记录状态大小（用于监控）
        try:
            import sys

            state_size = sys.getsizeof(str(state))
            self.logger.debug(f"Checkpoint state size for {self.name}: {state_size} bytes")
        except Exception:
            pass

        return state

    def restore_state(self, state: dict):
        """
        从 checkpoint 完整恢复任务状态

        恢复顺序：
        1. Task 层状态
        2. Operator 层状态
        3. Function 层状态（通过 operator.restore_state）

        Args:
            state: 保存的状态字典
        """
        self.logger.info(f"⏮️ Restoring state for task {self.name}")

        try:
            # === 恢复 Task 层状态 ===
            self._processed_count = state.get("processed_count", 0)
            self._error_count = state.get("error_count", 0)
            self._checkpoint_counter = state.get("checkpoint_counter", 0)
            self._last_checkpoint_time = state.get("last_checkpoint_time", 0.0)

            self.logger.info(
                f"✅ Task state restored: "
                f"processed={self._processed_count}, "
                f"errors={self._error_count}, "
                f"checkpoints={self._checkpoint_counter}"
            )

            # === 恢复 Operator 和 Function 状态 ===
            operator_state = state.get("operator_state")
            if operator_state and hasattr(self.operator, "restore_state"):
                try:
                    self.operator.restore_state(operator_state)
                    self.logger.info(f"✅ Operator state restored for {self.name}")

                    # 验证 function 状态是否恢复
                    if hasattr(self.operator, "function"):
                        function = self.operator.function

                        # 记录恢复的 function 属性
                        restored_attrs = []
                        if "function_state" in operator_state:
                            for attr_name in operator_state["function_state"].keys():
                                if hasattr(function, attr_name):
                                    value = getattr(function, attr_name)
                                    restored_attrs.append(f"{attr_name}={value}")

                        if restored_attrs:
                            self.logger.info(
                                f"✅ Function attributes restored: {', '.join(restored_attrs)}"
                            )

                except Exception as e:
                    self.logger.error(f"❌ Failed to restore operator state: {e}", exc_info=True)
            else:
                if not operator_state:
                    self.logger.warning(f"⚠️ No operator state found in checkpoint for {self.name}")
                elif not hasattr(self.operator, "restore_state"):
                    self.logger.warning(
                        f"⚠️ Operator {self.operator.__class__.__name__} does not support restore_state()"
                    )

            self.logger.info(f"🎉 Complete state restoration finished for task {self.name}")

        except Exception as e:
            self.logger.error(
                f"❌ Critical error during state restoration for {self.name}: {e}",
                exc_info=True,
            )
            raise

    def save_checkpoint_if_needed(self, fault_handler) -> bool:
        """
        如果需要，保存 checkpoint

        Args:
            fault_handler: 容错处理器

        Returns:
            True 如果保存了 checkpoint
        """
        # 检查是否是 CheckpointBasedRecovery
        from sage.kernel.fault_tolerance.impl.checkpoint_recovery import (
            CheckpointBasedRecovery,
        )

        if not isinstance(fault_handler, CheckpointBasedRecovery):
            return False

        current_time = time.time()
        interval = fault_handler.checkpoint_interval

        # 检查是否应该保存 checkpoint
        if (current_time - self._last_checkpoint_time) >= interval:
            state = self.get_state()
            success = fault_handler.save_checkpoint(self.name, state)

            if success:
                self._last_checkpoint_time = current_time
                self._checkpoint_counter += 1
                self.logger.debug(
                    f"Checkpoint #{self._checkpoint_counter} saved for task {self.name}"
                )

            return success

        return False

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

    def trigger(self, input_tag: str | None = None, packet: "Packet | None" = None) -> None:
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            if packet is not None:
                self.operator.process_packet(packet)  # type: ignore
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
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
        # 获取 fault_handler（如果有）
        fault_handler = None
        if (
            hasattr(self.ctx, "dispatcher")
            and self.ctx.dispatcher
            and hasattr(self.ctx.dispatcher, "fault_handler")
        ):
            fault_handler = self.ctx.dispatcher.fault_handler
            self.logger.debug(f"Task {self.name} has fault_handler: {type(fault_handler).__name__}")

        # Main execution loop
        while not self.ctx.is_stop_requested():
            try:
                # ✅ 定期保存 checkpoint
                if fault_handler:
                    self.save_checkpoint_if_needed(fault_handler)

                if self.is_spout:
                    self.logger.debug(f"Running spout node '{self.name}'")
                    if hasattr(self.operator, "receive_packet"):
                        self.operator.receive_packet(None)  # type: ignore

                    # 增加处理计数
                    self._processed_count += 1

                    # 检查是否在执行后收到了停止信号
                    if self.ctx.is_stop_requested():
                        break

                    self.logger.debug(f"self.delay: {self.delay}")
                    if self.delay > 0.002:
                        time.sleep(self.delay)
                else:
                    # For non-spout nodes, fetch input and process
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
                        self.logger.info(f"Task {self.name}: Received None packet, continuing loop")
                        if self.delay > 0.002:
                            time.sleep(self.delay)
                        continue

                    # Check if received packet is a StopSignal
                    if isinstance(data_packet, StopSignal):
                        self.logger.info(f"Node '{self.name}' received stop signal: {data_packet}")

                        from sage.kernel.api.operator.join_operator import JoinOperator
                        from sage.kernel.api.operator.sink_operator import SinkOperator

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
                            input_index = getattr(data_packet, "input_index", None)
                            self.operator.handle_stop_signal(
                                stop_signal_name=data_packet.source,
                                input_index=input_index,
                            )
                            continue

                        # 停止当前task的worker loop
                        from sage.kernel.api.operator.filter_operator import (
                            FilterOperator,
                        )
                        from sage.kernel.api.operator.keyby_operator import (
                            KeyByOperator,
                        )
                        from sage.kernel.api.operator.map_operator import MapOperator

                        if isinstance(self.operator, (KeyByOperator, MapOperator, FilterOperator)):
                            self.logger.info(
                                f"Intermediate operator {self.name} received stop signal, draining remaining data first"
                            )
                            drained = self._drain_and_process_remaining(data_packet)
                            self.logger.info(
                                f"Intermediate operator {self.name} drained {drained} packets before forwarding stop signal"
                            )
                            self.router.send_stop_signal(data_packet)
                            try:
                                stop_packet = Packet(payload=data_packet)
                                self.operator.receive_packet(stop_packet)
                            except Exception as e:
                                self.logger.error(
                                    f"Error processing StopSignal in {self.name}: {e}"
                                )
                            self.ctx.send_stop_signal_back(self.name)
                            self.ctx.set_stop_signal()
                            break
                        else:
                            self.router.send_stop_signal(data_packet)
                            should_stop_pipeline = self.ctx.handle_stop_signal(data_packet)
                            if should_stop_pipeline:
                                self.ctx.set_stop_signal()
                                break

                        continue

                    # 记录包处理开始（如果启用监控）
                    packet_id = None
                    if self._enable_monitoring and self.metrics_collector:
                        packet_id = self.metrics_collector.record_packet_start(
                            packet_id=getattr(data_packet, "packet_id", None),
                            packet_size=getattr(data_packet, "size", 0),
                        )

                    # 处理数据包
                    try:
                        self.operator.receive_packet(data_packet)

                        # 记录包处理成功
                        if self._enable_monitoring and self.metrics_collector and packet_id:
                            self.metrics_collector.record_packet_end(
                                packet_id=packet_id,
                                success=True,
                            )
                        self._processed_count += 1

                    except Exception as process_error:
                        # 记录包处理失败
                        if self._enable_monitoring and self.metrics_collector and packet_id:
                            self.metrics_collector.record_packet_end(
                                packet_id=packet_id,
                                success=False,
                                error_type=type(process_error).__name__,
                            )
                        self._error_count += 1
                        raise

            except Exception as e:
                if fault_handler:
                    try:
                        current_state = self.get_state()
                        saved = fault_handler.save_checkpoint(
                            task_id=self.name,
                            state=current_state,
                            force=True,  # 强制保存，忽略时间间隔
                        )
                        if saved:
                            self.logger.info(
                                f"💾 Checkpoint saved on exception for task {self.name} "
                                f"(processed={self._processed_count}, errors={self._error_count})"
                            )
                    except Exception as checkpoint_error:
                        self.logger.warning(
                            f"Failed to save checkpoint on exception: {checkpoint_error}"
                        )
                # ✅ 捕获异常并使用容错处理器
                self.logger.error(f"Critical error in node '{self.name}': {str(e)}", exc_info=True)
                self._error_count += 1

                # 通知 dispatcher 处理失败
                if fault_handler:
                    handled = fault_handler.handle_failure(self.name, e)
                    if handled:
                        self.logger.info(
                            f"Task {self.name} failure was handled by fault tolerance, "
                            f"task will be restarted"
                        )
                        # 任务将被重启，退出当前 worker loop
                        break
                    else:
                        self.logger.error(
                            f"Task {self.name} failure could not be handled, stopping..."
                        )
                        break
                else:
                    # 没有 dispatcher 或容错处理器，直接停止
                    self.logger.error(
                        f"No dispatcher available for fault handling, task {self.name} stopping"
                    )
                    break

        self.is_running = False
        self.logger.info(f"Task {self.name} worker loop exited")

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

            # 停止监控组件
            if self._enable_monitoring:
                if self.metrics_reporter:
                    self.metrics_reporter.stop_reporting()
                if self.resource_monitor:
                    self.resource_monitor.stop_monitoring()
                self.logger.debug(f"Stopped monitoring for task {self.name}")

            # # 清理算子资源
            # if hasattr(self.operator, 'cleanup'):
            #     self.operator.cleanup()
            # 这些内容应该会自己清理掉
            # # 清理路由器
            # if hasattr(self.router, 'cleanup'):
            #     self.router.cleanup()

            # 清理输入队列描述符
            if self.input_qd:
                if hasattr(self.input_qd, "cleanup"):
                    self.input_qd.cleanup()  # type: ignore
                elif hasattr(self.input_qd, "close"):
                    self.input_qd.close()  # type: ignore

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
            self.logger.warning(f"Sink task {self.name} timed out while draining in-flight data")
        else:
            self.logger.info(
                f"Sink task {self.name} drained {drained} in-flight packets before shutdown"
            )

        # 完成最终的关闭逻辑
        try:
            if hasattr(self.operator, "handle_stop_signal"):
                self.operator.handle_stop_signal()  # type: ignore
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

    def _drain_and_process_remaining(self, stop_signal: "StopSignal") -> int:
        """Drain and process remaining packets before forwarding stop signal."""
        if not self.input_qd:
            return 0
        drained_packets = 0
        timeout = 5.0
        quiet_period = 0.5
        poll_interval = 0.1
        start_time = time.time()
        last_packet_time = start_time
        self.logger.debug(f"Intermediate task {self.name} draining remaining packets")
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.logger.warning(f"Intermediate task {self.name} timed out while draining")
                break
            try:
                packet = self.input_qd.get(timeout=poll_interval)
            except QUEUE_EMPTY_EXCEPTIONS:
                if time.time() - last_packet_time >= quiet_period:
                    break
                continue
            if isinstance(packet, StopSignal):
                continue
            try:
                self.operator.receive_packet(packet)
                drained_packets += 1
                last_packet_time = time.time()
            except Exception as e:
                self.logger.error(f"Failed to process drained packet in {self.name}: {e}")
        return drained_packets

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

    # === Performance Monitoring API ===

    def get_current_metrics(self) -> TaskPerformanceMetrics | None:
        """
        获取当前性能指标

        Returns:
            TaskPerformanceMetrics 实例，如果监控未启用则返回 None
        """
        if not self._enable_monitoring or not self.metrics_collector:
            return None

        metrics = self.metrics_collector.get_real_time_metrics()

        # 添加资源监控数据
        if self.resource_monitor:
            cpu, memory = self.resource_monitor.get_current_usage()
            metrics.cpu_usage_percent = cpu
            metrics.memory_usage_mb = memory

        # 添加队列深度
        if self.input_qd:
            try:
                queue_instance = self.input_qd.queue_instance
                if queue_instance and hasattr(queue_instance, "qsize"):
                    metrics.input_queue_depth = queue_instance.qsize()
            except Exception:
                pass

        return metrics

    def reset_metrics(self) -> None:
        """重置性能指标"""
        if self.metrics_collector:
            self.metrics_collector.reset_metrics()

    def export_metrics(self, format: str = "json") -> str | None:
        """
        导出性能指标

        Args:
            format: 导出格式 ("json", "prometheus", "csv", "human")

        Returns:
            格式化的指标字符串，如果监控未启用则返回 None
        """
        if not self._enable_monitoring or not self.metrics_reporter:
            return None

        return self.metrics_reporter.generate_report(format=format)
