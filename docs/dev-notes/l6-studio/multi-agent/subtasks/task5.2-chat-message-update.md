# Task 5.2: ChatMessage 组件更新

## 目标
更新 ChatMessage 组件，支持显示 Agent 推理步骤。

## 依赖
- Task 5.1 (ReasoningAccordion)

## 文件位置
`packages/sage-studio/src/sage/studio/frontend/src/components/ChatMessage.tsx`（修改现有）

## 提示词

```
请更新 ChatMessage 组件，集成 ReasoningAccordion 展示推理步骤。

## 背景
现有 ChatMessage 只显示文本消息。
Multi-Agent 模式下，消息可能包含推理步骤。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/frontend/src/components/ChatMessage.tsx

2. 扩展消息类型:
   ```typescript
   interface ChatMessageProps {
     role: "user" | "assistant" | "system";
     content: string;
     steps?: AgentStep[];  // 新增：Agent 执行步骤
     isStreaming?: boolean;
   }
   ```

3. 布局:
   ```
   ┌─────────────────────────────────┐
   │ [Avatar]                        │
   │                                 │
   │ [ReasoningAccordion] (如果有)   │
   │                                 │
   │ [消息内容 - Markdown 渲染]      │
   └─────────────────────────────────┘
   ```

## 代码模板
```tsx
import React from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { ReasoningAccordion, AgentStep } from "./ReasoningAccordion";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  steps?: AgentStep[];
  isStreaming?: boolean;
  className?: string;
}

export function ChatMessage({
  role,
  content,
  steps,
  isStreaming,
  className,
}: ChatMessageProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={cn(
        "flex gap-3 p-4",
        isAssistant ? "bg-muted/50" : "",
        className
      )}
    >
      {/* Avatar */}
      <Avatar className="h-8 w-8 shrink-0">
        {isAssistant ? (
          <>
            <AvatarImage src="/sage-logo.svg" />
            <AvatarFallback>S</AvatarFallback>
          </>
        ) : (
          <AvatarFallback>U</AvatarFallback>
        )}
      </Avatar>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        {/* 推理步骤（仅 assistant 消息） */}
        {isAssistant && steps && steps.length > 0 && (
          <ReasoningAccordion steps={steps} />
        )}

        {/* 消息内容 */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <MarkdownRenderer content={content} />
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
```

## 注意
- steps 可选，兼容旧消息格式
- 仅 assistant 消息显示推理步骤
- 流式输出时显示光标动画
```

## 验收标准
- [ ] 支持 steps 属性
- [ ] ReasoningAccordion 正确集成
- [ ] 兼容旧消息格式
- [ ] 流式光标显示正常
