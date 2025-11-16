# Chat UI Testing Guide

## Phase 2 Chat UI Implementation Complete ✅

### 新增文件

1. **`src/store/chatStore.ts`** - Zustand store 管理 Chat 状态

   - 会话管理（创建、删除、切换）
   - 消息管理（添加、更新、流式追加）
   - 流式响应状态跟踪

1. **`src/components/ChatMode.tsx`** - ChatGPT 风格的聊天界面

   - 左侧会话列表
   - 右侧聊天窗口
   - 流式消息显示
   - 实时 SSE 连接

1. **`src/services/api.ts`** - 新增 Chat API 方法

   - `sendChatMessage()` - SSE 流式聊天
   - `getChatSessions()` - 获取会话列表
   - `deleteChatSession()` - 删除会话

### 修改文件

1. **`src/App.tsx`**

   - 添加 `mode` 状态（'builder' | 'chat'）
   - 条件渲染 Builder 或 Chat 界面
   - StatusBar 仅在 Builder 模式显示

1. **`src/components/Toolbar.tsx`**

   - 添加模式切换 Segmented 控件
   - Builder 工具按钮仅在 Builder 模式显示
   - Settings 在两种模式都可用

## 功能特性

### ✅ 已实现

- [x] ChatGPT 风格的双栏布局
- [x] 会话列表（左侧）
- [x] 消息窗口（右侧）
- [x] SSE 流式响应
- [x] 实时消息追加
- [x] 会话创建/删除
- [x] Builder ↔ Chat 模式切换
- [x] 响应式输入框（Enter 发送，Shift+Enter 换行）
- [x] 加载状态与错误处理
- [x] 自动滚动到最新消息

### 🔶 依赖后端

- [ ] 实际的 LLM 响应（当前返回 Echo）
- [ ] 会话持久化（当前内存存储）
- [ ] 消息历史加载

## 测试步骤

### 1. 一键启动 Chat 模式（推荐）

```bash
# 启动 gateway + backend + 前端
sage studio chat start
```

- 默认使用 Vite dev server（`--no-dev` 可选择预览模式）
- 前端默认地址 `http://localhost:5173`
- Gateway 默认端口 `8000`，可用 `--gateway-port` 修改

### 2. 手动启动（调试场景）

仍可在三个终端中分别运行：

```bash
# gateway
python -m sage.gateway.server

# studio backend
python -m sage.studio

# frontend dev server
sage studio npm run dev
```

### 3. 测试 Chat 功能

1. **模式切换**

   - 打开浏览器访问 `http://localhost:5173`
   - 在顶部工具栏看到 "Builder" 和 "Chat" 切换按钮
   - 点击 "Chat" 切换到聊天模式

1. **创建会话**

   - 点击 "New Chat" 按钮
   - 左侧会话列表会出现新会话

1. **发送消息**

   - 在底部输入框输入消息
   - 按 Enter 发送（Shift+Enter 换行）
   - 观察消息是否实时流式显示

1. **会话管理**

   - 切换不同会话
   - 删除会话（点击会话右侧的 "..." 菜单）
   - 清空当前会话（点击顶部 "Clear" 按钮）

### 4. 验证 API 调用

打开浏览器开发者工具（F12）：

- **Network 标签页**: 应该看到 `/api/chat/message` 的 fetch 请求
- **Console 标签页**: 检查是否有错误日志
- **Response**: SSE 流式数据应该是 `data: {"choices":[...]}\n\n` 格式

## 预期行为

### 正常流程

1. 用户输入消息 → 点击 Send
1. 用户消息立即显示在右侧（蓝色气泡）
1. AI 消息占位符出现（灰色气泡）
1. AI 响应逐字符流式显示
1. 响应完成后停止动画
1. 会话列表更新消息计数

### 当前限制（Phase 1）

- AI 响应是 Echo 模式（原样返回用户输入）
- 会话数据在刷新页面后丢失（内存存储）
- 没有实际的 SAGE DataStream 执行

## 下一步 (Phase 3)

1. **SAGE Kernel 集成**

   - 将 `OpenAIAdapter._execute_sage_pipeline()` 连接到真实 kernel
   - 解析 chat 消息为 DataStream 操作
   - 返回真实的 LLM 生成结果

1. **会话持久化**

   - 将 SessionManager 改为 Redis 后端
   - 支持跨实例会话共享

1. **高级功能**

   - 多轮对话上下文管理
   - 代码高亮显示
   - Markdown 渲染
   - 文件上传支持

## 故障排查

### 问题：点击 Chat 模式后界面空白

- **检查**: 浏览器 Console 是否有 TypeScript/React 错误
- **解决**: 确保所有新文件已保存，运行 `sage studio npm run dev` 重启

### 问题：发送消息无响应

- **检查**: Network 标签页是否有 404 错误
- **解决**: 确认 sage-studio backend 正在运行（端口 8080）

### 问题：SSE 连接失败

- **检查**: sage-gateway 是否运行（端口 9000）
- **检查**: CORS 配置是否正确
- **解决**: 查看 gateway 日志，确认 `/v1/chat/completions` 端点正常

### 问题：TypeScript 编译错误

- **检查**: `AppMode` 类型是否正确导出
- **解决**: 确保 `App.tsx` 导出了 `export type AppMode = ...`

## API 端点总结

### Studio Backend (`:8080`)

```
POST   /api/chat/message          # 发送消息（代理到 gateway）
GET    /api/chat/sessions         # 获取会话列表
DELETE /api/chat/sessions/{id}    # 删除会话
```

### Gateway (`:9000`)

```
POST   /v1/chat/completions       # OpenAI 兼容的聊天接口
GET    /sessions                  # 会话列表
POST   /sessions/{id}/clear       # 清空会话
DELETE /sessions/{id}             # 删除会话
```

## 成功标志

✅ 模式切换按钮正常工作 ✅ Chat 界面渲染正确（双栏布局） ✅ 可以创建新会话 ✅ 消息发送后实时流式显示 ✅ 会话列表动态更新 ✅ 删除会话功能正常 ✅ 无
TypeScript/Console 错误

______________________________________________________________________

**实现日期**: 2025-11-16 **状态**: Phase 2 前端完成，待 Phase 3 Kernel 集成
