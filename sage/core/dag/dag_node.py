from sage.core.io.message_queue import MessageQueue
import logging
import threading
import time


class BaseDAGNode:
    """
    Base class for DAG nodes, defining shared functionality for all node types.
    """

    def __init__(self, name, operator, config=None, is_spout=False):
        """
        Initialize the base DAG node.
        :param name: Unique name of the node.
        :param operator: An operator implementing the execution logic.
        :param config: Optional dictionary of configuration parameters for the operator.
        :param is_spout: Indicates if the node is the spout (starting point).
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
        """
        if node not in self.upstream_nodes:
            self.upstream_nodes.append(node)
            # self.logger.info(f"Node '{self.name}' connected to upstream node '{node.name}'.")

    def add_downstream_node(self, node):
        """
        Add a downstream node. The downstream node uses this node's output queue as its input source.
        :param node: A BaseDAGNode instance.
        """
        if node not in self.downstream_nodes:
            self.downstream_nodes.append(node)
            node.add_upstream_node(self)
            # self.logger.info(f"Node '{self.name}' connected to downstream node '{node.name}'.")

    def fetch_input(self):
        """
        Fetch input from upstream nodes' output queues.
        :return: Aggregated input data from upstream nodes or None if no data is available.
        """
        # 多个上游结点的代码
        # aggregated_input = []
        # for upstream_node in self.upstream_nodes:
        #     while not upstream_node.output_queue.empty():
        #         aggregated_input.append(upstream_node.output_queue.get())

        # 单个上游代码
        aggregated_input = self.upstream_nodes[0].output_queue.get()
        return aggregated_input if aggregated_input else None

    def emit(self,output):
        if output is not None:
            self.output_queue.put(output)

    def execute(self):
        """
        This method must be implemented by subclasses to define specific execution behavior.
        """
        raise NotImplementedError("Subclasses must implement the `execute` method.")



class OneShotDAGNode(BaseDAGNode):
    """
    One-shot execution variant of DAGNode.
    """

    def execute(self):
        """
        Execute the operator logic once.
        """
        self.logger.debug(f"Node '{self.name}' starting one-shot execution.")
        try:
            if self.is_spout:
                self.logger.debug(f"Node '{self.name}' is a spout. Executing without fetching input.")
                output=self.operator.execute()
                self.emit(output)
            else:
                input_data = self.fetch_input()
                if input_data is None:
                    self.logger.warning(f"Node '{self.name}' has no input to process.")
                    return
                output=self.operator.execute(input_data)
                self.emit(output)

            self.is_executed = True
        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")


class ContinuousDAGNode(BaseDAGNode):
    """
    Continuous execution variant of DAGNode, designed to have its worker loop
    controlled by an external thread.
    """

    def __init__(self, name, operator, config=None, is_spout=False):
        super().__init__(name, operator, config, is_spout)
        self.stop_event = threading.Event()  # 停止信号

    def run_loop(self):
        """
        Main worker loop to be executed by an external thread.
        """
        self.stop_event.clear()  # 重置停止信号
        self.logger.info(f"Node '{self.name}' worker loop started.")

        while not self.stop_event.is_set():
            try:
                # 1. Fetch input data
                if self.is_spout:
                    output=self.operator.execute()
                    self.emit(output)
                else :
                    input_data = self.fetch_input()
                    if input_data is None:
                        continue
                    output=self.operator.execute(input_data)
                    self.emit(output)
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()  # 发生错误时自动停止
                raise RuntimeError(f"Execution failed in node '{self.name}'")

    def stop(self):
        """
        Signal the worker loop to stop.
        """
        self.stop_event.set()
        self.logger.info(f"Node '{self.name}' received stop signal.")