# Neuromem Module / operator 模块

RAG常见算子包括Retriver、Prompt、Generator等

- test/测试(SAGE目录下)：
```
 pytest sage/api/operator/test/test.py
```

## Core Features / 核心功能
class SourceFunction(BaseOperator):
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