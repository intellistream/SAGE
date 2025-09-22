# NeuroMemVDB Demo

本条目演示了如何使用 **NeuroMemVDB** 来构建一个向量数据库 (VDB)，并通过全局索引实现 RAG (Retrieval-Augmented Generation) 的简单检索功能。

## 功能简介
- 创建并注册一个向量数据库集合（`demo_collection`）
- 插入 50 条示例数据（涵盖编程语言、AI、NLP、数据库、教育、应用等主题）
- 构建全局索引，支持基于语义的检索
- 使用 `LocalEnvironment` + `BatchFunction` + `SinkFunction` 实现批处理查询与结果输出

## 使用步骤

1. 克隆或保存本项目代码。

2. 运行以下命令，执行数据注入与索引构建：

```bash
   python examples/service/neuromem_vdb/hello_index_data.py
```

3. 运行以下命令，执行在线检索服务推理：
```bash
   python examples/service/neuromem_vdb/hello_neuromem_vdb_service.py 
```

✅ 通过以上步骤，你即可复现一个简易的 **NeuroMemVDB + RAG 检索 Demo**。
