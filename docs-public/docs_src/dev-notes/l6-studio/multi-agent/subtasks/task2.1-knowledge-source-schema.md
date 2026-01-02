# Task 2.1: 知识源 Schema 定义

## 目标

定义知识源的数据结构和配置 Schema。

## 文件位置

- `packages/sage-studio/src/sage/studio/services/knowledge_manager.py` (部分)
- `packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml`

## 提示词

````
请创建知识库管理器的基础数据结构和配置文件。

## 要求

### Part 1: Python 数据结构
文件: packages/sage-studio/src/sage/studio/services/knowledge_manager.py

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SourceType(Enum):
    """知识源类型"""
    MARKDOWN = "markdown"
    PYTHON_CODE = "python_code"
    JSON = "json"
    YAML = "yaml"
    PDF = "pdf"
    USER_UPLOAD = "user_upload"


@dataclass
class KnowledgeSource:
    """知识源定义"""
    name: str                          # 唯一标识符
    type: SourceType                   # 源类型
    path: str | Path                   # 文件/目录路径
    description: str = ""              # 描述
    enabled: bool = True               # 是否启用
    auto_load: bool = False            # 是否自动加载
    is_dynamic: bool = False           # 是否动态（如用户上传）
    file_patterns: list[str] = field(default_factory=lambda: ["*"])  # 文件匹配模式
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """检索结果"""
    content: str                       # 匹配的文本内容
    score: float                       # 相似度分数 (0-1)
    source: str                        # 来源名称
    file_path: str | None = None       # 原始文件路径
    chunk_id: str | None = None        # 分块 ID
    metadata: dict[str, Any] = field(default_factory=dict)
````

### Part 2: YAML 配置文件

文件: packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml

```yaml
# SAGE Studio 知识源配置
# 注意: auto_load=false 表示按需加载，不会在启动时自动加载

knowledge_sources:
  sage_docs:
    type: markdown
    path: "docs-public/docs_src"
    description: "SAGE 官方文档"
    enabled: true
    auto_load: false
    file_patterns:
      - "*.md"
      - "**/*.md"

  examples:
    type: python_code
    path: "examples/"
    description: "SAGE 示例代码"
    enabled: true
    auto_load: false
    file_patterns:
      - "*.py"
      - "**/*.py"

  api_reference:
    type: python_code
    path: "packages/"
    description: "SAGE API 文档 (从 docstring 提取)"
    enabled: true
    auto_load: false
    file_patterns:
      - "**/src/**/*.py"
    metadata:
      extract_docstrings: true

  user_uploads:
    type: user_upload
    path: "~/.local/share/sage/studio/uploads/"
    description: "用户上传的文档"
    enabled: true
    auto_load: false
    is_dynamic: true
    file_patterns:
      - "*.pdf"
      - "*.md"
      - "*.txt"
      - "*.py"

# 向量存储配置
vector_store:
  type: "chroma"  # 或 "milvus", "faiss"
  persist_dir: "~/.local/share/sage/studio/vector_db/"
  collection_prefix: "studio_kb_"

# Embedding 配置
embedding:
  model: "BAAI/bge-small-zh-v1.5"
  batch_size: 32
  max_length: 512
```

## 注意

- 路径支持 ~ 展开
- file_patterns 使用 glob 语法
- 所有源默认 auto_load=false（按需加载）

```

## 验收标准
- [ ] SourceType 枚举包含所有需要的类型
- [ ] KnowledgeSource 包含所有必要字段
- [ ] YAML 配置文件语法正确
- [ ] 配置支持 4+ 种知识源
```
