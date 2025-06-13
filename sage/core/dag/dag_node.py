import asyncio
import inspect
from typing import Type, TYPE_CHECKING, Union, Any
from sage.core.io.message_queue import MessageQueue
import logging
import threading
import time
import ray
from sage.core.runtime.operator_wrapper import OperatorWrapper

class BaseDAGNode:
    """
    Base class for DAG nodes, defining shared functionality for all node types.
    DAG节点基类，定义所有节点类型的共享功能
    """
    name: str  # Unique name of the node
    operator: OperatorWrapper  # Operator implementing the execution logic
    config: dict  # Configuration parameters for the operator
    is_spout: bool  # Indicates if the node is a spout (starting point)
    output_queue: MessageQueue  # Output queue for the node's results
    upstream_nodes: list  # List of upstream DAGNodes
    downstream_nodes: list  # List of downstream DAGNodes
    is_executed: bool  # Indicates if the node has been executed
    is_longrunning: bool  # Indicates if the node is a long-running process



    def __init__(self, name, operator, config=None, is_spout=False):
        """
        Initialize the base DAG node.
        :param name: Unique name of the node.
        :param operator: An operator implementing the execution logic.
        :param config: Optional dictionary of configuration parameters for the operator.
        :param is_spout: Indicates if the node is the spout (starting point).
        初始化基础DAG节点
        :param name: 节点唯一名称
        :param operator: 实现执行逻辑的操作器
        :param config: 操作器的可选配置参数字典
        :param is_spout: 标识是否为数据源节点（起始点）
        """
        self.name = name
        self.operator = operator
        self.config = config or {}
        self.is_spout = is_spout
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_queue = MessageQueue()
        self.upstream_nodes = []  # List of upstream DAGNodes
        self.downstream_nodes = []  # List of downstream DAGNodes
        self.is_executed = False
        self.is_longrunning = False

    def add_upstream_node(self, node):
        """
        Add an upstream node. This node fetches input from the upstream node's output queue.
        :param node: A BaseDAGNode instance.
        添加上游节点，本节点将从上游节点的输出队列获取输入
        :param node: BaseDAGNode实例
        """
        if node not in self.upstream_nodes:
            self.upstream_nodes.append(node)
            # self.logger.info(f"Node '{self.name}' connected to upstream node '{node.name}'.")

    def add_downstream_node(self, node):
        """
        Add a downstream node. The downstream node uses this node's output queue as its input source.
        :param node: A BaseDAGNode instance.
        添加下游节点，下游节点将使用本节点的输出队列作为输入源
        :param node: BaseDAGNode实例

        """
        if node not in self.downstream_nodes:
            self.downstream_nodes.append(node)
            node.add_upstream_node(self)
            # self.logger.info(f"Node '{self.name}' connected to downstream node '{node.name}'.")
    # 这里fetch_input返回的是class coroutine
    def fetch_input(self):
        """
        Fetch input from upstream nodes' output queues.
        :return: Aggregated input data from upstream nodes or None if no data is available.
        从上游节点的输出队列获取输入
        :return: 来自上游节点的聚合输入数据，无数据时返回None
        """
        # 多个上游结点的代码
        # aggregated_input = []
        # for upstream_node in self.upstream_nodes:
        #     while not upstream_node.output_queue.empty():
        #         aggregated_input.append(upstream_node.output_queue.get())

        # 单个上游代码
        aggregated_input=self.upstream_nodes[0].output_queue.get()

        # 调试信息
        # if aggregated_input is not None:
        #     self.logger.debug(f"[{self.name}] fetch_input() 返回类型: {type(aggregated_input)}")
        #     if hasattr(aggregated_input, '_id'):
        #         self.logger.debug(f"[{self.name}] 检测到Ray ObjectRef")
        #     elif inspect.iscoroutine(aggregated_input):
        #         self.logger.debug(f"[{self.name}] 检测到协程对象！")
        #     else:
        #         self.logger.debug(f"[{self.name}] 检测到普通数据对象")

        return aggregated_input if aggregated_input else None

    def emit(self,output):
        if output is not None:
            self.output_queue.put(output)

    def execute(self):
        """
        This method must be implemented by subclasses to define specific execution behavior.
        子类必须实现此方法以定义具体执行逻辑
        """
        raise NotImplementedError("Subclasses must implement the `execute` method.")

    def get_name(self):
        return self.name



class OneShotDAGNode(BaseDAGNode):
    """
    One-shot execution variant of DAGNode.
    DAG节点的一次性执行变体
    """

    def execute(self):
        """
        Execute the operator logic once.
        单次执行操作器逻辑
        """
        # self.logger.debug(f"Node '{self.name}' starting one-shot execution.")
        try:
            if self.is_spout:
                # self.logger.debug(f"Node '{self.name}' is a spout. Executing without fetching input.")
                ref=self.operator.execute()
                self.emit(ref)
            else:
                input_data_ref = self.fetch_input()
                input_data = ray.get(input_data_ref)
                if input_data is None:
                    self.logger.warning(f"Node '{self.name}' has no input to process.")
                    return
                output_ref=self.operator.execute(input_data)
                self.emit(output_ref)
            self.is_executed = True
        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")



class ContinuousDAGNode(BaseDAGNode):
    """
    Continuous execution variant of DAGNode, designed to have its worker loop
    controlled by an external thread.
    DAG节点的持续执行变体，设计为由外部线程控制其工作循环
    """

    def __init__(self, name, operator, config=None, is_spout=False):
        super().__init__(name, operator, config, is_spout)
        self.stop_event = threading.Event()  # 停止信号
        # 从配置中获取 duration，不存在或为 None 时默认为 None
        self.duration = config.get("duration",None) if config else None  # 关键修改点
        self._stop_timer = None  # 新增定时器对象

    def run_loop(self):
        """主工作循环 - 现在非常简洁"""
        self.stop_event.clear()
        # self.logger.info(f"Node '{self.name}' worker loop started.")

        # 定时器设置
        if self.duration is not None:
            if not isinstance(self.duration, (int, float)) or self.duration <= 0:
                raise ValueError("duration must be a positive number")
            self._stop_timer = threading.Timer(self.duration, self.stop)
            self._stop_timer.start()

        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    # 数据源节点 - 直接调用，OperatorWrapper处理所有复杂性
                    # self.logger.debug(f"Node '{self.name}' executing as spout")
                    result = self.operator.execute()
                    # self.logger.debug(f"Node '{self.name}' spout result type: {type(result)}")
                    self.emit(result)
                else:
                    # 处理节点
                    input_data = self.fetch_input()
                    if input_data is None:
                        time.sleep(0.1)
                        continue
                    
                    # 解析输入（如果是Ray ObjectRef）
                    if hasattr(input_data, '_id') or 'ObjectRef' in str(type(input_data)):
                        input_data = ray.get(input_data)
                    
                    # 执行算子 - OperatorWrapper保证返回同步结果
                    # self.logger.debug(f"Node '{self.name}' executing with input type: {type(input_data)}")
                    result = self.operator.execute(input_data)
                    # self.logger.debug(f"Node '{self.name}' result type: {type(result)}")
                    self.emit(result)
                    
            except Exception as e:
                self.logger.error(f"Critical error in node '{self.name}': {str(e)}", exc_info=True)
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")

        # 清理定时器
        if self._stop_timer and self._stop_timer.is_alive():
            self._stop_timer.cancel()

    def stop(self):
        """
        Signal the worker loop to stop.
        发送停止工作循环的信号
        """
        if not self.stop_event.is_set():
            self.stop_event.set()
            # 停止时同时取消定时器 (新增)
            if self._stop_timer and self._stop_timer.is_alive():
                self._stop_timer.cancel()
            self.logger.info(f"Node '{self.name}' received stop signal.")