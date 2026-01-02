# Kernel API 索引

`sage.core.api` 目录下的 Python 模块构成了 SAGE Kernel 的公开接口层。本节总结每个子模块提供的能力，并指向更详细的文档与源码位置。

```
sage/core/api/
├── base_environment.py   # Environment 抽象与通用逻辑
├── local_environment.py  # 本地 JobManager 集成
├── remote_environment.py # 远程 JobManager 客户端
├── datastream.py         # 单输入数据流算子链
├── connected_streams.py  # 多流连接、CoMap、Join
└── function/             # 算子实现所依赖的函数基类族
```

## 你会在这里找到什么

| 主题                                | 文档                                         | 相关源码                                                               |
| ----------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------- |
| Environment 生命周期、提交与停止    | [environments.md](environments.md)           | `base_environment.py`、`local_environment.py`、`remote_environment.py` |
| DataStream 链式算子                 | [datastreams.md](datastreams.md)             | `datastream.py`                                                        |
| ConnectedStreams（多流/CoMap/Join） | [connected-streams.md](connected-streams.md) | `connected_streams.py`                                                 |
| 自定义函数签名                      | [functions.md](functions.md)                 | `function/*.py`                                                        |

阅读建议：先浏览上述文档了解概念，再结合源码确认实现细节。

## 工作流速览

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("example")
stream = env.from_batch([1, 2, 3])
stream = stream.map(lambda value: value + 1)
stream.print()

env.submit(autostop=True)
```

这段代码用到了以下 API：

1. `LocalEnvironment` 构造与 `from_batch`（`BatchTransformation`）。
1. `DataStream.map` 以及 `lambda_function.wrap_lambda` 的自动封装。
1. `DataStream.print` 对 `sink(PrintSink, ...)` 的封装。
1. `submit(autostop=True)` 触发 `_wait_for_completion()`，等待本地 JobManager 运行结束。

## 当前限制与说明

- 本模块当前不提供窗口、侧输出、异步提交等 API；如需这些功能请参考源码中的 TODO 或 issue，避免在生产中使用尚未实现的接口。
- `register_service` 与 `call_service` 已在核心中实现，可直接使用，无需外部 SDK。
- CLI、监控、指标等能力不在 `sage.core.api` 范围内，相关说明已移至其它章节。

## 下一步

继续阅读各子章节或者直接打开相应 Python 文件查看实现。若发现文档与源码不一致，以源码为准并欢迎提交修订。
