# Playground 功能实施计划

> **当前状态**: Phase 2 已完成 ✅ | Phase 3 计划中 📅

---

## 🎯 目标

实现交互式 **Playground** 功能：
1. ✅ 模态框聊天界面
2. ✅ Agent 步骤可视化
3. ✅ 会话管理
4. ✅ 代码生成（Python/cURL）
5. ✅ Flow 执行集成
6. 📅 实时流式输出（WebSocket/SSE）

---

## ✅ Phase 1: UI 实现（已完成）

### 已实现功能

**1. Playground 组件** (`Playground.tsx` - 400+ 行)
- 模态框聊天界面
- 消息列表（用户/AI）
- 输入框（Enter 发送，Shift+Enter 换行）
- 发送/停止按钮
- 响应式布局

**2. Agent 步骤可视化**
- 折叠/展开面板
- 推理步骤展示
- 工具调用详情（输入/输出/耗时）
- 颜色区分不同类型

**3. 会话管理**
- 创建/切换/清空会话
- 会话下拉选择
- 消息历史

**4. 代码生成**
- Python API 调用示例
- cURL 命令示例
- 代码高亮
- 一键复制

**5. 状态管理** (`playgroundStore.ts` - 280 行)
- Zustand store
- 消息管理
- 会话管理
- 执行控制

**6. 样式设计** (`Playground.css` - 170 行)
- 深色主题代码视图
- 自定义滚动条
- 动画效果

**7. 后端 API** (`api.py`)
- `POST /api/playground/execute` 端点
- 请求/响应模型
- ~~当前返回模拟数据~~ → **已集成真实执行** ✅

---

## ✅ Phase 2: Flow 集成（已完成）

### 实现内容

**1. Flow 数据加载** ✅
- 从 `.sage/pipelines/` 加载 JSON 文件
- 解析 Flow 定义
- 错误处理

**2. 数据格式转换** ✅
- 前端 Flow 格式 → FlowDefinition
- 节点数据映射
- 连接关系映射
- 入口节点识别

**3. Flow 执行** ✅
- 集成 FlowEngine
- 按依赖顺序执行节点
- 节点间数据传递

**4. 结果映射** ✅
- 节点执行结果 → Agent 步骤
- 输入/输出数据收集
- 执行时间统计

**5. 输出生成** ✅
- 格式化最终输出
- 错误信息展示

---

## � 任务进度

### ⏳ Phase 2: Flow 集成（进行中）

- [ ] 连接 FlowEngine
- [ ] 节点执行映射
- [ ] 真实数据绑定
- [ ] 错误处理优化
- [ ] 执行时间统计

### 📅 Phase 3: 流式输出（计划中）

- [ ] WebSocket/SSE 支持
- [ ] 实时步骤更新
- [ ] 打字机效果
- [ ] 进度条显示

### 📅 Phase 4: 增强功能（计划中）

- [ ] 会话持久化（数据库）
- [ ] 步骤导出（JSON/Markdown）
- [ ] 性能分析工具
- [ ] A/B 测试支持

---

## 🧪 测试

### 已实现

- ✅ 自动化测试脚本 (`test_playground.sh`)
- ✅ 依赖检查
- ✅ 文件完整性检查
- ✅ TypeScript 编译检查

## 🎯 下一步

### Phase 2 优先级

1. **Flow 执行集成** (高优先级)
   - 连接 FlowEngine
   - 真实节点数据绑定
   - 错误处理

2. **流式输出** (中优先级)
   - SSE/WebSocket 支持
   - 实时更新

3. **会话持久化** (低优先级)
   - LocalStorage 临时存储
   - 数据库永久存储

### 技术选型

- **流式输出**: SSE (推荐) 或 WebSocket
- **状态持久化**: IndexedDB (前端) + PostgreSQL (后端)
- **性能优化**: 虚拟滚动 (react-window)

---
