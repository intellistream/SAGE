
from sage_core.function.filter_function import FilterFunction


class Query_Profiler(FilterFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)


    def execute(self,data):
