# autostop 功能在不同模式下的支持情况

**Date**: 2024-11-10\
**Author**: SAGE Team\
**Summary**: AutoStop 模式支持文档，包括自动停止机制的设计和实现

## 概述

`autostop=True` 功能现在可以正确清理服务资源。本文档说明在不同运行模式下的支持情况。

## 支持的模式

### ✅ 1. 本地模式（LocalEnvironment）

**完全支持** - 已测试验证

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("my_app")
env.register_service("my_service", MyService)
env.from_batch(MyBatch).sink(MySink)

env.submit(autostop=True)  # ✅ 会自动清理所有资源，包括服务
```

**工作原理：**

- 所有任务完成后，触发 `receive_node_stop_signal`
- 调用 `_cleanup_services_after_batch_completion`
- 停止并清理所有本地服务
- `_wait_for_completion` 等待清理完成

### ✅ 2. Ray 模式（LocalEnvironment + Ray backend）

**完全支持** - 代码已就绪

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("my_app")
env.register_service("my_service", MyService, remote=True)  # Ray Actor
env.from_batch(MyBatch).map(MyMap)  # 任务在 Ray 上运行

env.submit(autostop=True)  # ✅ 会自动清理 Ray Actors
```

**工作原理：**

- Dispatcher 检测到 `self.remote = True`
- 调用 `_cleanup_ray_services()` 方法
- 使用 `ActorWrapper.cleanup_and_kill()` 清理 Ray Actors
- 所有服务 Actors 被正确终止

**清理逻辑：**

```python
def _cleanup_ray_services(self):
    for service_name, service_task in self.services.items():
        if hasattr(service_task, "cleanup_and_kill"):
            # Ray Actor 服务
            cleanup_success, kill_success = service_task.cleanup_and_kill(
                cleanup_timeout=5.0, no_restart=True
            )
```

### ⚠️ 3. 完全远程模式（RemoteEnvironment）

**部分支持** - 需要远程 JobManager 配合

```python
from sage.core.api.remote_environment import RemoteEnvironment

env = RemoteEnvironment("my_app", host="remote_host", port=19001)
env.register_service("my_service", MyService)
env.from_batch(MyBatch).sink(MySink)

env.submit()  # ⚠️ RemoteEnvironment.submit() 不支持 autostop 参数
```

**当前状态：**

- `RemoteEnvironment.submit()` 方法签名不包含 `autostop` 参数
- 需要手动调用 `env.stop()` 来停止作业
- 或者等待远程 JobManager 支持 `autostop` 功能

**未来改进：**

1. 扩展 `RemoteEnvironment.submit(autostop=True)` 接口
1. 通过客户端协议传递 `autostop` 参数到远程 JobManager
1. 远程 Dispatcher 执行相同的清理逻辑

## 代码结构

### Dispatcher 中的清理逻辑

```python
# dispatcher.py

def receive_node_stop_signal(self, node_name: str):
    # ... 停止节点 ...

    if len(self.tasks) == 0:
        # 所有任务完成
        self.is_running = False

        if len(self.services) > 0:
            # 🔑 关键：清理服务
            self._cleanup_services_after_batch_completion()

def _cleanup_services_after_batch_completion(self):
    if self.remote:
        self._cleanup_ray_services()  # Ray 模式
    else:
        # 本地模式：逐个清理服务
        for service_name, service_task in list(self.services.items()):
            if hasattr(service_task, "stop"):
                service_task.stop()
            if hasattr(service_task, "cleanup"):
                service_task.cleanup()

    self.services.clear()  # 清空服务字典
```

### LocalEnvironment 中的等待逻辑

```python
# local_environment.py

def _wait_for_completion(self):
    while ...:
        dispatcher_stopped = not job_info.dispatcher.is_running
        if dispatcher_stopped:
            # 🔑 关键：等待服务也清理完成
            if len(dispatcher.services) == 0 and len(dispatcher.tasks) == 0:
                break  # 所有资源都清理完成
            else:
                # 继续等待服务清理
                continue
```

## 测试用例

### 本地模式测试

```bash
python test_autostop_service_improved.py
```

**预期结果：**

```
✅ SUCCESS: Service was properly initialized, used, and cleaned up!
  ✓ Initialized:       True
  ✓ Cleanup Called:    True
  ✓ Cleanup Completed: True
  ✓ Currently Running: False
```

### Ray 模式测试

手动验证（需要 Ray 环境）：

```python
import ray
ray.init()

env = LocalEnvironment("test_ray")
env.register_service("test_svc", TestService, remote=True)
# ... 构建管道 ...
env.submit(autostop=True)

# 检查 Ray dashboard，确认 Actors 被清理
```

## 最佳实践

### ✅ 推荐用法

```python
# 1. 本地开发和测试
env = LocalEnvironment("dev")
env.submit(autostop=True)

# 2. 生产环境使用 Ray
env = LocalEnvironment("prod")
env.register_service("my_service", MyService, remote=True)
env.submit(autostop=True)  # Ray Actors 会被自动清理
```

### ⚠️ 当前限制

```python
# RemoteEnvironment 不支持 autostop
env = RemoteEnvironment("remote", host="server", port=19001)
env.submit()  # 没有 autostop 参数

# 需要手动停止
env.stop()  # 手动调用停止
```

## 未来路线图

### Phase 1：✅ 完成

- [x] 本地模式支持 autostop 清理服务
- [x] Ray 模式清理逻辑实现
- [x] 测试验证

### Phase 2：计划中

- [ ] RemoteEnvironment 添加 autostop 参数
- [ ] JobManager 客户端协议扩展
- [ ] 远程模式端到端测试

### Phase 3：增强

- [ ] 配置化清理策略
- [ ] 优雅关闭超时配置
- [ ] 清理状态监控和报告

## 总结

| 模式         | 环境类                         | autostop 支持 | 服务清理      | 状态     |
| ------------ | ------------------------------ | ------------- | ------------- | -------- |
| **本地**     | LocalEnvironment               | ✅            | ✅ 本地服务   | 已验证   |
| **Ray**      | LocalEnvironment + remote=True | ✅            | ✅ Ray Actors | 代码就绪 |
| **完全远程** | RemoteEnvironment              | ⚠️ 不支持     | ⚠️ 需要手动   | 待增强   |

**结论：**

- ✅ 大多数使用场景（本地 + Ray）都已支持
- ⚠️ RemoteEnvironment 需要在未来版本中添加支持
- 🎯 当前修复已经覆盖了主要的生产用例
