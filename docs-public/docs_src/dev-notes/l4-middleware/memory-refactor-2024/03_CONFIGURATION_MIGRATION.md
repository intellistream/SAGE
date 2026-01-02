# 配置文件迁移方案

> **目标**: 将 13 个配置文件从旧格式迁移到新格式
>
> **原则**: 保持向后兼容，逐步弃用旧格式

______________________________________________________________________

## 🎯 迁移目标

### 当前问题

```yaml
# 旧格式 (examples/tutorials/L5-apps/configs/memory/*.yaml)
service:
  type: "short_term_memory"  # ❌ 旧命名
  config:
    backend_type: "vdb"       # ❌ 指定特定 Collection
    max_capacity: 10
```

**问题**:

1. ❌ `type` 使用旧名称（如 short_term_memory）
1. ❌ `backend_type` 绑定特定 Collection
1. ❌ 索引配置分散在各处

### 新格式

```yaml
# 新格式
service:
  type: "partitional.fifo_queue"  # ✅ 新命名
  config:
    # Collection 配置（统一）
    collection:
      name: "my_fifo_queue"
      persist: true

    # 索引配置（集中管理）
    indexes:
      - name: "fifo_queue"
        type: "fifo"
        config:
          max_size: 10

    # Service 业务配置
    embedding_dim: 768
    top_k: 5
```

**优势**:

1. ✅ 命名清晰（partitional/hierarchical 分类）
1. ✅ Collection 配置统一
1. ✅ 索引配置集中（易于管理）
1. ✅ 业务逻辑配置独立

______________________________________________________________________

## 📐 配置结构设计

### 标准配置模板

```yaml
# config_template.yaml

service:
  # ========== Service 类型 ==========
  type: "partitional.fifo_queue"  # 13 个 Service 之一

  # ========== Collection 配置 ==========
  config:
    collection:
      name: "my_collection"       # Collection 名称
      persist: true                # 是否持久化
      data_dir: "/path/to/data"   # 数据目录（可选）

    # ========== 索引配置 ==========
    indexes:
      - name: "index_1"            # 索引名称（唯一）
        type: "faiss"              # 索引类型（faiss, lsh, graph, bm25, fifo, segment）
        config:                    # 索引特定配置
          dim: 768                 # FAISS: 向量维度
          metric: "cosine"         # FAISS: 距离度量

      - name: "index_2"
        type: "bm25"
        config:
          k1: 1.5
          b: 0.75

    # ========== Embedding 配置 ==========
    embedder:
      type: "openai"               # openai / huggingface / local
      model: "text-embedding-ada-002"
      api_key: "${OPENAI_API_KEY}"  # 环境变量

    # ========== Summarizer 配置 ==========
    summarizer:
      type: "llm"                  # llm / extractive / none
      model: "gpt-4"
      max_length: 100

    # ========== Service 业务配置 ==========
    top_k: 5                       # 默认检索数量
    threshold: 0.7                 # 相似度阈值
    enable_cache: true             # 是否启用缓存

    # ========== 日志配置 ==========
    logging:
      level: "INFO"
      file: "logs/service.log"
```

______________________________________________________________________

## 📝 13 个 Service 配置示例

### Partitional Services

#### 1. FIFO Queue

```yaml
# configs/partitional_fifo_queue.yaml

service:
  type: "partitional.fifo_queue"
  config:
    collection:
      name: "fifo_queue_demo"
      persist: true

    indexes:
      - name: "main_queue"
        type: "fifo"
        config:
          max_size: 10             # 最多保留 10 条

    top_k: 5
```

#### 2. LSH Hash

```yaml
# configs/partitional_lsh_hash.yaml

service:
  type: "partitional.lsh_hash"
  config:
    collection:
      name: "lsh_demo"
      persist: true

    indexes:
      - name: "lsh_index"
        type: "lsh"
        config:
          dim: 768
          num_tables: 10           # LSH 哈希表数量
          num_bits: 8              # 每个哈希函数位数

    embedder:
      type: "huggingface"
      model: "sentence-transformers/all-MiniLM-L6-v2"

    top_k: 5
```

#### 3. Segment

```yaml
# configs/partitional_segment.yaml

service:
  type: "partitional.segment"
  config:
    collection:
      name: "segment_demo"
      persist: true

    indexes:
      - name: "time_segments"
        type: "segment"
        config:
          strategy: "time"         # time / topic / size
          segment_size: 50         # 每段最多 50 条
          overlap: 5               # 段间重叠 5 条

    top_k: 5
```

#### 4. Feature + Summary + VectorStore Combination

```yaml
# configs/partitional_feature_summary_vectorstore_combination.yaml

service:
  type: "partitional.feature_summary_vectorstore_combination"
  config:
    collection:
      name: "feature_summary_vector_demo"
      persist: true

    indexes:
      # Level 1: Feature Map (BM25)
      - name: "feature_map"
        type: "bm25"
        config:
          k1: 1.5
          b: 0.75

      # Level 2: Summary Vector (FAISS)
      - name: "summary_vector"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

      # Level 3: Full Text Vector (FAISS)
      - name: "full_text_vector"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

    embedder:
      type: "openai"
      model: "text-embedding-ada-002"

    summarizer:
      type: "llm"
      model: "gpt-4"
      max_length: 100

    top_k: 5
    enable_detailed_retrieval: true  # 是否启用 Level 3
```

#### 5. Inverted + VectorStore Combination

```yaml
# configs/partitional_inverted_vectorstore_combination.yaml

service:
  type: "partitional.inverted_vectorstore_combination"
  config:
    collection:
      name: "inverted_vector_demo"
      persist: true

    indexes:
      # Stage 1: BM25 Recall
      - name: "inverted_index"
        type: "bm25"
        config:
          k1: 1.5
          b: 0.75

      # Stage 2: FAISS Rerank
      - name: "vector_index"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

    embedder:
      type: "huggingface"
      model: "BAAI/bge-large-zh-v1.5"

    recall_k: 50        # Stage 1 召回数量
    top_k: 5            # Stage 2 精排数量
```

______________________________________________________________________

### Hierarchical Services

#### 6. Semantic + Inverted + Knowledge Graph

```yaml
# configs/hierarchical_semantic_inverted_knowledge_graph.yaml

service:
  type: "hierarchical.semantic_inverted_knowledge_graph"
  config:
    collection:
      name: "kg_demo"
      persist: true

    indexes:
      # Graph Index
      - name: "knowledge_graph"
        type: "graph"
        config:
          backend: "networkx"      # networkx / neo4j
          directed: true

      # Inverted Index
      - name: "inverted_index"
        type: "bm25"
        config:
          k1: 1.5
          b: 0.75

      # Vector Index
      - name: "vector_index"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

    # NER Model (实体提取)
    ner_model:
      type: "huggingface"
      model: "dslim/bert-base-NER"

    # RE Model (关系提取)
    relation_extractor:
      type: "huggingface"
      model: "rebel-large"

    embedder:
      type: "openai"
      model: "text-embedding-ada-002"

    top_k: 5
    graph_hop: 2          # 图遍历深度
```

#### 7. Linknote Graph

```yaml
# configs/hierarchical_linknote_graph.yaml

service:
  type: "hierarchical.linknote_graph"
  config:
    collection:
      name: "linknote_demo"
      persist: true

    indexes:
      - name: "note_graph"
        type: "graph"
        config:
          backend: "networkx"
          directed: false

      - name: "note_vector"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

    embedder:
      type: "openai"
      model: "text-embedding-ada-002"

    # Linknote 特定配置
    link_patterns:
      - "[[note_name]]"            # Obsidian 风格
      - "#tag"                     # Tag 链接

    top_k: 5
    graph_hop: 3
```

#### 8. Property Graph

```yaml
# configs/hierarchical_property_graph.yaml

service:
  type: "hierarchical.property_graph"
  config:
    collection:
      name: "property_graph_demo"
      persist: true

    indexes:
      - name: "property_graph"
        type: "graph"
        config:
          backend: "neo4j"         # 使用 Neo4j
          uri: "bolt://localhost:7687"
          username: "neo4j"
          password: "${NEO4J_PASSWORD}"

      - name: "property_vector"
        type: "faiss"
        config:
          dim: 768
          metric: "cosine"

    embedder:
      type: "openai"
      model: "text-embedding-ada-002"

    # Property Graph 特定配置
    node_properties:
      - "name"
      - "type"
      - "created_at"

    edge_properties:
      - "relation_type"
      - "weight"

    top_k: 5
    graph_hop: 2
```

______________________________________________________________________

## 🔄 配置迁移脚本

### 自动迁移工具

```python
# tools/config_migration.py

import yaml
from pathlib import Path
from typing import Dict, Any

# 旧名称 → 新名称映射
SERVICE_NAME_MAPPING = {
    "short_term_memory": "partitional.fifo_queue",
    "vector_memory": "partitional.lsh_hash",
    "graph_memory": "hierarchical.property_graph",
    "hierarchical_memory": "hierarchical.semantic_inverted_knowledge_graph",
    "hybrid_memory": "partitional.feature_summary_vectorstore_combination",
    "key_value_memory": "partitional.segment",
}

# backend_type → indexes 映射
BACKEND_TO_INDEXES = {
    "vdb": [
        {"name": "vector_index", "type": "faiss", "config": {"dim": 768}}
    ],
    "graph": [
        {"name": "graph_index", "type": "graph", "config": {"backend": "networkx"}}
    ],
    "hybrid": [
        {"name": "vector_index", "type": "faiss", "config": {"dim": 768}},
        {"name": "graph_index", "type": "graph", "config": {"backend": "networkx"}},
        {"name": "bm25_index", "type": "bm25", "config": {}}
    ]
}


def migrate_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """将旧配置迁移到新格式

    Args:
        old_config: 旧配置字典

    Returns:
        new_config: 新配置字典
    """
    service_config = old_config.get("service", {})
    old_type = service_config.get("type")
    old_config_dict = service_config.get("config", {})

    # 1. 映射 Service 名称
    new_type = SERVICE_NAME_MAPPING.get(old_type, old_type)

    # 2. 提取 Collection 配置
    collection_name = old_config_dict.get("collection_name", "default")
    backend_type = old_config_dict.get("backend_type", "vdb")

    # 3. 生成 indexes 配置
    indexes = BACKEND_TO_INDEXES.get(backend_type, [])

    # 4. 提取其他配置
    other_config = {
        k: v for k, v in old_config_dict.items()
        if k not in ["collection_name", "backend_type"]
    }

    # 5. 构建新配置
    new_config = {
        "service": {
            "type": new_type,
            "config": {
                "collection": {
                    "name": collection_name,
                    "persist": True
                },
                "indexes": indexes,
                **other_config
            }
        }
    }

    return new_config


def migrate_config_file(input_path: Path, output_path: Path):
    """迁移配置文件

    Args:
        input_path: 旧配置文件路径
        output_path: 新配置文件路径
    """
    # 读取旧配置
    with open(input_path, "r") as f:
        old_config = yaml.safe_load(f)

    # 迁移
    new_config = migrate_config(old_config)

    # 写入新配置
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Migrated: {input_path} → {output_path}")


def migrate_all_configs(input_dir: Path, output_dir: Path):
    """批量迁移所有配置文件"""
    for yaml_file in input_dir.glob("*.yaml"):
        output_file = output_dir / yaml_file.name
        migrate_config_file(yaml_file, output_file)


if __name__ == "__main__":
    input_dir = Path("examples/tutorials/L5-apps/configs/memory")
    output_dir = Path("examples/tutorials/L5-apps/configs/memory_v2")

    migrate_all_configs(input_dir, output_dir)
    print("🎉 All configs migrated!")
```

### 使用方法

```bash
# 迁移所有配置文件
python tools/config_migration.py

# 迁移单个文件
python tools/config_migration.py \
  --input examples/tutorials/L5-apps/configs/memory/short_term.yaml \
  --output examples/tutorials/L5-apps/configs/memory_v2/partitional_fifo_queue.yaml
```

______________________________________________________________________

## 🔍 配置验证

### 验证脚本

```python
# tools/config_validator.py

from typing import Dict, Any, List
from pydantic import BaseModel, Field, validator


class IndexConfig(BaseModel):
    """索引配置模型"""
    name: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)

    @validator("type")
    def validate_index_type(cls, v):
        allowed = ["faiss", "lsh", "graph", "bm25", "fifo", "segment"]
        if v not in allowed:
            raise ValueError(f"Invalid index type: {v}. Must be one of {allowed}")
        return v


class CollectionConfig(BaseModel):
    """Collection 配置模型"""
    name: str
    persist: bool = True
    data_dir: str = None


class ServiceConfig(BaseModel):
    """Service 配置模型"""
    collection: CollectionConfig
    indexes: List[IndexConfig]
    top_k: int = 5
    threshold: float = 0.7

    class Config:
        extra = "allow"  # 允许额外字段（业务配置）


class MemoryServiceConfigRoot(BaseModel):
    """配置文件根模型"""
    service: Dict[str, Any]

    @validator("service")
    def validate_service(cls, v):
        required_fields = ["type", "config"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: service.{field}")

        # 验证 type 格式
        service_type = v["type"]
        if not (service_type.startswith("partitional.") or
                service_type.startswith("hierarchical.")):
            raise ValueError(
                f"Invalid service type: {service_type}. "
                "Must start with 'partitional.' or 'hierarchical.'"
            )

        return v


def validate_config_file(config_path: Path) -> bool:
    """验证配置文件是否符合新格式

    Returns:
        True if valid, False otherwise
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Pydantic 验证
        MemoryServiceConfigRoot(**config)

        print(f"✅ Valid: {config_path}")
        return True

    except Exception as e:
        print(f"❌ Invalid: {config_path}")
        print(f"   Error: {e}")
        return False


def validate_all_configs(config_dir: Path):
    """批量验证所有配置文件"""
    valid_count = 0
    total_count = 0

    for yaml_file in config_dir.glob("*.yaml"):
        total_count += 1
        if validate_config_file(yaml_file):
            valid_count += 1

    print(f"\n📊 Summary: {valid_count}/{total_count} configs are valid")
```

______________________________________________________________________

## 📝 实施任务清单

### Task 3.1: 创建新配置文件 (1天)

- [ ] 为 13 个 Service 创建标准配置模板
- [ ] 添加详细注释和示例
- [ ] 验证所有配置文件格式正确

### Task 3.2: 实现迁移脚本 (0.5天)

- [ ] 实现 `migrate_config()` 函数
- [ ] 实现 `migrate_all_configs()` 批量迁移
- [ ] 测试迁移结果

### Task 3.3: 实现验证脚本 (0.5天)

- [ ] 使用 Pydantic 定义配置模型
- [ ] 实现 `validate_config_file()` 验证函数
- [ ] 添加详细错误提示

### Task 3.4: 文档更新 (0.5天)

- [ ] 更新配置文件说明文档
- [ ] 添加迁移指南
- [ ] 更新示例代码

______________________________________________________________________

## 🧪 测试

```python
def test_config_migration():
    """测试配置迁移"""
    old_config = {
        "service": {
            "type": "short_term_memory",
            "config": {
                "collection_name": "test",
                "backend_type": "vdb",
                "max_capacity": 10
            }
        }
    }

    new_config = migrate_config(old_config)

    assert new_config["service"]["type"] == "partitional.fifo_queue"
    assert new_config["service"]["config"]["collection"]["name"] == "test"
    assert len(new_config["service"]["config"]["indexes"]) > 0


def test_config_validation():
    """测试配置验证"""
    valid_config = {
        "service": {
            "type": "partitional.fifo_queue",
            "config": {
                "collection": {"name": "test", "persist": True},
                "indexes": [
                    {"name": "queue", "type": "fifo", "config": {"max_size": 10}}
                ],
                "top_k": 5
            }
        }
    }

    # 应该通过验证
    MemoryServiceConfigRoot(**valid_config)
```

______________________________________________________________________

**下一步**: 阅读 `04_TESTING_STRATEGY.md` 了解测试策略
