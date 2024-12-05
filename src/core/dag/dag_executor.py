import logging

class DAGExecutor:
    """
    Executes a Directed Acyclic Graph (DAG) by traversing its nodes and executing them in topological order.
    """

    def __init__(self):
        """
        Initialize the DAGExecutor.
        """
        self.logger = logging.getLogger(__name__)

    def execute(self, dag, input_data):
        """
        Execute the provided DAG.
        :param dag: Instance of the DAG class to be executed.
        :param input_data: Initial input data for the DAG execution.
        :return: Final output after executing all nodes in the DAG.
        """
        self.logger.info("Starting DAG execution.")
        node_results = {}

        # Traverse nodes in topological order
        for node in dag.get_topological_order():
            self.logger.info(f"Executing node: {node.name}")
            try:
                # Collect inputs from the predecessors
                predecessors = dag.get_predecessors(node)
                predecessor_outputs = [node_results[predecessor] for predecessor in predecessors]

                # Flatten input if there is only one predecessor
                input_for_node = predecessor_outputs[0] if len(predecessor_outputs) == 1 else predecessor_outputs

                # Execute the node and store the result
                node_results[node] = node.execute(input_for_node)
            except Exception as e:
                self.logger.error(f"Error during execution of node {node.name}: {str(e)}")
                raise RuntimeError(f"Execution failed at node {node.name}: {str(e)}")

        # Final output is the result of terminal nodes
        final_results = [node_results[node] for node in dag.get_terminal_nodes()]
        self.logger.info("DAG execution completed.")
        return final_results

    def execute_continuous(self, dag, input_stream, max_retries=3):
        """
        Execute a DAG continuously for streaming input.
        :param dag: Instance of the DAG class to be executed.
        :param input_stream: A generator or iterable that yields input data for the DAG.
        :param max_retries: Maximum retries allowed if execution fails.
        """
        self.logger.info("Starting continuous DAG execution.")
        try:
            for input_data in input_stream:
                self.logger.info(f"Processing input: {input_data}")
                retries = 0
                while retries < max_retries:
                    try:
                        result = self.execute(dag, input_data)
                        self.logger.info(f"Continuous execution result: {result}")
                        break
                    except Exception as e:
                        retries += 1
                        self.logger.warning(f"Retrying DAG execution ({retries}/{max_retries}) due to error: {str(e)}")
                if retries == max_retries:
                    self.logger.error(f"Max retries reached. Skipping input: {input_data}")
        except Exception as e:
            self.logger.error(f"Error during continuous DAG execution: {str(e)}")
            raise RuntimeError(f"Continuous execution failed: {str(e)}")
