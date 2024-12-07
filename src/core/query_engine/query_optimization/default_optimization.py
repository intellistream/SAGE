from src.core.dag.dag import DAG
from src.core.query_engine.query_optimization.base_optimization import BaseOptimization


class DefaultOptimization(BaseOptimization):
    def apply(self, dag):
        """
        Sort nodes by priority in topological order.
        """
        self.logger.info("Applying DefaultOptimization...")
        sorted_nodes = sorted(dag.get_topological_order(), key=lambda node: getattr(node, 'priority', 0), reverse=True)
        optimized_dag = DAG()
        for node in sorted_nodes:
            optimized_dag.add_node(node)
            for downstream in dag.edges.get(node, []):
                optimized_dag.add_edge(node, downstream)
        return optimized_dag
