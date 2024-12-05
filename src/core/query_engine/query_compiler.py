# src/core/query_engine/query_compiler.py

from src.core.dag.dag import DAG
from src.core.dag.dag_node import DAGNode
from src.core.operators.embedder import Embedder
from src.core.operators.retriever import Retriever
from src.core.operators.generator import Generator

class QueryCompiler:
    def __init__(self, memory_layers):
        self.memory_layers = memory_layers

    def compile_hql(self, query):
        """
        Parse and compile an HQL query into a DAG.
        """
        if query.upper().startswith("EXECUTE"):
            return self._compile_one_shot(query)
        elif query.upper().startswith("REGISTER"):
            return self._compile_continuous(query)
        else:
            raise ValueError("Invalid HQL query. Must start with EXECUTE or REGISTER.")

    def compile_natural_query(self, question):
        """
        Compile a natural language query into a DAG.
        """
        retriever_node = DAGNode("Retriever", {"query": question}, Retriever(self.memory_layers))
        generator_node = DAGNode("Generator", {"retriever": retriever_node}, Generator())
        return DAG([embedder_node, retriever_node, generator_node]) #E->R->G

    def _compile_one_shot(self, query):
        """
        Compile a one-shot HQL query into a DAG.
        """
        # Example: Retrieve or update logic
        operation = "Retriever" if "RETRIEVE" in query.upper() else "Updater"
        operator_class = Retriever if operation == "Retriever" else None  # Replace None with an Updater operator
        operator_node = DAGNode(operation, {"query": query}, operator_class(self.memory_layers))
        return DAG([operator_node])

    def _compile_continuous(self, query):
        """
        Compile a continuous HQL query.
        """
        # Placeholder: Add actual logic for parsing and handling continuous queries
        operator_node = DAGNode("ContinuousQuery", {"query": query}, None)
        return DAG([operator_node])
