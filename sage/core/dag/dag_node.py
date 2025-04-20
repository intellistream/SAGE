from sage.core.io.message_queue import MessageQueue
import logging
import threading
import time
import ray

class BaseDAGNode:
    """
    Base class for DAG nodes, defining shared functionality for all node types.
    DAG节点基类，定义所有节点类型的共享功能
    """

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
        self.output_queue = MessageQueue.remote()
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
        ref= self.upstream_nodes[0].output_queue.get.remote()
        aggregated_input =ray.get(ref)
        return aggregated_input if aggregated_input else None

    def emit(self,output):
        if output is not None:
            ref = self.output_queue.put.remote(output)
            ray.get(ref)

    def execute(self):
        """
        This method must be implemented by subclasses to define specific execution behavior.
        子类必须实现此方法以定义具体执行逻辑
        """
        raise NotImplementedError("Subclasses must implement the `execute` method.")



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
        self.logger.debug(f"Node '{self.name}' starting one-shot execution.")
        try:
            if self.is_spout:
                self.logger.debug(f"Node '{self.name}' is a spout. Executing without fetching input.")
                ref=self.operator.execute.remote()
                output=ray.get(ref)
                self.emit(output)
            else:
                input_data = self.fetch_input()
                if input_data is None:
                    self.logger.warning(f"Node '{self.name}' has no input to process.")
                    return
                ref=self.operator.execute.remote(input_data)
                output=ray.get(ref)
                self.emit(output)

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
        """
        Main worker loop to be executed by an external thread.
        由外部线程执行的主工作循环
        """
        self.stop_event.clear()  # 重置停止信号
        self.logger.info(f"Node '{self.name}' worker loop started.")

        # 仅在 duration 非 None 时启动定时器 (关键修改点)
        if self.duration is not None:
            # 检查 duration 是否为有效数值
            if not isinstance(self.duration, (int, float)) or self.duration <= 0:
                raise ValueError("duration 必须是正数")
            self._stop_timer = threading.Timer(self.duration, self.stop)
            self._stop_timer.start()

        while not self.stop_event.is_set():
            try:
                # 1. Fetch input data
                if self.is_spout:
                    ref = self.operator.execute.remote()
                    output=ray.get(ref)
                    self.emit(output)
                else:
                    input_data = self.fetch_input()
                    if input_data is None:
                        continue
                    ref = self.operator.execute.remote(input_data)
                    output=ray.get(ref)
                    self.emit(output)
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()  # 发生错误时自动停止
                raise RuntimeError(f"Execution failed in node '{self.name}'")

        # 循环结束后清理定时器 (新增)
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