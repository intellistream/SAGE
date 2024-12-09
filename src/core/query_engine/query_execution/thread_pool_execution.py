from concurrent.futures import ThreadPoolExecutor

from src.core.query_engine.dag import DAGNode
from src.core.query_engine.query_execution.base_execution import ExecutionStrategy


class ThreadPoolExecutionStrategy(ExecutionStrategy):
    """
    Thread-pool-based execution strategy for DAG.
    Executes each node as a separate task.
    """

    def __init__(self, max_workers=None):
        """
        Initialize the thread pool execution strategy.
        :param max_workers: Maximum number of threads in the pool.
        """
        self.max_workers = max_workers

    def execute(self, dag):
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for node in dag.get_topological_order():
                assert isinstance(node, DAGNode), f"Expected DAGNode, got {type(node).__name__}"
                futures[node.name] = executor.submit(node.execute)

            for name, future in futures.items():
                results[name] = future.result()
        return results
