import time
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.io_utils.sink import TerminalSink, FileSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever
from sage.common.utils.config.loader import load_config


def pipeline_run(config):
    """Create and run the data processing pipeline.
    
    Args:
        config (dict): The configuration parameters loaded from the config file.
    """
    try:
        env = LocalEnvironment()
        #env.set_memory(config=None)  # Set environment memory if required.

        # Constructing the data processing pipeline
        response_stream = (
            env.from_source(FileSource, config["source"])
            .map(ChromaRetriever, config["retriever"])
            .map(QAPromptor, config["promptor"])
            .map(OpenAIGenerator, config["generator"]["vllm"])
        )

        # Create separate streams for True and False responses using filter
        true_stream = response_stream.filter(lambda data: str(data[1]).lower().strip().startswith('true'))
        false_stream = response_stream.filter(lambda data: str(data[1]).lower().strip().startswith('false'))

        # Send filtered streams to their respective files
        true_stream.map(lambda data: f"TRUE: {data[0]} -> {data[1]}").sink(FileSink, config["sink_true"])
        false_stream.map(lambda data: f"FALSE: {data[0]} -> {data[1]}").sink(FileSink, config["sink_false"])

        # Send all responses to terminal for monitoring
        response_stream.map(lambda data: f"[RESULT] Q: {data[0]}\nA: {data[1]}\n").sink(TerminalSink, config["sink_terminal"])

        # Submit and run the pipeline
        env.submit()
        

        # Optional: Wait for 10 seconds before ending the pipeline (if necessary)
        time.sleep(10)

    except Exception as e:
        print(f"An error occurred while running the pipeline: {e}")
        raise


if __name__ == '__main__':
    import os
    # Load environment variables from .env file
    load_dotenv(override=False)

    # Load configuration from the YAML file
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_multiplex.yaml")
    config = load_config(config_path)

    # Run the pipeline
    pipeline_run(config)
