from core.operator.base_operator import BaseOperator
from core.function.source_function import StopSignal
from utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING, Iterator, Optional
from runtime.router.packet import Packet

if TYPE_CHECKING:
    from runtime.task.base_task import BaseTask

class BatchOperator(BaseOperator):
    """
    简化的批处理算子
    
    与SourceOperator类似，但具有以下特点：
    1. 自己管理数据迭代
    2. 当迭代返回None时自动发送停止信号
    3. 支持进度跟踪（可选）
    """

    def __init__(self, *args, **kwargs):
        # 提取批处理相关的配置参数
        self._progress_log_interval = kwargs.pop('progress_log_interval', 100)
        self._current_count = 0
        self._last_logged_count = 0
        
        super().__init__(*args, **kwargs)
        
        # 初始化数据迭代器
        self._data_iterator: Optional[Iterator] = None
        self._total_count: Optional[int] = None
        self._initialize_iterator()

    def _initialize_iterator(self):
        """初始化数据迭代器"""
        try:
            # 获取数据迭代器
            if hasattr(self.function, 'get_data_iterator'):
                self._data_iterator = self.function.get_data_iterator()
            elif hasattr(self.function, '__iter__'):
                self._data_iterator = iter(self.function)
            else:
                # 兼容现有的BatchFunction
                if hasattr(self.function, 'get_data_source'):
                    self._data_iterator = self.function.get_data_source()
                else:
                    raise ValueError(f"Function {self.function} does not provide data iterator")
            
            # 获取总数量（如果可用）
            if hasattr(self.function, 'get_total_count'):
                try:
                    self._total_count = self.function.get_total_count()
                    self.logger.info(f"Batch Operator {self.name} initialized with {self._total_count} total items")
                except:
                    self._total_count = None
                    self.logger.info(f"Batch Operator {self.name} initialized (unknown total count)")
            else:
                self.logger.info(f"Batch Operator {self.name} initialized (unknown total count)")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize iterator for {self.name}: {e}")
            self._data_iterator = iter([])  # 空迭代器

    def receive_packet(self, packet: 'Packet'):
        """批处理算子通常作为源算子，不接收上游数据包"""
        self.logger.warning(f"BatchOperator {self.name} received unexpected packet: {packet}")
        self.process_packet(packet)

    def process_packet(self, packet: 'Packet' = None):
        """
        处理数据包 - 简化版本
        
        核心逻辑：
        1. 从迭代器获取下一个数据
        2. 如果有数据，发送数据包
        3. 如果没有数据（StopIteration），发送停止信号
        """
        try:
            if self._data_iterator is None:
                self.logger.warning(f"BatchOperator {self.name} has no data iterator")
                self._send_stop_signal()
                return

            # 尝试获取下一个数据项
            try:
                data = next(self._data_iterator)
                
                if data is not None:
                    # 发送数据包
                    self.router.send(Packet(data))
                    self._current_count += 1
                    
                    # 记录进度
                    self._log_progress_if_needed()
                    
                    self.logger.debug(f"Batch Operator {self.name} sent data: {data}")
                else:
                    # 数据为None，继续迭代（允许数据源中有None值）
                    self.logger.debug(f"Batch Operator {self.name} got None data, continuing...")
                    
            except StopIteration:
                # 迭代结束，发送停止信号
                self.logger.info(f"Batch Operator {self.name} completed processing {self._current_count} items")
                self._send_stop_signal()
                
        except Exception as e:
            self.logger.error(f"Error in BatchOperator {self.name}.process(): {e}", exc_info=True)
            self._send_stop_signal()

    def _send_stop_signal(self):
        """发送停止信号"""
        stop_signal = StopSignal(self.name)
        self.logger.info(f"Batch Operator {self.name} sending stop signal: {stop_signal}")
        self.router.send_stop_signal(stop_signal)
        
        if self.task:
            self.task.stop()

    def _log_progress_if_needed(self):
        """根据配置的间隔记录进度日志"""
        if (self._current_count - self._last_logged_count >= self._progress_log_interval or 
            self._current_count == self._total_count):
            
            if self._total_count:
                completion_rate = self._current_count / self._total_count
                self.logger.info(
                    f"Batch Operator {self.name} progress: "
                    f"{self._current_count}/{self._total_count} ({completion_rate:.1%}) completed"
                )
            else:
                self.logger.info(f"Batch Operator {self.name} processed {self._current_count} items")
                
            self._last_logged_count = self._current_count

    def get_batch_info(self) -> Dict[str, Any]:
        """获取批处理信息"""
        completion_rate = 0.0
        if self._total_count and self._total_count > 0:
            completion_rate = self._current_count / self._total_count
        
        return {
            "name": self.name,
            "current_count": self._current_count,
            "total_count": self._total_count or "unknown",
            "completion_rate": completion_rate,
            "progress_percentage": f"{completion_rate:.1%}" if self._total_count else "unknown"
        }

    def reset_batch(self):
        """重置批处理状态"""
        self._current_count = 0
        self._last_logged_count = 0
        self._initialize_iterator()
        self.logger.info(f"Batch Operator {self.name} reset successfully")


class BatchSourceOperator(BatchOperator):
    """
    批处理源算子
    
    BatchSourceOperator是BatchOperator的别名，
    用于更清楚地表示这是一个源算子
    """
    pass
