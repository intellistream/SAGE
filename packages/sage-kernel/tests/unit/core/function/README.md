# Function Tests 模块

该目录包含 Sage Core 函数层的测试文件，测试各种数据流操作函数的功能。

## 测试文件说明

### `comap_test.py`
测试协同映射（CoMap）功能：
- 多流协同处理逻辑
- 协同窗口操作
- 状态同步机制

### `connected_keyby_test.py`
测试连接后的键分组操作：
- 连接流的键分组功能
- 分区策略测试
- 数据路由验证

### `filter_test.py`
测试过滤器功能：
- 条件过滤逻辑
- 谓词函数应用
- 过滤性能测试

### `flatmap_test.py`
测试扁平化映射功能：
- 一对多数据转换
- 嵌套数据结构处理
- 输出流平化

### `join_test.py`
测试流连接功能：
- 内连接、左连接、右连接
- 窗口连接操作
- 连接条件验证

### `kafka_test.py`
测试 Kafka 数据源功能：
- Kafka 消费者配置
- 消息序列化/反序列化
- 分区和偏移管理

### `keyby_test.py`
测试键分组功能：
- 键提取逻辑
- 分区策略
- 状态管理

## 运行测试

```bash
# 运行所有函数测试
python -m pytest sage/core/function/tests/

# 运行特定功能测试
python -m pytest sage/core/function/tests/filter_test.py
```

## 测试数据

测试使用模拟数据和本地 Kafka 实例进行验证。需要确保测试环境具备：
- 本地 Kafka 服务器（用于 Kafka 测试）
- 足够的内存用于大数据集测试
- 网络连接（用于分布式测试场景）
