import logging
from src.core.query_engine.query_compiler import QueryCompiler
from src.core.query_engine.query_executor import QueryExecutor
from src.core.memory.utils import initialize_memory_layers
from src.utils.logger import configure_logging


def run_debug_pipeline(input_text):
    """
    Runs the entire pipeline for a single input, from compilation to execution.
    :param input_text: The query or natural language input to process.
    """
    try:
        # Initialize logging and memory layers
        configure_logging(level=logging.DEBUG)
        memory_layers = initialize_memory_layers()

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
    # Define test inputs for debugging
    test_inputs = [
        "who is putin?",  # Natural language query for information retrieval
        # "summarize sanguo",  # Natural language query for summarization
        # "EXECUTE RETRIEVE key=value",  # HQL query for one-shot execution
        # "REGISTER RETRIEVE key=value"  # HQL query for continuous execution
    ]

    # Run each input through the debug pipeline
    for test_input in test_inputs:
        print(f"\nProcessing test input: {test_input}")
        run_debug_pipeline(test_input)
