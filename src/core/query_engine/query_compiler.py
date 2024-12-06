from src.core.dag.dag import DAG
from src.core.dag.dag_node import DAGNode
from src.core.operators.embedder import Embedder
from src.core.operators.retriever import Retriever
from src.core.operators.generator import Generator
from src.core.query_engine.query_optimizer import QueryOptimizer


class QueryCompiler:
    def __init__(self, memory_layers):
        self.memory_layers = memory_layers
        self.optimizer = QueryOptimizer()

    def compile(self, input_text):
        """
        Compile a query or natural language input into a DAG.
        :param input_text: User-provided query or question.
        :return: Optimized DAG and execution type.
        """
        if input_text.upper().startswith("EXECUTE"):
            dag = self._compile_one_shot(input_text)
            execution_type = "one_shot"
        elif input_text.upper().startswith("REGISTER"):
            dag = self._compile_continuous(input_text)
            execution_type = "continuous"
        else:
            dag = self.compile_natural_query(input_text)
            execution_type = "one_shot"

        # Optimize the DAG
        optimized_dag = self.optimizer.optimize(dag)
        return optimized_dag, execution_type

    def compile_natural_query(self, question):
        """
        Compile a natural language query into a DAG.
        """
        retriever_node = DAGNode("Retriever", {"query": question}, Retriever(self.memory_layers))
        generator_node = DAGNode("Generator", {"retriever": retriever_node}, Generator())
        return DAG([retriever_node, generator_node])  # Retriever -> Generator

    def _compile_one_shot(self, query):
        """
        Compile a one-shot HQL query into a DAG.
        """
        operation = "Retriever" if "RETRIEVE" in query.upper() else "Updater"
        operator_class = Retriever if operation == "Retriever" else None  # Replace None with an Updater operator
        operator_node = DAGNode(operation, {"query": query}, operator_class(self.memory_layers))
        return DAG([operator_node])

    def _compile_continuous(self, query):
        """
        Compile a continuous HQL query.
        """
        operator_node = DAGNode("ContinuousQuery", {"query": query}, None)  # Placeholder
        return DAG([operator_node])
