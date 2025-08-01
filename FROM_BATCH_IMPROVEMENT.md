# from_batch 方法改进文档

## 概述

`from_batch` 方法已经被改进为统一的多态接口，可以接受多种类型的输入源，大大简化了批处理数据源的创建。

## 支持的输入类型

### 1. 自定义批处理函数类
```python
class MyBatchFunction(BaseFunction):
    def get_data_iterator(self):
        return iter(range(100))
    
    def get_total_count(self):
        return 100

# 使用自定义函数类
stream = env.from_batch(MyBatchFunction, custom_param="value")
```

### 2. 数据列表或元组
```python
# 使用列表
data_list = ["apple", "banana", "cherry", "date"]
stream = env.from_batch(data_list)

# 使用元组
data_tuple = (1, 2, 3, 4, 5)
stream = env.from_batch(data_tuple)
```

### 3. 任何可迭代对象
```python
# 使用集合
data_set = {10, 20, 30, 40, 50}
stream = env.from_batch(data_set)

# 使用字符串（按字符迭代）
stream = env.from_batch("hello")

# 使用 range 对象
stream = env.from_batch(range(0, 100, 2))

# 使用生成器
def my_generator():
    for i in range(10):
        yield f"item_{i}"

stream = env.from_batch(my_generator())
```

## 配置参数

所有形式的 `from_batch` 都支持配置参数：

```python
# 基本配置
stream = env.from_batch(data, progress_log_interval=100)

# 自定义函数类 + 配置
stream = env.from_batch(
    MyBatchFunction,
    start=0, end=1000,          # 函数参数
    progress_log_interval=50    # transformation 配置
)
```

## 自动类型检测

方法会自动检测输入类型并选择合适的处理方式：

1. **类型检查**: 如果输入是 `BaseFunction` 的子类，则作为自定义函数处理
2. **列表/元组**: 使用 `SimpleBatchIteratorFunction` 处理
3. **其他可迭代对象**: 使用 `IterableBatchIteratorFunction` 处理
4. **错误处理**: 对于不可迭代的对象会抛出 `TypeError`

## 迁移指南

### 旧方法 → 新方法

```python
# 之前需要使用不同的方法
env.from_batch_collection(data_list)
env.from_batch_iterable(data_set, total_count=5)
env.from_batch(MyBatchFunction, param="value")

# 现在统一使用 from_batch
env.from_batch(data_list)
env.from_batch(data_set)
env.from_batch(MyBatchFunction, param="value")
```

## 优势

1. **统一接口**: 一个方法支持所有批处理数据源类型
2. **智能检测**: 自动识别输入类型并选择最佳处理方式
3. **向下兼容**: 现有代码无需修改
4. **灵活配置**: 支持所有原有的配置参数
5. **类型安全**: 提供清晰的错误信息

## 实现细节

- 使用类型检查和鸭子类型确定处理方式
- 内部调用专门的私有方法处理不同类型
- 保持了原有的所有功能和配置选项
- 提供了详细的错误信息和日志记录
