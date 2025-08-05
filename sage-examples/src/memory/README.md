# 内存和知识管理应用 (Memory Applications)

这个目录包含与SAGE框架内存系统相关的应用示例，展示了知识库构建、数据摄取、内存管理等功能。

## 📁 应用列表

### 🧬 专业知识库
#### `biology_rag_knowledge.py`
生物学专业知识库应用
- **功能**: 构建和查询生物学专业知识库
- **应用场景**: 科研问答、专业领域RAG
- **特点**: 专业术语理解、领域知识整合

### 💾 数据摄取和处理
#### `external_memory_ingestion_pipeline.py`
外部数据摄取管道
- **功能**: 将外部文件数据摄取到SAGE内存系统
- **应用场景**: 知识库构建、数据迁移、批量导入
- **流程**: 文件读取 → 文本分块 → 内存写入 → 结果输出
- **配置**: 使用`config_for_ingest.yaml`配置

### 🧠 内存问答系统
#### `memqa.py`
内存增强的问答系统
- **功能**: 基于GPU加速的内存问答
- **特点**: CUDA支持、高性能计算
- **应用**: 大规模知识检索和问答

### 📝 内存写入操作
#### `mem_offline_write.py`
离线内存写入示例
- **功能**: 批量离线数据写入内存系统
- **应用场景**: 数据预处理、知识库初始化

#### `mem_offline_write_test.py` 
内存写入功能测试
- **功能**: 测试内存写入功能的正确性
- **用途**: 开发调试、功能验证

### 🔧 内存操作示例
#### `mem_examples.py`
内存操作基础示例
- **功能**: 展示各种内存操作的基本用法
- **学习目标**: 理解内存API和操作模式

#### `raw_qa_insert.py`
原始QA数据插入
- **功能**: 将原始问答数据插入到内存系统
- **应用**: 数据格式转换、系统初始化

## 🚀 快速开始

### 数据摄取到内存系统
```bash
# 配置数据源路径
python external_memory_ingestion_pipeline.py
```

### 构建专业知识库
```bash
python biology_rag_knowledge.py
```

### 测试内存功能
```bash
python mem_offline_write_test.py
```

## ⚙️ 配置要求

### 数据摄取配置
使用`../config/config_for_ingest.yaml`：
```yaml
source:
  file_path: "data/input/"
chunk:
  chunk_size: 1000
  overlap: 100
writer:
  collection_name: "knowledge_base"
sink:
  output_path: "data/output/"
```

### GPU配置（可选）
如需GPU加速（如memqa.py）：
```bash
# 检查CUDA环境
nvidia-smi

# 安装GPU依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 💡 应用场景

### 🏢 企业知识库
- 文档自动摄取和索引
- 专业领域知识整合
- 企业内部问答系统

### 🔬 科研应用
- 学术文献知识库
- 专业术语和概念管理
- 研究数据的结构化存储

### 📚 教育平台
- 教学资源整合
- 智能问答助手
- 个性化学习推荐

## 🔧 故障排除

### 常见问题
1. **内存不足**: 调整chunk_size和batch_size
2. **CUDA错误**: 检查GPU驱动和PyTorch版本
3. **配置文件找不到**: 确认配置文件路径正确

### 性能优化
```python
# 调整批处理大小
config["chunk"]["chunk_size"] = 500  # 减少内存占用

# 开启GPU加速
torch.cuda.set_device(0)
```

## 🔗 相关资源

- [内存系统文档](../../packages/sage-userspace/src/sage/service/memory/)
- [配置文件说明](../config/README.md)
- [数据摄取最佳实践](../../docs/data-ingestion.md)
