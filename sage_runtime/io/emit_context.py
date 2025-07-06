from typing import Any
from abc import ABC, abstractmethod
from enum import Enum
from sage_utils.custom_logger import CustomLogger

class NodeType(Enum):
    LOCAL = "local"
    RAY_ACTOR = "ray_actor"

class DownstreamTarget:
    """下游目标节点的封装"""
    def __init__(self, 
                 node_type: NodeType, 
                 target_object: Any, 
                 target_input_tag: str):
        self.node_type = node_type
        self.target_object = target_object
        self.input_tag = target_input_tag



# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。


class BaseEmitContext(ABC):
    """
    基础Emit Context抽象类
    支持混合环境中本地和Ray Actor之间的通信
    """
    

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.logger = CustomLogger(
            object_name=f"EmitContext_{node_name}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )

    
    def route_and_send(self, target: DownstreamTarget, data: Any) -> None:
        """
        根据目标类型路由并发送数据
        
        Args:
            target: 目标节点信息
            data: 要发送的数据
        """
        try:
            if target.node_type == NodeType.LOCAL:
                self._send_to_local(target, data)
            elif target.node_type == NodeType.RAY_ACTOR:
                self._send_to_ray_actor(target, data)
            else:
                self.logger.error(f"Unknown target type: {target.node_type}")
        except Exception as e:
            self.logger.error(f"Failed to send data to {target.target_object}: {e}", exc_info=True)
    
    @abstractmethod
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到本地节点"""
        pass
    
    @abstractmethod
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到Ray Actor"""
        pass




