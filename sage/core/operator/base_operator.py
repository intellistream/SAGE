
from abc import ABC, abstractmethod
from typing import Any, List, Dict
from sage.core.io.emit_context import DownstreamTarget, NodeType
from sage.core.io.emit_context import BaseEmitContext
from sage.utils.custom_logger import CustomLogger
from sage.api.tuple import Data


# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。
class BaseOperator(ABC):
    def __init__(self, *args, **kwargs):
        self._name = self.__class__.__name__
        # 维护下游节点和路由逻辑
        self.downstream_channels: Dict[int, List[DownstreamTarget]] = {}
        self.downstream_round_robin: Dict[int, int] = {}


    def insert_emit_context(self, emit_context: BaseEmitContext):
        """
        Inject the emit context into the operator.
        This is typically called by the DAG node to set up the context.
        
        Args:
            emit_context: The emit context to be injected
        """
        self._emit_context = emit_context
        self._emit_context.logger = self.logger  # Use operator's logger for emit context
        self.logger.debug(f"Emit context injected for operator {self._name}")


    @abstractmethod
    def receive(self, channel: int, data: Data):
        """
        Receive data from upstream node through specified channel.
        Must be implemented by subclasses.
        
        Args:
            channel: The input channel number
            data: The data received from upstream
        """
        pass


    def emit(self, channel: int, data: Any, target_index: int = None):
        """
        Emit data to downstream node through specified channel and target.
        
        Args:
            channel: The output channel number, -1 for broadcast to all channels
            data: The data to emit
            target_index: Target index within channel (y-axis), None for round-robin
        """
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self._name}. "
                            "This should be injected by the DAG node.")
        
        # 确定要发送的通道列表
        if channel == -1:
            # x轴广播到所有下游通道
            channels_to_send = list(self.downstream_channels.keys())
        elif channel >= 0 and channel in self.downstream_channels:
            # 向指定通道发送
            channels_to_send = [channel]
        elif channel >= 0:
            # 正数但超出范围
            self.logger.warning(f"Channel index {channel} out of range for operator {self._name}")
            return
        else:
            # 负数但不是-1
            self.logger.warning(f"Invalid channel index {channel} for operator {self._name}. Use -1 for broadcast or non-negative integers for specific channels.")
            return
        
        # 向每个通道发送数据
        for ch in channels_to_send:
            targets = self.downstream_channels[ch]
            if not targets:
                self.logger.warning(f"No targets found for channel {ch} in operator {self._name}")
                continue
            
            # y轴目标选择
            if target_index is None:
                # round-robin选择
                target = targets[self.downstream_round_robin[ch] % len(targets)]
                self.downstream_round_robin[ch] += 1
            elif 0 <= target_index < len(targets):
                # 指定目标
                target = targets[target_index]
            else:
                # y轴索引越界
                self.logger.warning(f"Target index {target_index} out of range for channel {ch} "
                                f"in operator {self._name}. Channel has {len(targets)} targets.")
                continue
            
            # 发送数据
            try:
                self._emit_context.route_and_send(target, data)
            except Exception as e:
                self.logger.error(f"Failed to send data to target {target.node_name} "
                                f"on channel {ch}[{target_index}]: {e}", exc_info=True)



    def add_downstream_target(self,
                            output_channel: int,
                            target_object: Any, 
                            target_input_channel: int) -> None:
        """
        添加下游目标节点
        
        Args:
            output_channel: 自身的输出通道号
            node_type: 下游节点类型
            target_object: 下游节点对象
            target_input_channel: 下游节点的输入通道号
            node_name: 下游节点名称
        """
        from ray.actor import ActorHandle
        from sage.core.runtime.local.local_dag_node import LocalDAGNode
        # Debug log
        self.logger.debug(
            f"Adding downstream: output_channel={output_channel}, "
            f"target_object={target_object}, target_input_channel={target_input_channel}"
        )

        if(isinstance(target_object, ActorHandle)):
            node_type = NodeType.RAY_ACTOR
            self.logger.debug("Detected Ray ActorHandle as target")
        elif isinstance(target_object, str) or isinstance(target_object, LocalDAGNode):
            node_type = NodeType.LOCAL
            self.logger.debug("Detected Local DagNode as target")
        else:
            node_type = NodeType.LOCAL
            self.logger.warning(f"Unknown target type: {type(target_object)}. "
                            "Defaulting to LOCAL node type.")


        target = DownstreamTarget(node_type, target_object, target_input_channel)

        if output_channel not in self.downstream_channels:
            self.downstream_channels[output_channel] = []
            self.downstream_round_robin[output_channel] = 0
        self.downstream_channels[output_channel].append(target)

        self.logger.debug(f"Added downstream target: [out:{output_channel}] -> " f"{target_object}[in:{target_input_channel}] (type: {node_type.value})")
