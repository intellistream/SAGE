# 调度器测试文档

## 测试覆盖范围

本测试套件提供调度器模块的完整测试覆盖。

### 测试文件

1. **test_scheduler_complete.py** - 主测试套件（39个测试）

   - PlacementDecision 测试（8个）
   - BaseScheduler 接口测试（2个）
   - FIFOScheduler 测试（6个）
   - LoadAwareScheduler 测试（8个）
   - PlacementExecutor 测试（9个）
   - 集成测试（3个）
   - 性能测试（2个）

1. **test_node_selector.py** - NodeSelector 测试（需要 Ray）

   - NodeResources 测试
   - 节点选择算法测试（balanced/pack/spread）
   - 资源监控测试
   - 集群统计测试

## 运行测试

### 运行所有调度器测试

```bash
# 完整测试套件
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py -v

# NodeSelector 测试（需要 Ray）
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_node_selector.py -v

# 运行所有调度器测试
pytest packages/sage-kernel/tests/unit/kernel/scheduler/ -v
```

### 运行特定测试类

```bash
# 只测试 PlacementDecision
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py::TestPlacementDecision -v

# 只测试 FIFOScheduler
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py::TestFIFOScheduler -v

# 只测试 LoadAwareScheduler
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py::TestLoadAwareScheduler -v
```

### 运行特定测试方法

```bash
# 测试资源感知调度
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py::TestLoadAwareScheduler::test_make_decision_with_resources -v

# 测试节点选择
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py::TestLoadAwareScheduler::test_make_decision_with_node_selector -v
```

### 查看测试覆盖率

```bash
# 生成覆盖率报告
pytest packages/sage-kernel/tests/unit/kernel/scheduler/ --cov=sage.kernel.scheduler --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

## 测试详情

### 1. PlacementDecision 测试

测试调度决策数据结构的所有方面：

```python
class TestPlacementDecision:
    def test_default_initialization()        # 默认初始化
    def test_full_initialization()           # 完整初始化
    def test_immediate_default()             # 快捷方法：立即默认
    def test_with_resources()                # 快捷方法：资源需求
    def test_with_node()                     # 快捷方法：指定节点
    def test_to_dict()                       # 序列化
    def test_from_dict()                     # 反序列化
    def test_repr()                          # 字符串表示
```

**覆盖率**: 100%

### 2. BaseScheduler 测试

测试调度器抽象基类：

```python
class TestBaseScheduler:
    def test_scheduler_is_abstract()         # 验证抽象类
    def test_scheduler_interface()           # 验证接口定义
```

**覆盖率**: 100%

### 3. FIFOScheduler 测试

测试 FIFO 调度器的所有功能：

```python
class TestFIFOScheduler:
    def test_initialization()                # 初始化
    def test_make_decision()                 # 任务调度决策
    def test_make_service_decision()         # 服务调度决策
    def test_multiple_decisions()            # 多任务调度
    def test_get_metrics()                   # 性能指标
    def test_shutdown()                      # 关闭清理
```

**关键验证**:

- ✅ FIFO 按顺序调度
- ✅ 返回 `target_node=None`（使用 Ray 默认负载均衡）
- ✅ 决策历史记录
- ✅ 性能指标收集

### 4. LoadAwareScheduler 测试

测试负载感知调度器的资源感知能力：

```python
class TestLoadAwareScheduler:
    def test_initialization()                          # 初始化
    def test_make_decision_without_resources()         # 无资源需求
    def test_make_decision_with_resources()            # 带资源需求
    def test_make_decision_with_node_selector()        # NodeSelector 集成
    def test_make_service_decision()                   # 服务调度
    def test_concurrency_control()                     # 并发控制
    def test_task_completed()                          # 任务完成
    def test_memory_parsing()                          # 内存解析
    def test_get_metrics()                             # 性能指标
```

**关键验证**:

- ✅ 资源需求提取（CPU、GPU、内存）
- ✅ NodeSelector 集成和节点选择
- ✅ 并发限制控制
- ✅ 服务使用 spread 策略
- ✅ 任务完成后资源释放
- ✅ 集群统计信息

### 5. PlacementExecutor 测试

测试放置执行器的物理放置功能：

```python
class TestPlacementExecutor:
    def test_initialization()                          # 初始化
    def test_place_local_task()                        # 本地任务放置
    def test_place_remote_task_default()               # 远程任务（默认）
    def test_place_remote_task_with_node()             # 远程任务（指定节点）
    def test_build_ray_options_default()               # Ray 选项（默认）
    def test_build_ray_options_with_node()             # Ray 选项（指定节点）
    def test_build_ray_options_with_resources()        # Ray 选项（资源需求）
    def test_parse_memory()                            # 内存解析
    def test_get_stats()                               # 统计信息
```

**关键验证**:

- ✅ 本地任务直接创建
- ✅ 远程任务创建 Ray Actor
- ✅ `target_node=None` 不设置 scheduling_strategy
- ✅ `target_node` 转换为 NodeAffinitySchedulingStrategy
- ✅ 资源需求转换为 Ray API 参数
- ✅ 放置统计信息

### 6. 集成测试

测试调度器和执行器的完整流程：

```python
class TestSchedulerIntegration:
    def test_fifo_scheduler_to_placement()             # FIFO 完整流程
    def test_load_aware_scheduler_to_placement()       # LoadAware 完整流程
    def test_service_scheduling_flow()                 # 服务调度流程
```

**验证流程**:

```
Scheduler.make_decision()
    → PlacementDecision
    → PlacementExecutor.place_task()
    → Task/Actor
```

### 7. 性能测试

测试调度器的性能表现：

```python
class TestSchedulerPerformance:
    def test_fifo_scheduler_latency()                  # FIFO 延迟
    def test_load_aware_scheduler_latency()            # LoadAware 延迟
```

**性能基准**:

- FIFO：100 任务 \< 1 秒，平均延迟 \< 10ms
- LoadAware：50 任务 \< 2 秒

### 8. NodeSelector 测试

测试资源监控和节点选择算法：

```python
class TestNodeResources:
    # NodeResources 数据类测试

class TestNodeSelector:
    def test_update_node_cache()                       # 节点缓存更新
    def test_select_best_node_balanced()               # 负载均衡策略
    def test_select_best_node_pack()                   # 紧凑放置策略
    def test_select_best_node_spread()                 # 分散放置策略
    def test_select_best_node_with_gpu()               # GPU 节点选择
    def test_track_task_placement()                    # 任务跟踪
    def test_get_cluster_stats()                       # 集群统计
    # ... 更多测试
```

**关键验证**:

- ✅ 集群资源监控
- ✅ 三种调度策略正确性
- ✅ GPU 节点识别和选择
- ✅ 任务分配跟踪
- ✅ 集群统计准确性

## 测试结果

### 最新测试运行

```
========== 39 passed in 1.88s ==========
```

**状态**: ✅ 全部通过

### 测试覆盖率

| 模块                        | 覆盖率   | 说明                            |
| --------------------------- | -------- | ------------------------------- |
| decision.py                 | 100%     | PlacementDecision 完全覆盖      |
| api.py                      | 100%     | BaseScheduler 接口完全覆盖      |
| simple_scheduler.py         | 100%     | FIFOScheduler 完全覆盖          |
| resource_aware_scheduler.py | 95%      | LoadAwareScheduler 主要功能覆盖 |
| placement.py                | 90%      | PlacementExecutor 核心功能覆盖  |
| node_selector.py            | 需要 Ray | 在有 Ray 环境中测试             |

### 未覆盖的场景

以下场景需要真实 Ray 集群环境：

1. **真实 Ray Actor 创建**

   - 当前使用 Mock，真实环境需要 Ray 集群

1. **真实节点资源监控**

   - NodeSelector 真实集群监控
   - 节点故障处理
   - 资源耗尽场景

1. **端到端集成**

   - Dispatcher → Scheduler → Placement → Ray
   - 真实任务执行
   - 任务迁移和恢复

## 添加新测试

### 测试新调度器

```python
class TestMyScheduler:
    """测试自定义调度器"""

    def test_initialization(self):
        """测试初始化"""
        scheduler = MyScheduler(param=value)
        assert scheduler.param == value

    def test_make_decision(self):
        """测试调度决策"""
        scheduler = MyScheduler()
        task_node = Mock()
        task_node.name = "test"

        decision = scheduler.make_decision(task_node)

        assert isinstance(decision, PlacementDecision)
        # 验证决策逻辑
```

### 测试新策略

```python
def test_new_strategy(self):
    """测试新的调度策略"""
    scheduler = LoadAwareScheduler(strategy="new_strategy")

    # Mock 节点
    # ...

    best_node = scheduler.node_selector.select_best_node(
        cpu_required=2, strategy="new_strategy"
    )

    # 验证策略正确性
    assert best_node == expected_node
```

## 调试测试

### 查看详细输出

```bash
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py -v -s
```

### 只运行失败的测试

```bash
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py --lf
```

### 进入调试器

```bash
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_scheduler_complete.py --pdb
```

### 查看 Mock 调用

```python
# 在测试中
mock_selector.select_best_node.assert_called_once_with(
    cpu_required=4,
    gpu_required=1,
    memory_required=8589934592,
    custom_resources=None,
    strategy="balanced",
)

# 打印所有调用
print(mock_selector.select_best_node.call_args_list)
```

## 持续集成

### GitHub Actions 配置

```yaml
name: Scheduler Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e packages/sage-kernel[test]
      - name: Run tests
        run: |
          pytest packages/sage-kernel/tests/unit/kernel/scheduler/ -v --cov=sage.kernel.scheduler
```

## 总结

✅ **完整覆盖**: 39 个测试，覆盖所有核心功能\
✅ **快速执行**: 所有测试 \< 2 秒\
✅ **易于维护**: 清晰的测试结构和命名\
✅ **Mock 隔离**: 不依赖真实
Ray 集群\
✅ **文档齐全**: 每个测试都有清晰的说明

测试套件确保调度器模块的正确性、性能和可靠性！
