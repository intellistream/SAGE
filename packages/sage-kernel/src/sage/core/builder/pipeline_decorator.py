from sage.core.builder.builder import PipelineBuilder
from sage.core.api.datastream import DataStream
from typing import TYPE_CHECKING, Callable
    


# python的修饰器decorator的底层到底是怎么执行的？
'''
@decorator_with_args("namespace")
def function():
    ...
等价于：
def function():
    ...

function = decorator_with_args("namespace")(function)
'''

class PipelineTemplate:
    def __init__(self, fn: Callable[["PipelineBuilder"], "DataStream"], namespace: str):
        self.fn = fn
        self.namespace = namespace
        self.builder = PipelineBuilder(remote = (self.namespace == "remote"))
        end_stream = self.fn(self.builder)
        end_stream.set_as_output()
        self.handle = self.builder.env.submit()
    def __call__(self, *args, **kwargs):
        return self.handle(*args, **kwargs)

def pipeline(namespace):
    def decorator(fn: Callable[["PipelineBuilder"], "DataStream"]):
        return PipelineTemplate(fn, namespace)
    return decorator
                