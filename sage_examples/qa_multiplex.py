import time
from dotenv import load_dotenv

from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink, FileSink
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_common_funs.dataflow.splitter import Splitter
from sage_common_funs.dataflow.merger import Merger
from sage_utils.config_loader import load_config


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
            .map(OpenAIGenerator, config["generator"])
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
        env.run_streaming()

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
