# SAGE-DB Service（通过 VDB Service 集成）

SAGE-DB 是企业版的高性能向量数据库组件，位于 enterprise/sage_db/。在服务层推荐通过 VDB Service 对接使用，即“VDB Service（SAGE-DB
后端）”。当企业组件可用时，VDB Service 可将 SAGE-DB 作为底层引擎来提供向量集合管理、批量写入与相似检索等能力。

- 组件代码位置：packages/sage-middleware/src/sage/middleware/enterprise/sage_db/
  - 核心：sage_db.py（Python 封装，导出 SageDB/IndexType/SearchParams 等）
  - C++ 源码：include/sage_db/\*.h、src/sage_db.cpp
  - Python 占位接口（最小模式）：python/sage_db.py
  - 企业导出入口：enterprise/sage_db/__init__.py（is_available(), get_status() 等）
- 服务对接：通过 VDB Service 统一暴露 API（services/vdb/）
  - 导出：services/vdb/__init__.py 提供 VDBService, create_vdb_service_factory
  - 示例：services/vdb/examples/vdb_demo.py 展示 add_vectors(), search(), get_vector() 等

说明：

- 本文以“VDB Service（SAGE-DB 后端）”作为 SAGE-DB 的服务形态进行说明
- 若你需要更底层的自定义服务封装，可在你的 Service 内直接使用 enterprise.sage_db.SageDB

## 一、编译与可用性检查

企业组件可用性取决于构建与许可证。常见路径如下（请以你仓库版本的构建脚本为准）：

1. 安装中间件（开发态）

```bash
# 仓库根目录
pip install -e packages/sage-middleware
```

2. 在企业模块目录下安装/构建（若独立）

```bash
cd packages/sage-middleware/src/sage/middleware/enterprise/sage_db
# 若提供 pyproject/setup.py
pip install -v .
# 或（含 C++ 扩展的常见命令）
python setup.py build_ext --inplace -j4
python setup.py install
```

3. 在运行时检查可用性

```python
from sage.middleware.enterprise import sage_db as enterprise_sage_db

if enterprise_sage_db.is_available():
    print("SAGE-DB ready:", enterprise_sage_db.get_status())
else:
    print("SAGE-DB unavailable, fallback to other VDB backends")
```

## 二、以 VDB Service 形态对外提供服务

VDB Service 是上层统一的“向量数据库服务”，当 SAGE-DB 可用且配置为后端时，即构成“SAGE-DB Service”。

- 常见方法（参见 examples/README 与 vdb_demo.py）
  - add_vectors(vectors, ids?, metadata?)
  - search(query, top_k, filters?)
  - get_vector(id)
  - 其他如集合管理、更新/删除等以你本地版本实现为准

### 1) 注册 VDB Service

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.services.vdb import VDBService  # services/vdb/__init__.py 导出


def vdb_service_factory():
    # 如果 VDBService 支持通过构造参数/配置选择后端，可在此指定 SAGE-DB
    # 例如：VDBService(backend="sage_db", config={...})
    # 若当前版本不支持显式指定，通常在内部检测 enterprise.sage_db 可用性并选用
    return VDBService()


env = LocalEnvironment("sage_db_service_demo")
env.register_service("vdb_service", vdb_service_factory)
```

### 2) 在 Function 中调用

```python
from sage.core.api.function.base_function import BaseFunction


class VectorWorkflow(BaseFunction):
    def execute(self, data):
        vectors = data["vectors"]  # List[List[float]]
        ids = data.get("ids")  # Optional[List[str]]
        metadata = data.get("metadata")  # Optional[List[dict]]

        # 写入向量
        self.call_service["vdb_service"].add_vectors(
            vectors=vectors, ids=ids, metadata=metadata
        )

        # 相似检索
        results = self.call_service["vdb_service"].search(
            query=data["query_vector"],
            top_k=data.get("top_k", 5),
            filters=data.get("filters"),
        )

        # 读取单条向量
        item = None
        if ids:
            item = self.call_service["vdb_service"].get_vector(ids[0])

        return {"results": results, "first_item": item}
```

- 异步调用
  ```python
  fut = self.call_service_async["vdb_service"].search(query=q, top_k=10)
  async_results = fut.result(timeout=5)
  ```

## 三、SAGE-DB 组件能力与 VDB 映射（概览）

SAGE-DB 组件导出丰富的核心 API/类型（以企业模块为准）：

- 类型与枚举：IndexType, DistanceMetric, SearchParams, QueryResult, DatabaseConfig
- 核心类：SageDB
  - add / batch_add / update / delete（按实现）
  - search / batch_search（相似检索/批检索）
  - build_index / train_index / is_trained（索引管理）
  - set_metadata / get_metadata / find_by_metadata（元数据操作）
  - save / load（持久化）
  - size / dimension / index_type / config（状态与统计）
  - query_engine()/vector_store()/metadata_store()（高级接口）

在服务层（VDB Service），通常暴露的是“对上稳定的少量方法族”（add_vectors/search/get_vector 等），并在内部将配置与搜索参数翻译为 SageDB 的
SearchParams/索引类型等低层细节。

建议：

- 业务侧优先通过 VDB Service 使用对上稳定的方法族
- 如需特定索引/距离度量/批检索等高级能力，可在服务层扩展方法或在你自定义服务中直接持有 SageDB 实例进行封装

## 四、与 Memory/Neuromem 的协作

- Memory Service 在内部可将 VDB Service（SAGE-DB 后端）作为向量检索引擎，统一编排 KV/Graph 与向量后端
- 使用建议：业务 Function 进行“长期记忆”编排时优先通过 memory_service；仅在“纯向量场景”直接使用 vdb_service

## 五、错误处理与性能建议

- 可用性与降级
  - 在服务启动时检测 enterprise.sage_db.is_available()，不可用时降级到其他向量后端
- 批量接口
  - 批量写入/检索可显著提升吞吐；在 VDB Service/SageDB 层选择 batch 接口（若提供）
- 索引与训练
  - 对需要高性能的检索任务，提前构建/训练索引（build_index/train_index），并为查询设置合理的 SearchParams
- 超时与资源
  - 在调用侧设置合理的超时；在服务侧配置线程/内存/GPU 资源，避免 OOM/饱和

## 参考与源码入口

- 企业组件：packages/sage-middleware/src/sage/middleware/enterprise/sage_db/
  - Python 封装：enterprise/sage_db/sage_db.py
  - C++ 实现：enterprise/sage_db/include 与 enterprise/sage_db/src
  - 可用性接口：enterprise/sage_db/__init__.py（is_available, get_status）
- VDB Service：packages/sage-middleware/src/sage/middleware/services/vdb/
  - __init__.py 导出 VDBService, create_vdb_service_factory
  - 示例：services/vdb/examples/vdb_demo.py
