# SAGE Memory Pipeline 规范化重构任务总览

> 本文档描述记忆系统的规范化重构任务，按模块拆分为互不干扰的独立任务。

## 一、重构目标

根据记忆系统的架构约束，本次重构旨在：

1. **统一记忆服务接口**：所有 MemoryService 的 insert/retrieve/delete 接口统一
1. **规范算子操作边界**：每个 pre\_/post\_ 算子只有大类操作，小类方法不建立类函数
1. **支持主动/被动插入**：PreInsert 传递插入方法，MemoryInsert 执行具体插入
1. **明确职责边界**：严格遵循各阶段的存储访问约束

## 二、架构约束（必须遵守）

```
记忆操作（4 阶段）+ 记忆数据结构

记忆数据结构：
├── 统一接口：insert(entry, vector, metadata, insert_mode, insert_params) -> str
│             retrieve(query, vector, metadata, top_k) -> list[dict]
│             delete(entry_id) -> bool
└── 插入可提供多种方法，检索/删除方法固定

记忆操作：
├── PreInsert   : 预处理记忆数据，决定插入方式，仅允许检索
├── MemoryInsert: 根据数据和插入方法执行插入
├── PostInsert  : 优化记忆数据结构，仅允许一次 检索→删除→插入
├── PreRetrieval: 预处理提问，不允许访问记忆数据结构
├── MemoryRetrieval: 根据提问返回结果，不允许外部决定检索方式
└── PostRetrieval: 处理返回结果，允许多次查询并拼接 prompt
```

## 三、重构任务拆分

### 任务一：MemoryService 统一接口规范（R-SERVICE）

**文件**: `REFACTOR_R1_SERVICE_INTERFACE.md`

**范围**: `packages/sage-middleware/src/sage/middleware/components/sage_mem/services/`

**目标**: 统一所有 MemoryService 的接口签名

**负责人可独立完成**: ✅ 是

______________________________________________________________________

### 任务二：PreInsert 算子重构（R-PRE-INSERT）

**文件**: `REFACTOR_R2_PRE_INSERT.md`

**范围**: `packages/sage-benchmark/.../libs/pre_insert.py`

**目标**:

1. 只保留大类操作方法（action 级别）
1. 小类实现逻辑内联到大类方法中
1. 支持传递插入方法给 MemoryInsert

**负责人可独立完成**: ✅ 是

______________________________________________________________________

### 任务三：PostInsert 算子重构（R-POST-INSERT）

**文件**: `REFACTOR_R3_POST_INSERT.md`

**范围**: `packages/sage-benchmark/.../libs/post_insert.py`

**目标**:

1. 只保留大类操作方法
1. 服务级操作统一通过 optimize() 委托
1. 严格遵循"一次 检索→删除→插入"约束

**负责人可独立完成**: ✅ 是

______________________________________________________________________

### 任务四：PreRetrieval 算子重构（R-PRE-RETRIEVAL）

**文件**: `REFACTOR_R4_PRE_RETRIEVAL.md`

**范围**: `packages/sage-benchmark/.../libs/pre_retrieval.py`

**目标**:

1. 只保留大类操作方法
1. 确保不访问记忆数据结构

**负责人可独立完成**: ✅ 是

______________________________________________________________________

### 任务五：PostRetrieval 算子重构（R-POST-RETRIEVAL）

**文件**: `REFACTOR_R5_POST_RETRIEVAL.md`

**范围**: `packages/sage-benchmark/.../libs/post_retrieval.py`

**目标**:

1. 只保留大类操作方法
1. 允许多次查询服务

**负责人可独立完成**: ✅ 是

______________________________________________________________________

### 任务六：MemoryInsert 插入方法扩展（R-MEM-INSERT）

**文件**: `REFACTOR_R6_MEMORY_INSERT.md`

**范围**: `packages/sage-benchmark/.../libs/memory_insert.py`

**目标**:

1. 支持从 PreInsert 接收插入方法
1. 根据 insert_mode 和 insert_params 调用服务

**负责人可独立完成**: ✅ 是

______________________________________________________________________

## 四、任务依赖关系

```
任务一（R-SERVICE）
    ↓
    ├─→ 任务二（R-PRE-INSERT）
    ├─→ 任务三（R-POST-INSERT）
    ├─→ 任务四（R-PRE-RETRIEVAL）
    ├─→ 任务五（R-POST-RETRIEVAL）
    └─→ 任务六（R-MEM-INSERT）
```

**说明**：

- 任务一是基础，定义统一接口后，其他任务可并行进行
- 任务二~六互不依赖，可独立完成

## 五、验收标准

1. **接口统一**：所有 MemoryService 遵循相同的方法签名
1. **代码规范**：算子只有大类方法，小类逻辑内联
1. **约束遵守**：各阶段的存储访问权限正确
1. **测试通过**：现有测试用例不回归

## 六、注意事项

1. 修改服务接口时需同步更新 `MemoryServiceFactory`
1. 保持向后兼容，可选参数使用默认值
1. 每个任务完成后需运行 `sage-dev project test` 验证
