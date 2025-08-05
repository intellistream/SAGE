# SAGE 工具模块

工具模块提供丰富的专用工具集合，包括学术搜索、图像处理、文本提取等功能，为SAGE框架提供强大的扩展能力。

## 模块概述

工具模块实现了各种专业化的工具，每个工具都专注于特定的功能领域，可以独立使用或与SAGE数据流管道集成。

## 核心工具

### `arxiv_paper_searcher.py`
ArXiv论文搜索工具：
- 搜索ArXiv学术论文数据库
- 支持多种搜索策略（关键词、作者、分类等）
- 提供论文元数据提取
- 支持批量搜索和结果过滤
- 包含引用分析和相关论文推荐

### `image_captioner.py`
图像描述生成工具：
- 自动生成图像的文字描述
- 支持多种图像格式（JPG、PNG、GIF等）
- 提供可配置的描述详细程度
- 支持多语言描述生成
- 包含图像内容分析和理解

### `text_detector.py`
文本检测工具：
- 从图像中检测和提取文本
- 支持多语言OCR识别
- 提供文本位置和边界框信息
- 支持手写文字和打印文字识别
- 包含文本方向和角度矫正

### `url_text_extractor.py`
URL文本提取工具：
- 从网页URL提取主要文本内容
- 自动去除广告和导航元素
- 支持多种网站结构适配
- 提供内容质量评估
- 包含反爬虫机制处理

### `nature_news_fetcher.py`
Nature新闻获取工具：
- 自动获取Nature期刊的最新新闻
- 提供新闻分类和标签
- 支持定时更新和推送
- 包含新闻内容结构化处理
- 提供相关研究文献链接

### `searcher_tool.py`
通用搜索工具：
- 提供统一的搜索接口
- 支持多种搜索引擎集成
- 包含搜索结果聚合和去重
- 提供搜索质量评估
- 支持自定义搜索策略

### [基础框架](./base/)
工具开发的标准框架和注册管理。

### [测试模块](./tests/)
全面的工具功能测试覆盖。

## 主要特性

- **多样化功能**: 覆盖文本、图像、网络等多个领域
- **高质量输出**: 经过优化的算法确保输出质量
- **易于集成**: 标准接口，易于集成到各种应用
- **可扩展性**: 支持自定义工具开发和扩展
- **性能优化**: 高效的处理算法和缓存机制

## 应用场景

### 学术研究
- 文献搜索和管理
- 论文内容分析
- 研究趋势分析
- 引用网络构建

### 内容处理
- 多媒体内容分析
- 文本提取和清洗
- 内容质量评估
- 信息结构化

### 数据收集
- 网络数据爬取
- 实时信息监控
- 数据源整合
- 信息更新追踪

## 快速开始

```python
# ArXiv论文搜索
from sage.lib.tools.arxiv_paper_searcher import ArxivPaperSearcher

searcher = ArxivPaperSearcher()
papers = searcher.search("machine learning", max_results=10)

# 图像描述生成
from sage.lib.tools.image_captioner import ImageCaptioner

captioner = ImageCaptioner()
description = captioner.caption("path/to/image.jpg")

# 文本检测
from sage.lib.tools.text_detector import TextDetector

detector = TextDetector()
text_results = detector.detect_text("path/to/image_with_text.jpg")

# URL文本提取
from sage.lib.tools.url_text_extractor import URLTextExtractor

extractor = URLTextExtractor()
content = extractor.extract("https://example.com/article")
```

## 在SAGE中使用

```python
from sage.api.env import LocalEnvironment
from sage.lib.tools import ArxivPaperSearcher, ImageCaptioner

# 创建环境
env = LocalEnvironment("research_pipeline")

# 创建论文搜索流
query_stream = env.source(QuerySource, queries=["AI", "ML", "NLP"])
paper_stream = query_stream.map(ArxivPaperSearcher, max_results=5)

# 创建图像处理流
image_stream = env.source(ImageSource, image_folder="images/")
caption_stream = image_stream.map(ImageCaptioner, language="zh")

# 输出结果
paper_stream.sink(FileSink, output="papers.json")
caption_stream.sink(FileSink, output="captions.json")

# 执行管道
env.execute()
```

## 工具配置

### 搜索工具配置
```python
searcher_config = {
    "max_results": 100,
    "sort_by": "relevance",
    "date_range": "last_year",
    "include_abstracts": True,
    "language": "en"
}
```

### 图像工具配置
```python
image_config = {
    "model": "blip2",
    "max_length": 50,
    "num_beams": 5,
    "language": "zh",
    "confidence_threshold": 0.8
}
```

### 文本提取配置
```python
extractor_config = {
    "user_agent": "SAGE-Bot/1.0",
    "timeout": 30,
    "max_content_length": 1000000,
    "remove_ads": True,
    "preserve_links": False
}
```

## 性能优化

### 缓存策略
- 搜索结果缓存
- 图像处理结果缓存
- 网页内容缓存
- 模型推理缓存

### 批量处理
- 批量搜索优化
- 批量图像处理
- 并行文本提取
- 异步任务处理

### 资源管理
- GPU资源调度
- 内存使用优化
- 网络连接复用
- 临时文件清理

## 扩展开发

### 自定义工具
```python
from sage.lib.tools.base import BaseTool

class CustomTool(BaseTool):
    def __init__(self, config=None):
        super().__init__(config)
        self.initialize()
    
    def execute(self, input_data):
        # 实现工具逻辑
        return processed_result
    
    def validate_input(self, input_data):
        # 输入验证
        return True
```

### 工具注册
```python
from sage.lib.tools.base import ToolRegistry

registry = ToolRegistry()
registry.register_tool("custom_tool", CustomTool)
```

## 最佳实践

1. **错误处理**: 实现完善的异常处理机制
2. **资源管理**: 及时释放网络和文件资源
3. **速率限制**: 遵守API使用限制和礼貌性原则
4. **结果验证**: 对工具输出进行质量检查
5. **监控日志**: 记录工具使用情况和性能指标
