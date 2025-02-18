import logging
import time

from src.core.neuromem.memory.utils import initialize_memory_manager
from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.utils.logger import configure_logging
from src.core.query_engine.query_execution.query_queue import QueryQueue

def run_debug_pipeline(input_text, memory_manager):
    """
    Runs the entire pipeline for a single input, from compilation to execution.
    :param input_text: The query or natural language input to process.
    :param memory_manager: The initialized memory manager for memory layers.
    """
    try:
        # Initialize query components
        compiler = QueryCompiler(memory_manager)
        executor = QueryExecutor(memory_manager)

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
    # Initialize memory layers
    memory_manager = initialize_memory_manager()

    try:

        # Initialize the query queue
        query_queue = QueryQueue(memory_manager, run_debug_pipeline, max_workers=1)

        # Define test inputs for debugging
        test_inputs = [
            "What is the Lisa? First Round",  # Natural language query for information retrieval
            "What is the Lisa? Second Round",  # Natural language query for information retrieval
            "What is the Lisa? Third Round",  # Natural language query for information retrieval
            # "Summarize the contexts you have loaded.",  # Natural language query for summarization
            # "EXECUTE RETRIEVE key=value",  # HQL query for one-shot execution
            # "REGISTER RETRIEVE key=value"  # HQL query for continuous execution
        ]

        # Simulate incoming queries with random delays
        for test_input in test_inputs:
            time.sleep(0.5)  # Simulating arrival delay
            query_queue.add_query(test_input)

        # Wait for queue to process all queries
        query_queue.query_queue.join()

        # Flush STM to LTM after session ending
        logging.info(f"Flushing session context to LTM")
        memory_manager.flush_stm_to_ltm()

        # Define test inputs for debugging
        test_inputs = [
            "What is the Lisa? Fourth Round, New session",  # Natural language query for information retrieval
        ]

        for test_input in test_inputs:
            query_queue.add_query(test_input)

        query_queue.query_queue.join()  # Ensure all queries are processed

    finally:
        # Reset memory layers after testing
        logging.info("Resetting memory layers...")
        for layer_name, layer in memory_manager.get_memory_layers().items():
            layer.clean()
        logging.info("Memory layers reset successfully.")
