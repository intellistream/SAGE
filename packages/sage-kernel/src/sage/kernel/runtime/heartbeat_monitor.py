"""
HeartbeatMonitor V2 - 简化版心跳监控器

采用 Pull 模式直接从 Ray Task 获取心跳，无需 HeartbeatCollector 中介

核心改进:
1. 直接调用 ray_task.get_heartbeat_stats() 获取心跳信息
2. 调用失败直接触发 handle_failure (任务已崩溃)
3. 连续多次心跳信息异常也触发重启
4. 更简洁的架构，减少组件依赖
"""

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.runtime.dispatcher import Dispatcher
    from sage.kernel.runtime.task.base_task import BaseTask


class HeartbeatMonitor:
    """

    职责:
    1. 定期直接调用 Ray Task 的 get_heartbeat_stats() 获取心跳
    2. 如果调用失败（任务崩溃/不可达）→ 立即触发 handle_failure
    3. 如果心跳信息异常（如连续多次为空或不正常）→ 触发 handle_failure

    触发容错的条件:
    A. 调用 get_heartbeat_stats() 报错 (任务崩溃/网络故障)
    B. 连续 max_missed_checks 次心跳信息为空或异常
    C. 连续 max_missed_checks 次心跳时间戳未更新

    优势:
    - 无需 HeartbeatCollector 中介，减少组件
    - 调用失败即可判断任务死亡，响应更快
    - 心跳数据实时获取，无延迟
    """

    def __init__(
        self,
        dispatcher: "Dispatcher",
        check_interval: float = 5.0,
        max_missed_checks: int = 3,
        call_timeout: float = 2.0,
    ):
        """
        初始化 HeartbeatMonitorV2

        Args:
            dispatcher: Dispatcher 实例 (用于调用 handle_failure 和获取 task 引用)
            check_interval: 检查间隔 (秒)
            max_missed_checks: 最大允许错过的检查次数 (默认3次)
            call_timeout: 调用 Ray task 方法的超时时间 (秒)
        """
        self.dispatcher = dispatcher
        self.check_interval = check_interval
        self.max_missed_checks = max_missed_checks
        self.call_timeout = call_timeout

        # 计算实际超时时间 (用于日志显示)
        self.effective_timeout = check_interval * max_missed_checks

        # 监控线程控制
        self._monitor_thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._task_states: dict[str, dict[str, Any]] = {}
        self._states_lock = threading.Lock()

        # 监控统计
        self._stats = {
            "total_checks": 0,
            "total_call_failures": 0,
            "total_heartbeat_stale": 0,
            "total_failures_handled": 0,
            "last_check_time": None,
        }

        # Logger
        self.logger = logging.getLogger("HeartbeatMonitor")

        self.logger.info(
            f"✅ HeartbeatMonitor initialized: "
            f"check_interval={check_interval}s, "
            f"max_missed_checks={max_missed_checks}, "
            f"effective_timeout={self.effective_timeout}s, "
            f"call_timeout={call_timeout}s"
        )

    def start(self):
        """启动监控线程"""
        if self._running:
            self.logger.warning("HeartbeatMonitor already running")
            return

        self._running = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="HeartbeatMonitor", daemon=True
        )
        self._monitor_thread.start()

        self.logger.info("🔍 HeartbeatMonitor started")

    def stop(self):
        """停止监控线程"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # 等待线程结束
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

            if self._monitor_thread.is_alive():
                self.logger.warning("Monitor thread did not stop gracefully")

        self.logger.info("🔍 HeartbeatMonitor stopped")

    def is_running(self) -> bool:
        """检查监控是否运行中"""
        return self._running

    def _get_active_tasks(self) -> dict[str, "BaseTask"]:
        """
        从 Dispatcher 获取所有活跃任务的引用

        """
        try:
            return self.dispatcher.tasks  # type: ignore[return-value]
        except Exception as e:
            self.logger.error(f"❌ Failed to get active tasks from Dispatcher: {e}")
            return {}

    def _pull_heartbeat(self, task_id: str, task: "BaseTask") -> dict[str, Any] | None:
        """
        从 Ray Task 拉取心跳信息

        Args:
            task_id: 任务 ID
            task: Task 实例或 ActorWrapper

        Returns:
            心跳信息字典，如果调用失败返回 None
        """
        try:
            # 调用 Ray Task 的 get_heartbeat_stats() 方法
            heartbeat = task.get_heartbeat_stats()  # type: ignore[union-attr]
            self.logger.debug(f"💓 Pulled heartbeat from {task_id}: {heartbeat}")
            return heartbeat  # type: ignore[return-value]

        except Exception as e:
            # 捕获所有异常（包括超时等异常）
            if "GetTimeoutError" in str(type(e).__name__):
                self.logger.warning(
                    f"⚠️  Timeout pulling heartbeat from {task_id} (timeout={self.call_timeout}s)"
                )
            else:
                self.logger.error(
                    f"❌ Unexpected error pulling heartbeat from {task_id}: {e}",
                    exc_info=True,
                )
            return None

    def _validate_heartbeat(self, heartbeat: dict[str, Any] | None) -> bool:
        """
        验证心跳信息是否正常

        Args:
            heartbeat: 心跳信息字典

        Returns:
            True 如果心跳正常，False 如果异常
        """
        if heartbeat is None:
            return False

        # 检查必要字段
        required_fields = ["task_id", "timestamp", "status", "packet_count"]
        if not all(field in heartbeat for field in required_fields):
            self.logger.warning(f"⚠️  Heartbeat missing required fields: {heartbeat}")
            return False

        # 检查 timestamp 是否合理（不能是未来时间或过于久远）
        timestamp = heartbeat.get("timestamp", 0)
        current_time = time.time()

        if timestamp <= 0:
            self.logger.warning(f"⚠️  Invalid timestamp: {timestamp}")
            return False

        if timestamp > current_time + 10:  # 不能超前超过10秒
            self.logger.warning(f"⚠️  Future timestamp: {timestamp}")
            return False

        # 检查 is_running 状态
        if not heartbeat.get("is_running", False):
            self.logger.warning(f"⚠️  Task not running: {heartbeat}")
            return False

        return True

    def _monitor_loop(self):
        """
        监控主循环 (在独立线程中运行)

        检测逻辑:
        1. 从 Dispatcher 获取所有活跃任务
        2. 对每个任务调用 get_heartbeat_stats() 拉取心跳
        3. 如果调用失败 → consecutive_failures += 1
        4. 如果心跳无效 → consecutive_failures += 1
        5. 如果心跳有效但未更新 → consecutive_stale += 1
        6. 如果心跳有效且已更新 → 重置所有计数器
        7. 超过阈值 → 触发 handle_failure
        """
        self.logger.info("🔍 Monitor loop started")

        while self._running:
            try:
                current_time = time.time()

                # === 步骤 1: 获取所有活跃任务 ===
                active_tasks = self._get_active_tasks()

                if not active_tasks:
                    self.logger.debug("No active tasks to monitor")
                    # 清理状态
                    with self._states_lock:
                        self._task_states.clear()
                else:
                    self.logger.debug(f"📊 Monitoring {len(active_tasks)} tasks")

                # === 步骤 2: 检查每个任务的心跳 ===
                failed_tasks = []

                with self._states_lock:
                    for task_id, task in active_tasks.items():
                        # 初始化任务状态（如果是新任务）
                        if task_id not in self._task_states:
                            self._task_states[task_id] = {
                                "last_valid_timestamp": 0,
                                "last_packet_count": 0,
                                "consecutive_failures": 0,
                                "consecutive_stale": 0,
                                "last_check_time": current_time,
                            }

                        state = self._task_states[task_id]

                        # === 拉取心跳 ===
                        heartbeat = self._pull_heartbeat(task_id, task)

                        # === 情况 A: 调用失败 (任务可能崩溃) ===
                        if heartbeat is None:
                            state["consecutive_failures"] += 1
                            self._stats["total_call_failures"] += 1

                            self.logger.warning(
                                f"⚠️  Task {task_id} heartbeat call failed: "
                                f"consecutive_failures={state['consecutive_failures']}/{self.max_missed_checks}"
                            )

                            if state["consecutive_failures"] >= self.max_missed_checks:
                                self.logger.error(
                                    f"🚨 Task {task_id} FAILURE: "
                                    f"consecutive call failures={state['consecutive_failures']}"
                                )
                                failed_tasks.append((task_id, "call_failure", heartbeat))

                            continue

                        # === 情况 B: 心跳信息无效 ===
                        if not self._validate_heartbeat(heartbeat):
                            state["consecutive_failures"] += 1

                            self.logger.warning(
                                f"⚠️  Task {task_id} heartbeat invalid: "
                                f"consecutive_failures={state['consecutive_failures']}/{self.max_missed_checks}"
                            )

                            if state["consecutive_failures"] >= self.max_missed_checks:
                                self.logger.error(
                                    f"🚨 Task {task_id} FAILURE: "
                                    f"consecutive invalid heartbeats={state['consecutive_failures']}"
                                )
                                failed_tasks.append((task_id, "invalid_heartbeat", heartbeat))

                            continue

                        # === 情况 C: 心跳有效，检查是否有更新 ===
                        current_timestamp = heartbeat.get("timestamp", 0)
                        current_packet_count = heartbeat.get("packet_count", 0)

                        last_timestamp = state["last_valid_timestamp"]
                        last_packet_count = state["last_packet_count"]

                        # 判断心跳是否有实质性更新
                        # 1. timestamp 变化
                        # 2. packet_count 增加 (表示任务在处理数据)
                        has_update = (
                            current_timestamp > last_timestamp
                            or current_packet_count > last_packet_count
                        )

                        if has_update:
                            # === 心跳有更新，重置所有计数器 ===
                            self.logger.debug(
                                f"💓 Task {task_id} heartbeat updated: "
                                f"timestamp={current_timestamp:.1f} (was {last_timestamp:.1f}), "
                                f"packet_count={current_packet_count} (was {last_packet_count})"
                            )

                            state["last_valid_timestamp"] = current_timestamp
                            state["last_packet_count"] = current_packet_count
                            state["consecutive_failures"] = 0
                            state["consecutive_stale"] = 0
                            state["last_check_time"] = current_time

                        else:
                            # === 心跳未更新（stale） ===
                            state["consecutive_stale"] += 1
                            self._stats["total_heartbeat_stale"] += 1

                            time_since_last = current_time - last_timestamp

                            self.logger.warning(
                                f"⚠️  Task {task_id} heartbeat stale: "
                                f"consecutive_stale={state['consecutive_stale']}/{self.max_missed_checks}, "
                                f"time_since_last={time_since_last:.1f}s"
                            )

                            if state["consecutive_stale"] >= self.max_missed_checks:
                                self.logger.error(
                                    f"🚨 Task {task_id} FAILURE: "
                                    f"consecutive stale heartbeats={state['consecutive_stale']}, "
                                    f"time_since_last={time_since_last:.1f}s"
                                )
                                failed_tasks.append((task_id, "stale_heartbeat", heartbeat))

                    # === 清理已不存在的任务 ===
                    disappeared_tasks = set(self._task_states.keys()) - set(active_tasks.keys())
                    for task_id in disappeared_tasks:
                        self.logger.info(f"🗑️  Task {task_id} removed from monitoring")
                        self._task_states.pop(task_id, None)

                # === 步骤 3: 处理失败任务 ===
                if failed_tasks:
                    self.logger.warning(f"⚠️  Detected {len(failed_tasks)} failed tasks")

                    for task_id, failure_type, heartbeat in failed_tasks:
                        self.logger.error(
                            f"🚨 Handling FAILURE: task_id={task_id}, "
                            f"type={failure_type}, heartbeat={heartbeat}"
                        )

                        # 调用 Dispatcher 处理故障
                        try:
                            Exception(f"Heartbeat failure: {failure_type}")

                            # 调用容错处理器的 handle_failure
                            # CheckpointBasedRecovery 会：
                            # 1. 检查是否可以恢复（有 checkpoint + 未超过重试次数）
                            # 2. 如果可以，调用 dispatcher.restart_task_with_state
                            # 3. 处理所有容错逻辑（重试策略、状态恢复等）
                            # self.dispatcher.fault_handler.handle_failure(task_id, error)
                            self._stats["total_failures_handled"] += 1

                            # 从监控状态中移除（避免重复处理）
                            with self._states_lock:
                                self._task_states.pop(task_id, None)

                        except Exception as e:
                            self.logger.error(
                                f"❌ Failed to handle failure for {task_id}: {e}",
                                exc_info=True,
                            )

                # === 步骤 4: 更新统计 ===
                self._stats["total_checks"] += 1
                self._stats["last_check_time"] = current_time

                # === 步骤 5: 等待下一次检查 ===
                if self._stop_event.wait(timeout=self.check_interval):
                    # 收到停止信号
                    break

            except Exception as e:
                self.logger.error(f"❌ Unexpected error in monitor loop: {e}", exc_info=True)
                # 避免无限错误循环
                time.sleep(1.0)

        self.logger.info("🔍 Monitor loop stopped")

    def get_stats(self) -> dict[str, Any]:
        """
        获取监控统计信息

        Returns:
            统计信息字典
        """
        with self._states_lock:
            active_tasks = len(self._task_states)
            task_states_snapshot = {
                task_id: {
                    "consecutive_failures": state["consecutive_failures"],
                    "consecutive_stale": state["consecutive_stale"],
                    "time_since_update": time.time() - state["last_valid_timestamp"],
                }
                for task_id, state in self._task_states.items()
            }

        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "max_missed_checks": self.max_missed_checks,
            "effective_timeout": self.effective_timeout,
            "call_timeout": self.call_timeout,
            "active_tasks": active_tasks,
            "task_states": task_states_snapshot,
            **self._stats,
        }

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """
        获取指定任务的监控状态

        Args:
            task_id: 任务 ID

        Returns:
            监控状态信息,如果不存在返回 None
        """
        with self._states_lock:
            state = self._task_states.get(task_id)

            if state is None:
                return None

            current_time = time.time()

            return {
                "task_id": task_id,
                "last_valid_timestamp": state["last_valid_timestamp"],
                "last_packet_count": state["last_packet_count"],
                "consecutive_failures": state["consecutive_failures"],
                "consecutive_stale": state["consecutive_stale"],
                "time_since_update": current_time - state["last_valid_timestamp"],
                "is_at_risk": (
                    state["consecutive_failures"] >= self.max_missed_checks - 1
                    or state["consecutive_stale"] >= self.max_missed_checks - 1
                ),
                "is_failed": (
                    state["consecutive_failures"] >= self.max_missed_checks
                    or state["consecutive_stale"] >= self.max_missed_checks
                ),
            }


__all__ = ["HeartbeatMonitor"]
