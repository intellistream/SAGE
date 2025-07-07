
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set
from sage_core.api.collector import Collector
# from sage_runtime.io.base_emit_context import BaseEmitContext, DownstreamTarget, NodeType
# from sage_runtime.runtime_context import RuntimeContext
from sage_utils.custom_logger import CustomLogger
import inspect

from sage_core.api.base_function import BaseFunction
from sage_core.api.tuple import Data

# TODO: 将Memory的API使用在这里。
# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。

class BaseOperator(ABC):
    def __init__(self, function: BaseFunction, session_folder: Optional[str] = None, name: Optional[str] = None):
        self.collector = Collector(self)  # 用于收集数据
        self.logger = CustomLogger(
            filename=f"Node_{name}",
            session_folder = session_folder or None,
            console_output=False,
            file_output=True,
            name = f"{name}_{self.__class__.__name__}"
        )
        self.function = function
        self.function.insert_collector(self.collector)

        self._name = self.__class__.__name__
        # 维护下游节点和路由逻辑
        # downstream_channel->broadcasting_groups->targets
        from sage_runtime.io.base_emit_context import DownstreamTarget
        self.downstream_channels:Dict[str, Dict[int, Dict[int, DownstreamTarget]]] = {}
        # self.downstream_channels: Dict[int,Dict[int, List[DownstreamTarget]] ] = {}
        self.downstream_round_robin: Dict[str, Dict[int, int]] = {}
        for index, (output_tag, output_type) in enumerate(self.function.declare_outputs()):
            self.downstream_channels[output_tag] = {}
            self.downstream_round_robin[output_tag] = {}


        self.runtime_context = None

    

    def insert_emit_context(self, emit_context):
        """
        Inject the emit context into the operator.
        This is typically called by the DAG node to set up the context.
        
        Args:
            emit_context: The emit context to be injected
        """
        self._emit_context = emit_context
        self._emit_context.logger = self.logger  # Use operator's logger for emit context
        self.logger.debug(f"Emit context injected for operator {self._name}")

    def insert_runtime_context(self, runtime_context  = None):
        self.runtime_context = runtime_context
        self.function.insert_runtime_context(runtime_context)

    def process_data(self, tag: str, data: Data):
        """
        Smart dispatch for multi-input operator.
        """
        try:
            if(len(self.function.__class__.declare_inputs()) == 0):
                # No inputs declared, call execute without arguments
                result = self.function.execute()
            elif(len(self.function.__class__.declare_inputs()) == 1):
                result = self.function.execute(data)
            else:
                result = self.function.execute(tag, data)
            if result is not None:
                self.emit(None, result)

        except Exception as e:
            self.logger.error(f"Error in {self._name}.receive(): {e}")
            raise


    # def process_data(self, channel: int, data: Data):
    #     """
    #     Receive data from upstream node through specified channel.
    #     Default implementation calls execute() and emits result to channel 0.
    #     Can be overridden by subclasses for custom receive logic.
        
    #     Args:
    #         channel: The input channel number
    #         data: The data received from upstream
    #     """
    #     try:
    #         # Default behavior: call execute with received data and emit to channel 0
    #         if(data is None):
    #             result = self.function.execute()
    #         else:
    #             result = self.function.execute(data)
    #         if result is not None:
    #             self.emit(-1, result)
    #             # Note: Using -1 to indicate broadcasting to each output channel
    #     except Exception as e:
    #         self.logger.error(f"Error in {self._name}.receive(): {e}")
    #         raise


    def emit(self, tag: str, data: Any):
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
        if tag is None:
            # x轴广播到所有下游通道
            target_groups = self.downstream_channels.items()
        else:
            if tag not in self.downstream_channels:
                self.logger.warning(f"Invalid output tag '{tag}' for operator {self._name}.")
                return
            target_groups = [(tag, self.downstream_channels[tag])]

        # 向每个通道发送数据
        for tag, broadcast_groups in target_groups:
            for broadcast_index, parallel_targets in broadcast_groups.items():

                # round-robin选择
                target = parallel_targets[self.downstream_round_robin[tag][broadcast_index] % len(parallel_targets)]
                self.downstream_round_robin[tag][broadcast_index] += 1
                # 发送数据
                try:
                    self._emit_context.route_and_send(target, data)
                except Exception as e:
                    self.logger.error(f"Failed to send data to target {target.node_name} "
                                    f"on channel {ch} group[{broadcast_index}]: {e}", exc_info=True)



    def add_downstream_target(self,
                            output_tag: str,
                            broadcast_index,
                            parallel_index: int,
                            target_object: Any, 
                            target_input_tag: str) -> None:

        # Debug log
        self.logger.debug(
            f"Adding downstream: output_tag={output_tag}, broadcast_index={broadcast_index}, parallel_index={parallel_index}, "
            f"target_object={target_object}, target_input_tag={target_input_tag}"
        )
        from sage_runtime.executor.local_dag_node import LocalDAGNode
        from ray.actor import ActorHandle
        from sage_runtime.io.base_emit_context import NodeType, DownstreamTarget

        if(isinstance(target_object, ActorHandle)):
            node_type = NodeType.RAY_ACTOR
            self.logger.debug("Detected Ray ActorHandle as target")
        elif isinstance(target_object, str) or isinstance(target_object, LocalDAGNode):
            node_type = NodeType.LOCAL
            self.logger.debug(f"Detected Local DagNode as target, name is {target_object.name}")
        else:
            node_type = NodeType.LOCAL
            self.logger.warning(f"Unknown target type: {type(target_object)}. "
                            "Defaulting to LOCAL node type.")


        target = DownstreamTarget(node_type, target_object, target_input_tag)

        if output_tag not in self.downstream_channels:
            raise ValueError(f"Output tag {output_tag} not found in operator {self._name}. "
                            "Ensure the output tag is declared in the function.")
        if broadcast_index not in self.downstream_channels[output_tag]:
            self.downstream_channels[output_tag][broadcast_index] = {}
            self.downstream_round_robin[output_tag][broadcast_index] = 0
        self.downstream_channels[output_tag][broadcast_index][parallel_index] = target

        self.logger.debug(f"Added downstream target: [out:{output_tag}] -> " f"{target_object}[in:{target_input_tag}] (type: {node_type.value})")
