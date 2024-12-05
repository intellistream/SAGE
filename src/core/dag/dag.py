import logging
from collections import deque

class DAG:
    """
    Directed Acyclic Graph (DAG) class to manage nodes and execution flow.
    """

    def __init__(self):
        """
        Initialize an empty DAG.
        """
        self.nodes = set()
        self.edges = {}  # Dictionary to store edges as {parent: [children]}
        self.logger = logging.getLogger(__name__)

    def add_node(self, node):
        """
        Add a node to the DAG.
        :param node: DAGNode instance to add.
        """
        if node not in self.nodes:
            self.nodes.add(node)
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
            self.logger.info(f"Edge added from {parent.name} to {child.name}.")

    def get_predecessors(self, node):
        """
        Get all predecessor nodes of the given node.
        :param node: DAGNode instance.
        :return: List of predecessor nodes.
        """
        return [parent for parent, children in self.edges.items() if node in children]

    def get_terminal_nodes(self):
        """
        Get all terminal nodes (nodes with no children).
        :return: List of terminal nodes.
        """
        return [node for node, children in self.edges.items() if not children]

    def get_topological_order(self):
        """
        Perform topological sorting of the DAG nodes.
        :return: List of nodes in topological order.
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
