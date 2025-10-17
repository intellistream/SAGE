# SAGE 应用开发最佳实践：资源清理

## 问题背景

在开发 SAGE Pipeline 应用时，如果不正确地清理资源，可能导致：
- 进程无法正常退出（僵尸进程）
- 资源泄漏（文件句柄、网络连接等）
- Service Pipeline 持续轮询，消耗 CPU
- 数据库连接未关闭

## 解决方案

### 1. 使用 `env.close()` 优雅退出

在应用程序结束时，**务必**调用 `env.close()` 方法：

```python
def main():
    env = LocalEnvironment("my_app")
    
    # 注册服务
    env.register_service("my_service", MyService, config)
    
    # 创建 Pipeline
    env.from_source(MySource).map(MyMap).sink(MySink)
    
    # 提交并等待完成
    env.submit(autostop=True)
    
    # ============================================================
    # 【重要】清理资源 - 最佳实践
    # ============================================================
    # 在应用结束时，务必调用 env.close() 来优雅地关闭所有资源：
    # 1. 停止所有正在运行的 Pipeline
    # 2. 关闭所有注册的 Service
    # 3. 释放文件句柄、网络连接等资源
    # 4. 防止资源泄漏和僵尸进程
    # ============================================================
    env.close()
    print("✅ 环境已清理，程序正常退出")
```

### 2. Pipeline-as-Service 模式的额外清理

如果使用 Pipeline-as-Service 模式（通过 `PipelineBridge`），需要在处理完所有数据后**显式关闭 bridges**：

```python
class DisplayAnswer(SinkFunction):
    def __init__(self, bridges=None, total_tasks=5):
        super().__init__()
        self.bridges = bridges or []
        self.total_tasks = total_tasks
        self.processed_count = 0
    
    def execute(self, data):
        # ... 处理数据 ...
        
        self.processed_count += 1
        
        # 所有任务完成后，关闭 bridges
        if self.processed_count >= self.total_tasks:
            for bridge in self.bridges:
                bridge.close()
```

### 3. SourceFunction 检查 Bridge 状态

Service Pipeline 的 SourceFunction 应该检查 bridge 是否已关闭：

```python
class MyServiceSource(SourceFunction):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
    
    def execute(self):
        # 检查 bridge 是否已关闭
        if self.bridge._closed:
            return None
        
        request = self.bridge.next(timeout=0.1)
        return request if request else None
```

## 完整示例

参见 `examples/tutorials/memory/rag_memory_pipeline.py`，它展示了：
- ✅ 使用 `env.close()` 清理环境
- ✅ 在 SinkFunction 中关闭 bridges
- ✅ 在 SourceFunction 中检查 bridge 状态
- ✅ 使用 `autostop=True` 自动停止批处理任务

## 效果

正确使用这些最佳实践后：
- ✅ 程序能够正常退出（不需要 Ctrl+C 或 timeout）
- ✅ 所有资源被正确释放
- ✅ 没有僵尸进程或资源泄漏
- ✅ 日志清晰显示清理过程

## 调试建议

如果程序无法正常退出，检查：
1. 是否调用了 `env.close()`？
2. Service Pipelines 的 bridges 是否已关闭？
3. SourceFunction 是否检查了 bridge 状态？
4. 是否有其他阻塞操作（如无限循环、未关闭的网络连接）？

## 总结

**记住这个简单的规则**：

```python
env = LocalEnvironment("app")
try:
    # ... 应用逻辑 ...
    env.submit(autostop=True)
finally:
    env.close()  # 无论发生什么，都要清理资源
```

这样可以大大减少应用开发中的 bug！
