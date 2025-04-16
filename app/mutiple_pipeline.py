import logging
import sage
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.reranker import BGEReranker
import time
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink, FileSink
from sage.api.operator.operator_impl.writer import SimpleWriter
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator.operator_impl.sink import TerminalSink
from typing import Tuple, List
import yaml
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/config.yaml')
logging.basicConfig(level=logging.INFO)

# ---- Initialize and Submit Pipeline ----
# Create a new pipeline instance
manager = sage.memory.init_default_manager()

# Create memory table
memory = sage.memory.create_table("long_term_memory", manager=manager)

pipeline = sage.pipeline.Pipeline("generate_pipeline")
# Step 1: Define the data source (e.g., incoming user query)
query_stream = pipeline.add_source(FileSource(config))
# Step 2: Use a retriever to fetch relevant chunks from vector memory
query_and_chunks_stream = query_stream.retrieve(SimpleRetriever(config))
# Step 3: Construct a prompt by combining the query and the retrieved chunks
prompt_stream = query_and_chunks_stream.construct_prompt(QAPromptor(config))
# Step 4: Generate the final response using a language model
response_stream = prompt_stream.generate_response(OpenAIGenerator(config))
sink_stream = response_stream.sink(FileSink(config))

# Submit the pipeline to the SAGE runtime
pipeline.submit(config={"is_long_running": True, "duration": 1, "frequency": 30})
time.sleep(5)
pipeline.stop()
time.sleep(5)

