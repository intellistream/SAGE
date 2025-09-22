from collections import deque
from typing import TYPE_CHECKING, Any, Deque, Dict, Tuple, Union

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.communication.packet import Packet
from sage.kernel.runtime.communication.router.packet import StopSignal
from sage.core.operator.base_operator import BaseOperator

if TYPE_CHECKING:
    from sage.core.communication.metronome import Metronome


class BatchOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 检查function是否启用metronome
        self._metronome = None
        if hasattr(self.function, "use_metronome") and self.function.use_metronome:
            if (
                hasattr(self.function, "metronome")
                and self.function.metronome is not None
            ):
                self._metronome = self.function.metronome
                self.logger.info(
                    f"BatchOperator {self.name} using metronome: {self._metronome.name}"
                )
            else:
                self.logger.warning(
                    f"BatchOperator {self.name} use_metronome=True but no metronome provided"
                )

    def receive_packet(self, packet: "Packet"):
        self.process_packet(packet)

    def process_packet(self, packet: "Packet" = None):
        try:
            # 如果启用了metronome，在执行前等待锁释放
            if self._metronome is not None:
                self.logger.debug(
                    f"BatchOperator {self.name} waiting for metronome release"
                )
                if not self._metronome.wait_for_release(timeout=30.0):  # 30秒超时
                    self.logger.error(
                        f"BatchOperator {self.name} metronome wait timeout"
                    )
                    self.ctx.set_stop_signal()
                    return
                self.logger.debug(
                    f"BatchOperator {self.name} got metronome release, executing function"
                )

            result = self.function.execute()
            self.logger.debug(
                f"Operator {self.name} processed data with result: {result}"
            )

            # 如果结果是None，表示批处理完成，发送停止信号
            if result is None:
                self.logger.info(
                    f"Batch Operator {self.name} completed, sending stop signal"
                )

                # 如果使用metronome，强制释放以避免死锁
                if self._metronome is not None:
                    self._metronome.force_release()

                # 源节点完成时，先通知JobManager该节点完成
                self.ctx.send_stop_signal_back(self.name)

                # 然后向下游发送停止信号
                stop_signal = StopSignal(self.name)
                self.router.send_stop_signal(stop_signal)

                # 通过ctx停止task
                self.ctx.set_stop_signal()
                return

            # 发送正常数据包
            if result is not None:
                success = self.router.send(Packet(result))
                # If sending failed (e.g., queue is closed), stop the task
                if not success:
                    self.logger.warning(
                        f"Batch Operator {self.name} failed to send packet, stopping task"
                    )
                    self.ctx.set_stop_signal()
                    return

                # 如果启用了metronome，发送数据后立即锁定，等待Sink处理完成
                if self._metronome is not None:
                    self.logger.debug(
                        f"BatchOperator {self.name} locking metronome after sending data"
                    )
                    self._metronome.lock_after_send()

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
