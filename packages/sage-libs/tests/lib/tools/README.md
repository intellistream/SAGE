# SAGE 工具模块测试

工具模块的完整测试套件，确保各种工具的功能正确性和可靠性。

## 测试概述

本目录包含对SAGE工具模块所有工具的测试，覆盖功能测试、性能测试和集成测试。

## 测试文件

### `arxiv_paper_searcher_test.py`
ArXiv论文搜索工具测试：
- 论文搜索功能测试
- 搜索结果准确性验证
- API连接和错误处理测试
- 搜索性能基准测试

### `image_captioner_test.py`
图像描述生成工具测试：
- 图像识别和描述生成测试
- 多种图像格式支持测试
- 描述质量评估测试
- 处理速度和资源使用测试

### `nature_news_fetcher_test.py`
Nature新闻获取工具测试：
- 新闻内容获取测试
- 内容解析和结构化测试
- 更新频率和实时性测试
- API限制和错误处理测试

### `text_detector_test.py`
文本检测工具测试：
- 图像中文本检测测试
- OCR准确性验证测试
- 多语言文本检测测试
- 检测速度和准确性测试

### `url_text_extractor_test.py`
URL文本提取工具测试：
- 网页内容提取测试
- HTML解析和清理测试
- 多种网站兼容性测试
- 提取速度和质量测试

## 测试数据

### 图像测试数据
- 不同格式的测试图像（PNG、JPG、GIF等）
- 包含文本的图像样本
- 不同分辨率和质量的图像
- 边界条件测试图像

### 文本测试数据
- 多语言文本样本
- 不同长度的文本内容
- 特殊格式文本（代码、公式等）
- 噪声和异常文本

### 网络测试数据
- 各种类型的网页URL
- 学术论文链接
- 新闻网站链接
- 错误和无效链接

## 运行测试

```bash
# 运行所有工具测试
python -m pytest sage/lib/tools/tests/

# 运行特定工具测试
python -m pytest sage/lib/tools/tests/arxiv_paper_searcher_test.py
python -m pytest sage/lib/tools/tests/image_captioner_test.py

# 运行性能测试
python -m pytest sage/lib/tools/tests/ -m "performance"

# 运行集成测试
python -m pytest sage/lib/tools/tests/ -m "integration"
```

## 测试配置

### 环境要求
- 网络连接（用于API调用测试）
- GPU支持（用于图像处理测试）
- 充足的内存（用于大文件处理测试）

### 测试参数
```python
TEST_CONFIG = {
    "timeout": 30,                # 测试超时时间
    "max_retries": 3,            # 最大重试次数
    "test_data_path": "test_data/",  # 测试数据路径
    "mock_external_apis": True,   # 是否模拟外部API
    "performance_threshold": {    # 性能阈值
        "response_time": 5.0,
        "accuracy": 0.85
    }
}
```

## 性能基准

### 响应时间目标
- ArXiv搜索: < 3秒
- 图像描述: < 5秒
- 文本检测: < 2秒
- URL提取: < 10秒

### 准确性目标
- 文本检测准确率: > 90%
- 图像描述相关性: > 85%
- 内容提取完整性: > 95%

## 持续集成

测试集成到CI/CD流程：
- 自动化测试执行
- 测试报告生成
- 性能回归检测
- 代码覆盖率监控
