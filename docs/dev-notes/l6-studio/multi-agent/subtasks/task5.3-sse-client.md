# Task 5.3: SSE 客户端处理

## 目标
实现前端 SSE 客户端，处理 Agent 流式响应。

## 依赖
- Task 3.3 (后端 SSE 格式)

## 文件位置
`packages/sage-studio/src/sage/studio/frontend/src/lib/sse-client.ts`

## 提示词

```
请实现 SSE 客户端，处理 Agent API 的流式响应。

## 背景
后端 /api/chat/agent 返回 SSE 流，格式如下:
```
event: step
data: {"step_id": "abc", "type": "reasoning", ...}

event: text
data: 你好

event: done
data:
```

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/frontend/src/lib/sse-client.ts

2. 提供 hook 方式使用:
   ```typescript
   const { sendMessage, steps, text, isLoading, error } = useAgentChat();
   ```

3. 处理三种事件:
   - step: 累积到 steps 数组
   - text: 累积到 text 字符串
   - error: 设置 error
   - done: 设置 isLoading = false

## 代码模板
```typescript
// sse-client.ts
export interface AgentStep {
  step_id: string;
  type: "reasoning" | "tool_call" | "tool_result" | "response";
  content: string;
  status: "pending" | "running" | "completed" | "failed";
  metadata?: Record<string, unknown>;
}

interface SSECallbacks {
  onStep?: (step: AgentStep) => void;
  onText?: (text: string) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}

export async function streamAgentChat(
  message: string,
  sessionId: string,
  history: Array<{ role: string; content: string }>,
  callbacks: SSECallbacks
): Promise<void> {
  const response = await fetch("/api/chat/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, history }),
  });

  if (!response.ok) {
    callbacks.onError?.(`HTTP ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError?.("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 解析 SSE 事件
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";  // 保留未完成的行

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7);
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        handleEvent(currentEvent, data, callbacks);
      }
    }
  }

  callbacks.onDone?.();
}

function handleEvent(event: string, data: string, callbacks: SSECallbacks) {
  switch (event) {
    case "step":
      try {
        const step = JSON.parse(data) as AgentStep;
        callbacks.onStep?.(step);
      } catch (e) {
        console.error("Failed to parse step:", e);
      }
      break;
    case "text":
      callbacks.onText?.(data);
      break;
    case "error":
      try {
        const { error } = JSON.parse(data);
        callbacks.onError?.(error);
      } catch {
        callbacks.onError?.(data);
      }
      break;
    case "done":
      callbacks.onDone?.();
      break;
  }
}


// useAgentChat.ts
import { useState, useCallback, useRef } from "react";
import { streamAgentChat, AgentStep } from "./sse-client";

export function useAgentChat() {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (
      message: string,
      sessionId: string,
      history: Array<{ role: string; content: string }>
    ) => {
      // 重置状态
      setSteps([]);
      setText("");
      setError(null);
      setIsLoading(true);

      await streamAgentChat(message, sessionId, history, {
        onStep: (step) => setSteps((prev) => [...prev, step]),
        onText: (t) => setText((prev) => prev + t),
        onError: (e) => setError(e),
        onDone: () => setIsLoading(false),
      });
    },
    []
  );

  const reset = useCallback(() => {
    setSteps([]);
    setText("");
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    steps,
    text,
    isLoading,
    error,
    sendMessage,
    reset,
  };
}
```

## 注意
- 正确处理 SSE 格式
- 支持中文和特殊字符
- 错误时调用 onError
- 考虑取消请求
```

## 验收标准
- [ ] 正确解析 SSE 事件
- [ ] steps 和 text 正确累积
- [ ] 错误处理完善
- [ ] hook API 易用
