from src.core.query_engine.dag.base_dag_node import BaseDAGNode


class OneShotDAGNode(BaseDAGNode):
    """
    One-shot execution variant of DAGNode.
    """

    def execute(self):
        """
        Execute the operator logic once.
        """
        self.logger.debug(f"Node '{self.name}' starting one-shot execution.")
        try:
            if self.is_spout:
                self.logger.debug(f"Node '{self.name}' is a spout. Executing without fetching input.")
                self.operator.output_queue = self.output_queue
                self.operator.execute()
            else:
                input_data = self.fetch_input()
                if input_data is None:
                    self.logger.warning(f"Node '{self.name}' has no input to process.")
                    return

                self.operator.output_queue = self.output_queue
                self.operator.execute(input_data, **self.config)

            self.is_executed = True
        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")
