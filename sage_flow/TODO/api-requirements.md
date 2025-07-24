# Python API核心要求 - SAGE生态系统兼容

**sage_flow必须提供与sage_core DataStream API完全兼容的Python接口**，支持链式调用构建算子流。参考sage_examples中的实现模式：

## 基础API兼容性模式
```python
# 标准SAGE DataStream API模式 - sage_flow必须兼容
from sage_core.api.local_environment import LocalEnvironment
from sage_flow.functions import (
    TextCleanerFunction, DocumentParserFunction, 
    EmbeddingGeneratorFunction, ImagePreprocessorFunction
)
from sage_flow.sources import FileDataSource, KafkaDataSource, DirectoryDataSource  
from sage_flow.sinks import VectorStoreSink, TerminalSink, FileSink
from sage_utils.config_loader import load_config

def create_sage_flow_pipeline(config_path: str):
    """sage_flow的标准使用模式 - 必须与sage_examples兼容"""
    config = load_config(config_path)
    env = LocalEnvironment("sage_flow_pipeline")
    env.set_memory(config=config.get("memory"))
    
    # sage_flow数据处理流程 - 链式调用（与sage_examples一致）
    (env
        .from_source(FileDataSource, config["source"])           # 数据源
        .map(DocumentParserFunction, config["parser"])           # 文档解析  
        .map(TextCleanerFunction, config["cleaner"])            # 文本清理
        .filter(lambda msg: msg.get_quality_score() > 0.5)      # 质量过滤
        .map(EmbeddingGeneratorFunction, config["embedder"])     # 向量化
        .sink(VectorStoreSink, config["sink"])                   # 向量存储
    )
    
    env.submit()      # 提交作业
    env.close()       # 清理资源
```

## 高级API集成模式
```python
# 多模态数据处理 - 参考sage_examples/multiagent_app.py模式
def create_multimodal_pipeline():
    config = load_config("multimodal_config.yaml")
    env = LocalEnvironment("multimodal_processing")
    
    # 文本分支
    text_stream = (env
        .from_source(DirectoryDataSource, config["text_source"])
        .map(TextCleanerFunction, config["text_cleaner"])
        .map(EmbeddingGeneratorFunction, config["text_embedder"])
    )
    
    # 图像分支  
    image_stream = (env
        .from_source(DirectoryDataSource, config["image_source"])
        .map(ImagePreprocessorFunction, config["image_processor"])
        .map(EmbeddingGeneratorFunction, config["image_embedder"])
    )
    
    # 多模态融合
    (text_stream
        .union(image_stream)
        .map(MultiModalFusionFunction, config["fusion"])
        .sink(VectorStoreSink, config["multimodal_sink"])
    )
    
    env.submit()
    env.run_streaming()

# 实时流处理 - 参考sage_examples/kafka_query.py
def create_streaming_pipeline():
    config = load_config("streaming_config.yaml")
    env = LocalEnvironment("streaming_processing")
    
    (env
        .from_source(KafkaDataSource, config["kafka_source"])
        .key_by(lambda msg: msg.get_user_id())                  # 分区键
        .window(size="5min", slide="1min")                      # 时间窗口
        .map(StreamProcessorFunction, config["processor"])       # 流处理
        .aggregate(count="count", avg="response_time")           # 聚合
        .sink(VectorStoreSink, config["stream_sink"])
    )
    
    env.submit()
    env.run_streaming()
```

## 配置驱动模式 - 完全兼容sage_examples
```python
# 配置文件驱动 - 与sage_examples/external_memory_ingestion_pipeline.py一致
def create_config_driven_pipeline(config_file: str):
    config = load_config(config_file)
    env = LocalEnvironment(config["job_name"])
    env.set_memory(config=config.get("memory"))
    
    # 动态构建处理链 - 基于配置
    stream = env.from_source(
        source_type=config["source"]["type"],  # FileDataSource, KafkaDataSource等
        source_config=config["source"]["config"]
    )
    
    # 动态添加处理函数
    for processor in config["processors"]:
        stream = stream.map(
            function_type=processor["function"],
            function_config=processor["config"]
        )
    
    # 输出配置
    stream.sink(
        sink_type=config["sink"]["type"],
        sink_config=config["sink"]["config"]
    )
    
    env.submit()
    if config.get("streaming_mode"):
        env.run_streaming()
    else:
        env.run_batch()
```

## 关键兼容性要求

**API兼容性要求**：
- [ ] **环境管理**: 支持`LocalEnvironment`和`RemoteEnvironment`
- [ ] **配置加载**: 兼容`sage_utils.config_loader`的YAML配置
- [ ] **链式调用**: 支持`env.from_source().map().filter().sink()`模式
- [ ] **内存集成**: 支持`env.set_memory()`与sage_memory集成
- [ ] **日志集成**: 兼容`sage_utils.logging_utils`和`CustomLogger`
- [ ] **作业管理**: 支持`env.submit()`，`env.close()`，`env.run_streaming()`
- [ ] **错误处理**: 提供详细错误信息和调试支持
- [ ] **监控集成**: 为sage_frontend提供实时性能指标

**具体API方法**：
- [ ] `env.from_source(SourceClass, config)` - 数据源创建
- [ ] `.map(FunctionClass, config)` - 一对一变换
- [ ] `.filter(FilterClass/lambda, config)` - 条件过滤
- [ ] `.flatmap(FlatMapClass, config)` - 一对多变换
- [ ] `.sink(SinkClass, config)` - 数据输出
- [ ] `.connect(other_stream)` - 流连接
- [ ] `.keyby(KeyFunction, strategy)` - 分组操作
- [ ] 支持lambda函数和自定义Function类
- [ ] 配置驱动的算子参数化
- [ ] 与sage_memory、sage_libs无缝集成
