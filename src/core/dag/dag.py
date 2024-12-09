import logging
from collections import deque
from typing import List

from src.core.dag.dag_node import DAGNode


class DAG:
    """
    Directed Acyclic Graph (DAG) class to manage nodes and execution flow.
    """

    def __init__(self):
        """
        Initialize an empty DAG.
        """
        self.nodes = []  # Changed from set to list
        self.edges = {}  # Dictionary to store edges as {parent: [children]}
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_node(self, node):
        """
        Add a node to the DAG.
        :param node: DAGNode instance to add.
        """
        if node not in self.nodes:
            self.nodes.append(node)  # Maintain order of addition
            self.edges[node] = []
            self.logger.info(f"Node added: {node.name}")

    def add_edge(self, parent, child):
        """
        Add a directed edge from parent to child.
        :param parent: Parent DAGNode.
        :param child: Child DAGNode.
        """
        if parent not in self.nodes or child not in self.nodes:
            raise ValueError("Both parent and child nodes must be part of the DAG.")
        if child in self.edges[parent]:
            self.logger.warning(f"Edge already exists from {parent.name} to {child.name}.")
        else:
            self.edges[parent].append(child)
            parent.add_downstream_node(child)
            self.logger.info(f"Edge added from {parent.name} to {child.name}.")

    def get_topological_order(self) -> List['DAGNode']:
        """
        Perform topological sorting of the DAG nodes.
        :return: List of DAGNode instances in topological order.
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

    def get_node_by_name(self, name: str) -> 'DAGNode':
        """
        Retrieve a node from the DAG by its name.
        :param name: The name of the node to retrieve.
        :return: The DAGNode instance with the given name.
        :raises ValueError: If no node with the given name exists in the DAG.
        """
        for node in self.nodes:
            if node.name == name:
                return node
        raise ValueError(f"Node with name '{name}' not found in the DAG.")
