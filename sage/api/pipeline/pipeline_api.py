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
        engine = Engine.get_instance()
        engine.submit_pipeline(self, config=config or {}) # API -> operators -> compiler -> dag (DAGNode + io) -> executor -> neuronmem
        print(f"[Pipeline] Pipeline '{self.name}' submitted to engine with config: {config or {}}")

        # 近期完成的工作：
        # metric模块：完成了evaluator类，实现了"em","f1","acc","recall","precision","rouge_score"等评估功能
        # prompt模块：完成了baseTemplate、SummaryTemplate、QaTemplate
        # compiler模块：
        # 与peilin学长沟通后，对dag模块进行构造，将先前传输operator实例修改为传输其对应的类，由peilin学长统一进实例化进行管理调度
        # 对于逻辑图向物理图的转化初步进行了一些尝试，可以实现简单逻辑的DAG构建
        # 存在的问题：
        # 根据yancan师兄群里发的api接口文档，已对逻辑图向物理图的转化建立起一定认识，但是关于其中IO缓冲仍存在一些疑问：在物理图中的IO缓冲区是需要在logic_graph中维护一个Queue去进行缓冲，还是和operator算子一样只需要构造一个IO模块的Node调用其他模块就可以
        # Template的返回值，在FLASHRAG中的prompt相关按照openai与非openai两种进行处理，二者区别在于返回值不同，一种返回字符串，另外一种是openai兼容的消息列表形式，每个消息包含角色和内容。之前的话说要统一使用openapi接口，Template的返回值是否修改为均以消息列表形式返回吗
        # 3:08
        # xiaojie