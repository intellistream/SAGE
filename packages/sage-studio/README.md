# SAGE Studio

## 📋 Overview

**SAGE Studio** 是一个现代化的低代码 Web UI 包，用于可视化开发和管理 SAGE 数据流水线。

> **包名**: `isage-studio`\
> **技术栈**: React 18 + TypeScript + FastAPI\\

## 🏗️ 架构概述

Studio 采用**前后端分离**架构，直接接入 SAGE 核心引擎：

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + Vite)                   │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Flow Editor  │  │  Playground  │  │  Properties  │ │
│  │   (画布编辑)   │  │  (对话测试)   │  │  (配置面板)   │ │
│  └───────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ⬇ HTTP/REST API
┌─────────────────────────────────────────────────────────┐
│               后端 (FastAPI - api.py)                    │
│  • 节点注册表 (Node Registry)                            │
│  • Pipeline 构建器 (Pipeline Builder)                    │
│  • API 端点 (flows, operators, execution)               │
└─────────────────────────────────────────────────────────┘
                         ⬇ Python API
┌─────────────────────────────────────────────────────────┐
│                  SAGE 核心引擎                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  sage-kernel (Environment, DataStream API)      │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  sage-middleware (RAG Operators: Generator,     │   │
│  │   Retriever, Reranker, Promptor, Chunker...)    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  sage-libs (IO: FileSource, PrintSink...)       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 关键组件

1. **PipelineBuilder** (`services/pipeline_builder.py`)

   - 将可视化 Flow 转换为 SAGE DataStream Pipeline
   - 拓扑排序节点，构建执行图
   - 映射节点到 SAGE Operator 类

1. **NodeRegistry** (`services/node_registry.py`)

   - 管理 UI 节点类型 → SAGE Operator 的映射
   - 预注册所有 SAGE 中间件算子
   - 支持自定义算子扩展

1. **Backend API** (`config/backend/api.py`)

   - FastAPI 服务，提供 RESTful 接口
   - 处理 Flow 保存/加载、执行请求
   - 调用 PipelineBuilder 构建并执行 SAGE Pipeline

## 🚀 Installation

### Environment Requirements

- **Python**: 3.10+ (必需)
- **Node.js**: 18+ (推荐 LTS)
- **SAGE**: 完整安装 (包括 kernel, middleware, libs)

### 安装 SAGE Studio

```bash
# 方式 1: 通过 SAGE 元包安装（推荐）
pip install isage  # 自动包含 isage-studio

# 方式 2: 开发模式安装
cd packages/sage-studio
pip install -e .

# 验证安装
python -c "from sage.studio.studio_manager import StudioManager; print('✓ Studio installed')"
```

## 📖 Quick Start

### 🎯 方式一：使用 SAGE CLI（推荐）

```bash
# 启动 Studio（前端 + 后端）- 开发模式（推荐）
sage studio start --dev

# 或者生产模式（需要先构建）
sage studio start

# 查看运行状态
sage studio status

# 在浏览器中打开
sage studio open

# 查看日志
sage studio logs          # 前端日志
sage studio logs --backend # 后端日志

# 停止服务
sage studio stop

# 管理前端依赖
sage studio npm install    # 安装/更新 npm 依赖
sage studio npm run lint   # 运行前端脚本
```

**访问地址**：

- 🌐 前端：http://localhost:5173
- 🔌 后端：http://localhost:8080

**注意**：首次使用或开发调试时，建议使用 `--dev` 开发模式，启动更快且支持热重载。

### 🎯 方式二：手动启动（开发调试）

```bash
# 终端 1: 启动后端
cd packages/sage-studio
python -m sage.studio.config.backend.api
# 后端运行在: http://localhost:8080

# 终端 2: 启动前端
cd packages/sage-studio/src/sage/studio/frontend
sage studio npm install
sage studio npm run dev
# 前端运行在: http://localhost:5173
```

### 检查服务状态

```bash
# 检查端口
lsof -i :8080  # 后端
lsof -i :5173  # 前端

# 检查后端健康
curl http://localhost:8080/health

# 查看日志
tail -f /tmp/sage-studio-backend.log
tail -f /tmp/sage-studio-frontend.log
```

## 💡 使用指南

### 1. 创建 Pipeline

**步骤**:

1. 在浏览器打开 http://localhost:5173
1. 从左侧节点面板拖拽节点到画布
1. 连接节点创建数据流
1. 点击节点配置参数（右侧属性面板）
1. 点击工具栏 "保存" 按钮

**示例 RAG Pipeline**:

```
FileSource → SimpleRetriever → BGEReranker → QAPromptor → OpenAIGenerator → PrintSink
```

### 2. 使用 Playground

**Playground** 是对话式测试界面，可以直接与 Pipeline 交互。

**步骤**:

1. 保存 Flow 后，点击工具栏 "💬 Playground" 按钮
1. 在输入框输入消息（如查询问题）
1. 按 Enter 发送（Shift+Enter 换行）
1. 查看 AI 响应和执行步骤

**特性**:

- ✅ 实时执行 Pipeline
- ✅ 显示 Agent 步骤（每个节点的执行过程）
- ✅ 代码生成（Python / cURL）
- ✅ 会话管理（多轮对话）

### 3. 核心功能

#### 画布编辑

- 🎨 拖放节点到画布
- 🔗 连接节点创建数据流
- ⚙️ 动态配置节点参数
- 🔍 画布缩放和导航

#### 流程管理

- 💾 保存/加载流程
- 📋 流程列表查看
- 🗑️ 删除流程
- 📤 导出流程为 JSON 文件
- 📥 导入流程配置

#### MVP 增强功能 ✨ (v0.2.0-alpha)

**1. 节点输出预览**

- 实时查看节点执行输出
- 支持 JSON 格式化显示
- 支持原始数据和错误信息查看
- 使用方法：选择节点 → 右侧属性面板 → "输出预览" 标签

**2. 流程导入/导出**

- 导出完整流程配置为 JSON
- 从文件导入流程
- 支持流程分享和备份
- 使用方法：工具栏 → "导出" / "导入" 按钮

**3. 环境变量管理**

- 图形化管理 API 密钥等配置
- 密码字段安全输入
- 支持增量更新
- 使用方法：工具栏 → "设置" 按钮（齿轮图标）

**4. 实时日志查看器**

- 终端风格的日志显示
- 按节点/级别过滤
- 自动滚动和导出功能
- 使用方法：底部状态栏 → "显示日志" 按钮

📖 **详细文档**: 查看 [MVP_ENHANCEMENT.md](./MVP_ENHANCEMENT.md) 了解完整功能说明

#### 快捷键

- `Ctrl+S`: 保存流程
- `Ctrl+Z`: 撤销
- `Ctrl+Shift+Z` / `Ctrl+Y`: 重做
- `Delete`: 删除选中节点
- `Escape`: 取消选择

### 4. 前端开发

```bash
cd src/sage/studio/frontend

# 开发模式
sage studio npm run dev          # 启动 Vite dev server (localhost:5173)

# 生产构建
sage studio npm run build        # 构建到 dist/
sage studio npm run preview      # 预览构建结果

# 代码质量
sage studio npm run lint         # ESLint 检查
sage studio npm run format       # Prettier 格式化
```

### 5. 后端开发

```bash
cd packages/sage-studio

# 直接运行
python -m sage.studio.config.backend.api

# 验证运行
curl http://localhost:8080/health

# 查看 API 文档
open http://localhost:8080/docs  # Swagger UI
```

## 📂 目录结构

```
sage-studio/
├── README.md                      # 本文件 ⭐
├── pyproject.toml                # 包配置和依赖
│
├── src/sage/studio/
│   ├── __init__.py
│   ├── studio_manager.py         # Studio 管理器 ⭐
│   │
│   ├── config/backend/
│   │   └── api.py                # FastAPI 后端 ⭐
│   │
│   ├── services/                 # 核心服务 ⭐
│   │   ├── node_registry.py      # 节点注册表 (UI → SAGE Operator 映射)
│   │   └── pipeline_builder.py  # Pipeline 构建器 (转换为 SAGE DataStream)
│   │
│   ├── models/                   # 数据模型
│   │   └── __init__.py           # VisualPipeline, VisualNode, VisualConnection
│   │
│   ├── data/operators/           # 节点定义 JSON 文件
│   │   ├── FileSource.json
│   │   ├── SimpleRetriever.json
│   │   ├── OpenAIGenerator.json
│   │   └── ...
│   │
│   └── frontend/                 # React 前端 ⭐
│       ├── package.json          # 前端依赖
│       ├── vite.config.ts        # Vite 配置
│       ├── tsconfig.json         # TypeScript 配置
│       └── src/
│           ├── App.tsx           # 主应用组件
│           ├── components/       # React 组件
│           │   ├── FlowEditor.tsx      # React Flow 画布
│           │   ├── Toolbar.tsx         # 工具栏 (保存/加载/运行)
│           │   ├── NodePalette.tsx     # 节点面板
│           │   ├── PropertiesPanel.tsx # 属性配置
│           │   └── Playground.tsx      # Playground 对话界面
│           ├── store/            # Zustand 状态管理
│           │   ├── flowStore.ts        # Flow 编辑状态
│           │   └── playgroundStore.ts  # Playground 状态
│           ├── hooks/            # 自定义 Hooks
│           │   ├── useJobStatusPolling.ts
│           │   └── useKeyboardShortcuts.ts
│           └── services/         # API 客户端
│               └── api.ts        # 后端 API 封装
│
└── tests/
    ├── test_node_registry.py     # 节点注册表测试
    ├── test_pipeline_builder.py  # Pipeline 构建器测试
    └── test_studio_cli.py        # CLI 命令测试
```

## 🔧 工作原理

### 从可视化到执行

```
1️⃣ 用户在 UI 中创建 Flow
   └─> VisualPipeline (nodes + connections)

2️⃣ 保存 Flow
   └─> 序列化为 JSON → .sage/pipelines/pipeline_xxx.json

3️⃣ 点击 "执行" / Playground 发送消息
   └─> POST /api/playground/execute
       │
       ├─> 加载 Flow JSON
       │
       ├─> PipelineBuilder.build(visual_pipeline)
       │   ├─> 拓扑排序节点（确定执行顺序）
       │   ├─> NodeRegistry 查找 Operator 类
       │   └─> 使用 SAGE DataStream API 构建 Pipeline:
       │       env.from_source(...)
       │          .map(Retriever, ...)
       │          .map(Reranker, ...)
       │          .map(Promptor, ...)
       │          .map(Generator, ...)
       │          .sink(PrintSink)
       │
       └─> env.execute() → SAGE 引擎执行
           └─> 返回结果给前端
```

### 核心服务详解

#### 1. NodeRegistry（节点注册表）

**职责**: 管理 UI 节点类型 → SAGE Operator 类的映射

**示例映射**:

```python
{
    "generator": OpenAIGenerator,      # sage-middleware
    "retriever": ChromaRetriever,      # sage-middleware
    "reranker": BGEReranker,          # sage-middleware
    "promptor": QAPromptor,           # sage-middleware
    "chunker": CharacterSplitter,     # sage-libs
    "evaluator": F1Evaluate,          # sage-middleware
}
```

**扩展方式**:

```python
from sage.studio.services import get_node_registry

registry = get_node_registry()
registry.register("my_custom_op", MyCustomOperator)
```

#### 2. PipelineBuilder（Pipeline 构建器）

**职责**: 将 VisualPipeline 转换为可执行的 SAGE Pipeline

**关键步骤**:

1. **验证**: 检查节点类型是否已注册、连接是否有效
1. **拓扑排序**: 使用 Kahn 算法确定执行顺序，检测循环依赖
1. **构建 DataStream**:
   ```python
   env = LocalEnvironment()
   stream = env.from_source(FileSource, "data.txt")
   stream = stream.map(Retriever, config={...})
   stream = stream.map(Generator, config={...})
   stream.sink(PrintSink)
   ```
1. **返回 Environment**: 调用方执行 `env.execute()`

#### 3. Backend API（FastAPI 服务）

**主要端点**:

- `GET /api/operators`: 获取所有可用节点类型
- `POST /api/pipeline/submit`: 保存 Flow
- `GET /api/jobs/all`: 获取所有 Pipeline（包括已保存的 Flow）
- `POST /api/playground/execute`: 执行 Playground 对话
- `GET /api/signal/status/{job_id}`: 查询执行状态

**数据存储**:

- `.sage/pipelines/`: Flow JSON 文件
- `.sage/states/`: 运行时状态
- `.sage/configs/`: Pipeline 配置

### 技术栈

#### 前端

```
React 18.2 + TypeScript 5.2
├── React Flow 11.10.4      # 可视化图编辑器
├── Ant Design 5.12         # UI 组件库
├── Zustand 4.4.7           # 状态管理
├── Axios 1.6.2             # HTTP 客户端
└── Vite 5.0.8              # 构建工具
```

#### 后端

```
FastAPI + Python 3.10+
├── Pydantic 2.0            # 数据验证
├── Uvicorn                 # ASGI 服务器
├── sage-kernel             # Environment, DataStream API
├── sage-middleware         # RAG Operators
└── sage-libs               # IO: Source, Sink
```

### 数据流

```
前端 (localhost:5173)
    ↓ HTTP REST
后端 API (localhost:8080)
    ↓ Python API
SAGE 引擎
    ├─> sage-kernel (执行引擎)
    ├─> sage-middleware (算子库)
    └─> sage-libs (IO 工具)
```

## 🛠️ 开发指南

### 添加自定义节点

**步骤 1**: 实现 SAGE Operator

```python
# my_custom_package/my_operator.py
from sage.common.core import MapOperator

class MyCustomOperator(MapOperator):
    """自定义算子"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.param = config.get("param", "default")

    def execute(self, data):
        # 实现算子逻辑
        result = self.process(data)
        return result
```

**步骤 2**: 注册到 NodeRegistry

```python
# 在 node_registry.py 中添加
from my_custom_package.my_operator import MyCustomOperator

def _register_default_operators(self):
    # ...现有注册...

    # 自定义算子
    self._registry["my_custom"] = MyCustomOperator
```

**步骤 3**: 创建节点定义 JSON

```json
// data/operators/MyCustomOperator.json
{
    "id": 999,
    "name": "MyCustomOperator",
    "description": "我的自定义算子",
    "module_path": "my_custom_package.my_operator",
    "class_name": "MyCustomOperator",
    "isCustom": true
}
```

**步骤 4**: 重启 Studio

```bash
sage studio stop
sage studio start
```

现在可以在 UI 中使用新节点了！

### 扩展数据源

支持的数据源类型（在 `PipelineBuilder._create_source` 中）:

- `file`: 通用文件源
- `json_file`: JSON 文件
- `csv_file`: CSV 文件
- `text_file`: 文本文件
- `socket`: 网络 socket
- `kafka`: Kafka topic
- `database`: 数据库查询
- `api`: HTTP API

**添加新数据源**:

```python
# 在 pipeline_builder.py 的 _create_source 中添加
elif source_type == "my_source":
    # 自定义参数
    param1 = node.config.get("param1")
    param2 = node.config.get("param2")
    return MyCustomSource, (param1, param2), {}
```

### 调试技巧

```bash
# 1. 检查端口占用
lsof -i :5173  # 前端
lsof -i :8080  # 后端

# 2. 查看日志
sage studio logs          # 前端日志
sage studio logs --backend # 后端日志

# 或直接查看日志文件
tail -f ~/.sage/studio_backend.log
tail -f ~/.sage/studio.log

# 3. 测试后端 API
curl http://localhost:8080/health
curl http://localhost:8080/api/operators

# 4. 清理缓存
rm -rf ~/.sage/studio/node_modules
rm -rf ~/.sage/studio/.vite
rm -rf ~/.sage/pipelines/*
rm -rf ~/.sage/states/*

# 5. 重新安装依赖
cd src/sage/studio/frontend
rm -rf node_modules package-lock.json
sage studio npm install

# 6. Python 调试
python -m pdb -m sage.studio.config.backend.api

# 7. 查看 SAGE Pipeline 构建过程
# 在 api.py 中添加 print 语句
print(f"Building pipeline: {visual_pipeline}")
```

### 单元测试

```bash
# 运行所有测试
cd packages/sage-studio
pytest tests/

# 运行特定测试
pytest tests/test_node_registry.py
pytest tests/test_pipeline_builder.py

# 带覆盖率
pytest --cov=src/sage/studio tests/
```

### 代码质量

```bash
# Python 代码格式化
cd packages/sage-studio
black src/
isort src/

# 类型检查
mypy src/

# Linting
ruff check src/

# 前端代码格式化
cd src/sage/studio/frontend
sage studio npm run format
sage studio npm run lint
```

## 📋 依赖关系

### Python 依赖

**SAGE 核心组件** (必需):

- `isage-kernel>=0.1.0` - 执行引擎 (Environment, DataStream API)
- `isage-middleware>=0.1.0` - RAG 算子库 (Generator, Retriever, Reranker...)
- `isage-libs>=0.1.0` - IO 工具 (FileSource, PrintSink...)
- `isage-common>=0.1.0` - 通用组件

**Web 框架**:

- `fastapi>=0.115,<0.116` - REST API 框架
- `uvicorn[standard]>=0.34.0` - ASGI 服务器
- `pydantic>=2.0.0` - 数据验证

**工具库**:

- `psutil` - 进程管理 (StudioManager)
- `requests` - HTTP 客户端
- `rich` - 终端 UI

### 前端依赖

**核心框架**:

- `react@^18.2.0` - UI 框架
- `react-dom@^18.2.0` - DOM 渲染
- `typescript@^5.2.2` - 类型系统

**UI 组件**:

- `reactflow@^11.10.4` - 流程图编辑器
- `antd@^5.12.0` - Ant Design 组件库
- `lucide-react@^0.294.0` - 图标库

**状态管理**:

- `zustand@^4.4.7` - 轻量级状态管理

**构建工具**:

- `vite@^5.0.8` - 开发服务器和构建工具
- `@vitejs/plugin-react@^4.2.1` - React 插件

完整依赖列表见 `pyproject.toml` 和 `frontend/package.json`。

## 🐛 故障排除

### 常见问题

#### 1. 后端无响应

```bash
# 检查进程
ps aux | grep "sage.studio.config.backend.api"

# 检查端口
lsof -i :8080

# 查看日志
tail -f /tmp/sage-studio-backend.log

# 重启后端
kill -9 <PID>
python -m sage.studio.config.backend.api &
```

**可能原因**:

- ❌ SAGE 包未正确安装 → `pip install -e packages/sage-kernel packages/sage-middleware packages/sage-libs`
- ❌ 缺少依赖 → `pip install -e packages/sage-studio`
- ❌ 端口被占用 → `lsof -i :8080` 查看占用进程

#### 2. 前端编译/启动错误

```bash
cd src/sage/studio/frontend

# 清理缓存
rm -rf node_modules package-lock.json .vite

# 重新安装
sage studio npm install

# 启动
sage studio npm run dev
```

**可能原因**:

- ❌ Node.js 版本过低 → 需要 18+
- ❌ npm 依赖损坏 → 删除 `node_modules` 重新安装
- ❌ 端口被占用 → Vite 会自动尝试 5174, 5175...

#### 3. Pipeline 执行失败

```bash
# 查看详细错误
tail -f /tmp/sage-studio-backend.log

# 检查 SAGE 安装
python -c "from sage.kernel.api import LocalEnvironment; print('✓ kernel OK')"
python -c "from sage.middleware.rag import OpenAIGenerator; print('✓ middleware OK')"
python -c "from sage.libs.io.source import FileSource; print('✓ libs OK')"
```

**可能原因**:

- ❌ 节点类型未注册 → 检查 `node_registry.py`
- ❌ 节点配置错误 → 检查节点参数是否正确
- ❌ SAGE Operator 导入失败 → 检查包安装

#### 4. Playground 无响应

```bash
# 检查 Flow 是否保存
ls ~/.sage/pipelines/

# 检查后端 API
curl -X POST http://localhost:8080/api/playground/execute \
  -H "Content-Type: application/json" \
  -d '{"flowId": "pipeline_xxx", "input": "test", "sessionId": "test"}'
```

**可能原因**:

- ❌ Flow 未保存 → 先保存 Flow
- ❌ 后端未启动 → 检查 `lsof -i :8080`
- ❌ 网络请求失败 → 检查浏览器控制台

#### 5. 端口被占用

```bash
# 查看占用
lsof -i :5173  # 前端
lsof -i :8080  # 后端

# 杀死进程
kill -9 $(lsof -t -i:5173)
kill -9 $(lsof -t -i:8080)

# 或使用 SAGE CLI
sage studio stop
sage studio start --dev
```

#### 6. 环境问题

```bash
# 检查 Python 版本
python --version  # 需要 3.10+

# 检查 SAGE 安装
pip list | grep isage

# 检查 Node.js 版本
node --version  # 需要 18+
npm --version

# 检查工作目录
pwd  # 应该在 SAGE 项目根目录或 sage-studio 目录
```

### 完全重置

如果问题持续，尝试完全重置：

```bash
# 1. 停止所有服务
sage studio stop
kill -9 $(lsof -t -i:8080)
kill -9 $(lsof -t -i:5173)

# 2. 清理缓存
rm -rf ~/.sage/studio/
rm -rf ~/.sage/cache/
rm -rf /tmp/sage-studio-*.log

# 3. 重新安装前端依赖
cd packages/sage-studio/src/sage/studio/frontend
rm -rf node_modules package-lock.json .vite
sage studio npm install

# 4. 重新安装 Python 包
cd packages/sage-studio
pip install -e .

# 5. 重新启动
sage studio start --dev
```

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.
