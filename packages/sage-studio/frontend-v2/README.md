# SAGE Studio v2.0 Frontend

现代化的可视化流程编辑器，基于 React + React Flow 构建。

## 🎯 特性

- ✨ **现代化 UI** - 基于 React 18 + Ant Design
- 🎨 **可视化编辑** - React Flow 拖拽式流程设计
- 🚀 **高性能** - Vite 构建，快速热重载
- 📦 **TypeScript** - 完整的类型支持
- 🎭 **状态管理** - Zustand 轻量级状态管理
- 🔌 **API 集成** - 连接 Phase 1 后端 API

## 📦 安装依赖

```bash
# 使用 npm
npm install

# 或使用 pnpm (推荐)
pnpm install

# 或使用 yarn
yarn install
```

## 🚀 开发

```bash
# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

后端 API 会自动代理到 `http://localhost:8080`，请确保后端服务已启动。

## 🏗️ 构建

```bash
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 📁 项目结构

```
frontend-v2/
├── src/
│   ├── components/          # React 组件
│   │   ├── FlowEditor.tsx   # React Flow 编辑器
│   │   ├── Toolbar.tsx      # 工具栏
│   │   ├── NodePalette.tsx  # 节点面板
│   │   ├── PropertiesPanel.tsx  # 属性面板
│   │   ├── StatusBar.tsx    # 状态栏
│   │   └── nodes/           # 自定义节点组件
│   │       └── CustomNode.tsx
│   ├── store/               # Zustand 状态管理
│   │   └── flowStore.ts
│   ├── App.tsx              # 主应用组件
│   ├── main.tsx             # 入口文件
│   └── index.css            # 全局样式
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 🎨 主要组件

### FlowEditor
React Flow 核心编辑器，支持：
- 节点拖拽和连接
- 缩放和平移
- 小地图预览
- 背景网格

### NodePalette
节点库面板，包含：
- 节点分类显示
- 搜索过滤
- 拖拽添加节点

### PropertiesPanel
属性编辑面板，用于：
- 查看节点信息
- 编辑节点参数
- 配置节点属性

### Toolbar
工具栏，提供：
- 流程执行控制
- 保存/加载功能
- 撤销/重做
- 视图控制

## 🔌 API 集成

前端通过 Axios 与后端通信：

```typescript
// 获取可用节点
GET /api/nodes

// 执行流程
POST /api/flows/execute

// 保存流程
POST /api/flows/save

// 加载流程
GET /api/flows/:id
```

## ✅ 已完成功能

- [x] ✅ 拖拽式节点编辑器 - React Flow 集成
- [x] ✅ 节点库面板 - 动态加载、搜索、分类
- [x] ✅ 属性编辑面板 - 实时编辑节点属性
- [x] ✅ 后端 API 集成 - 完整的服务层
- [x] ✅ 状态管理 - Zustand 实现
- [x] ✅ 节点选择和连接 - 可视化操作

## 🎯 下一步开发

- [ ] 实现流程执行逻辑 (Run/Stop 按钮)
- [ ] 添加实时状态更新 (WebSocket)
- [ ] 实现流程保存/加载功能
- [ ] 添加更多节点类型支持
- [ ] 实现撤销/重做功能
- [ ] 添加快捷键支持
- [ ] 优化性能和用户体验

### 已知问题 🐛

1. **状态轮询缺失**: 运行流程后，节点状态不会自动更新，需要手动实现轮询
2. **配置定义硬编码**: 节点配置定义在前端硬编码，应从后端 API 获取
3. **加载流程数据格式**: 需要确认后端返回的流程数据结构与转换逻辑匹配
4. **运行状态持久化**: 刷新页面后运行状态丢失

## 📚 文档

- [API 集成文档](docs/API_INTEGRATION.md) - API 使用指南
- [Phase 2 完成报告](docs/PHASE2_API_COMPLETE.md) - 当前进度

## 📝 技术栈

- **框架**: React 18
- **构建工具**: Vite 5
- **语言**: TypeScript
- **图编辑器**: React Flow 11
- **UI 组件**: Ant Design 5
- **状态管理**: Zustand 4
- **HTTP 客户端**: Axios
- **图标**: Lucide React
- **样式**: Tailwind CSS 3

## 📄 许可证

MIT License - 详见 LICENSE 文件
