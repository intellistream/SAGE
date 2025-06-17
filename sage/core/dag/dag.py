import logging
from collections import deque
from typing import List

from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode


class DAG:
    name: str
    node_mapping: dict
    execution_type: str
    config_mapping: dict
    platform: str
    """
    Directed Acyclic Graph (DAG) class to manage nodes and execution flow.
    有向无环图（DAG）类，用于管理节点和执行流程。
    """

    def __init__(self,id,strategy=None):
        """
        Initialize an empty DAG.
        """
        self.name = None
        self.nodes = []  # Changed from set to list
        self.edges = {}  # Dictionary to store edges as {parent: [children]}
        self.id=id
        self.strategy="oneshot" if strategy is None else strategy
        self.logger = logging.getLogger(self.__class__.__name__)
        self.working_config=None
    def add_node(self, node):
        """
        Add a node to the DAG.
        :param node: DAGNode instance to add.
        将节点添加到DAG中。
        :param node: 要添加的DAGNode实例。
        """
        if node not in self.nodes:
            self.nodes.append(node)  # Maintain order of addition
            self.edges[node] = []
            # self.logger.info(f"Node added: {node.name}")

    def add_edge(self, parent, child):
        """
        Add a directed edge from parent to child.
        :param parent: Parent DAGNode.
        :param child: Child DAGNode.
         添加从父节点到子节点的有向边。
         初始化一个空的DAG。
        :param parent: 父节点DAGNode。
        :param child: 子节点DAGNode。
        """
        if parent not in self.nodes or child not in self.nodes:
            raise ValueError("Both parent and child nodes must be part of the DAG.")
        if child in self.edges[parent]:
            self.logger.warning(f"Edge already exists from {parent.name} to {child.name}.")
        else:
            self.edges[parent].append(child)
            parent.add_downstream_node(child)
            # self.logger.info(f"Edge added from {parent.name} to {child.name}.")

    def get_topological_order(self) -> List['BaseDAGNode']:
        """
        Perform topological sorting of the DAG nodes.
        :return: List of DAGNode instances in topological order.
        对DAG节点进行拓扑排序。
        :return: 拓扑顺序排列的DAGNode实例列表。
        """
        in_degree = {node: 0 for node in self.nodes}
        for parent in self.edges:
            for child in self.edges[parent]:
                in_degree[child] += 1

        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        sorted_nodes = []

        while queue:
            current = queue.popleft()
            sorted_nodes.append(current)
            for child in self.edges[current]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(sorted_nodes) != len(self.nodes):
            raise RuntimeError("The graph contains a cycle and is not a valid DAG.")

        self.logger.info("Topological sort completed.")
        return sorted_nodes

    def get_node_by_name(self, name: str) -> 'BaseDAGNode':
        """
        Retrieve a node from the DAG by its name.
        :param name: The name of the node to retrieve.
        :return: The DAGNode instance with the given name.
        :raises ValueError: If no node with the given name exists in the DAG.
        根据节点名称检索DAG中的节点。
        :param name: 要检索的节点名称。
        :return: 对应名称的DAGNode实例。
        :raises ValueError: 如果DAG中不存在指定名称的节点。
        """
        for node in self.nodes:
            if node.name == name:
                return node
        raise ValueError(f"Node with name '{name}' not found in the DAG.")

