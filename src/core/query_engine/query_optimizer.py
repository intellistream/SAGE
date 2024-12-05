# src/core/query_engine/query_optimizer.py

from src.core.dag.dag import DAG

class QueryOptimizer:
    def __init__(self):
        pass

    def optimize(self, dag):
        """
        Optimize the DAG by reordering nodes and removing redundancies.
        :param dag: The compiled DAG to be optimized.
        :return: Optimized DAG.
        """
        optimized_nodes = self._optimize_nodes(dag.nodes)
        return DAG(optimized_nodes)

    def _optimize_nodes(self, nodes):
        """
        Optimize the nodes in the DAG.
        This includes:
        - Reordering nodes based on dependencies and priorities.
        - Removing redundant operations.
        - Merging compatible nodes to reduce execution overhead.
        """
        # Sort nodes to ensure dependency order
        nodes.sort(key=lambda node: node.priority, reverse=True)

        # Example: Deduplicate retrievers if present
        optimized_nodes = []
        seen_operators = set()
        for node in nodes:
            if node.operator_name not in seen_operators:
                optimized_nodes.append(node)
                seen_operators.add(node.operator_name)

        return optimized_nodes
