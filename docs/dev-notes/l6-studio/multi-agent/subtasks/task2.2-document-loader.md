# Task 2.2: 文档加载器实现

## 目标
实现不同类型文档的加载和分块逻辑。

## 依赖
- Task 2.1 (SourceType, KnowledgeSource)

## 文件位置
`packages/sage-studio/src/sage/studio/services/document_loader.py`

## 提示词

```
请实现文档加载器，支持加载不同类型的文档并进行分块。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/document_loader.py

2. 实现 DocumentLoader 类:
   ```python
   from pathlib import Path
   from typing import Iterator
   from dataclasses import dataclass

   @dataclass
   class DocumentChunk:
       content: str
       source_file: str
       chunk_index: int
       metadata: dict

   class DocumentLoader:
       def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
           self.chunk_size = chunk_size
           self.chunk_overlap = chunk_overlap

       def load_directory(
           self,
           path: Path,
           patterns: list[str],
           source_type: SourceType
       ) -> Iterator[DocumentChunk]:
           """加载目录下的所有匹配文件"""
           pass

       def load_file(self, path: Path, source_type: SourceType) -> list[DocumentChunk]:
           """加载单个文件"""
           pass

       def _load_markdown(self, path: Path) -> list[DocumentChunk]:
           """加载 Markdown 文件"""
           pass

       def _load_python(self, path: Path) -> list[DocumentChunk]:
           """加载 Python 文件，提取 docstring 和代码"""
           pass

       def _load_pdf(self, path: Path) -> list[DocumentChunk]:
           """加载 PDF 文件"""
           pass

       def _chunk_text(self, text: str, metadata: dict) -> list[DocumentChunk]:
           """将长文本切分为多个 chunk"""
           pass
   ```

3. 分块策略:
   - Markdown: 按标题 (##) 分块，保留标题作为 metadata
   - Python: 按函数/类分块，提取 docstring
   - PDF: 按页分块，或按段落分块
   - 通用文本: 按字符数分块，保留重叠

4. Metadata 包含:
   - source_file: 文件路径
   - source_type: 文件类型
   - title: 标题（如果有）
   - language: 语言（对于代码）

## 代码模板
```python
import ast
import re
from pathlib import Path
from typing import Iterator

from sage.studio.services.knowledge_manager import SourceType


@dataclass
class DocumentChunk:
    content: str
    source_file: str
    chunk_index: int
    metadata: dict


class DocumentLoader:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_directory(
        self,
        path: Path,
        patterns: list[str],
        source_type: SourceType
    ) -> Iterator[DocumentChunk]:
        path = Path(path).expanduser()
        for pattern in patterns:
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    yield from self.load_file(file_path, source_type)

    def load_file(self, path: Path, source_type: SourceType) -> list[DocumentChunk]:
        loaders = {
            SourceType.MARKDOWN: self._load_markdown,
            SourceType.PYTHON_CODE: self._load_python,
            SourceType.PDF: self._load_pdf,
        }
        loader = loaders.get(source_type, self._load_text)
        return loader(path)

    def _load_markdown(self, path: Path) -> list[DocumentChunk]:
        content = path.read_text(encoding="utf-8")
        # 按 ## 标题分块
        sections = re.split(r'\n(?=##\s)', content)
        chunks = []
        for i, section in enumerate(sections):
            # 提取标题
            title_match = re.match(r'^##\s+(.+)', section)
            title = title_match.group(1) if title_match else f"Section {i}"
            chunks.append(DocumentChunk(
                content=section.strip(),
                source_file=str(path),
                chunk_index=i,
                metadata={"title": title, "type": "markdown"}
            ))
        return chunks

    # ... 实现其他加载方法
```

## 注意
- 处理文件编码问题 (UTF-8, GBK 等)
- 处理大文件时使用生成器避免内存问题
- PDF 加载需要 pypdf 或 pdfplumber 依赖
```

## 验收标准
- [ ] 支持 Markdown, Python, PDF 三种格式
- [ ] 分块逻辑合理（不破坏句子）
- [ ] 正确提取 metadata
- [ ] 处理了编码和大文件问题
