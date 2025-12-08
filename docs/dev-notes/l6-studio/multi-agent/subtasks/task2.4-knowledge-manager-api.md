# Task 2.4: KnowledgeManager API

## 目标
实现 KnowledgeManager 的完整 API，整合配置加载、文档加载、向量存储。

## 依赖
- Task 2.1 (Schema)
- Task 2.2 (DocumentLoader)
- Task 2.3 (VectorStore)

## 文件位置
`packages/sage-studio/src/sage/studio/services/knowledge_manager.py` (完善)

## 提示词

```
请完善 KnowledgeManager 类，实现知识库的完整管理功能。

## 要求
1. 整合前面实现的组件:
   - DocumentLoader: 加载文档
   - VectorStore: 向量存储和检索

2. 实现完整的 KnowledgeManager:
   ```python
   class KnowledgeManager:
       def __init__(self, config_path: str | Path | None = None):
           """
           初始化知识库管理器

           Args:
               config_path: 配置文件路径，默认使用 studio 内置配置
           """
           pass

       def _load_config(self, config_path: Path | None) -> None:
           """加载 YAML 配置"""
           pass

       async def ensure_source_loaded(self, source_name: str) -> bool:
           """确保指定知识源已加载

           这是"按需加载"的核心方法:
           1. 检查是否已加载
           2. 如未加载，调用 DocumentLoader
           3. 将 chunks 添加到 VectorStore
           """
           pass

       async def add_document(
           self,
           file_path: str | Path,
           source_name: str = "user_uploads"
       ) -> bool:
           """添加单个文档（用于文件上传）"""
           pass

       async def search(
           self,
           query: str,
           sources: list[str] | None = None,
           limit: int = 5,
           score_threshold: float = 0.7,
       ) -> list[SearchResult]:
           """在指定知识源中检索

           Args:
               query: 检索查询
               sources: 指定检索源，None 表示所有已加载的源
               limit: 返回结果数量
               score_threshold: 最低分数阈值
           """
           pass

       def get_loaded_sources(self) -> list[str]:
           """获取已加载的知识源列表"""
           pass

       def get_source_stats(self, source_name: str) -> dict:
           """获取知识源统计信息"""
           pass
   ```

3. 配置加载:
   - 从 knowledge_sources.yaml 读取配置
   - 支持环境变量覆盖
   - 路径支持 ~ 展开

4. 按需加载策略:
   - 启动时不加载任何源
   - 首次检索某源时自动加载
   - 缓存已加载状态

## 代码模板
```python
import yaml
from pathlib import Path
from typing import Optional

from sage.studio.services.document_loader import DocumentLoader
from sage.studio.services.vector_store import VectorStore


class KnowledgeManager:
    """知识库管理器

    负责管理多个知识源，实现按需加载和统一检索。
    """

    def __init__(self, config_path: str | Path | None = None):
        self.sources: dict[str, KnowledgeSource] = {}
        self._loaded_sources: set[str] = set()
        self._vector_stores: dict[str, VectorStore] = {}
        self._doc_loader = DocumentLoader()

        self._load_config(config_path)

    def _load_config(self, config_path: Path | None) -> None:
        if config_path is None:
            # 默认配置路径
            config_path = Path(__file__).parent.parent / "config" / "knowledge_sources.yaml"

        config_path = Path(config_path).expanduser()
        if not config_path.exists():
            return  # 使用默认配置

        with open(config_path) as f:
            config = yaml.safe_load(f)

        for name, source_config in config.get("knowledge_sources", {}).items():
            self.sources[name] = KnowledgeSource(
                name=name,
                type=SourceType(source_config["type"]),
                path=source_config["path"],
                description=source_config.get("description", ""),
                enabled=source_config.get("enabled", True),
                auto_load=source_config.get("auto_load", False),
                is_dynamic=source_config.get("is_dynamic", False),
                file_patterns=source_config.get("file_patterns", ["*"]),
            )

    async def ensure_source_loaded(self, source_name: str) -> bool:
        if source_name in self._loaded_sources:
            return True

        source = self.sources.get(source_name)
        if not source or not source.enabled:
            return False

        # 创建或获取向量存储
        if source_name not in self._vector_stores:
            self._vector_stores[source_name] = VectorStore(
                collection_name=f"studio_kb_{source_name}",
                persist_dir=Path("~/.local/share/sage/studio/vector_db/").expanduser(),
            )

        # 加载文档
        chunks = list(self._doc_loader.load_directory(
            Path(source.path).expanduser(),
            source.file_patterns,
            source.type,
        ))

        # 添加到向量存储
        await self._vector_stores[source_name].add_documents(chunks)

        self._loaded_sources.add(source_name)
        return True

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> list[SearchResult]:
        # 确定要检索的源
        target_sources = sources or list(self._loaded_sources)

        # 确保源已加载
        for source_name in target_sources:
            await self.ensure_source_loaded(source_name)

        # 在各源中检索并合并结果
        all_results = []
        for source_name in target_sources:
            if source_name in self._vector_stores:
                results = await self._vector_stores[source_name].search(
                    query, limit, score_threshold
                )
                all_results.extend(results)

        # 按分数排序，取 top-k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:limit]
```

## 注意
- 线程安全：考虑并发访问
- 错误处理：源不存在、加载失败等情况
- 日志记录：加载和检索过程
```

## 验收标准
- [ ] 配置文件正确加载
- [ ] 按需加载工作正常
- [ ] 多源检索并合并结果
- [ ] 支持用户上传文档
