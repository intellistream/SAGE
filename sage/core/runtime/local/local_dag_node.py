from __future__ import annotations
import asyncio
import inspect
import logging
import threading
import time
from typing import Any, Type, TYPE_CHECKING, Union, List, Optional, Tuple


#from sage.archive.operator_wrapper import OperatorWrapper
from sage.api.base_operator import BaseOperator
from sage.core.graph import SageGraph, GraphEdge, GraphNode
from sage.core.io.message_queue import MessageQueue
from sage.core.io.emit_context import  NodeType
from sage.core.io.local_emit_context import LocalEmitContext
from sage.api.transformation import BaseTransformation, TransformationType
from sage.utils.custom_logger import CustomLogger
import ray
from ray.actor import ActorHandle


class LocalDAGNode:
    """
    Multiplexer DAG Node.

    This node can handle multiple upstream nodes and emit results to multiple downstream nodes.
    It is designed for scenarios where data from multiple sources needs to be processed together.
    """

    def __init__(self, 
                 name:str,
                 transformation:BaseTransformation) -> None:
        """
        Initialize the multiplexer DAG node.
# 
        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.name = name
        self.transformation = transformation
        self.operator = transformation.build_instance()  # Build operator instance from transformation
        self.is_spout = transformation.transformation_type == TransformationType.SOURCE  # Check if this is a spout node 正确
        
        self.input_buffer = MessageQueue()  # Local input buffer for this node



        self._current_channel_index = 0
        self._initialized = False
        # Create emit context
        # Create emit context for mixed environment
        self.emit_context = LocalEmitContext(self.name)
        self._emit_context_injected = False


        self.logger = CustomLogger(
            object_name=f"LocalDAGNode_{self.name}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        # self.logger.info(f"transformation_type: {transformation.transformation_type}")
        self.logger.info(f"Initialized LocalDAGNode: {self.name} (spout: {self.is_spout})")




    def _ensure_initialized(self):
        """
        Ensure that all runtime objects are initialized.
        Called when the node actually starts running.
        """
        if self._initialized:
            return
            
        
        # Initialize stop event
        self.stop_event = threading.Event()
        
        # Inject emit context
        if hasattr(self.operator, 'set_emit_context') and not self._emit_context_injected:
            try:
                self.operator.set_emit_context(self.emit_context)
                self._emit_context_injected = True
                self.logger.debug(f"Injected emit context for operator in node {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to inject emit context in node {self.name}: {e}")
        
        self._initialized = True
    
    def put(self, data_packet: Tuple[int, Any]):
        """
        向输入缓冲区放入数据包
        
        Args:
            data_packet: (input_channel, data) 元组
        """
        self.input_buffer.put(data_packet, timeout=1.0)
        self.logger.debug(f"Put data packet into buffer: channel={data_packet[0]}")


    def add_downstream_node(self, output_edge: GraphEdge, downstream_operator: Union['LocalDAGNode', ActorHandle]):
        """
        添加下游节点到emit context
        
        Args:
            output_edge: 输出边
            downstream_operator: 下游操作符（本地节点或Ray Actor）
        """
        try:
            if isinstance(downstream_operator, ActorHandle):
                # Ray Actor
                self.emit_context.add_downstream_target(
                    output_channel=output_edge.upstream_channel,
                    node_type=NodeType.RAY_ACTOR,
                    target_object=downstream_operator,
                    target_input_channel=output_edge.downstream_channel,
                    node_name=f"RayActor_{output_edge.downstream_node.name}"
                )
                self.logger.debug(f"Added Ray actor downstream: {self.name}[{output_edge.upstream_channel}] -> "
                                f"{output_edge.downstream_node.name}[{output_edge.downstream_channel}]")
            
            elif isinstance(downstream_operator, LocalDAGNode):
                # 本地节点
                self.emit_context.add_downstream_target(
                    output_channel=output_edge.upstream_channel,
                    node_type=NodeType.LOCAL,
                    target_object=downstream_operator,
                    target_input_channel=output_edge.downstream_channel,
                    node_name=downstream_operator.name
                )
                self.logger.debug(f"Added local node downstream: {self.name}[{output_edge.upstream_channel}] -> "
                                f"{downstream_operator.name}[{output_edge.downstream_channel}]")
            else:
                raise TypeError(f"Unsupported downstream operator type: {type(downstream_operator)}")
                
        except Exception as e:
            self.logger.error(f"Error adding downstream node: {e}", exc_info=True)
            raise
    

    def _inject_emit_context_if_needed(self):
        """
        Inject emit context if not already done and if supported by operator.
        This is called at runtime to avoid serialization issues.
        """
        if not self._emit_context_injected and hasattr(self.operator, 'set_emit_context'):
            try:
                self.operator.set_emit_context(self.emit_context)
                self._emit_context_injected = True
                self.logger.debug(f"Injected emit context for operator in node {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to inject emit context in node {self.name}: {e}")

    def run_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """

        # Ensure all runtime objects are initialized
        self._ensure_initialized()
        self.stop_event.clear()

        # Main execution loop
        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.receive(0, None)
                    time.sleep(1)  # Sleep to avoid busy loop
                else:
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    data_packet = self.input_buffer.get(timeout=0.5)
                    if(data_packet is None):
                        time.sleep(0.1)  # Short sleep when no data to process
                        continue
                    (input_channel, data) = data_packet
                    self.logger.debug(f"Processing data from buffer: channel={input_channel}")
                    # Call operator's receive method with the channel_id and data
                    self.operator.receive(input_channel, data)
                    
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if hasattr(self, 'stop_event') and self.stop_event and not self.stop_event.is_set():
            self.stop_event.set()
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Node '{self.name}' received stop signal.")


    def __getstate__(self):
        """
        Custom serialization to exclude non-serializable objects.
        """
        state = self.__dict__.copy()
        # Remove non-serializable objects
        state.pop('logger', None)
        state.pop('stop_event', None)
        return state

    def __setstate__(self, state):
        """
        Custom deserialization to restore state.
        """
        self.__dict__.update(state)
        # Mark as not initialized so runtime objects will be created when needed
        self._initialized = False


