# SAGE

## 1. Installation

Please refer to `installation\README.md` for project installation.

If you are using Windows, please install `Docker Desktop` first.

## 2. Running SAGE Interactively

### 2.1 Hugging Face Authentication

Before running the SAGE system, ensure you log in to Hugging Face:
```bash
huggingface-cli login --token <your_huggingface_token>
```

### 2.2 Interactive CLI

You can interact with the SAGE system using the interactive CLI:
```bash
python api/interactive_cli.py
```

### 2.3 If you use Pycharm or other IDE to run SAGE

Please remember to update the python interpreter to use conda, sage environment configured automatically by our installation scripts.

If you face any other issues, please log them in our issues board.

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
