from typing import Tuple, List, Optional
from .. import operator, model, memory, pipeline

class StaticSource(operator.SourceFunction):
    def __init__(self, input_query: str):
        super().__init__()
        self.query = input_query

    def execute(self, context=None) -> str:
        return self.query


class SimpleRetriever(operator.RetrieverFunction):
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.embedding_model = model.apply_embedding_model("default")

        # session-aware STM name fallback
        stm_name = f"short_term_memory_{session_id}" if session_id else "short_term_memory"

        # create session STM if not exists
        try:
            memory.create_table(memory_table_name=stm_name, memory_table_backend="kv_store.rocksdb")
        except Exception:
            pass

        self.memory_collections = memory.connect(
            stm_name, "long_term_memory", "dynamic_contextual_memory"
        )
        self.retrieval_func = memory.retrieve_func

    def execute(self, input_query: str, context=None) -> Tuple[str, List[str]]:
        embedding = self.embedding_model.embed(input_query)
        chunks = self.memory_collections.retrieve(embedding, self.retrieval_func)
        return input_query, chunks


class SimplePromptConstructor(operator.PromptFunction):
    def __init__(self):
        super().__init__()
        self.prompt_constructor = self.set_prompt_constructor("default")

    def execute(self, inputs: Tuple[str, List[str]], context=None) -> Tuple[str, str]:
        query, chunks = inputs
        return query, self.prompt_constructor.construct(query, chunks)


class LlamaGenerator(operator.GeneratorFunction):
    def __init__(self):
        super().__init__()
        self.model = model.apply_generator_model("llama_8b")

    def execute(self, combined_prompt: str, context=None) -> str:
        return self.model.generate(combined_prompt)


class ContextWriter(operator.WriterFunction):
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.embedding_model = model.apply_embedding_model("default")
        stm_name = f"short_term_memory_{session_id}" if session_id else "short_term_memory"

        # Create if not exists
        try:
            memory.create_table(memory_table_name=stm_name, memory_table_backend="kv_store.rocksdb")
        except Exception:
            pass

        self.memory_collections = memory.connect(stm_name)
        self.write_func = memory.write_func

    def execute(self, inputs: Tuple[str, List[str]], context=None) -> None:
        self.memory_collections.write(inputs, self.write_func)


def run_query(query: str, session_id: Optional[str] = None) -> str:
    """
    High-level entry point for users to execute a query using a submitted pipeline.
    Supports optional session for STM-based memory.
    """
    query_pipeline = pipeline.Pipeline("query_pipeline")

    source = StaticSource(query)
    query_stream = query_pipeline.add_source(source) # pipeline : source -> ?

    # 提交给server的就是一个logical dag. Query Rewriter
    retriever = SimpleRetriever(session_id=session_id)
    prompt = SimplePromptConstructor()
    generator = LlamaGenerator()
    writer = ContextWriter(session_id=session_id)

    q_chunks = query_stream.retrieve(retriever)
    prompt_stream = q_chunks.construct_prompt(prompt)
    response_stream = prompt_stream.generate_response(generator)
    response_stream.save_context(writer)

    query_pipeline.submit(config={"is_long_running": False, "duration": 0, "frequency": 0})

    return f"Pipeline submitted for session: {session_id or 'default'}"
