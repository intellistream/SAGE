from abc import abstractmethod
from sage_core.function.map_function import MapFunction
from sage_utils.config_loader import load_config

class GeneratorFunction(MapFunction):

    @abstractmethod
    def __init__(self):
        self.generator_config=load_config("config/generator_presets.yaml")
        super().__init__()