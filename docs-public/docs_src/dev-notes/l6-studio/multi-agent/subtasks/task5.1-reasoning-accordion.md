# Task 5.1: ReasoningAccordion 组件

## 目标

实现前端 ReasoningAccordion 组件，展示 Agent 推理步骤。

## 依赖

- Task 3.1 (AgentStep Schema - 对应前端类型)

## 文件位置

`packages/sage-studio/src/sage/studio/frontend/src/components/ReasoningAccordion.tsx`

## 提示词

````
请实现 ReasoningAccordion React 组件，用于展示 Agent 推理步骤。

## 背景
Multi-Agent 系统会流式返回执行步骤 (AgentStep)，前端需要:
1. 实时展示每个步骤
2. 可折叠展开查看详情
3. 显示步骤状态（进行中、完成、失败）

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/frontend/src/components/ReasoningAccordion.tsx

2. 组件 Props:
   ```typescript
   interface AgentStep {
     step_id: string;
     type: "reasoning" | "tool_call" | "tool_result" | "response";
     content: string;
     status: "pending" | "running" | "completed" | "failed";
     metadata?: Record<string, any>;
   }

   interface ReasoningAccordionProps {
     steps: AgentStep[];
     isExpanded?: boolean;
     onToggle?: () => void;
   }
````

3. UI 设计:
   - 默认收起，显示 "思考中..." 或 "思考完成"
   - 展开后显示步骤列表
   - 每个步骤有图标和状态指示

## 代码模板

```tsx
import React, { useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Brain, Wrench, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentStep {
  step_id: string;
  type: "reasoning" | "tool_call" | "tool_result" | "response";
  content: string;
  status: "pending" | "running" | "completed" | "failed";
  metadata?: Record<string, any>;
}

interface ReasoningAccordionProps {
  steps: AgentStep[];
  className?: string;
}

const stepIcons = {
  reasoning: Brain,
  tool_call: Wrench,
  tool_result: CheckCircle,
  response: CheckCircle,
};

const statusColors = {
  pending: "text-gray-400",
  running: "text-blue-500 animate-pulse",
  completed: "text-green-500",
  failed: "text-red-500",
};

export function ReasoningAccordion({ steps, className }: ReasoningAccordionProps) {
  const hasRunning = steps.some((s) => s.status === "running");
  const allCompleted = steps.length > 0 && steps.every((s) => s.status === "completed");

  const headerText = hasRunning
    ? "思考中..."
    : allCompleted
    ? `思考完成 (${steps.length} 步)`
    : "推理步骤";

  return (
    <Accordion type="single" collapsible className={cn("w-full", className)}>
      <AccordionItem value="reasoning" className="border-none">
        <AccordionTrigger className="py-2 text-sm text-muted-foreground hover:no-underline">
          <div className="flex items-center gap-2">
            {hasRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Brain className="h-4 w-4" />
            )}
            <span>{headerText}</span>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2 pl-4 border-l-2 border-muted">
            {steps.map((step) => {
              const Icon = stepIcons[step.type] || Brain;
              return (
                <div
                  key={step.step_id}
                  className="flex items-start gap-2 text-sm"
                >
                  <Icon
                    className={cn("h-4 w-4 mt-0.5", statusColors[step.status])}
                  />
                  <div className="flex-1">
                    <p className={cn(
                      step.status === "failed" && "text-red-500"
                    )}>
                      {step.content}
                    </p>
                    {step.metadata && Object.keys(step.metadata).length > 0 && (
                      <pre className="mt-1 text-xs text-muted-foreground bg-muted p-2 rounded overflow-x-auto">
                        {JSON.stringify(step.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

export default ReasoningAccordion;
```

## 注意

- 使用 shadcn/ui Accordion 组件
- 步骤类型对应不同图标
- 状态用颜色和动画区分
- metadata 可选显示

```

## 验收标准
- [ ] 组件正确渲染步骤列表
- [ ] 折叠/展开功能正常
- [ ] 状态指示清晰
- [ ] 响应式设计
```
