# Changelog - SAGE Studio v2.0

所有 SAGE Studio v2.0 (React 版本) 的重要变更都将记录在此文件中。

### 🎉 Phase 2 完成 (100%)

Phase 2 核心可视化编辑器功能全部完成！

### ✨ 新增功能

#### 状态轮询 (Job Status Polling) ⭐⭐⭐⭐⭐
- 自动轮询作业状态 (每秒一次)
- 实时更新节点边框颜色
  - 🔵 运行中: 蓝色边框
  - 🟢 已完成: 绿色边框
  - 🔴 失败: 红色边框
- 作业完成自动停止轮询
- 组件卸载时自动清理
- 新增 `useJobStatusPolling` Hook

#### 撤销/重做 (Undo/Redo) ⭐⭐⭐⭐
- 支持最多 50 步历史记录
- 自动保存所有节点/边变化
- 工具栏按钮根据状态自动启用/禁用
- 深度克隆避免状态引用问题
- 新增 `undo()`, `redo()`, `canUndo()`, `canRedo()` 方法

#### 键盘快捷键 (Keyboard Shortcuts) ⭐⭐⭐⭐
- `Ctrl/Cmd + Z` - 撤销
- `Ctrl/Cmd + Shift + Z` 或 `Ctrl/Cmd + Y` - 重做
- `Ctrl/Cmd + S` - 保存流程
- `Delete` / `Backspace` - 删除选中节点
- 跨平台支持 (Mac Cmd / Windows Ctrl)
- 输入框保护 (在输入框中不触发)
- 新增 `useKeyboardShortcuts` Hook

### 🏗️ 架构改进

#### Store 扩展
- 新增 `history: HistoryState[]` - 历史栈
- 新增 `historyIndex: number` - 当前历史位置
- 新增 `currentJobId: string | null` - 当前作业 ID
- 新增 `jobStatus: JobStatus | null` - 作业状态对象
- 新增 `isPolling: boolean` - 轮询状态标志

#### 新增文件
- `src/hooks/useJobStatusPolling.ts` - 状态轮询 Hook (93 行)
- `src/hooks/useKeyboardShortcuts.ts` - 键盘快捷键 Hook (100 行)

#### 修改文件
- `src/store/flowStore.ts` - 扩展历史和作业状态管理 (+120 行)
- `src/components/Toolbar.tsx` - 集成新 Hooks 和按钮 (+50 行)

### 📚 文档更新

- 新增 `PHASE2_FINAL_COMPLETION_REPORT.md` - Phase 2 完成报告
- 新增 `PHASE2_TESTING_GUIDE.md` - 完整测试指南
- 新增 `PHASE2_SUMMARY.md` - 功能总结
- 更新 `../QUICK_ACCESS.md` - 进度和功能列表

### 🐛 Bug 修复

- 修复 JobStatus 类型与 API 不一致问题 (jobId → job_id)
- 修复 React Hook 调用顺序问题 (移到函数定义后)
- 修复 Icon 组件命名冲突 (Undo → UndoIcon)

### ⚡ 性能优化

- 历史栈限制为 50 个状态，避免内存溢出
- 使用 useRef 避免重复轮询
- 轮询智能停止，减少不必要的 API 调用
- 深度克隆使用 JSON 序列化，性能高效


### 🏗️ 架构

#### 技术栈
- React 18.2.0
- TypeScript 5.2.2
- React Flow 11.10.4
- Zustand 4.4.7 (状态管理)
- Ant Design 5.22.6 (UI 组件)
- Vite 5.4.20 (构建工具)

#### 核心组件
- `FlowCanvas` - 主画布组件 (React Flow)
- `NodePanel` - 左侧节点列表
- `ConfigPanel` - 右侧配置面板
- `Toolbar` - 顶部工具栏
- `CustomNode` - 自定义节点组件

#### 状态管理
- `flowStore` (Zustand) - 全局流程状态
  - nodes, edges - 画布节点和边
  - selectedNode - 选中的节点
  - config - 当前节点配置
  - running - 运行状态

#### API 集成
- `submitFlow` - 提交流程配置
- `startJob` - 启动流程执行
- `stopJob` - 停止流程执行
- `getJobStatus` - 获取作业状态
- `getJobLogs` - 获取执行日志

### 📚 文档

- `README.md` - 项目概述
- `PHASE2_COMPLETION_REPORT.md` - Phase 2 完成报告
- `../QUICK_ACCESS.md` - 快速访问指南

### ⚙️ 配置

- 后端 API: `http://localhost:8080`
- 前端端口: `3000` (Vite)
- TypeScript: Strict mode
- ESLint: React + TypeScript 规则

### 📦 依赖

主要依赖:
```json
{
  "react": "^18.2.0",
  "react-flow-renderer": "^11.10.4",
  "zustand": "^4.4.7",
  "antd": "^5.22.6",
  "typescript": "^5.2.2",
  "vite": "^5.4.20"
}
```

---

