# 阶段 3: 数据处理与向量化支持

## 3.1 数据清理与预处理 - Python API实现
专注于大数据范式的数据清理能力，提供sage_examples兼容的Python接口：

### Python API设计目标：
```python
# 参考sage_examples/qa_openai.py和external_memory_ingestion_pipeline.py
from sage_flow.environment import SageFlowEnvironment
from sage_flow.functions import (
    DocumentParserFunction, TextCleanerFunction, 
    ImagePreprocessorFunction, DeduplicatorFunction
)
from sage_flow.sources import FileDataSource, DirectoryDataSource
from sage_flow.sinks import TerminalSink, FileSink
from sage_utils.config_loader import load_config

def create_data_cleaning_pipeline():
    \"\"\"数据清理管道 - 兼容sage_examples模式\"\"\"
    config = load_config("sage_flow_config.yaml")
    env = SageFlowEnvironment("data_cleaning")
    env.set_memory(config=config.get("memory"))
    
    # 多格式数据源 - 链式处理
    (env
        .from_source(DirectoryDataSource, {
            "path": "/data/raw_documents/",
            "formats": ["pdf", "docx", "txt", "html", "csv"],
            "recursive": True,
            "batch_size": 100
        })
        .map(DocumentParserFunction, {
            "extract_metadata": True,
            "preserve_structure": False,
            "encoding": "auto"
        })
        .map(TextCleanerFunction, {
            "remove_patterns": [r"\\s+", r"[^\\w\\s]"],
            "min_length": 50,
            "quality_threshold": 0.3
        })
        .filter(lambda msg: msg.get_quality_score() > 0.5)
        .map(DeduplicatorFunction, {
            "similarity_threshold": 0.8,
            "hash_method": "simhash"
        })
        .sink(FileSink, {
            "output_path": "/data/cleaned/",
            "format": "jsonl",
            "compress": True
        })
    )
    
    env.submit()
    env.run_streaming()
```

### C++后端实现要求（对应Python API）：
- [ ] **多格式数据解析器** - C++17/20实现
  - JSON: 使用 `rapidjson` 或 `nlohmann/json`
  - XML: 使用 `pugixml` 或 `tinyxml2`
  - CSV: 使用 `fast-cpp-csv-parser`
  - PDF: 集成 `poppler-cpp` 或 `mupdf`
  - DOCX: 使用 `libxml2` 解析Office文档

- [ ] **文本清理和预处理** - 高性能C++实现
  ```cpp
  namespace sage_flow {
  class TextCleanerFunction final : public MapOperator {
   public:
    explicit TextCleanerFunction(const TextCleanConfig& config);
    auto map(std::unique_ptr<MultiModalMessage> input) 
        -> std::unique_ptr<MultiModalMessage> override;
   private:
    std::vector<std::regex> compiled_patterns_;
    auto cleanText(const std::string& text) const -> std::string;
    auto calculateQualityScore(const std::string& text) const -> float;
  };
  }
  ```

- [ ] **数据去重和相似性检测** - 算法优化
  - 使用SimHash、MinHash等高效算法
  - C++ STL容器优化的查找和比较
  - 内存友好的大数据处理

- [ ] **图像预处理** - OpenCV集成
  ```cpp
  class ImagePreprocessorFunction final : public MapOperator {
   public:
    auto map(std::unique_ptr<MultiModalMessage> input) 
        -> std::unique_ptr<MultiModalMessage> override;
   private:
    cv::Size target_size_;
    auto resizeImage(const cv::Mat& image) const -> cv::Mat;
    auto extractFeatures(const cv::Mat& image) const -> VectorData;
  };
  ```

### 与sage_examples集成验证：
- [ ] 配置文件兼容: 支持与现有YAML配置格式兼容
- [ ] 错误处理一致: 与sage_libs的错误处理模式统一
- [ ] 日志格式统一: 使用sage_utils.logging_utils格式
- [ ] 性能指标: 提供与sage_frontend兼容的监控指标

## 3.2 向量化与Embedding支持 - Python API实现
提供与sage_memory和sage_libs集成的向量化处理能力：

### Python API设计目标：
```python
# 参考sage_libs/rag/retriever.py和sage_memory设计模式
from sage_flow.environment import SageFlowEnvironment
from sage_flow.functions import (
    TextEmbeddingFunction, ImageEmbeddingFunction,
    DenseVectorIndexFunction, HybridIndexFunction
)
from sage_flow.operators import WindowOperator, AggregateOperator

def create_text_embedding_pipeline():
    \"\"\"文本向量化管道 - 兼容sage_memory\"\"\"
    config = load_config("embedding_config.yaml")
    env = SageFlowEnvironment("text_embedding")
    env.set_memory(config=config.get("memory"))
    
    (env
        .from_source(FileDataSource, {
            "path": "/data/cleaned_texts/",
            "batch_size": 500
        })
        .map(TextEmbeddingFunction, {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "device": "cuda:0",
            "batch_size": 32,
            "normalize": True,
            "pooling": "mean"
        })
        .window(WindowOperator, {
            "window_type": "tumbling",
            "size": 1000,
            "timeout_ms": 30000
        })
        .map(DenseVectorIndexFunction, {
            "index_type": "hnsw",
            "ef_construction": 200,
            "max_connections": 16,
            "distance_metric": "cosine"
        })
        .sink(VectorStoreSink, {
            "collection_name": "text_embeddings",
            "metadata_fields": ["source", "timestamp", "quality_score"]
        })
    )
    
    env.submit()
    env.run_streaming()
```

### C++后端向量化实现：
- [ ] **Embedding生成器** - 集成深度学习框架
  - 支持ONNX Runtime或LibTorch
  - 批量处理优化
  - GPU加速支持
  - 内存池管理

- [ ] **向量索引系统** - 高性能索引算法
  - HNSW (Hierarchical Navigable Small World)
  - IVF (Inverted File)
  - 暴力搜索 (Brute Force)
  - 自定义索引算法

### 与SAGE生态集成：
- [ ] sage_memory集成: 自动向量存储和检索
- [ ] sage_libs集成: 与RAG系统协作
- [ ] 性能监控: 向sage_frontend提供实时指标

## 3.3 实时流处理 - Python API实现
支持流式数据处理和实时更新：

### 实时处理能力：
- [ ] **流式数据源**: Kafka、WebSocket、文件监控
- [ ] **窗口操作**: 时间窗口、计数窗口、会话窗口
- [ ] **状态管理**: 有状态函数、检查点机制
- [ ] **实时索引更新**: 增量向量索引构建
- [ ] **低延迟处理**: 毫秒级处理延迟目标
