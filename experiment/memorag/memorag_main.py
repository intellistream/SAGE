import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import logging
from src.core.query_engine.query_compilation.query_state import QueryState
from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.core.neuromem.memory.utils import initialize_memory_manager
from src.utils.logger import configure_logging, get_logger
from src.utils.query import Query
from src.utils.file_path import QUERY_FILE

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
    log_dir = "/workspace/experiment/memorag/log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "debug_pipeline.log")
    configure_logging(level=logging.INFO, log_file=log_file)
    logger = get_logger(__name__)

    memory_manager = initialize_memory_manager()

    try:
        query = Query(QUERY_FILE)
        for dialogue_index, turn, q, r in query.iter_all_dialogues():
            print(f"\nProcessing dialogue-{dialogue_index} query-{turn}: {q}")
            current_query = QueryState(q)
            print(f"\nProcessing test input: {current_query.natural_query}")
            run_debug_pipeline(current_query, memory_manager)

            if turn == query.dialogue_info[dialogue_index]["dialogue_length"] - 1:
                logging.info(f"Flushing session context to LTM")
                memory_manager.flush_stm_to_ltm()

    finally:
        # Reset memory layers after testing
        logging.info("Resetting memory layers...")
        for layer_name, layer in memory_manager.get_memory_layers().items():
            layer.clean()
        logging.info("Memory layers reset successfully.")
