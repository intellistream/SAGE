from sage.core.builder.pipeline_decorator import pipeline
from sage.core.module.module import module, dataflow

@pipeline(namespace = 'local')
def ppl(input_stream):
    result_stream = input_stream.map(lambda x:x*2)
    return result_stream

print(ppl(10))

# 如果说是纯面向对象，我们就要在dataflow里维护一个id。

@module()
class TestModule:
    def __init__(self, factor):
        self.factor = factor
        self.submodule = TestSubmodule(offset=3)

    def multiply(self, x):
        return x * self.factor
    
    @dataflow
    def multiply_dsl(self,input_stream):
        return input_stream.map(self.factor).map(self.submodule.add_dsl).map(self.submodule.add)
    
@module()
class TestSubmodule:
    def __init__(self, offset):
        self.offset = offset
    
    def add(self, x):
        return x + self.offset
    
    @dataflow
    def add_dsl(self, input_stream):
        return input_stream.map(self.add)
    
    
my_module = TestModule(5)
print(my_module.multiply_dsl(10))