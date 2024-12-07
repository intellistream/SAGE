from src.core.dag.dag import DAG
from src.core.dag.dag_node import DAGNode
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
            dag, execution_type = self._compile_one_shot(input_text), "one_shot"
        elif input_text.upper().startswith("REGISTER"):
            dag, execution_type = self._compile_continuous(input_text), "continuous"
        else:
            dag, execution_type = self.compile_natural_query(input_text), "one_shot"

        # Optimize the DAG
        optimized_dag = self.optimizer.optimize(dag)
        return optimized_dag, execution_type

    def compile_natural_query(self, question):
        """
        Compile a natural language query into a DAG.
        :param question: The natural language query string.
        :return: DAG instance.
        """
        dag = DAG()
        retriever_node = DAGNode("Retriever", Retriever(self.memory_layers), is_spout=True)
        generator_node = DAGNode("Generator", Generator())

        # Add nodes and edges
        dag.add_node(retriever_node)
        dag.add_node(generator_node)
        dag.add_edge(retriever_node, generator_node)

        return dag

    def _compile_one_shot(self, query):
        """
        Compile a one-shot HQL query into a DAG.
        :param query: HQL query string.
        :return: DAG instance.
        """
        dag = DAG()
        operation = "Retriever" if "RETRIEVE" in query.upper() else "Updater"
        operator_class = Retriever if operation == "Retriever" else None  # Replace with actual Updater class
        operator_node = DAGNode(operation, operator_class(self.memory_layers), is_spout=True)

        dag.add_node(operator_node)

        return dag

    def _compile_continuous(self, query):
        """
        Compile a continuous HQL query into a DAG.
        :param query: HQL query string.
        :return: DAG instance.
        """
        dag = DAG()
        operator_node = DAGNode("ContinuousQuery", None, is_spout=True)  # Placeholder for continuous operator

        dag.add_node(operator_node)

        return dag
