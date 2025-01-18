import logging
import json
from src.core.query_engine.query_compilation.query_compiler import QueryCompiler
from src.core.query_engine.query_execution.query_executor import QueryExecutor
from src.core.neuromem.memory.utils import initialize_memory_layers
from src.utils.logger import configure_logging
from src.utils.file_path import KG_RESULTS_FILE


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

def run_kg_pipeline(input_text, memory_layers):
    """
        input_text: (query, query_time). 
        search_result: List of page snippets from search results.
    """
    try:
        query, query_time = input_text
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


def process_json_file(file_path):
    """
    Process a JSON file containing search interactions.
    """
    interactions = []  # 用于存储所有交互数据的列表

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                interaction = json.loads(line)
                interactions.append(interaction)  
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {str(e)}")

    return interactions  


if __name__ == "__main__":
    
    configure_logging(level=logging.INFO)
    try:
        all_interactions = process_json_file('data/CRAG/task_1_top_200.jsonl')

        if all_interactions:
            # 取出其中一个交互数据
            first_interaction = all_interactions[0]

            answer = first_interaction.get('answer')
            query = first_interaction.get('query')
            logging.info(f"Gold Answer: {answer}")
            query_time = first_interaction.get('query_time')
            search_results = first_interaction.get('search_results', [])

            # HACK: Web pages temporarily stored in the database
            memory_layers = initialize_memory_layers(query, query_time, search_results)

            run_kg_pipeline((query, query_time), memory_layers)

            # Reset KG results file
            with open(KG_RESULTS_FILE, "w", encoding="utf-8") as file:
                pass  
            logging.info(f"KG results File has been emptied.")
        else:
            logging.info("No interactions found in the file.")
    except Exception as e:
        logging.error(f"Error during processing: {str(e)}")
    finally:
        # Reset memory layers after testing
        logging.info("Resetting memory layers...")
        for layer_name, layer in memory_layers.items():
            layer.clean()
        logging.info("Memory layers reset successfully.")
    


