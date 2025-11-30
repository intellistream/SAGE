# L4 Middleware Dev Notes

sage-middleware 属于 L4（中间件层），包含 C++ 扩展、neuromem 内存系统、存储引擎等核心组件。该目录用于追踪这些组件的开发、问题修复及功能增强。

## 目录结构

```
l4-middleware/
├── README.md                          # 本文件
├── archive/                           # 已归档的文档（已完成的 issue 修复等）
│
├── # === Autostop 功能文档 ===
├── AUTOSTOP_MODE_SUPPORT.md           # Autostop 模式在不同执行环境下的支持
├── AUTOSTOP_SERVICE_FIX_SUMMARY.md    # Autostop 服务修复总结
├── REMOTE_AUTOSTOP_IMPLEMENTATION.md  # 远程 Autostop 实现
├── fix-autostop-service-cleanup.md    # Autostop 服务清理修复说明（中文）
├── remote-mode-support.md             # 远程模式支持说明
│
├── # === Document Storage ===
├── DOCUMENT_STORAGE_FEATURE.md        # 文档存储功能架构
├── DOCUMENT_STORAGE_STATUS.md         # 文档存储实现状态 ✅
├── DOCUMENT_STORAGE_USER_GUIDE.md     # 文档存储用户指南（中文）
│
├── # === Neuromem / Graph Memory ===
├── GRAPH_MEMORY_FINAL_STATUS.md       # Graph Memory 实现最终状态 ✅
├── memory-statistics-feature.md       # Memory 统计功能
│
└── song_migration_complete.md         # SONG GPU ANN 后端迁移完成
```

> **归档文档**: Issue #610 (Multimodal Storage) 和 Neuromem 子模块修复相关文档已移动到 `archive/` 目录。

## 核心组件

### 1. Neuromem 内存系统

**位置**: `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/`

| 组件 | 位置 | 功能 |
|------|------|------|
| `TextStorage` | `storage_engine/text_storage.py` | 原始文档存储 |
| `MetadataStorage` | `storage_engine/metadata_storage.py` | 元数据管理 |
| `VectorStorage` | `storage_engine/vector_storage.py` | 向量存储 |
| `VDBMemoryCollection` | `memory_collection/vdb_collection.py` | 向量数据库集合（RAG） |
| `GraphMemoryCollection` | `memory_collection/graph_collection.py` | 图记忆集合 ✅ |
| `MemoryManager` | `memory_manager.py` | 集合生命周期管理 |

### 2. Multimodal Storage

**位置**: `packages/sage-middleware/src/sage/middleware/components/sage_db/python/multimodal_sage_db.py`

支持的模态类型：
- TEXT (文本)
- IMAGE (图片)
- AUDIO (音频)
- VIDEO (视频)
- TABULAR (表格)
- TIME_SERIES (时间序列)
- CUSTOM (自定义)

融合策略 (7 种)：CONCATENATION, WEIGHTED_AVERAGE, ATTENTION_BASED, CROSS_MODAL_TRANSFORMER, TENSOR_FUSION, BILINEAR_POOLING, CUSTOM

### 3. Autostop Service

**功能**: 允许 SAGE 应用在完成任务后自动停止并正确清理后台服务。

支持模式：
- ✅ 本地模式 (LocalEnvironment)
- ✅ Ray 模式 (LocalEnvironment + remote=True)
- ⚠️ 完全远程模式 (RemoteEnvironment) - 部分支持

### 4. SONG GPU ANN 后端

**位置**: `packages/sage-middleware/src/sage/middleware/components/sage_db/`

已完成从 sage-db_outdated 到现代 sage_db 的迁移，移除 LibTorch 依赖，保留 CUDA kernel 实现。

## 已完成的功能

| 功能 | 状态 | 相关文档 |
|------|:----:|----------|
| Document Storage | ✅ | `DOCUMENT_STORAGE_STATUS.md` |
| Graph Memory Collection | ✅ | `GRAPH_MEMORY_FINAL_STATUS.md` |
| Multimodal Storage (#610) | ✅ | `archive/ISSUE_610_STATUS.md` |
| Autostop Local Mode | ✅ | `AUTOSTOP_MODE_SUPPORT.md` |
| SONG GPU Migration | ✅ | `song_migration_complete.md` |

## 代码位置参考

```
packages/sage-middleware/src/sage/middleware/
├── components/
│   ├── sage_db/           # 数据库组件（含 multimodal、SONG）
│   ├── sage_mem/          # 内存系统
│   │   └── neuromem/      # 🔗 git submodule
│   ├── sage_flow/         # 数据流组件
│   ├── sage_refiner/      # Refiner 组件
│   └── sage_tsdb/         # 时序数据库
├── operators/             # 中间件算子
├── context/               # 上下文管理
└── utils/                 # 工具函数
```

## 相关资源

- [Neuromem 架构分析](../cross-layer/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md)
- [数据类型架构](../cross-layer/architecture/DATA_TYPES_ARCHITECTURE.md)
- [公共文档](../../docs-public/docs_src/guides/packages/sage-middleware/)
- [L3 Libs Dev Notes](../l3-libs/) - 上游依赖
- [L5 Apps Dev Notes](../l5-apps/) - 下游消费者
