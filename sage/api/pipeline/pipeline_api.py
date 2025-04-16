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

    def submit(self, config=None):
        """
        Submit the pipeline to the SAGE engine.
        The engine is responsible for compiling and executing the DAG.

        Args:
            config (dict, optional): Configuration options for runtime execution.
                Example:
                {
                    "is_long_running": True,
                    "duration": 1,
                    "frequency": 30
                }
        """
        engine = Engine.get_instance() # client side
        engine.submit_pipeline(self, config=config or {}) # compile dag -> register engine
        print(f"[Pipeline] Pipeline '{self.name}' submitted to engine with config: {config or {}}")

    def stop(self):
        engine= Engine.get_instance() # client side
        engine.stop_pipeline(self) # stop the pipeline
        print(f"[Pipeline] Pipeline '{self.name}' stopped.")