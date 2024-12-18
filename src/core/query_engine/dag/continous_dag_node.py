import threading
import time

from src.core.query_engine.dag.base_dag_node import BaseDAGNode


class ContinuousDAGNode(BaseDAGNode):
    """
    Continuous execution variant of DAGNode, supporting multithreaded processing.
    """

    def __init__(self, name, operator, config=None, is_spout=False, num_threads=1):
        """
        Initialize the continuous DAG node.
        :param num_threads: Number of threads to use for execution.
        """
        super().__init__(name, operator, config, is_spout)
        self.num_threads = num_threads
        self.stop_event = threading.Event()

    def execute(self):
        """
        Start multiple threads for continuous execution.
        """
        self.logger.info(f"Node '{self.name}' starting continuous execution with {self.num_threads} threads.")
        threads = [
            threading.Thread(target=self._worker, daemon=True)
            for _ in range(self.num_threads)
        ]

        for thread in threads:
            thread.start()

        try:
            while any(thread.is_alive() for thread in threads):
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info(f"Stopping execution for node '{self.name}'.")
            self.stop_event.set()
            for thread in threads:
                thread.join()

    def _worker(self):
        """
        Worker thread for continuous execution.
        """
        while not self.stop_event.is_set():
            try:
                input_data = self.fetch_input()
                if input_data:
                    self.operator.output_queue = self.output_queue
                    self.operator.execute(input_data, **self.config)
            except Exception as e:
                self.logger.error(f"Error in node '{self.name}' during continuous execution: {str(e)}")
                raise RuntimeError(f"Continuous execution failed in node '{self.name}': {str(e)}")
