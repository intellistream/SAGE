# sage.runtime/base_router.py
import traceback

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from sage.core.function.source_function import StopSignal
from sage.runtime.communication.router.packet import Packet
from sage.utils.queue_adapter import create_queue

# 添加 Ray 相关导入以检测 Actor
try:
    import ray
    from ray.actor import ActorHandle
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    ActorHandle = None

if TYPE_CHECKING:
    from sage.runtime.communication.router.connection import Connection
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
    
    def _is_ray_actor(self, obj) -> bool:
        """检测对象是否为 Ray Actor"""
        if not RAY_AVAILABLE:
            return False
        return isinstance(obj, ActorHandle) or hasattr(obj, 'remote')
    
    def add_connection(self, connection: 'Connection') -> None:
        """
        添加下游连接
        
        Args:
            connection: Connection对象，包含所有连接信息
        """
        broadcast_index = connection.broadcast_index
        parallel_index = connection.parallel_index
        
        try:
            # 检测 target_handle 是否为 Ray Actor
            is_ray_actor = self._is_ray_actor(connection.target_handle)
            
            if is_ray_actor:
                self.logger.info(f"🔗 Router: Getting remote input_buffer from target task '{connection.target_name}' (Ray Actor)")
                connection.target_buffer = connection.target_handle.get_input_buffer.remote()
                self.logger.info(f"✅ Router: Successfully got remote input_buffer from {connection.target_name}")
            else:
                self.logger.info(f"🔗 Router: Getting input_buffer from target task '{connection.target_name}' (Local object)")
                # 对于本地对象，直接获取目标任务的input_buffer
                connection.target_buffer = connection.target_handle.get_input_buffer()
                self.logger.info(f"✅ Router: Successfully got input_buffer from {connection.target_name}")
                
            # Debug log
            self.logger.debug(
                f"Adding connection: broadcast_index={broadcast_index}, parallel_index={parallel_index}, target={connection.target_name}, is_ray_actor={is_ray_actor}"
            )
            
            # 初始化广播组（如果不存在）
            if broadcast_index not in self.downstream_groups:
                self.downstream_groups[broadcast_index] = {}
                self.downstream_group_roundrobin[broadcast_index] = 0
            
            # 保存完整的Connection对象
            self.downstream_groups[broadcast_index][parallel_index] = connection
            
            self.logger.info(f"Added connection to {connection.target_name}")
            self.logger.info(f"Current downstream groups: {list(self.downstream_groups.keys())}")
            
        except Exception as e:
            self.logger.error(f"Failed to add connection to {connection.target_name}: {e}", exc_info=True)
            raise

    
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
        self.logger.debug(f"Router {self.name}: Send called with downstream_groups: {list(self.downstream_groups.keys())}")
        
        if not self.downstream_groups:
            self.logger.warning(f"No downstream connections available for {self.name}")
            self.logger.warning(f"Current downstream_groups state: {self.downstream_groups}")
            return False
        
        try:
            self.downstream_max_load = 0.0
            self.logger.info(f"Router {self.name}: Sending packet: {packet.payload}")
            self.logger.info(f"Router {self.name}: Downstream groups: {list(self.downstream_groups.keys())}")
            self.logger.debug(f"Emitting packet: {packet}")
            
            # 根据packet的分区信息选择路由策略
            if packet.is_keyed():
                self.logger.info(f"Router {self.name}: Using keyed routing")
                result = self._route_packet(packet)
            else:
                self.logger.info(f"Router {self.name}: Using round-robin routing")
                result = self._route_round_robin_packet(packet)
            
            self.logger.info(f"Router {self.name}: Routing result: {result}")
            self._adjust_delay_based_on_load()
            return True
        except Exception as e:
            self.logger.error(f"Error emitting packet: {e}", exc_info=True)
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
            self.logger.info(f"Router {self.name}: Starting packet delivery to {connection.target_name}")
            
            self.downstream_max_load = max(self.downstream_max_load, connection.get_buffer_load())
            routed_packet = self._create_routed_packet(connection, packet)
            self.logger.info(f"Router {self.name}: Created routed packet: {routed_packet}")
            
            target_buffer = connection.target_buffer
            target_handle = connection.target_handle
            self.logger.info(f"Router {self.name}: Target buffer: {target_buffer} (type: {type(target_buffer)})")
            self.logger.info(f"Router {self.name}: Target handle: {target_handle} (type: {type(target_handle)})")
            
            # 检查是否为 Ray Actor
            is_ray_actor = self._is_ray_actor(target_handle)
            self.logger.info(f"Router {self.name}: Is Ray Actor: {is_ray_actor}")
            
            # 检查 target_buffer 是否是 Ray ObjectRef
            is_ray_object_ref = RAY_AVAILABLE and str(type(target_buffer)).find('ray._raylet.ObjectRef') != -1
            self.logger.info(f"Router {self.name}: Is Ray ObjectRef: {is_ray_object_ref}")
            
            if is_ray_actor:
                # 对于 Ray Actor，直接调用 put_packet 方法（不使用 hasattr 检查）
                self.logger.info(f"Router {self.name}: Using Ray Actor put_packet method")
                try:
                    result_future = target_handle.put_packet.remote(routed_packet)
                    # 等待结果以确保调用成功
                    result = ray.get(result_future)
                    self.logger.info(f"Router {self.name}: Ray Actor put_packet result: {result}")
                    if not result:
                        self.logger.error(f"Router {self.name}: put_packet returned False")
                        return False
                except AttributeError as e:
                    self.logger.error(f"Router {self.name}: Ray Actor does not have put_packet method: {e}")
                    return False
                except Exception as e:
                    self.logger.error(f"Router {self.name}: Failed to call Ray Actor put_packet: {e}")
                    return False
            elif is_ray_object_ref:
                # target_buffer 是 Ray ObjectRef，这种情况不应该发生，因为我们应该从上面的分支处理
                self.logger.error(f"Router {self.name}: Unexpected Ray ObjectRef without Ray Actor handle")
                return False
            elif hasattr(target_buffer, 'put_nowait'):
                # 这是一个普通的队列对象
                self.logger.info(f"Router {self.name}: Calling target_buffer.put_nowait() on local buffer")
                target_buffer.put_nowait(routed_packet)
            else:
                # 回退方案
                self.logger.warning(f"Router {self.name}: Using fallback method for unknown buffer type: {type(target_buffer)}")
                target_buffer.put_nowait(routed_packet)
            
            self.logger.info(f"Router {self.name}: Successfully sent packet to target")
            self.logger.debug(
                f"Sent {'keyed' if packet.is_keyed() else 'unkeyed'} packet "
                f"to {connection.target_name} (strategy: {packet.partition_strategy or 'round-robin'})"
            )
            return True
        except RuntimeError as e:
            # Check if the queue is closed
            if "Queue is closed" in str(e):
                self.logger.warning(
                    f"Queue to {connection.target_name} is closed, setting stop signal in context"
                )
                # 设置上下文的停止信号，让源任务停止
                self.ctx.set_stop_signal()
                return False
            else:
                # Other RuntimeError
                self.logger.error(
                    f"Failed to send packet to {connection.target_name}: {e}\n{traceback.format_exc()}"
                )
                return False
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
