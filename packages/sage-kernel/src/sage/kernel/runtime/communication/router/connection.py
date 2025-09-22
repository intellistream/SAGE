from typing import Union, TYPE_CHECKING
from dataclasses import dataclass
import time

if TYPE_CHECKING:
    from sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor

@dataclass
class Connection:
    """
    用于表示节点间的连接，包含队列描述符和路由信息
    """
    def __init__(self,
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 queue_descriptor: 'BaseQueueDescriptor',
                 target_input_index: int):
        
        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name
        self.queue_descriptor: 'BaseQueueDescriptor' = queue_descriptor
        self.target_input_index: int = target_input_index
        
        # 负载状态跟踪（保留用于监控）
        self._load_history = []  # 存储最近的负载历史
        self._last_load_check = time.time()
        self._load_trend = 0.0  # 负载趋势：正数表示增加，负数表示减少
        self._max_history_size = 10  # 保存最近10次的负载记录
    
    def get_buffer_load(self) -> float:
        """
        获取目标缓冲区的负载率 (0.0-1.0)
        """
        try:
            # 通过队列描述符获取队列
            target_queue = self.queue_descriptor.get_queue()
            
            if hasattr(target_queue, 'qsize') and hasattr(target_queue, 'maxsize'):
                # 标准队列类型
                current_size = target_queue.qsize()
                max_size = target_queue.maxsize
                if max_size > 0:
                    load_ratio = current_size / max_size
                else:
                    load_ratio = 0.0
            elif hasattr(target_queue, 'get_buffer_stats'):
                # 如果是SageQueue类型，使用统计信息
                stats = target_queue.get_buffer_stats()
                load_ratio = stats.get('utilization', 0.0)
            else:
                # 其他类型，暂时返回0
                load_ratio = 0.0
            
            return load_ratio
            
        except Exception:
            return 0.0
    
    # def should_increase_delay(self) -> bool:
    #     """
    #     判断是否应该增加delay
    #     当前负载 > 60% 且比上次记录的高
    #     """
    #     current_load = self.get_buffer_load()
    #     return current_load > 0.6
    
    # def should_decrease_delay(self) -> bool:
    #     """
    #     判断是否应该减少delay
    #     当前负载 < 30% 且比上次记录的低
    #     """
    #     current_load = self.get_buffer_load()
    #     return current_load < 0.3
    
    # def _update_load_history(self, current_load: float):
    #     """更新负载历史和计算趋势"""
    #     current_time = time.time()
        
    #     # 添加到历史记录
    #     self._load_history.append((current_time, current_load))
        
    #     # 保持历史记录大小
    #     if len(self._load_history) > self._max_history_size:
    #         self._load_history.pop(0)
        
    #     # 计算负载趋势（最近3个点的斜率）
    #     if len(self._load_history) >= 3:
    #         recent_points = self._load_history[-3:]
    #         # 计算简单的线性趋势
    #         time_diff = recent_points[-1][0] - recent_points[0][0]
    #         load_diff = recent_points[-1][1] - recent_points[0][1]
            
    #         if time_diff > 0:
    #             self._load_trend = load_diff / time_diff
    #         else:
    #             self._load_trend = 0.0
        
    #     self._last_load_check = current_time
    
    def get_load_trend(self) -> float:
        """
        获取负载趋势
        返回值：正数表示负载增加，负数表示负载减少，0表示稳定
        """
        return self._load_trend
    
    def is_load_increasing(self) -> bool:
        """负载是否在增加"""
        return self._load_trend > 0.05  # 5%/秒的增长视为增加
    
    def is_load_decreasing(self) -> bool:
        """负载是否在减少"""
        return self._load_trend < -0.05  # 5%/秒的减少视为减少