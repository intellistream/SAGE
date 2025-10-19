# Phase 3 实施计划 - Playground 优先

---

## 🎯 核心目标

实现 **Playground** 功能，让用户可以：
1. 在右侧面板实时与流程对话
2. 查看中间步骤的输出
3. 快速测试和调试 RAG 流程
4. 提升开发效率和用户体验

---

## 📋 功能需求

### 1. UI 布局 (Split Panel)

```
┌──────────────────────────────────────────────┐
│  Toolbar (工具栏)                             │
├─────────────────────┬────────────────────────┤
│                     │  Playground            │
│                     │  ┌──────────────────┐  │
│   Flow Canvas       │  │  💬 对话历史    │  │
│   (画布 60%)        │  │                  │  │
│                     │  │  User: 你好      │  │
│   ┌─────┐ ┌─────┐  │  │  Bot: 你好！    │  │
│   │节点1│→│节点2│  │  │                  │  │
│   └─────┘ └─────┘  │  └──────────────────┘  │
│                     │                        │
│                     │  ┌──────────────────┐  │
│                     │  │ 📝 输入框        │  │
│                     │  │ 发送问题...      │  │
│                     │  └──────────────────┘  │
│                     │  [发送] [清空]         │
└─────────────────────┴────────────────────────┘
```

**技术方案**:
- 使用 `react-split-pane` 或 Ant Design `Layout.Sider`
- 可拖拽调整宽度
- 可收起/展开
- 响应式设计 (最小宽度 300px)

---

### 2. 聊天界面 (Chat UI)

**组件**: `Playground.tsx`

**功能**:
- ✅ 对话历史显示
  - 用户消息 (右对齐，蓝色背景)
  - Bot 回复 (左对齐，灰色背景)
  - 时间戳
  - 复制按钮
  
- ✅ 输入框
  - 多行文本输入
  - 支持 Enter 发送
  - Shift+Enter 换行
  - 字符计数
  
- ✅ 控制按钮
  - 发送按钮 (禁用状态: 输入为空或正在发送)
  - 清空历史按钮
  - 导出对话按钮 (可选)

**数据结构**:
```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  nodeOutputs?: Record<string, any> // 中间步骤输出
}

interface PlaygroundState {
  messages: Message[]
  isLoading: boolean
  currentJobId: string | null
}
```

---

### 3. 中间步骤展示 (Intermediate Steps)

**展开式设计**:
```
User: RAG 是什么？

Bot: RAG 是检索增强生成...
  
  🔍 中间步骤 ▼
    ├─ [检索] 找到 3 个相关文档
    │   └─ 文档1: RAG 介绍 (相似度: 0.92)
    │   └─ 文档2: 生成技术 (相似度: 0.85)
    │   └─ 文档3: 检索方法 (相似度: 0.78)
    │
    ├─ [Rerank] 重排序结果
    │   └─ 最终排序: [文档1, 文档3, 文档2]
    │
    └─ [LLM] 生成答案
        └─ Token 数: 150
        └─ 耗时: 2.3s
```

**技术实现**:
- Ant Design `Collapse` 组件
- 树形结构显示
- 每个步骤可展开查看详情
- 支持复制单个步骤结果

---

### 4. WebSocket 实时通信 (可选)

**目标**: 实现流式响应

**当前方案** (Phase 3.1):
- 使用轮询 (复用现有 `getJobStatus`)
- 每 500ms 轮询一次
- 流程完成后停止轮询

**未来方案** (Phase 3.2):
- 使用 WebSocket 连接
- 服务端推送中间结果
- 实现打字机效果 (流式输出)

**WebSocket 协议**:
```typescript
// 客户端 → 服务端
{
  type: 'query',
  job_id: 'job-123',
  question: '什么是 RAG？'
}

// 服务端 → 客户端 (流式)
{
  type: 'intermediate_step',
  job_id: 'job-123',
  node: 'retriever',
  data: { documents: [...] }
}

{
  type: 'final_answer',
  job_id: 'job-123',
  answer: 'RAG 是...'
}
```

---

## 🏗️ 技术实现

### 新增组件

#### 1. `Playground.tsx`

**位置**: `src/components/Playground.tsx`

**结构**:
```tsx
import React, { useState } from 'react'
import { Input, Button, List, Collapse, message } from 'antd'
import { SendOutlined, ClearOutlined } from '@ant-design/icons'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  nodeOutputs?: Record<string, any>
}

export const Playground: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    // 发送消息逻辑
  }

  const handleClear = () => {
    setMessages([])
    message.success('已清空对话历史')
  }

  return (
    <div className="playground-container">
      <div className="message-list">
        {messages.map(msg => (
          <MessageItem key={msg.id} message={msg} />
        ))}
      </div>
      
      <div className="input-area">
        <Input.TextArea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="输入问题..."
          autoSize={{ minRows: 2, maxRows: 6 }}
        />
        <div className="button-group">
          <Button onClick={handleClear} icon={<ClearOutlined />}>
            清空
          </Button>
          <Button
            type="primary"
            onClick={handleSend}
            icon={<SendOutlined />}
            loading={isLoading}
            disabled={!input.trim()}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

#### 2. `MessageItem.tsx`

**位置**: `src/components/MessageItem.tsx`

**功能**: 单条消息显示组件

```tsx
interface MessageItemProps {
  message: Message
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user'
  
  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-header">
        <span className="role">{isUser ? '你' : 'SAGE'}</span>
        <span className="timestamp">
          {new Date(message.timestamp).toLocaleTimeString()}
        </span>
      </div>
      
      <div className="message-content">
        {message.content}
      </div>
      
      {message.nodeOutputs && (
        <IntermediateSteps steps={message.nodeOutputs} />
      )}
    </div>
  )
}
```

---

#### 3. `IntermediateSteps.tsx`

**位置**: `src/components/IntermediateSteps.tsx`

**功能**: 中间步骤展示

```tsx
interface IntermediateStepsProps {
  steps: Record<string, any>
}

export const IntermediateSteps: React.FC<IntermediateStepsProps> = ({ steps }) => {
  return (
    <Collapse ghost>
      <Collapse.Panel header="🔍 中间步骤" key="1">
        <Tree treeData={formatSteps(steps)} />
      </Collapse.Panel>
    </Collapse>
  )
}

function formatSteps(steps: Record<string, any>) {
  // 将步骤格式化为树形结构
  return Object.entries(steps).map(([node, output]) => ({
    title: node,
    key: node,
    children: formatOutput(output)
  }))
}
```

---

### Store 扩展

**文件**: `src/store/flowStore.ts`

**新增状态**:
```typescript
{
  // Playground 状态
  playgroundMessages: Message[]
  playgroundLoading: boolean
  playgroundVisible: boolean  // 是否显示 Playground
}
```

**新增方法**:
```typescript
// Playground 控制
addMessage(message: Message)
clearMessages()
setPlaygroundLoading(loading: boolean)
togglePlayground()
```

---

### API 扩展

**文件**: `src/api.ts`

**新增接口**:
```typescript
// 发送查询到流程
export async function queryFlow(
  pipelineId: string,
  question: string
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  })
  return response.json()
}

interface QueryResponse {
  job_id: string
  answer: string
  intermediate_steps?: Record<string, any>
  metadata?: {
    tokens: number
    duration: number
  }
}
```

---

## 📝 实施步骤

### 第 1 步: UI 布局 (1 天)

- [ ] 添加 `react-split-pane` 依赖
- [ ] 修改 `App.tsx` 实现 Split Panel 布局
- [ ] 创建 `Playground.tsx` 基础组件
- [ ] 添加样式文件 `Playground.css`
- [ ] 实现收起/展开功能
- [ ] 测试响应式布局

**验收标准**:
- 画布和 Playground 可以拖拽调整宽度
- Playground 可以收起/展开
- 移动端自动隐藏 Playground

---

### 第 2 步: 聊天界面 (1 天)

- [ ] 实现 `MessageItem.tsx` 组件
- [ ] 实现消息列表滚动
- [ ] 实现输入框和发送按钮
- [ ] 添加清空历史功能
- [ ] 添加复制消息功能
- [ ] 实现自动滚动到最新消息

**验收标准**:
- 用户消息和 Bot 回复样式正确
- Enter 发送，Shift+Enter 换行
- 消息列表自动滚动
- 可以复制单条消息

---

### 第 3 步: API 集成 (1 天)

- [ ] 扩展 Store 添加 Playground 状态
- [ ] 实现 `queryFlow` API 调用
- [ ] 实现消息发送逻辑
- [ ] 实现 loading 状态处理
- [ ] 实现错误处理
- [ ] 集成状态轮询

**验收标准**:
- 发送消息后正确调用 API
- 显示 loading 状态
- 收到回复后正确显示
- 错误时显示友好提示

---

### 第 4 步: 中间步骤展示 (1 天)

- [ ] 创建 `IntermediateSteps.tsx` 组件
- [ ] 实现树形结构展示
- [ ] 实现展开/折叠功能
- [ ] 添加步骤详情格式化
- [ ] 添加复制步骤功能
- [ ] 优化样式

**验收标准**:
- 中间步骤以树形结构展示
- 可以展开/折叠每个步骤
- 步骤详情格式化清晰
- 可以复制单个步骤

---

### 第 5 步: 测试和优化 (1 天)

- [ ] 编写单元测试
- [ ] 端到端测试
- [ ] 性能优化 (虚拟滚动)
- [ ] 样式优化
- [ ] 文档编写
- [ ] Bug 修复

**验收标准**:
- 所有功能正常工作
- 无明显性能问题
- 代码覆盖率 > 80%
- 文档完整

---

## 🎨 样式设计

### 配色方案

```css
/* 用户消息 */
.message-item.user {
  background: #1890ff;
  color: white;
  align-self: flex-end;
}

/* Bot 回复 */
.message-item.assistant {
  background: #f0f0f0;
  color: #333;
  align-self: flex-start;
}

/* 中间步骤 */
.intermediate-steps {
  background: #fafafa;
  border-left: 3px solid #1890ff;
  padding: 12px;
  margin-top: 8px;
}
```

### 布局参数

```css
.playground-container {
  width: 40%;           /* 占 40% 宽度 */
  min-width: 300px;     /* 最小宽度 */
  max-width: 600px;     /* 最大宽度 */
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.input-area {
  padding: 16px;
  border-top: 1px solid #d9d9d9;
}
```

---

## 🧪 测试计划

### 单元测试

```typescript
describe('Playground', () => {
  it('should render empty state', () => {
    // 测试空状态渲染
  })

  it('should send message on button click', async () => {
    // 测试发送消息
  })

  it('should clear messages', () => {
    // 测试清空历史
  })

  it('should display intermediate steps', () => {
    // 测试中间步骤显示
  })
})
```

### 集成测试

1. **基础流程测试**
   - 用户输入问题
   - 点击发送
   - 显示 loading
   - 收到回复
   - 显示中间步骤

2. **边界情况测试**
   - 空输入不可发送
   - 超长消息处理
   - 网络错误处理
   - 并发请求处理

3. **性能测试**
   - 100 条消息渲染性能
   - 滚动性能
   - 内存占用

---

## 📚 参考资料

### LangFlow Playground

参考 LangFlow 的 Playground 实现：
- UI 布局: Split Panel
- 聊天界面: 左右对话气泡
- 中间步骤: 折叠面板展示
- 流式输出: 打字机效果

### React Split Pane

库选择:
- `react-split-pane` (推荐)
- `allotment` (备选)
- Ant Design `Layout.Sider` (简单场景)

### WebSocket 实现

参考:
- `socket.io-client` (成熟方案)
- 原生 WebSocket API (轻量)

---

## 🎯 验收标准

Phase 3.1 (Playground) 完成需要满足：

### 功能完整性 ✅

- [ ] Split Panel 布局实现
- [ ] 聊天界面实现
- [ ] 消息发送/接收
- [ ] 中间步骤展示
- [ ] 清空历史功能
- [ ] 收起/展开功能

### 用户体验 ✅

- [ ] 响应速度 < 100ms
- [ ] 流畅的滚动
- [ ] 友好的错误提示
- [ ] 清晰的 loading 状态
- [ ] 美观的 UI 设计

### 代码质量 ✅

- [ ] TypeScript 类型完整
- [ ] 代码注释清晰
- [ ] 遵循 React 最佳实践
- [ ] 无 ESLint 警告
- [ ] 单元测试覆盖

### 文档完整 ✅

- [ ] 功能说明文档
- [ ] API 接口文档
- [ ] 用户使用指南
- [ ] 开发者文档

---

## 🚀 下一步 (Phase 3.2)

完成 Playground 后，继续实施：

1. **Tweaks** (2-3 天)
   - 运行时参数覆盖
   - 快速实验配置

2. **模板库** (3-5 天)
   - 10+ RAG 模板
   - 一键导入使用

3. **WebSocket 优化** (2 天)
   - 替换轮询为 WebSocket
   - 实现流式输出

---

**文档创建**: 2025-10-17  
**状态**: 准备启动 🚀  
**负责人**: 开发团队
