```
sage/
├── api/                  # 开放给用户开发应用的高层 API
│   ├── memory/           # Memory API（memory.create / connect / collection.write 等）
│   ├── model/            # 模型调用（embedding_model, model.apply 等）
│   ├── operator/         # 开发者定义的 Operator 接口（SourceFunction 等）
│   ├── pipeline/         # 构建 Logical Graph（Pipeline, submit）
│   └── __init__.py       # 提供 import sage.* 的统一入口
│
├── core/                 # 系统底层核心执行逻辑
│   ├── compiler/         # Query compiler，将 pipeline 编译为物理图 DAG
│   ├── dag/              # DAG 结构与 DAGNode 定义
│   ├── engine/           # Runtime 执行引擎（负责调度 DAGNode，调用 operator.execute）
│   ├── io/               # I/O Queue 实现（算子之间的异步通信）
│   ├── metrics/          # 性能与运行状态监控（延迟、吞吐量等）
│   ├── neuronmem/        # 底层 Memory 系统（Memory Collection + backend 接入）
│   ├── operator/         # 系统内置 Operator 实现（可选，与 api.operator 区分）
│   └── __init__.py
└── __init__.py           # 顶层统一包入口
```

