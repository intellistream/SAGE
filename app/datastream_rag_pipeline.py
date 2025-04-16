from sympy.multipledispatch.dispatcher import source
import logging
import sage
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.reranker import BGEReranker
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink
from sage.api.operator.operator_impl.writer import SimpleWriter
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from typing import Tuple, List
import yaml

logging.basicConfig(level=logging.DEBUG)
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('config.yaml')
# # ---- Initialize Memory ----
# # Define short-term memory (e.g., for current session context)
# sage.memory.create_table(
#     memory_table_name="short_term_memory",
#     memory_table_backend="kv_store.rocksdb"
# )
#
# # Define long-term memory (e.g., for persistent knowledge base)
# sage.memory.create_table(
#     memory_table_name="long_term_memory",
#     memory_table_backend="vector_db.candy",
#     embedding_model=sage.model.apply_embedding_model("default")
# )
#
# # Define dynamic contextual memory (e.g., for adapting memory per request context)
# sage.memory.create_table(
#     memory_table_name="dynamic_contextual_memory", # Predefine DCM. DCM API, ingest from external, external_memory_write_operator
#     memory_table_backend="vector_db.candy",
#     embedding_model=sage.model.apply_embedding_model("default")
# )


# # ---- Implement Operators ----
# # Text source operator: reads user queries from a Kafka topic
# class TextSource(sage.operator.SourceFunction):
#     def __init__(self):
#         super().__init__()
#
#     # Produces a query from text
#     def execute(self, context=None) -> str:
#         # TODO: Mock the original example
#         return "What is the Lisa?"
#
#
# # Retriever operator: embeds the query and retrieves top-k relevant chunks from memory
# class SimpleRetriever(sage.operator.RetrieverFunction):
#     def __init__(self):
#         super().__init__()
#         # Initialize the embedding_model model for vectorization
#         self.embedding_model = sage.model.apply_embedding_model("default")
#         # Connect to multiple memory collections (STM, LTM, DCM)
#         # self.memory_collections = sage.memory.connect(
#         #     "short_term_memory", "long_term_memory", "dynamic_contextual_memory"
#         # )
#         self.stm = sage.memory.connect("short_term_memory")
#         self.ltm = sage.memory.connect("long_term_memory")
#         self.dcm = sage.memory.connect("dynamic_contextual_memory")
#         # Define the retrieval function (e.g., weighted aggregation, similarity ranking)
#         self.retrieval_func = sage.memory.retrieve_func
#
#     # Returns both the original query and the retrieved memory chunks
#     def execute(self, input_query: str, context=None) -> Tuple[str, List[str]]:
#         embedding = self.embedding_model.embed(input_query)
#         chunks = self.stm.retrieve(embedding, self.retrieval_func)
#         return input_query, chunks
#
#
# # Prompt constructor: takes the query and chunks and builds a complete prompt
# class SimplePromptConstructor(sage.operator.PromptFunction):
#     def __init__(self):
#         super().__init__()
#         # Initialize a prompt construction logic (template-based, few-shot, etc.)
#         self.prompt_constructor = self.set_prompt_constructor("default")
#
#     # Constructs the prompt and returns (query, prompt) tuple
#     def execute(self, inputs: Tuple[str, List[str]], context=None) -> Tuple[str, str]:
#         query, chunks = inputs
#         return query, self.prompt_constructor.construct(query, chunks)
#
#
# # Generator operator: generates a final response from the prompt using an LLM
# class LlamaGenerator(sage.operator.GeneratorFunction):
#     def __init__(self):
#         super().__init__()
#         # Load or configure a local or remote LLM (e.g., llama_8b)
#         self.model = sage.model.apply_generator_model("llama_8b")
#
#     # Generates the model's response given a prompt string
#     def execute(self, combined_prompt: str, context=None) -> str:
#         return self.model.generate(combined_prompt)


# ---- Initialize and Submit Pipeline ----
# Create a new pipeline instance
manager = sage.memory.init_default_manager()

# Create memory table
memory = sage.memory.create_table("my_memory", manager)


pipeline = sage.pipeline.Pipeline("example_pipeline")

# Step 1: Define the data source (e.g., incoming user query)
query_stream = pipeline.add_source(FileSource(config))

# Step 2: Use a retriever to fetch relevant chunks from vector memory
query_and_chunks_stream = query_stream.retrieve(SimpleRetriever(config))

# Step 3: Construct a prompt by combining the query and the retrieved chunks
prompt_stream = query_and_chunks_stream.construct_prompt(QAPromptor(config))

# Step 4: Generate the final response using a language model
response_stream = prompt_stream.generate_response(OpenAIGenerator(config))

# response_stream.sink(SinkFunction())

# Submit the pipeline to the SAGE runtime
pipeline.submit(config={"is_long_running": True, "duration": 1, "frequency": 30})

