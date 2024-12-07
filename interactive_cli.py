import logging
from src.core.query_engine.query_compiler import QueryCompiler
from src.core.query_engine.query_executor import QueryExecutor
from src.utils.logger import configure_logging
from src.utils.helpers import initialize_memory_layers


def display_welcome_message():
    """
    Display the welcome message for the console.
    """
    logging.info("Starting LLH Interactive Console")
    print("Welcome to the LLH Interactive Console")
    print("You can:\n  - Ask natural language questions\n  "
          "- Submit EXECUTE or REGISTER queries in HQL\n  - Type 'exit' to quit")

def process_user_input(user_input, compiler, executor):
    """
    Process the user input by compiling and executing the query.
    :param user_input: The input provided by the user.
    :param compiler: Instance of QueryCompiler to compile the query.
    :param executor: Instance of QueryExecutor to execute the compiled query.
    """
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


def interactive_console(compiler, executor):
    """
    Start an interactive console for user interaction.
    :param compiler: Instance of QueryCompiler to compile queries.
    :param executor: Instance of QueryExecutor to execute queries.
    """
    display_welcome_message()

    while True:
        user_input = input("\n>>> ").strip()

        if user_input.lower() == "exit":
            logging.info("Exiting LLH Interactive Console")
            print("Goodbye!")
            break

        process_user_input(user_input, compiler, executor)


def main():
    """
    Main entry point for the program.
    """
    # Configure logging
    configure_logging()

    # Initialize memory layers
    memory_layers = initialize_memory_layers()

    # Initialize query components
    compiler = QueryCompiler(memory_layers)
    executor = QueryExecutor(memory_layers)

    # Start the interactive console
    interactive_console(compiler, executor)


if __name__ == "__main__":
    main()
