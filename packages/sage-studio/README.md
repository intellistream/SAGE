# SAGE Studio

**SAGE Studio** 是一个现代化的低代码 Web UI 包，用于可视化开发和管理 SAGE RAG 数据流水线。

> **包名**: `isage-studio`  
> **技术栈**: React 18 + FastAPI  

## 快速开始

### 环境要求

- **Python**: 3.8+ (推荐 3.10)
- **Node.js**: 16+ (推荐 18)
- **Conda**: sage 环境

### 🎯 推荐方式：使用 SAGE CLI（最简单！）

```bash
# 一键启动 Studio（前端 + 后端）
sage studio start

# 查看运行状态
sage studio status

# 在浏览器中打开
sage studio open

# 查看日志
sage studio logs

# 停止服务
sage studio stop
```

**访问地址**：
- 🌐 前端：http://localhost:5173
- 🔌 后端：http://localhost:8080

### 方式二：手动启动（开发调试）

```bash
# 1. 启动后端 API（在 sage 环境中）
cd SAGE/packages/sage-studio
python -m sage.studio.config.backend.api &
# 后端运行在: http://localhost:8080

# 2. 启动前端界面（React v2）
cd frontend
npm install  # 首次运行
npm run dev
# 前端访问: http://localhost:3000 或 http://localhost:3001
```

### 检查服务状态

```bash
# 检查后端
lsof -i :8080

# 检查 conda 环境
conda info --envs | grep "*"
# 应该显示: sage * miniconda3/envs/sage

# 验证 Phase 1 功能
python verify_standalone.py
python test_phase1.py
```

## 📦 安装（可选）

如果需要完整安装：

```bash
# 完整安装 SAGE（包括 Studio）
pip install isage

# 或使用快速安装脚本
./quickstart.sh

# 开发模式安装
cd packages/sage-studio
pip install -e .
```

## � 使用方式

### React 前端 v2.0（推荐）

```bash
cd frontend

# 开发模式
npm run dev          # 启动开发服务器 (localhost:3000/3001)
npm run build        # 构建生产版本
npm run preview      # 预览构建结果

# 代码质量
npm run lint         # ESLint 检查
npm run type-check   # TypeScript 类型检查
```

**核心功能**:
- 🎨 拖放节点到画布
- 🔗 连接节点创建数据流
- ⚙️ 动态配置节点参数
- 💾 保存/加载流程
- ▶️ 运行/停止流程（实时状态更新）
- 🔍 画布缩放和导航
- ↩️ 撤销/重做 (Ctrl+Z/Ctrl+Shift+Z)
- ⌨️ 键盘快捷键 (Ctrl+S 保存, Delete 删除)
- 🔄 兼容旧版 Angular 格式

### Angular 前端（旧版 - 仅兼容性保留）

**注意**: Phase 1 已完成，推荐使用 React v2 前端。

```bash
# 如需使用旧版 Angular 界面
sage studio start     # http://localhost:4200
sage studio stop
```

### 后端 API

```bash
# 直接运行
python -m sage.studio.config.backend.api

# 验证运行
curl http://localhost:8080/health
```

## 📂 目录结构

```
sage-studio/
├── README.md                      # 本文件 ⭐
├── QUICK_ACCESS.md               # 快速访问入口 ⭐
├── STANDALONE_MODE_INDEX.md      # Phase 1 文档导航
│
├── frontend/                  # React 前端 v2.0 ⭐
│   ├── src/
│   │   ├── components/           # React 组件
│   │   │   ├── FlowCanvas.tsx    # React Flow 画布
│   │   │   ├── Toolbar.tsx       # 工具栏 (保存/加载/运行/撤销/重做)
│   │   │   ├── NodePanel.tsx     # 节点库
│   │   │   └── ConfigPanel.tsx   # 配置面板
│   │   ├── store/                # Zustand 状态管理
│   │   │   └── flowStore.ts      # 流程状态 (含历史栈)
│   │   ├── hooks/                # 自定义 Hooks
│   │   │   ├── useJobStatusPolling.ts   # 状态轮询
│   │   │   └── useKeyboardShortcuts.ts  # 快捷键
│   │   └── services/             # API 客户端
│   │       └── api.ts            # API 封装
│   ├── CHANGELOG.md              # 更新日志
│   ├── PHASE2_FINAL_COMPLETION_REPORT.md  # Phase 2 完成报告
│   ├── PHASE3_PLAYGROUND_PLAN.md         # Phase 3 规划
│   ├── FIX_UNDO_REDO_BUG_REPORT.md      # Bug 修复报告
│   └── UNDO_REDO_TEST_CHECKLIST.md      # 测试清单
│
├── src/sage/studio/
│   ├── config/backend/
│   │   └── api.py                # FastAPI 后端 ⭐
│   ├── data/                     # 节点定义
│   ├── docs/                     # 文档
│   └── frontend/                 # Angular 前端（旧版）
│
├── docs/
│   ├── standalone-mode/          # Phase 1 文档 (已完成)
│   ├── COMPETITIVE_ANALYSIS.md   # 竞品分析 ⭐
│   └── COMPETITIVE_STRATEGY_QUICKREF.md  # 战略快速参考
│
├── verify_standalone.py          # 验证脚本
├── QUICK_ACCESS.md               # 快速访问入口 ⭐
└── pyproject.toml                # 包配置
```

## 🏗️ 技术架构

### 前端架构（React v2.0）

```
React 18.2.0 + TypeScript 5.2.2
├── React Flow 11.10.4      # 可视化图编辑器
├── Ant Design 5.22.6       # UI 组件库
├── Zustand 4.4.7           # 状态管理
├── Axios 1.6.2             # HTTP 客户端
├── Vite 5.0.8              # 构建工具
└── Tailwind CSS 3.4.0      # 样式框架
```

**关键特性**:
- 🎯 **TypeScript 全覆盖**: 完整的类型安全
- 🔄 **React Flow**: 高性能图形编辑器
- 📦 **模块化设计**: 组件、状态、服务分离
- 🎨 **响应式布局**: 适配各种屏幕尺寸

### 后端架构（FastAPI）

```
FastAPI + Python 3.10+
├── Phase 1 接口抽象层
│   ├── 插件系统 (BasePlugin)
│   ├── 节点定义 (OperatorNode)
│   └── 执行引擎 (PipelineExecutor)
├── RESTful API
│   ├── /flows              # 流程管理
│   ├── /jobs               # 任务执行
│   └── /operators          # 节点定义
└── 文件系统存储
    └── .sage/              # 数据目录
```

### 数据流

```
用户操作
    ↓
Frontend (localhost:3000)
    ↓ Vite Proxy (/api → :8080)
Backend API (localhost:8080)
    ↓
.sage/ 目录
    ├── pipelines/      # 流程配置 JSON
    ├── states/         # 运行状态
    └── operators/      # 节点定义
```

### 包分离设计

- **sage-studio**: 包含所有 Studio 功能（前端、后端、管理器）
- **sage-tools**: 提供 CLI 命令集成
- **sage**: 元包，默认依赖所有组件

优点：
- ✅ 功能独立，易于维护
- ✅ 可选安装（灵活部署）
- ✅ 清晰的依赖关系

## 🛠️ 开发指南

### React 前端开发（v2.0）

```bash
cd frontend

# 开发服务器
npm run dev              # http://localhost:3000

# 代码质量
npm run lint             # ESLint 检查
npm run lint:fix         # 自动修复
npm run type-check       # TypeScript 检查

# 构建
npm run build            # 生产构建
npm run preview          # 预览构建结果

# 测试（待添加）
npm test
```

**开发建议**:
- 使用 TypeScript 严格模式
- 遵循 React Hooks 最佳实践
- 组件职责单一，便于测试
- API 调用统一在 `services/` 目录

### 后端开发（FastAPI）

```bash
cd SAGE/packages/sage-studio

# 开发模式
python -m sage.studio.config.backend.api

# Phase 1 测试
python test_phase1.py

# 验证独立运行
python verify_standalone.py

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

### 调试技巧

```bash
# 检查端口占用
lsof -i :3000  # 前端
lsof -i :8080  # 后端

# 查看日志
tail -f ~/.sage/logs/api.log

# 重启服务
# 前端：Ctrl+C 后重新 npm run dev
# 后端：kill 进程后重启 Python

# 清理缓存
rm -rf frontend/node_modules
rm -rf .sage/states/*
```

## 📋 依赖关系

### 核心依赖
- `isage-common>=0.1.0` - 通用组件
- `isage-kernel>=0.1.0` - 核心引擎
- `isage-middleware>=0.1.0` - 中间件
- `isage-libs>=0.1.0` - 应用库

### Web 框架
- `fastapi>=0.115,<0.116` - Web 框架
- `uvicorn[standard]>=0.34.0` - ASGI 服务器
- `starlette>=0.40,<0.47` - Web 工具包
- `websockets>=11.0` - WebSocket 支持


## 🔄 升级指南

### 从 Angular (Phase 1) 迁移到 React (Phase 2)

**流程兼容性**: ✅ 自动处理

React 前端会自动检测和转换 Angular 格式的流程：

```typescript
// 自动检测逻辑（Toolbar.tsx）
const isAngularFormat = 
  pipeline.elements?.[0]?.data?.operatorId !== undefined;

if (isAngularFormat) {
  // 自动转换为 React Flow 格式
  convertedNodes = convertAngularToReactFlow(pipeline);
}
```

**旧格式（Angular）**:
```json
{
  "elements": [{
    "data": {"operatorId": "source_local", ...}
  }]
}
```

**新格式（React Flow）**:
```json
{
  "nodes": [{
    "data": {"label": "本地文件源", ...}
  }]
}
```

**迁移步骤**:
1. ✅ 无需手动操作，加载时自动转换
2. ✅ 编辑后保存为新格式
3. ✅ 保留原始格式在 `config` 字段

### 从旧版 Studio 升级

```bash
# 升级到新版本
pip install --upgrade isage isage-studio isage-tools

# 或重新运行安装脚本
./quickstart.sh

# 导入路径无需修改
from sage.studio.studio_manager import StudioManager
```

## 🐛 故障排除

### 常见问题

**后端无响应**:
```bash
# 检查进程
ps aux | grep "sage.studio.config.backend.api"

# 重启后端
kill -9 <PID>
python -m sage.studio.config.backend.api &
```

**前端编译错误**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

**端口被占用**:
```bash
# 查看占用
lsof -i :3000
lsof -i :8080

# 杀死进程
kill -9 $(lsof -t -i:3000)
```

**Conda 环境问题**:
```bash
# 确认在 sage 环境
conda info --envs | grep "*"

# 激活 sage
conda activate sage

# 检查 .bashrc
tail -3 ~/.bashrc  # 应该有 "conda activate sage"
```
