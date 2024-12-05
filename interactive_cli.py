import logging
from src.core.query_engine.query_compiler import QueryCompiler
from src.core.query_engine.query_executor import QueryExecutor
from src.core.query_engine.query_optimizer import QueryOptimizer
from src.utils.logger import configure_logging

def interactive_console(compiler, executor, optimizer):
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
            if user_input.upper().startswith("EXECUTE") or user_input.upper().startswith("REGISTER"):
                # Compile HQL queries into DAG
                query_plan = compiler.compile_hql(user_input)
            else:
                # Compile natural language queries into DAG
                query_plan = compiler.compile_natural_query(user_input)

            # Optimize the DAG
            optimized_plan = optimizer.optimize(query_plan)

            # Execute the optimized DAG
            result = executor.execute(optimized_plan)
            print(f"Result: {result}")

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
    optimizer = QueryOptimizer()
    executor = QueryExecutor(memory_layers)

    # Start the interactive console
    interactive_console(compiler, executor, optimizer)
