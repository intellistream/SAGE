from src.core.dag.dag import DAG
from src.core.dag.dag_node import DAGNode
from src.core.operators.retriever import Retriever
from src.core.operators.generator import Generator
from src.core.operators.spout import Spout
from src.core.operators.summarizer import Summarizer
from src.core.query_engine.query_optimizer import QueryOptimizer


class QueryCompiler:
    def __init__(self, memory_layers):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_layers: Dictionary containing memory layer instances.
        """
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

    def compile_natural_query(self, natural_query):
        """
        Compile a natural language query into a DAG.
        :param natural_query: The natural language query string.
        :return: DAG instance.
        """
        # Step 1: Parse the question to understand the user's intent
        intent = self._parse_query(natural_query)

        # Step 2: Create the DAG and add the Spout node
        dag = DAG()
        spout_node = DAGNode(
            name="Spout",
            operator=Spout(input_data=natural_query),
            is_spout=True
        )
        dag.add_node(spout_node)

        # Step 3: Add downstream nodes based on intent
        if intent == "information_retrieval":
            retriever_node = DAGNode(
                name="Retriever",
                operator=Retriever(self.memory_layers.get("long_term")),  # Use long-term memory for retrieval
                config={"k": 5}  # Example: retrieving top-5 results
            )
            dag.add_node(retriever_node)
            dag.add_edge(spout_node, retriever_node)
        elif intent == "summarization":
            retriever_node = DAGNode(
                name="Retriever",
                operator=Retriever(self.memory_layers.get("long_term")),  # Use long-term memory
                config={"k": 5}
            )
            summarizer_node = DAGNode(
                name="Summarizer",
                operator=Summarizer(),
                config={"summary_length": 100}  # Example additional parameter
            )
            dag.add_node(retriever_node)
            dag.add_node(summarizer_node)
            dag.add_edge(spout_node, retriever_node)
            dag.add_edge(retriever_node, summarizer_node)
        elif intent == "question_answering":
            retriever_node = DAGNode(
                name="Retriever",
                operator=Retriever(self.memory_layers.get("long_term")),  # Use long-term memory
                config={"k": 3}  # Retrieve top-3 relevant items
            )
            generator_node = DAGNode(
                name="Generator",
                operator=Generator(),
                config={"max_length": 50}  # Example additional parameter
            )
            dag.add_node(retriever_node)
            dag.add_node(generator_node)
            dag.add_edge(spout_node, retriever_node)
            dag.add_edge(retriever_node, generator_node)
        else:
            raise ValueError(f"Unsupported query type: {intent}")

        return dag

    def _parse_query(self, natural_query):
        """
        A basic NLP-based method to extract intent from a query.
        TODO: Replace with an advanced NLP pipeline.
        :param natural_query: The query to process.
        :return: The detected intent.
        """
        if "summarize" in natural_query.lower():
            return "summarization"
        elif "who" in natural_query.lower() or "is" in natural_query.lower():
            return "information_retrieval"
        else:
            return "question_answering"  # Default intent for other types

    def _compile_one_shot(self, query):
        """
        Compile a one-shot HQL query into a DAG.
        :param query: HQL query string.
        :return: DAG instance.
        """
        dag = DAG()
        operation = "Retriever" if "RETRIEVE" in query.upper() else None
        if not operation:
            raise ValueError("Unsupported HQL operation.")
        retriever_node = DAGNode(
            name="Retriever",
            operator=Retriever(self.memory_layers.get("long_term")),  # Use long-term memory
            is_spout=True
        )
        dag.add_node(retriever_node)
        return dag

    def _compile_continuous(self, query):
        """
        Compile a continuous HQL query into a DAG.
        :param query: HQL query string.
        :return: DAG instance.
        """
        dag = DAG()
        operator_node = DAGNode("ContinuousQuery", None, is_spout=True)
        dag.add_node(operator_node)
        return dag
