import logging
import pytest
from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.core.llh.memory import initialize_memory_layers
from src.utils.logger import configure_logging


@pytest.fixture(scope="module")
def memory_layers():
    """
    Fixture to initialize and reset memory layers for testing.
    """
    # Initialize memory layers
    layers = initialize_memory_layers()
    yield layers

    # Clean up memory layers after testing
    logging.info("Resetting memory layers...")
    for layer_name, layer in layers.items():
        layer.clean()
    logging.info("Memory layers reset successfully.")


@pytest.mark.parametrize("input_text,expected_execution_type", [
    ("What is the Eiffel Tower?", "one_shot"),  # Test case for information retrieval
    ("Summarize Sanguo", "one_shot"),          # Test case for summarization
])
def test_pipeline(input_text, expected_execution_type, memory_layers):
    """
    Test the entire pipeline for a single input, from compilation to execution.
    :param input_text: The query or natural language input to process.
    :param expected_execution_type: Expected execution type for the input.
    :param memory_layers: Memory layers fixture.
    """
    try:
        # Configure logging for the test
        configure_logging(level=logging.DEBUG)

        # Initialize query components
        compiler = QueryCompiler(memory_layers)
        executor = QueryExecutor(memory_layers)

        # Compile the query
        logging.info(f"Compiling input: {input_text}")
        dag, execution_type = compiler.compile(input_text)

        assert execution_type == expected_execution_type, (
            f"Expected execution type '{expected_execution_type}', but got '{execution_type}'."
        )

        logging.info(f"Compiled DAG: {dag}")

        # Execute the query
        if execution_type == "one_shot":
            logging.info("Executing one-shot query...")
            result = executor.execute(dag)
            logging.info(f"Execution result: {result}")
            assert result is not None, "Execution result should not be None."
        elif execution_type == "continuous":
            logging.info("Registering continuous query...")
            executor.register_continuous_query(dag)
            logging.info("Continuous query registered successfully.")
        else:
            raise ValueError(f"Unknown execution type: {execution_type}")

    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
