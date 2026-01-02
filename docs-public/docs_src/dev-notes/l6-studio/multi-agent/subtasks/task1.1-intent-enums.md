# Task 1.1: Intent 枚举定义

## 目标

定义用户意图的枚举类型和结果数据结构。

## 文件位置

`packages/sage-studio/src/sage/studio/services/intent_classifier.py` (部分)

## 设计说明

### 意图分类（简化版）

经过分析，用户意图可以简化为 4 类：

| 意图                 | 说明                             | 示例                                                |
| -------------------- | -------------------------------- | --------------------------------------------------- |
| **KNOWLEDGE_QUERY**  | 知识库问答（包括研究指导）       | "SAGE 怎么安装？"、"怎么写 Related Work？"          |
| **SAGE_CODING**      | SAGE 编程助手（Pipeline + 代码） | "帮我写一个数据处理 Pipeline"、"这段代码哪里错了？" |
| **SYSTEM_OPERATION** | 系统操作                         | "启动 LLM 服务"、"查看状态"                         |
| **GENERAL_CHAT**     | 普通对话                         | "你好"、"谢谢"                                      |

### 知识领域标签

KNOWLEDGE_QUERY 可以进一步标记领域：

- `sage_docs`: SAGE 框架文档
- `examples`: 代码示例
- `research_guidance`: 研究方法论（导师经验）
- `user_uploads`: 用户上传的资料

## 提示词

````
请在 SAGE 项目中创建意图分类器的基础数据结构。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/intent_classifier.py
2. 创建 UserIntent 枚举，包含以下意图类型:
   - KNOWLEDGE_QUERY: 知识库问答（SAGE 文档、研究指导、用户资料）
   - SAGE_CODING: SAGE 编程助手（Pipeline 生成、代码调试、API 解释）
   - SYSTEM_OPERATION: 系统操作（启动服务、查看状态、管理知识库）
   - GENERAL_CHAT: 普通对话

3. 创建 KnowledgeDomain 枚举，表示知识领域:
   - SAGE_DOCS: SAGE 框架文档
   - EXAMPLES: 代码示例
   - RESEARCH_GUIDANCE: 研究方法论（导师经验文档）
   - USER_UPLOADS: 用户上传的资料

4. 创建 IntentResult 数据类:
   - intent: UserIntent
   - confidence: float (0-1)
   - knowledge_domains: list[KnowledgeDomain] | None (仅 KNOWLEDGE_QUERY)
   - matched_keywords: list[str]
   - raw_prediction: Any | None (用于调试)

## 代码模板
```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UserIntent(Enum):
    """用户意图类型

    简化为 4 类核心意图：
    - KNOWLEDGE_QUERY: 任何需要检索知识库的问题
    - SAGE_CODING: SAGE 框架相关的编程任务
    - SYSTEM_OPERATION: 系统管理操作
    - GENERAL_CHAT: 普通对话
    """
    KNOWLEDGE_QUERY = "knowledge_query"
    SAGE_CODING = "sage_coding"
    SYSTEM_OPERATION = "system_operation"
    GENERAL_CHAT = "general_chat"


class KnowledgeDomain(Enum):
    """知识领域

    用于 KNOWLEDGE_QUERY 意图时，指定要检索的知识来源。
    """
    SAGE_DOCS = "sage_docs"          # SAGE 框架官方文档
    EXAMPLES = "examples"             # 代码示例和教程
    RESEARCH_GUIDANCE = "research_guidance"  # 研究方法论、写作经验
    USER_UPLOADS = "user_uploads"     # 用户上传的资料


@dataclass
class IntentResult:
    """意图分类结果

    Attributes:
        intent: 识别出的用户意图
        confidence: 置信度 (0-1)
        knowledge_domains: 相关知识领域（仅 KNOWLEDGE_QUERY 时有效）
        matched_keywords: 命中的关键词列表
        raw_prediction: 原始预测结果（调试用）
    """
    intent: UserIntent
    confidence: float
    knowledge_domains: list[KnowledgeDomain] | None = None
    matched_keywords: list[str] = field(default_factory=list)
    raw_prediction: Any | None = None

    def should_search_knowledge(self) -> bool:
        """是否需要检索知识库"""
        return self.intent == UserIntent.KNOWLEDGE_QUERY

    def get_search_sources(self) -> list[str]:
        """获取要检索的知识源"""
        if not self.knowledge_domains:
            return ["sage_docs", "examples"]  # 默认检索
        return [d.value for d in self.knowledge_domains]
````

## 注意

- Layer: L6 (sage-studio)
- 使用 Python 3.10+ 语法
- 添加完整的 docstring
- 遵循 tools/ruff.toml 代码风格

```

## 验收标准
- [ ] UserIntent 枚举包含 4 种意图类型
- [ ] KnowledgeDomain 枚举包含 4 种知识领域
- [ ] IntentResult 包含所有必要字段
- [ ] 代码通过 ruff 检查
- [ ] 有完整的类型注解和 docstring
```
