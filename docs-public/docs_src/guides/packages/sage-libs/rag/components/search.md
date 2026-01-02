# 外部搜索组件 (External Search Components)

本文档详细介绍SAGE框架中`sage.libs.rag.searcher`模块的外部搜索组件。外部搜索组件是RAG系统的信息扩展层，负责从互联网和外部数据源获取实时信息，弥补本地知识库的时效性和覆盖范围限制。

## 组件概述

### 核心功能

外部搜索组件在RAG系统中承担以下关键职责：

- **实时信息获取**：从互联网获取最新的信息和数据
- **知识库扩展**：扩展本地知识库无法覆盖的领域和内容
- **时效性保障**：提供具有时效性的新闻、事件和数据更新
- **多源聚合**：整合来自不同搜索引擎和数据源的信息

### 应用场景

- **新闻资讯查询**：获取最新的新闻报道和时事分析
- **实时数据检索**：查询股价、天气、汇率等动态数据
- **趋势分析**：获取行业动态和市场趋势信息
- **事实核查**：验证信息的准确性和时效性

### 技术架构

外部搜索采用API集成架构：

```
用户查询 → 查询优化 → API调用 → 结果处理 → 信息整合 → 标准化输出
   ↓         ↓         ↓         ↓         ↓         ↓
 意图分析 → 关键词提取 → 第三方API → 内容解析 → 去重排序 → 结构化数据
```

## BochaWebSearch

### 组件描述

`BochaWebSearch`是基于BochaAI API的网络搜索器，提供高质量的中文网络搜索服务，支持实时信息检索和智能结果摘要。

### 技术规格

**服务特性**：

- 支持中英文搜索查询
- 提供搜索结果摘要生成
- 支持分页查询和结果数量控制
- 提供丰富的元数据信息

**API限制**：

- 每日API调用次数限制（根据订阅计划）
- 单次查询最大结果数限制
- 查询频率限制

**配置参数**：

| 参数名     | 类型 | 默认值 | 必需性 | 说明                     |
| ---------- | ---- | ------ | ------ | ------------------------ |
| `api_key`  | str  | -      | 必需   | BochaAI API访问密钥      |
| `count`    | int  | 10     | 可选   | 返回搜索结果数量（1-50） |
| `page`     | int  | 1      | 可选   | 页码，用于分页查询       |
| `summary`  | bool | True   | 可选   | 是否生成搜索结果摘要     |
| `language` | str  | "auto" | 可选   | 搜索语言偏好             |
| `region`   | str  | "cn"   | 可选   | 搜索地区偏好             |

### 实现示例

#### 基础搜索功能

```python
from sage.libs.rag.searcher import BochaWebSearch

# 基础配置
config = {"api_key": "your-bocha-api-key", "count": 5, "summary": True}

# 初始化搜索器
searcher = BochaWebSearch(config)

# 执行搜索
query = "2024年人工智能发展趋势"
search_results = searcher.execute(query)

print(f"搜索查询: {query}")
print(f"找到 {len(search_results['results'])} 个结果")

# 输出搜索结果
for i, result in enumerate(search_results["results"], 1):
    print(f"\n{i}. {result['title']}")
    print(f"   链接: {result['url']}")
    print(f"   摘要: {result['snippet'][:200]}...")
    if "publish_date" in result:
        print(f"   发布时间: {result['publish_date']}")
```

#### 分页搜索

```python
# 配置分页搜索
paginated_config = {
    "api_key": "your-bocha-api-key",
    "count": 8,  # 每页8个结果
    "page": 1,  # 从第1页开始
    "summary": True,
}

searcher = BochaWebSearch(paginated_config)


# 多页搜索示例
def search_multiple_pages(query, max_pages=3):
    all_results = []

    for page in range(1, max_pages + 1):
        # 更新页码
        paginated_config["page"] = page
        searcher = BochaWebSearch(paginated_config)

        # 执行搜索
        page_results = searcher.execute(query)
        all_results.extend(page_results["results"])

        print(f"第{page}页: 获取到 {len(page_results['results'])} 个结果")

        # 如果当前页结果不足，说明没有更多页面
        if len(page_results["results"]) < paginated_config["count"]:
            break

    return all_results


# 执行多页搜索
query = "机器学习在医疗领域的应用"
comprehensive_results = search_multiple_pages(query, max_pages=3)
print(f"\n总共获取到 {len(comprehensive_results)} 个搜索结果")
```

#### 高级搜索配置

```python
# 高级搜索配置
advanced_config = {
    "api_key": "your-bocha-api-key",
    "count": 15,
    "summary": True,
    "language": "zh-cn",  # 中文搜索
    "region": "cn",  # 中国地区
    "safe_search": "strict",  # 安全搜索
    "time_range": "month",  # 最近一个月的结果
}

advanced_searcher = BochaWebSearch(advanced_config)

# 专业搜索示例
professional_queries = [
    "区块链技术最新发展",
    "量子计算突破性进展",
    "新能源汽车市场分析",
]

for query in professional_queries:
    results = advanced_searcher.execute(query)
    print(f"\n=== {query} ===")

    # 显示前3个最相关的结果
    for i, result in enumerate(results["results"][:3], 1):
        print(f"{i}. {result['title']}")
        print(f"   摘要: {result['snippet']}")
        print(f"   来源: {result.get('source', 'Unknown')}")
        print()
```

### 结果格式说明

#### 标准输出格式

```python
{
    "query": str,  # 原始搜索查询
    "results": [  # 搜索结果列表
        {
            "title": str,  # 页面标题
            "url": str,  # 页面URL
            "snippet": str,  # 内容摘要
            "source": str,  # 来源网站
            "publish_date": str,  # 发布日期（如果可用）
            "relevance_score": float,  # 相关性分数
            "language": str,  # 内容语言
            "content_type": str,  # 内容类型
        }
    ],
    "total_count": int,  # 总结果数量
    "search_time": float,  # 搜索耗时
    "summary": str,  # 整体搜索摘要（如果启用）
}
```

#### 错误处理格式

```python
{
    "error": str,  # 错误描述
    "error_code": int,  # 错误代码
    "query": str,  # 原始查询
    "results": [],  # 空结果列表
}
```
