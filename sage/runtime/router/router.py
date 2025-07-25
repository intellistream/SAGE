# sage.runtime/base_router.py
import traceback

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from sage.core.function.source_function import StopSignal
from sage.runtime.router.packet import Packet
from sage.utils.mmap_queue.sage_queue import SageQueue

if TYPE_CHECKING:
    from sage.runtime.router.connection import Connection
    from sage.runtime.runtime_context import RuntimeContext

class BaseRouter(ABC):
    """
    路由器基类，负责管理下游连接和数据包路由
    子类只需要实现具体的数据发送逻辑
    """
    
    def __init__(self, ctx: 'RuntimeContext'):
        self.name = ctx.name
        self.ctx = ctx
        
        # 下游连接管理
        self.downstream_groups: Dict[int, Dict[int, 'Connection']] = {}
        self.downstream_group_roundrobin: Dict[int, int] = {}
        self.downstream_max_load: float = 0.0  # 最大延迟，单位为秒
        # Logger
        self.logger = ctx.logger
        self.logger.debug(f"Initialized {self.__class__.__name__} for {self.name}")
    
    def add_connection(self, connection: 'Connection') -> None:
        """
        添加下游连接
        
        Args:
            connection: Connection对象，包含所有连接信息
        """
        broadcast_index = connection.broadcast_index
        parallel_index = connection.parallel_index
        if connection.target_type == "local":
            self.logger.debug(f"Adding local connection to {connection.target_name}")
            connection.target_buffer = SageQueue(connection.target_name)
            self.logger.debug(f"connection.target_buffer.get_stats(): {connection.target_buffer.get_stats()}")
        else:  # 直接对ray节点通信
            connection.target_buffer = connection.target_handle.get_input_buffer.remote()
        # Debug log
        self.logger.debug(
            f"Adding connection: broadcast_index={broadcast_index}, parallel_index={parallel_index}, target={connection.target_name}"
        )
        
        # 初始化广播组（如果不存在）
        if broadcast_index not in self.downstream_groups:
            self.downstream_groups[broadcast_index] = {}
            self.downstream_group_roundrobin[broadcast_index] = 0
        
        # 保存完整的Connection对象
        self.downstream_groups[broadcast_index][parallel_index] = connection
        
        self.logger.info(f"Added connection to {connection.target_name}")

    
    def get_connections_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        info = {}
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            info[f"broadcast_group_{broadcast_index}"] = {
                "count": len(parallel_targets),
                "roundrobin_position": self.downstream_group_roundrobin[broadcast_index],
                "targets": [
                    {
                        "parallel_index": parallel_index,
                        "target_name": connection.target_name
                    }
                    for parallel_index, connection in parallel_targets.items()
                ]
            }
        return info

    

    def send_stop_signal(self, stop_signal: 'StopSignal') -> None:
        """
        发送停止信号给所有下游连接
        
        Args:
            stop_signal: 停止信号对象
        """
        self.logger.info(f"Sending stop signal: {stop_signal}")
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                try:
                    connection.target_buffer.put_nowait(stop_signal)
                    self.logger.debug(f"Sent stop signal to {connection.target_name}")
                except Exception as e:
                    self.logger.error(f"Failed to send stop signal to {connection.target_name}: {e}")

    def send(self, packet: 'Packet') -> bool:
        """
        发送数据包，根据其分区信息选择路由策略
        
        Args:
            packet: 要发送的packet，可能包含分区信息
            
        Returns:
            bool: 是否成功发送
        """
        if not self.downstream_groups:
            self.logger.warning(f"No downstream connections available for {self.name}")
            return False
        
        try:
            self.downstream_max_load = 0.0
            self.logger.debug(f"Emitting packet: {packet}")
            
            # 根据packet的分区信息选择路由策略
            if packet.is_keyed():
                self._route_packet(packet)
            else:
                self._route_round_robin_packet(packet)
            self._adjust_delay_based_on_load()
        except Exception as e:
            self.logger.error(f"Error emitting packet: {e}")
            return False
    
    def _route_packet(self, packet: 'Packet') -> bool:
        """使用分区信息进行路由"""
        strategy = packet.partition_strategy
        
        if strategy == "hash":
            return self._route_hashed_packet(packet)
        elif strategy == "broadcast":
            return self._route_broadcast_packet(packet)
        else:
            return self._route_round_robin_packet(packet)
    
    def _route_round_robin_packet(self, packet: 'Packet') -> bool:
        """使用轮询策略进行路由"""
        success = True
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if not parallel_targets:  # 空的并行目标组
                continue
                
            # 获取当前轮询位置
            current_round_robin = self.downstream_group_roundrobin[broadcast_index]
            parallel_indices = list(parallel_targets.keys())
            target_parallel_index = parallel_indices[current_round_robin % len(parallel_indices)]
            
            # 更新轮询位置
            self.downstream_group_roundrobin[broadcast_index] = (current_round_robin + 1) % len(parallel_indices)
            
            # 发送到选中的连接
            connection = parallel_targets[target_parallel_index]
            if not self._deliver_packet(connection, packet):
                success = False
        
        return success
    
    def _route_broadcast_packet(self, packet: 'Packet') -> bool:
        """使用广播策略进行路由"""
        success = True
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                if not self._deliver_packet(connection, packet):
                    success = False
        
        return success
    
    def _route_hashed_packet(self, packet: 'Packet') -> bool:
        """使用哈希分区策略进行路由"""
        if not packet.partition_key:
            self.logger.warning("Hash routing requested but no partition key provided, falling back to round-robin")
            return self._route_round_robin_packet(packet)
        
        success = True
        partition_key = packet.partition_key
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if not parallel_targets:
                continue
                
            # 基于分区键计算目标索引
            parallel_indices = list(parallel_targets.keys())
            target_index = hash(partition_key) % len(parallel_indices)
            target_parallel_index = parallel_indices[target_index]
            
            connection = parallel_targets[target_parallel_index]
            if not self._deliver_packet(connection, packet):
                success = False
        
        return success
    
    def _deliver_packet(self, connection: 'Connection', packet: 'Packet') -> bool:
        try:
            # 检查下游负载并动态调整delay
            
            self.downstream_max_load = max(self.downstream_max_load, connection.get_buffer_load())
            routed_packet = self._create_routed_packet(connection, packet)
            target_buffer = connection.target_buffer
            target_buffer.put_nowait(routed_packet)
            self.logger.debug(
                f"Sent {'keyed' if packet.is_keyed() else 'unkeyed'} packet "
                f"to {connection.target_name} (strategy: {packet.partition_strategy or 'round-robin'})"
            )
            return True
        except Exception as e:
            """记录发送失败日志"""
            self.logger.error(
                f"Failed to send packet to {connection.target_name}: {e}\n{traceback.format_exc()}"
            )
            return False
    
    def _adjust_delay_based_on_load(self, connection: 'Connection' = None):
        """
        根据当前连接的负载动态调整delay
        
        Args:
            connection: 当前发送的目标连接
        """
        # 旧路径 emit_packet 调用时不会传 connection；此时直接返回
        if connection is None:
            return

        try:
            self.logger.debug(f"Adjusting delay based on downstream load: {self.downstream_max_load:.3f}")
            # 获取当前delay
            current_delay = self.ctx.delay
            self.logger.debug(f"Current delay: {self.ctx.delay* 1000 :.3f}ms")
            # 根据当前连接的负载调整delay
            new_delay = current_delay * (0.5 + self.downstream_max_load)
            if new_delay < 0.001:
                new_delay = 0.001
            self.ctx.delay = new_delay  # 直接把最大限制给去掉
            self.logger.info(f"Adjusted delay to {self.ctx.delay* 1000 :.3f}ms")
                
        except Exception as e:
            self.logger.warning(f"Failed to adjust delay based on load: {e}\n{traceback.format_exc()}")

    def clear_all_connections(self):
        """清空所有连接"""
        self.downstream_groups.clear()
        self.downstream_group_roundrobin.clear()
    
    def _create_routed_packet(self, connection: 'Connection', packet: 'Packet') -> 'Packet':
        """创建路由后的数据包"""
        return Packet(
            payload=packet.payload,
            input_index=connection.target_input_index,
            partition_key=packet.partition_key,
            partition_strategy=packet.partition_strategy,
        )
