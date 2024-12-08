# LLH
```
LLH/
├── interactive_cli.py                    # Interactive CLI for natural language queries and HQL input.
├── README.md                             # Overview, setup instructions, and usage examples.
├── requirements.txt                      # Python dependencies required for the project.
├── src/                                  # Main source code directory.
│   ├── __init__.py                       # Marks this directory as a Python package.
│   ├── core/                             # Core system logic.
│   │   ├── __init__.py                   # Marks this directory as a Python package.
│   │   ├── embedding/                    # text, image data embedding.
│   │   │   ├── __init__.py               # Marks this directory as a Python package.
│   │   │   ├── text_preprocessor.py      # Embedding texts.
│   │   │   ├── multimodal_preprocessor.py # Embedding multimodal data.
│   │   ├── query_engine/                 # Query compilation, optimization, and execution.
│   │   │   ├── __init__.py               # Marks this directory as a Python package.
│   │   │   ├── query_compiler.py         # Compiles queries (HQL or natural) into DAGs.
│   │   │   ├── query_optimizer.py        # Optimizes and reorders DAGs into efficient query plans.
│   │   │   ├── query_executor.py         # Executes one-shot or continuous query plans using DAG.
│   │   ├── dag/                          # DAG components for query execution.
│   │   │   ├── __init__.py               # Marks this directory as a Python package.
│   │   │   ├── dag.py                    # DAG class for managing nodes and execution flow.
│   │   │   ├── dag_node.py               # Represents individual nodes, wrapping operators.
│   │   │   ├── dag_executor.py           # Executes the DAG for queries via the query engine.
│   │   ├── memory/                       # Hierarchical memory layer logic.
│   │   │   ├── __init__.py               # Marks this directory as a Python package.
│   │   │   ├── short_term_memory.py      # Short-term memory (KV-pairs from LLM) backed by CANDY.
│   │   │   ├── long_term_memory.py       # Long-term memory (persistent knowledge) backed by CANDY.
│   │   │   ├── ...                       # Other memory types.
│   │   ├── operators/                    # Core operators implementing functionalities.
│   │   │   ├── __init__.py               # Marks this directory as a Python package.
│   │   │   ├── base_operator.py          # Base operator
│   │   │   ├── hallucination_detection.py # Optional operator for hallucination detection and retries.
│   │   │   ├── prompter.py               # Generates dynamic prompts based on user queries.
│   │   │   ├── retriever.py              # Retrieves data from memory or external sources.
│   │   │   ├── generator.py              # Generates responses using vLLM.
│   │   │   ├── model_editor.py           # Dynamically updates the LLM model.
│   │   │   ├── docwriter.py              # Generates structured outputs or documentation.
│   ├── utils/                            # Utility functions for logging, configuration, and helpers.
│   │   ├── __init__.py                   # Marks this directory as a Python package.
│   │   ├── logger.py                     # Configures logging for the system.
│   │   ├── helpers.py                    # Common helper functions.
│   │   ├── config.py                     # Manages configuration settings.
│   ├── agents/                         # External integrations or extensions.
│   │   ├── __init__.py                   # Marks this directory as a Python package.
│   │   ├── query_agent.py                # AI agent assisting with query planning.
│   │   ├── network_agent.py              # Handles data retrieval from external sources (e.g., internet).
├── tests/
│   │   ├── ...                           #
├── deps/                                 # External dependencies and submodules.
│   ├── vLLM/                             # LLM inference submodule for generation and editing.
│   │   ├── ...                           #
│   ├── CANDY/                            # C++ vector database submodule for LLH memory.
│   │   ├── ...                           #
```

```
1. Use Case: Handling a Natural Language Query
Flow:
User enters a natural question into the CLI.
The question is compiled into a DAG using operators like Retriever and Generator.
The DAG is executed to fetch data from memory layers and generate a response using LLM (vLLM).

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_natural_query()
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Creates nodes for Retriever and Generator
    -> query_executor.py:QueryExecutor.execute()
        -> dag_executor.py:DAGExecutor.execute()
            -> retriever.py:Retriever.execute()
                -> short_term_memory.py:ShortTermMemory.retrieve()
                    -> CANDY API:VectorDB.search()
            -> generator.py:Generator.execute()
                -> vLLM API:LLMEngine.generate()
```

```
2. Use Case: Executing a One-Shot CQL Query
Flow:
User submits a EXECUTE query via CLI.
The query is parsed and compiled into a DAG.
The DAG is executed, which may modify memory layers or retrieve information.

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_cql()
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Constructs nodes based on query type
    -> query_optimizer.py:QueryOptimizer.optimize()
        -> dag.py:DAG.reorder_nodes()
    -> query_executor.py:QueryExecutor.execute()
        -> dag_executor.py:DAGExecutor.execute()
            -> retriever.py:Retriever.execute()  # If query involves retrieval
                -> long_term_memory.py:LongTermMemory.retrieve()
                    -> CANDY API:VectorDB.search()
            -> updater.py:Updater.execute()  # If query involves updates
                -> long_term_memory.py:LongTermMemory.update()
                    -> CANDY API:VectorDB.update()
```

```
3. Use Case: Registering a Continuous Query
Flow:
User submits a REGISTER query via CLI.
The query is parsed and registered for continuous execution.
The QueryExecutor launches a thread to execute the query at intervals or upon events.

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_cql()
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Constructs DAG for continuous query
    -> query_executor.py:QueryExecutor.register_continuous_query()
        -> threading.Thread(target=query_executor.py:QueryExecutor._execute_continuously)
            -> dag_executor.py:DAGExecutor.execute()
                -> retriever.py:Retriever.execute()
                    -> network_agent.py:NetworkAgent.fetch_data()  # Fetches new data from internet
                -> hallucination_detection.py:HallucinationDetection.execute()
                -> prompter.py:Prompter.execute()
                -> generator.py:Generator.execute()
```
```
4. Use Case: Updating the Memory Layers
Flow:
A query triggers an update to the memory layers.
The query is compiled into a DAG with an Updater operator.
The Updater modifies the short-term or long-term memory layer using CANDY.

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_cql()
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Constructs a DAG with Updater node
    -> query_executor.py:QueryExecutor.execute()
        -> dag_executor.py:DAGExecutor.execute()
            -> updater.py:Updater.execute()
                -> long_term_memory.py:LongTermMemory.update()
                    -> CANDY API:VectorDB.update()

```

```
5. Use Case: Handling a Complex Workflow with Multiple Operators

A complex natural query or CQL triggers a multi-step DAG.
Operators like Retriever, Generator, Docwriter, and ModelEditor interact sequentially.
The system executes the workflow using the DAG.

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_natural_query() or compile_cql()
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Constructs a complex DAG
    -> query_optimizer.py:QueryOptimizer.optimize()
        -> dag.py:DAG.reorder_nodes()
    -> query_executor.py:QueryExecutor.execute()
        -> dag_executor.py:DAGExecutor.execute()
            -> retriever.py:Retriever.execute()
                -> long_term_memory.py:LongTermMemory.retrieve()
                    -> CANDY API:VectorDB.search()
            -> generator.py:Generator.execute()
                -> vLLM API:LLMEngine.generate()
            -> model_editor.py:ModelEditor.execute()
                -> vLLM API:LLMEngine.modify_model()
            -> docwriter.py:Docwriter.execute()
                -> helpers.py:Helpers.format_output()

```

```
6. Use Case: The user asks a natural language query, requesting low-hallucination output.

interactive_cli.py:interactive_console()
    -> query_compiler.py:QueryCompiler.compile_natural_query(hallucination_required=True)
        -> dag.py:DAG.__init__()
        -> dag_node.py:DAGNode.__init__()  # Constructs nodes with HD and retrieval dependencies
    -> query_executor.py:QueryExecutor.execute()
        -> dag_executor.py:DAGExecutor.execute()
            -> retriever.py:Retriever.execute()  # Short-term memory
                -> short_term_memory.py:ShortTermMemory.retrieve()
            -> hallucination_detection.py:HallucinationDetection.execute()
                -> triggers retries if hallucination_detected=True:
                    -> retriever.py:Retriever.execute()  # Long-term memory
                        -> long_term_memory.py:LongTermMemory.retrieve()
                    -> retriever.py:Retriever.execute()  # Internet
                        -> network_agent.py:NetworkAgent.fetch_data()
            -> generator.py:Generator.execute()  # Re-generates refined response
            -> hallucination_detection.py:HallucinationDetection.execute()
                -> Repeat until resolved or retries exhausted
```

```
7. Use Case: 
The user requests continous learning of retriever (registered to the system); 

the user asks natural language queries.

Alternatively: 

(The user requests fine-tune of retriever +) the user asks natural language queries 
                    -> the user asks natural language queries; repeat x 1000;                    
                    + Operator's Memory (no need a VDB);
                    + Embedder needs to pass information (query embedding & document embedding) to Retriever.

```