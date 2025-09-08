from sage.core.api.datastream import DataStream
from sage.core.api.local_environment import LocalEnvironment
from sage.core.transformation.base_transformation import BaseTransformation


class PipelineBuilder(DataStream):
    def __init__(self, remote: bool = False):
        self.env = LocalEnvironment("pipeline_env", config=None)
        self.initialized = False
        
    def _apply(self, transformation) -> DataStream:
        if(self.initialized is False):
            self.initialized = True
        else:
            raise RuntimeError("Pipeline can only have one source")
        self.env.pipeline.append(transformation)
        return DataStream(self.env, transformation)