import time
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io.source import FileSource
from sage.libs.io.sink import TerminalSink, FileSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.libs.dataflow.splitter import Splitter
from sage.libs.dataflow.merger import Merger
from sage.utils.config_loader import load_config


def pipeline_run(config):
    """Create and run the data processing pipeline.
    
    Args:
        config (dict): The configuration parameters loaded from the config file.
    """
    try:
        env = LocalEnvironment()
        env.set_memory(config=None)  # Set environment memory if required.

        # Constructing the data processing pipeline
        response_stream = (
            env.from_source(FileSource, config["source"])
            .map(DenseRetriever, config["retriever"])
            .map(QAPromptor, config["promptor"])
            .map(OpenAIGenerator, config["generator"]["local"])
        )

        # Split response into true/false streams
        true_stream = response_stream.map(Splitter)
        true_stream.sink(FileSink, config["sink_true"])

        # Process false stream separately
        false_stream = true_stream.side_output("false")
        false_stream.sink(FileSink, config["sink_false"])

        # Connecting true and false streams for further processing
        connected_streams = true_stream.connect(false_stream)

        # Merge the streams before output
        merged_stream = connected_streams.map(Merger)
        merged_stream.sink(TerminalSink, config["sink_terminal"])

        # Submit and run the pipeline
        env.submit()
        

        # Optional: Wait for 10 seconds before ending the pipeline (if necessary)
        time.sleep(10)

    except Exception as e:
        print(f"An error occurred while running the pipeline: {e}")
        raise


if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv(override=False)

    # Load configuration from the YAML file
    config = load_config("config_multiplex.yaml")

    # Run the pipeline
    pipeline_run(config)
