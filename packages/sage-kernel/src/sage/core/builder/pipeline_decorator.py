from sage.core.builder.builder import PipelineBuilder
from sage.core.api.datastream import DataStream
from typing import TYPE_CHECKING, Callable

from sage.core.communication.pipeline_proxy import AsyncPipelineCallProxy


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
        self.builder = PipelineBuilder(remote=(self.namespace == "remote"))
        end_stream = self.fn(self.builder)
        # 其中的fn就是dataflow model的变换，self.builder就代表初始的datastream
        end_stream.transformation.is_sink = True
        self.builder._environment.submit()
        # TODO: 每一个进程都会有一个handle，但是env有可能是remote和唯一的
        self.handle = AsyncPipelineCallProxy(self.builder._environment)

    def __call__(self, *args, **kwargs):
        return self.handle(*args, **kwargs)


def pipeline(namespace):
    def decorator(fn: Callable[["PipelineBuilder"], "DataStream"]):
        return PipelineTemplate(fn, namespace)

    return decorator
