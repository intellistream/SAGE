import logging
from src.core.query_engine.query_compiler import QueryCompiler
from src.core.query_engine.query_executor import QueryExecutor
from src.utils.logger import configure_logging


def interactive_console(compiler, executor):
    """
    Start an interactive console for user interaction.
    """
    logging.info("Starting LLH Interactive Console")
    print("Welcome to the LLH Interactive Console")
    print("You can:\n  - Ask natural language questions\n  - Submit EXECUTE or REGISTER queries in HQL\n  - Type 'exit' to quit")

    while True:
        user_input = input("\n>>> ").strip()

        if user_input.lower() == "exit":
            logging.info("Exiting LLH Interactive Console")
            print("Goodbye!")
            break

        try:
            # Compile the query or natural language input
            dag, execution_type = compiler.compile(user_input)

            # Execute the DAG based on its type
            if execution_type == "one_shot":
                result = executor.execute(dag)
                print(f"Result: {result}")
            elif execution_type == "continuous":
                executor.register_continuous_query(dag)
                print(f"Continuous query registered successfully.")
            else:
                raise ValueError("Unknown execution type.")

        except Exception as e:
            logging.error(f"Error processing input: {str(e)}")
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    from src.core.memory.short_term_memory import ShortTermMemory
    from src.core.memory.long_term_memory import LongTermMemory
    from src.utils.helpers import initialize_memory_layers

    # Configure logging
    configure_logging()

    # Initialize memory layers
    memory_layers = initialize_memory_layers()

    # Initialize query components
    compiler = QueryCompiler(memory_layers)
    executor = QueryExecutor(memory_layers)

    # Start the interactive console
    interactive_console(compiler, executor)
