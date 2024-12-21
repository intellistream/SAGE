import logging
from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.core.neuromem.memory.utils import initialize_memory_layers
from src.utils.logger import configure_logging

def run_debug_pipeline(input_text, memory_layers):
    """
    Runs the entire pipeline for a single input, from compilation to execution.
    :param input_text: The query or natural language input to process.
    :param memory_layers: The initialized memory layers.
    """
    try:
        # Initialize query components
        compiler = QueryCompiler(memory_layers)
        executor = QueryExecutor(memory_layers)

        # Compile the query
        logging.info(f"Compiling input: {input_text}")
        dag, execution_type = compiler.compile(input_text)
        logging.info(f"Compiled DAG: {dag}")

        # Execute the query
        if execution_type == "one_shot":
            logging.info("Executing one-shot query...")
            result = executor.execute(dag)
            logging.info(f"Execution result: {result}")
        elif execution_type == "continuous":
            logging.info("Registering continuous query...")
            executor.register_continuous_query(dag)
            logging.info("Continuous query registered successfully.")
        else:
            raise ValueError(f"Unknown execution type: {execution_type}")

    except Exception as e:
        logging.error(f"Error during processing: {str(e)}")


if __name__ == "__main__":
    # Configure logging
    configure_logging(level=logging.INFO)

    from huggingface_hub import login

    login(token="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")

    # Initialize memory layers
    memory_layers = initialize_memory_layers()

    try:
        # Define test inputs for debugging
        test_inputs = [
            "What is the Everest?",  # Natural language query for information retrieval
            # "Summarize the contexts you have loaded.",  # Natural language query for summarization
            # "EXECUTE RETRIEVE key=value",  # HQL query for one-shot execution
            # "REGISTER RETRIEVE key=value"  # HQL query for continuous execution
        ]

        # Run each input through the debug pipeline
        for test_input in test_inputs:
            print(f"\nProcessing test input: {test_input}")
            run_debug_pipeline(test_input, memory_layers)

    finally:
        # Reset memory layers after testing
        logging.info("Resetting memory layers...")
        for layer_name, layer in memory_layers.items():
            layer.clean()
        logging.info("Memory layers reset successfully.")
