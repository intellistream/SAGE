# Task 5: Frontend Improvements (前端改进)

## 任务概述

更新 SAGE Studio 的前端界面，以支持 Multi-Agent 架构的交互体验。核心是可视化 Agent 的推理过程（Reasoning）和工具调用（Tool
Calls），让用户了解系统是如何工作的，而不仅仅是看到最终结果。

**优先级**: P1 (中)\
**预计工时**: 2-3 天\
**可并行**: 是（依赖 Task 3 API 定义）

## 目标

1. **可视化推理链**: 展示 Agent 的思考过程（Thought Process）
1. **工具调用展示**: 显示工具调用的输入、输出和状态
1. **流式响应处理**: 适配后端新的 SSE 流式协议
1. **交互优化**: 支持展开/折叠推理步骤，避免干扰阅读

## 文件位置

```
packages/sage-studio/src/sage/studio/frontend/src/components/ChatMode.tsx
packages/sage-studio/src/sage/studio/frontend/src/components/ReasoningAccordion.tsx
packages/sage-studio/src/sage/studio/frontend/src/services/api.ts
packages/sage-studio/src/sage/studio/frontend/src/store/chatStore.ts
```

## 数据结构设计

### AgentStep (前端类型定义)

```typescript
// src/store/chatStore.ts

export type StepType = 'reasoning' | 'tool_call' | 'tool_result' | 'response';
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface AgentStep {
    id: string;
    type: StepType;
    content: string;
    status: StepStatus;
    timestamp: number;
    metadata?: {
        tool_name?: string;
        tool_input?: any;
        tool_output?: any;
        confidence?: number;
        [key: string]: any;
    };
}

export interface ChatMessage {
    // ... 现有字段 ...
    reasoningSteps?: AgentStep[]; // 新增：关联的推理步骤
}
```

## 组件设计

### 1. ReasoningAccordion (推理折叠面板)

增强现有的 `ReasoningAccordion` 组件，支持更丰富的步骤展示。

```tsx
// src/components/ReasoningAccordion.tsx

interface ReasoningAccordionProps {
    steps: AgentStep[];
    isStreaming: boolean;
}

export const ReasoningAccordion: React.FC<ReasoningAccordionProps> = ({ steps, isStreaming }) => {
    // 渲染逻辑：
    // 1. 默认折叠，但在流式传输时自动展开
    // 2. 根据 step.type 渲染不同图标和样式
    //    - reasoning: 🧠 思考中...
    //    - tool_call: 🛠️ 调用工具 [ToolName]
    //    - tool_result: ✅ 工具返回
    // 3. 支持点击查看工具调用的详细 JSON 数据

    return (
        <div className="reasoning-container">
            {/* ... */}
        </div>
    );
};
```

### 2. ChatMode (聊天主界面)

修改 `handleSendMessage` 和 SSE 处理逻辑。

```tsx
// src/components/ChatMode.tsx

// 在 SSE 回调中处理不同类型的事件
const handleStreamUpdate = (event: any) => {
    if (event.type === 'step') {
        // 更新推理步骤
        addReasoningStep(sessionId, messageId, event.data);
    } else if (event.type === 'content') {
        // 更新最终回复内容
        appendToMessage(sessionId, messageId, event.data);
    } else if (event.type === 'error') {
        // 处理错误
    }
};
```

## API 集成

修改 `src/services/api.ts` 中的 `sendChatMessage`，适配新的 SSE 格式。

```typescript
// src/services/api.ts

export async function sendChatMessage(
    message: string,
    sessionId: string,
    onStep: (step: AgentStep) => void,
    onContent: (chunk: string) => void,
    onError: (error: Error) => void,
    onComplete: () => void
) {
    // 使用 fetchEventSource 或类似的 SSE 库
    // 解析后端返回的 event-stream
    // event: step -> onStep(JSON.parse(data))
    // event: message -> onContent(data)
    // event: error -> onError(...)
}
```

## 实现步骤

### Step 1: 更新 Store 和类型定义

在 `chatStore.ts` 中添加 `AgentStep` 类型，并更新 `ChatMessage` 接口。添加用于更新步骤的 Action (`addReasoningStep`,
`updateReasoningStep`)。

### Step 2: 增强 ReasoningAccordion

修改组件以支持新的步骤类型。为工具调用添加特殊的渲染逻辑（如代码块高亮显示输入/输出）。

### Step 3: 更新 API 服务

重构 `sendChatMessage` 以支持解析自定义 SSE 事件（不仅仅是文本块）。

### Step 4: 集成 ChatMode

在 `ChatMode.tsx` 中连接 Store、API 和 UI 组件。确保在发送消息时正确处理流式更新。

## 提示词（复制使用）

```
请在 SAGE 项目中改进前端 Chat 界面以支持 Multi-Agent 可视化。

## 背景
后端 AgentOrchestrator 现在会流式返回推理步骤（AgentStep）和最终回复。前端需要展示这些步骤，让用户看到 Agent 的思考和工具调用过程。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/frontend/src/
2. 更新 chatStore.ts: 添加 AgentStep 类型和相关 Actions
3. 更新 ReasoningAccordion.tsx: 支持展示 tool_call 和 tool_result，优化样式
4. 更新 api.ts: 适配新的 SSE 事件流 (event: step, event: message)
5. 更新 ChatMode.tsx: 集成上述变更

## 交互细节
- 推理过程默认折叠，但在生成时自动展开
- 工具调用应显示工具名称，点击可查看详细参数
- 最终回复像以前一样打字机显示
```
