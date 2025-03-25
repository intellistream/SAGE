import logging
import queue
import threading
import time


class QueryQueue:
    """
    A queue to manage query requests and process them asynchronously.
    """

    def __init__(self, memory_manager, process_fn, max_workers=2):
        """
        Initialize the query queue.
        :param memory_manager: The memory manager instance.
        :param process_fn: Function to process each query (e.g., run_debug_pipeline).
        :param max_workers: Number of worker threads to process queries.
        """
        self.query_queue = queue.Queue()
        self.memory_manager = memory_manager
        self.workers = []
        self.max_workers = max_workers
        self.stop_event = threading.Event()
        self.process_fn = process_fn

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
                self.process_fn(query, self.memory_manager)

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
