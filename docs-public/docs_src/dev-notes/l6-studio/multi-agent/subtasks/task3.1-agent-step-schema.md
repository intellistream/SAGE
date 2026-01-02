# Task 3.1: AgentStep Schema 定义

## 目标

定义 Agent 执行步骤的数据模型，用于前后端通信。

## 依赖

无（基础模块）

## 文件位置

`packages/sage-studio/src/sage/studio/models/agent_step.py`

## 提示词

````
请定义 AgentStep 数据模型，作为 Agent 执行步骤的标准格式。

## 背景
Multi-Agent 系统需要流式输出执行步骤，前端展示推理过程。
需要统一的数据模型便于序列化和类型检查。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/models/agent_step.py

2. 使用 dataclass + JSON 序列化:
   ```python
   @dataclass
   class AgentStep:
       step_id: str
       type: StepType
       content: str
       status: StepStatus
       metadata: dict[str, Any]
````

3. 定义枚举:
   - StepType: reasoning, tool_call, tool_result, response
   - StepStatus: pending, running, completed, failed

## 代码模板

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class StepType(str, Enum):
    """步骤类型"""
    REASONING = "reasoning"      # 推理思考
    TOOL_CALL = "tool_call"      # 工具调用
    TOOL_RESULT = "tool_result"  # 工具返回
    RESPONSE = "response"        # 最终回复


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败


@dataclass
class AgentStep:
    """Agent 执行步骤

    表示 Multi-Agent 系统执行过程中的一个步骤，
    用于前端展示推理过程和工具调用。
    """
    step_id: str
    type: StepType
    content: str
    status: StepStatus = StepStatus.COMPLETED
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        type: StepType | str,
        content: str,
        status: StepStatus | str = StepStatus.COMPLETED,
        **metadata
    ) -> AgentStep:
        """便捷创建方法"""
        if isinstance(type, str):
            type = StepType(type)
        if isinstance(status, str):
            status = StepStatus(status)

        return cls(
            step_id=str(uuid.uuid4())[:8],
            type=type,
            content=content,
            status=status,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "step_id": self.step_id,
            "type": self.type.value,
            "content": self.content,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentStep:
        """从字典创建"""
        return cls(
            step_id=data["step_id"],
            type=StepType(data["type"]),
            content=data["content"],
            status=StepStatus(data["status"]),
            metadata=data.get("metadata", {}),
        )


# 便捷工厂函数
def reasoning_step(content: str, **metadata) -> AgentStep:
    """创建推理步骤"""
    return AgentStep.create(StepType.REASONING, content, **metadata)


def tool_call_step(content: str, tool_name: str, **metadata) -> AgentStep:
    """创建工具调用步骤"""
    return AgentStep.create(
        StepType.TOOL_CALL,
        content,
        status=StepStatus.RUNNING,
        tool_name=tool_name,
        **metadata
    )


def tool_result_step(content: str, tool_name: str, **metadata) -> AgentStep:
    """创建工具结果步骤"""
    return AgentStep.create(StepType.TOOL_RESULT, content, tool_name=tool_name, **metadata)
```

## 注意

- Enum 值使用字符串便于 JSON 序列化
- 提供 to_dict/from_dict 便于序列化
- 便捷工厂函数简化创建

```

## 验收标准
- [ ] 枚举定义完整
- [ ] dataclass 正确实现
- [ ] JSON 序列化/反序列化正常
- [ ] 工厂函数可用
```
