# Middleware 分层与实践指南

SAGE Middleware 的代码现实主要围绕 Neuromem
记忆栈展开。下文从实际实现出发，重新梳理“中间件层”在当前仓库中的分层与用法，避免与历史文档中尚未落地的微服务网格、硬件调度等概念混淆。

## 当前四层结构

1. **API 层**（`sage.core.api`）

   - `BaseFunction` / `BaseService` 的 `call_service` 与 `call_service_async` 构成了唯一稳定的对外接口。
   - 目前没有专门的 Service API Gateway，函数直接依赖注册表中的服务实例。

1. **服务层**（示例封装）

   - 现有示例包括 `NeuroMemVDBService`、`SageDBService`、`SageFlowService`，分别位于
     `components/<component>/micro_service/`，用于把相应组件包装成 `BaseService` 风格的进程内服务。
   - 不包含服务发现、注册中心或远程通信；所有调用路径依旧是进程内对象间的直接调用。

1. **组件层**（核心逻辑）

   - `neuromem`、`sage_db`、`sage_flow` 共同构成组件层：前者提供纯 Python 的记忆栈，后两者提供可选的 C++ 加速与各自的数据结构实现。
   - Neuromem 下的 `MemoryManager` 管理集合生命周期，`VDBMemoryCollection` / `KVMemoryCollection` /
     `GraphMemoryCollection` 提供多种读写能力（当前以 VDB 为主），并通过 `search_engine/` 与 `storage_engine/`
     的工厂模式装配索引与存储。
   - `sage_db`、`sage_flow` 在成功构建对应扩展时公开 Python 绑定与服务封装；若扩展缺失则在导入阶段降级为不可用状态。

1. **存储 / 执行层**

   - 文本与元数据分别由 `TextStorage`、`MetadataStorage`（基于本地文件）持久化。
   - 向量索引依赖 `index_factory`（默认 FAISS），可根据配置落盘并重建。

## 实践要点

- **关注真实可用的入口**：默认构建仅包含 `NeuroMemVDB` / `NeuroMemVDBService`；`SageDBService`、`SageFlowService`
  需先按各自仓库说明完成 C++ 扩展构建后方可启用。
- **提前创建索引**：`NeuroMemVDBService` 假设集合存在 `global_index`；在实例化前先调用 `create_index` + `init_index`。
- **嵌入模型准备**：默认走 HuggingFace 模型，若需离线/自定义模型，可通过 `EmbeddingModel(method="mockembedder", ...)`
  或传入自定义参数。
- **持久化路径**：默认写到当前工作目录下的 `data/neuromem_vdb/`，在容器或生产环境中请显式指定 `MemoryManager` 的 `data_dir`。
- **测试策略**：利用 `NeuroMemVDB` 的批量插入与 `retrieve`，可以在不启动任何额外服务的情况下完成功能验证。

## 后续演进方向（尚未实现）

- 真正的远程服务化（HTTP/gRPC）与服务注册中心。
- 面向 KV / Graph 集合的完整实现与统一编排。
- 与 Ray、消息队列等内核通信层的深度结合。
- 基于可用扩展的 GPU / C++ 加速通路。
