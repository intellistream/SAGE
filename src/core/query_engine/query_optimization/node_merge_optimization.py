from src.core.dag.dag import DAG
from src.core.query_engine.query_optimization.base_optimization import BaseOptimization


class MergeNodesOptimization(BaseOptimization):
    def apply(self, dag):
        """
        Merge compatible nodes to reduce execution overhead.
        """
        self.logger.info("Applying MergeNodesOptimization...")
        optimized_dag = DAG()
        seen_operators = set()

        for node in dag.get_topological_order():
            if node.operator_name not in seen_operators:
                optimized_dag.add_node(node)
                seen_operators.add(node.operator_name)
            # Reconnect edges
            for downstream in dag.edges.get(node, []):
                optimized_dag.add_edge(node, downstream)

        return optimized_dag
