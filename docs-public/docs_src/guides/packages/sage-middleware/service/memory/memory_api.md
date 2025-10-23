# Memory Service API 速览

目前仓库开箱即用的服务化入口是 `NeuroMemVDBService`。它继承自 `BaseService`，用于对接 `VDBMemoryCollection`。若已构建可选的 `sage_db` / `sage_flow` 扩展，可另行参考其目录下的 `SageDBService`、`SageFlowService`。下表整理了 `NeuroMemVDBService` 的主要方法：

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `__init__` | `NeuroMemVDBService(collection_name: Union[str, List[str]])` | 连接一个或多个已存在的 VDB 集合；集合需要事先创建索引。 |
| `retrieve` | `retrieve(query_text: str, topk: int = 5, collection_name: Optional[str] = None, with_metadata: bool = False, **kwargs)` | 在指定或全部集合上执行检索，结果中附带 `source_collection` 字段。 |
| `_create_index` | `_create_index(collection_name: str, index_name: str, **kwargs)` | 为已经注册的集合创建索引，内部使用 `VDBMemoryCollection.create_index`。 |

> 其余公共方法均来自 `BaseService`（如 `close`、`health_check` 等）。

详细使用说明请参阅 [`memory_service.md`](./memory_service.md) 与 [`components/neuromem.md`](../../components/neuromem.md)。