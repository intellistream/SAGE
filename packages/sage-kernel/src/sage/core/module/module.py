import uuid
from sage.core.builder.builder import PipelineBuilder
from sage.core.api.datastream import DataStream
from sage.core.communication.pipeline_proxy import AsyncPipelineCallProxy
import ray

def dataflow(fn):
    fn._is_dataflow_method = True
    return fn



# @ray.remote
class ModuleInstance:
    def __init__(self, cls, args, kwargs):
        self._instance = cls(*args, **kwargs)
        self.compiled_proxys = {}
        
    # dag的本质是一个状态机。每一个状态都代表下一步要干嘛。即使有多路分支，那么就给每一个分支一个uuid和下一步要干嘛的映射。
    # 对于对象并发问题，我们可以加开关，强制单线程，或者让用户选择暴露在并发之下
    def compile_dataflow(self, method_name):
        # 一个RemoteInstance可能会被多个handle引用，所以说proxy要缓存
        if method_name in self.compiled_proxys:
            return self.compiled_proxys[method_name]
        
        dataflow_dsl_function = getattr(self._instance, method_name)
        builder = PipelineBuilder(remote=False)
        end_stream = dataflow_dsl_function(builder)
        # TODO: 把这里改写成compiler.compile(dataflow_dsl_function)，得到一个dag的结果引用。
        end_stream.transformation.is_sink = True
        # TODO: 把这个调用收到datastream的方法里边去
        builder._environment.submit()
        # TODO: 也收到builder的方法里边去，把environment和builder给集成到一块去
        proxy = AsyncPipelineCallProxy(builder._environment)
        # TODO: proxy里边不可序列化的对象，需要延迟初始化 
        self.compiled_proxys[method_name] = proxy
        return proxy

def module():
    def decorator(cls):
        class ModuleHandle:
            def __init__(self, *args, **kwargs):
                # self._remote_instance = RemoteInstance.remote(cls, *args, **kwargs)
                self._remote_instance = ModuleInstance(cls, args, kwargs)
                # 测试的时候先假装是本地的
                # 或者也可以直接从集群要这个实例的handle
                
                for attr_name in dir(cls):
                    attr = getattr(cls, attr_name)
                    if callable(attr) and getattr(attr, "_is_dataflow_method", False):
                        # future = self._remote_instance.compile_dataflow.remote(attr_name)
                        # local_dataflow_handle = ray.get(future)
                        local_dataflow_handle = self._remote_instance.compile_dataflow(attr_name)
                        setattr(self, attr_name, local_dataflow_handle)
            
            def __del__(self):
                pass
                # TODO: 降低远程实例的引用计数
        return ModuleHandle
    return decorator