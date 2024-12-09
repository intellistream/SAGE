from src.core.query_engine.dag.one_shot_dag_node import OneShotDAGNode
from src.core.query_engine.query_execution.base_execution import ExecutionStrategy


class SequentialExecutionStrategy(ExecutionStrategy):
    """
    Sequential execution strategy for DAG.
    """

    def execute(self, dag):
        results = {}
        for node in dag.get_topological_order():
            assert isinstance(node, OneShotDAGNode), f"Expected OneShotDAGNode, got {type(node).__name__}"
            result = node.execute()
            results[node.name] = result
        return results
