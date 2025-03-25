from sage.core.query_engine.query_optimization.base_optimization import BaseOptimization
from sage.core.query_engine.query_optimization.no_op_optimization import NoOpOptimization


class QueryOptimizer:
    def __init__(self, optimization_methods=None):
        """
        Initialize the QueryOptimizer with a list of optimization strategies.
        """
        if optimization_methods is None:
            optimization_methods = [NoOpOptimization()]  # Use NoOpOptimization as the default strategy
        self.optimization_methods = optimization_methods

    def optimize(self, dag):
        """
        Apply all registered optimization methods in sequence.
        :param dag: The input DAG.
        :return: Optimized DAG.
        """
        optimized_dag = dag
        for method in self.optimization_methods:
            if not isinstance(method, BaseOptimization):
                raise ValueError(f"Optimization method {method} must inherit from BaseOptimization.")
            optimized_dag = method.apply(optimized_dag)
        return optimized_dag
