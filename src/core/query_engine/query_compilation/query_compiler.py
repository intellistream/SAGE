from src.core.query_engine.dag.continous_dag_node import ContinuousDAGNode
from src.core.query_engine.dag.dag import DAG
from src.core.query_engine.operators.retriever import Retriever
from src.core.query_engine.operators.spout import Spout
from src.core.query_engine.dag.one_shot_dag_node import OneShotDAGNode
from src.core.query_engine.query_compilation.pipeline_manager import PipelineManager
from src.core.query_engine.query_optimization.query_optimizer import QueryOptimizer

"""
Tasks of QueryCompiler

1. Syntax Parsing:
    Transform the user query into a base DAG structure.
2. Basic Intent Analysis:
    Determine whether the query is a retrieval, summarization, or generation task.
3. Straightforward Node Insertion:
    Add DAG nodes in an order that reflects logical query execution
"""
class QueryCompiler:
    def __init__(self, memory_manager):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        """
        self.memory_manager = memory_manager
        self.optimizer = QueryOptimizer()

    def compile(self, input_text):
        """
        Compile a query or natural language input into a DAG.
        :param input_text: User-provided query or question.
        :return: Optimized DAG and execution type.
        """
        # memorag 实验备注 before
        # if input_text.upper().startswith("EXECUTE"):
        #     dag, execution_type = self._compile_one_shot(input_text), "one_shot"
        # elif input_text.upper().startswith("REGISTER"):
        #     dag, execution_type = self._compile_continuous(input_text), "continuous"
        # else:
        #     dag, execution_type = self.compile_natural_query(input_text), "one_shot"
        # memorag 实验备注 after
        dag, execution_type = self.compile_natural_query(input_text), "one_shot"

        # Optimize the DAG
        optimized_dag = self.optimizer.optimize(dag)
        return optimized_dag, execution_type

    def add_one_shot_spout(self, natural_query):
        """
        Initialize a DAG with a Spout node.
        :param natural_query: The natural language query string.
        :return: Initialized DAG with a Spout node.
        """
        dag = DAG()
        spout_node = OneShotDAGNode(
            name="Spout",
            operator=Spout(input_data=natural_query),
            is_spout=True
        )
        dag.add_node(spout_node)
        return dag

    def add_continous_spout(self, natural_query):
        """
        Initialize a DAG with a Spout node.
        :param natural_query: The natural language query string.
        :return: Initialized DAG with a Spout node.
        """
        dag = DAG()
        spout_node = ContinuousDAGNode(
            name="Spout",
            operator=Spout(input_data=natural_query),
            is_spout=True
        )
        dag.add_node(spout_node)
        return dag

    def compile_natural_query(self, natural_query):
        """
        Compile a natural language query into a DAG.
        :param natural_query: The natural language query string.
        :return: DAG instance.
        """
        # Step 1: Parse the question to understand the user's intent
        intent = self._parse_query(natural_query.natural_query)

        # Step 2: Initialize the DAG and add the Spout node
        dag = self.add_one_shot_spout(natural_query)

        # Step 3: Use PipelineManager to add the pipeline
        pipeline_manager = PipelineManager(self.memory_manager)
        spout_node = dag.get_node_by_name("Spout")

        if intent == "summarization":
            pipeline_manager.add_summarization_pipeline(dag, spout_node)
        elif intent == "question_answering":
            pipeline_manager.add_question_answering_pipeline(dag, spout_node)
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
        # if "summarize" in natural_query.lower():
        #     return "summarization"
        # else:
        #     return "question_answering"  # Default intent for other types
        return "question_answering"

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
        retriever_node = OneShotDAGNode(
            name="Retriever",
            operator=Retriever(self.memory_manager),  # Use long-term memory
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
        operator_node = ContinuousDAGNode("ContinuousQuery", None, is_spout=True)
        dag.add_node(operator_node)
        return dag
