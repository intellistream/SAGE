from sage.core.engine.runtime import Engine
from sage.api.pipeline.datastream_api import DataStream

class Pipeline:
    def __init__(self, name: str):
        self.name = name
        self.operators = []
        self.data_streams = []

    def _register_operator(self, operator):
        self.operators.append(operator)

    def add_source(self, source_func):
        """
        Adds a source function and returns a DataStream
        """
        stream = DataStream(operator=source_func, pipeline=self, name="source")
        self.data_streams.append(stream)
        return stream

    def submit(self):
        """
        Submit the pipeline to the SAGE engine.
        The engine is responsible for compiling and executing the DAG.
        """
        engine = Engine.get_instance()
        engine.submit_pipeline(self)
        print(f"[Pipeline] Pipeline '{self.name}' submitted to engine.