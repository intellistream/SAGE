import logging
import queue
import threading
import time

from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.core.neuromem.memory.utils import initialize_memory_manager
from src.utils.logger import configure_logging


class QueryQueue:
    """
    A queue to manage query requests and process them asynchronously.
    """

    def __init__(self, memory_manager, max_workers=2):
        """
        Initialize the query queue.
        :param memory_manager: The memory manager instance.
        :param max_workers: Number of worker threads to process queries.
        """
        self.query_queue = queue.Queue()
        self.memory_manager = memory_manager
        self.workers = []
        self.max_workers = max_workers
        self.stop_event = threading.Event()

        # Start worker threads
        for _ in range(max_workers):
            worker = threading.Thread(target=self.process_queries, daemon=True)
            worker.start()
            self.workers.append(worker)

    def add_query(self, query):
        """
        Add a new query to the queue with a timestamp.
        :param query: The input query string.
        """
        timestamp = time.time()  # Record time query enters queue
        self.query_queue.put((query, timestamp))
        logging.info(f"Query added to queue: {query}")

    def process_queries(self):
        """
        Worker function that processes queries from the queue.
        """
        while not self.stop_event.is_set():
            try:
                # Retrieve query and timestamp
                query, timestamp = self.query_queue.get(timeout=1)
                start_time = time.time()  # Timestamp before processing
                logging.info(f"Processing query: {query}")

                # Run the pipeline
                run_debug_pipeline(query, self.memory_manager)

                end_time = time.time()  # Timestamp after processing
                queue_time = start_time - timestamp  # Time spent in queue
                total_latency = end_time - timestamp  # Total end-to-end latency

                logging.info(f"Query completed: {query} | Queue Wait Time: {queue_time:.2f}s | Total Latency: {total_latency:.2f}s")
                self.query_queue.task_done()

            except queue.Empty:
                continue  # Continue waiting for new queries

    def shutdown(self):
        """
        Stop the workers gracefully.
        """
        self.stop_event.set()
        for worker in self.workers:
            worker.join()
        logging.info("Query queue workers shut down.")

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
        query_queue = QueryQueue(memory_manager, max_workers=1)

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
