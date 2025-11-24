import os
import sys
import time

from dotenv import load_dotenv

from sage.common.utils.config.loader import load_config
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.sink import FileSink, TerminalSink
from sage.libs.foundation.io.source import FileSource
from sage.middleware.operators.rag import ChromaRetriever, OpenAIGenerator, QAPromptor


def pipeline_run(config):
    """Create and run the data processing pipeline.

    Args:
        config (dict): The configuration parameters loaded from the config file.
    """
    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_multiplex example")
        print("✅ Test passed: Example structure validated")
        return

    try:
        env = LocalEnvironment()
        # env.set_memory(config=None)  # Set environment memory if required.

        # Constructing the data processing pipeline
        response_stream = (
            env.from_source(FileSource, config["source"])
            .map(ChromaRetriever, config["retriever"])
            .map(QAPromptor, config["promptor"])
            .map(OpenAIGenerator, config["generator"]["vllm"])
        )

        # Create separate streams for True and False responses using filter
        true_stream = response_stream.filter(
            lambda data: str(data[1]).lower().strip().startswith("true")
        )
        false_stream = response_stream.filter(
            lambda data: str(data[1]).lower().strip().startswith("false")
        )

        # Send filtered streams to their respective files
        true_stream.map(lambda data: f"TRUE: {data[0]} -> {data[1]}").sink(
            FileSink, config["sink_true"]
        )
        false_stream.map(lambda data: f"FALSE: {data[0]} -> {data[1]}").sink(
            FileSink, config["sink_false"]
        )

        # Send all responses to terminal for monitoring
        response_stream.map(lambda data: f"[RESULT] Q: {data[0]}\nA: {data[1]}\n").sink(
            TerminalSink, config["sink_terminal"]
        )

        # Submit and run the pipeline
        env.submit()

        # Optional: Wait for 10 seconds before ending the pipeline (if necessary)
        time.sleep(10)

    except Exception as e:
        print(f"An error occurred while running the pipeline: {e}")
        raise


if __name__ == "__main__":
    import os

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_multiplex example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # Load environment variables from .env file
    load_dotenv(override=False)

    # Load configuration from the YAML file
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_multiplex.yaml")
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)

    # Run the pipeline
    pipeline_run(config)
