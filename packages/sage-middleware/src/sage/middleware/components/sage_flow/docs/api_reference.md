# SageFlow API 参考

## Python DSL API

SageFlow 提供了一个流畅的链式 API 用于数据流处理。以下是主要类和方法的详细描述。

### Stream 类

`Stream` 是 SageFlow 数据流的入口点，支持链式操作。

#### 构造函数
```python
Stream.from_list(data: List[Any]) -> Stream
```
- **参数**: `data` - 输入数据列表
- **返回**: `Stream` 实例
- **描述**: 从 Python 列表创建数据流。

#### 链式方法

- `map(func: Callable[[Any], Any]) -> Stream`
  - **参数**: `func` - 映射函数
  - **返回**: `Stream` - 应用映射后的流
  - **类型提示**: `Callable[[TInput], TOutput]`

- `filter(func: Callable[[Any], bool]) -> Stream`
  - **参数**: `func` - 过滤函数
  - **返回**: `Stream` - 过滤后的流
  - **类型提示**: `Callable[[T], bool]`

- `sink(func: Callable[[Any], None]) -> Stream`
  - **参数**: `func` - 接收函数
  - **返回**: `Stream` - 应用接收器的流
  - **类型提示**: `Callable[[T], None]`

- `execute() -> None`
  - **描述**: 执行整个数据流管道
  - **返回**: 无

#### 类型提示支持
所有方法均支持 mypy 类型检查：
```python
from typing import List, Callable, Any, TypeVar

T = TypeVar('T')
U = TypeVar('U')

class Stream:
    def map(self, func: Callable[[T], U]) -> 'Stream[U]': ...
    def filter(self, func: Callable[[T], bool]) -> 'Stream[T]': ...
```

## C++ API (部分可用)

### BaseOperator (模板化)
```cpp
template<typename InputType, typename OutputType>
class BaseOperator {
public:
    virtual void process(const InputType& input) = 0;
    virtual ~BaseOperator() = default;
};
```

### Response 类
```cpp
class Response {
public:
    Response() = default;  // 默认构造函数
    Response(const std::optional<OutputType>& data);
    // 其他成员...
};
```

更多 C++ 细节请参考源代码头文件。