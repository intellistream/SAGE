# Neuromem Module / operator 模块

RAG常见算子包括Retriver、Prompt、Generator等

- test/测试(SAGE目录下)：
```
 pytest sage/api/operator/test/test.py
```

## Core Features / 核心功能
class SourceFunction(BaseFuction):
    """
    Operator for read data
    """



## Directory Structure / 目录结构

.
|-- README.md
|-- __init__.py
|-- base_operator_api.py
|-- chunk_function_api.py
|-- generator_function_api.py
|-- operator_impl
|   |-- __init__.py
|   |-- generator.py
|   |-- promptor.py
|   |-- refiner.py
|   |-- reranker.py
|   |-- retriever.py
|   |-- sink.py
|   |-- source.py
|   `-- writer.py
|-- prompt_function_api.py
|-- refiner_funtion_api.py
|-- reranker_function_api.py
|-- retriever_function_api.py
|-- sink_function_api.py
|-- source_function_api.py
|-- summarize_function_api.py
|-- test
|   |-- config.yaml
|   |-- question.txt
|   `-- test.py
`-- writer_function_api.py

详细用法请参考 test/test.py 中的示例



# 图算子设计文档
## 多路输入多路输出的operator设计
引擎不需要关心数据怎么投喂给operator， 引擎只要把多个输入流的数据交给它就行了。无论是merge逻辑还是join逻辑，operator在内部维护缓冲区和在内部处理。同理引擎也不用去解释operator的内容，只要给operator

同理引擎也不需要去解释operator传出去的数据。引擎只需要提供好输出通道就可以了。


### 多路输入operator
我们要让operator在内部维护其状态，然后提供一个输出的接口方法output(data, channel)
同时对于输入数据，让operator提供execute(input data, channel)的方法。
```python
        # Main execution loop
        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    result = self.operator.execute()
                    self.emit(result)
                    if self.output_queue.qsize():
                        print(f"{self.name} queue size is{self.output_queue.qsize()} ")
                else:
                    input_data = self.fetch_input()
                    if input_data is None:
                        time.sleep(1)  # Short sleep when no data to process
                        continue
                    result = self.operator.execute(input_data)
                    self.emit(result)
                    if self.output_queue.qsize():
                        print(f"{self.name} queue size is{self.output_queue.qsize()} ")
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")
```