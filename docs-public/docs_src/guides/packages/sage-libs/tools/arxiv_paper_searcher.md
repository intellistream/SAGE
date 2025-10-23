# SAGE 工具文档: `_Searcher_Tool`

!!! success "工具状态: 可用"
    **版本**: 1.0.0
    **描述**: 这是一个功能强大的工具，用于在 [arXiv.org](https://arxiv.org/) 上搜索学术论文。它通过网页抓取技术，根据用户提供的查询关键词，获取论文的标题、作者、摘要和链接等信息。

---

## 1. 功能概述

`_Searcher_Tool` 是 SAGE 系统中的一个基础工具，它封装了对 arXiv 网站的搜索逻辑。用户可以指定搜索关键词、每页返回结果数以及最大返回结果数，工具会自动处理网络请求、HTML 解析和数据提取，最终返回一个结构化的论文列表。

!!! warning "使用限制"
    为了避免对 arXiv 服务器造成过大压力，该工具内部将单次查询的最大结果数硬编码限制为 **100** 条。

---

## 2. 参数详解

该工具通过 `execute` 方法接收参数来执行搜索。

### 输入参数

| 参数名 (Parameter) | 类型 (Type) | 描述 | 默认值 |
|:-------------------|:------------|:-----------------------------------------------------------------------------------------------------------------------------------|:---------|
| `query` | `str` | **必需**。用于搜索论文的关键词或短语。 | 无 |
| `size` | `int` | 每页显示的搜索结果数量。如果提供的值无效，会自动选择一个最接近的有效值。有效值为 `[25, 50, 100, 200]`。 | `25` |
| `max_results` | `int` | 希望返回的最大论文数量。实际返回数量不会超过 100。 | `25` |

### 输出格式

该工具的 `execute` 方法返回一个 `list`，其中每个元素都是一个 `dict`，代表一篇论文。每个字典包含以下键：

| 键 (Key) | 类型 (Type) | 描述 |
|:-----------|:------------|:---------------------------|
| `title` | `str` | 论文的完整标题。 |
| `authors` | `str` | 论文的作者列表，以逗号分隔。 |
| `abstract` | `str` | 论文的摘要内容。 |
| `link` | `str` | 指向该论文在 arXiv 上的 PDF 或详情页的链接。 |

---

## 3. 使用示例

以下是一些演示如何调用 `_Searcher_Tool` 的示例。

=== "基础搜索"
    搜索关于“大型语言模型工具代理 (tool agents with large language models)”的论文。

    ```python title="基础搜索示例"
    from your_module import _Searcher_Tool # 请替换为实际的模块路径

    # 1. 初始化工具
    tool = _Searcher_Tool()

    # 2. 定义查询并执行
    query = "tool agents with large language models"
    results = tool.execute(query=query)

    # 3. 打印结果
    for paper in results:
        print(f"Title: {paper['title']}")
    ```

=== "高级搜索"
    搜索关于“量子计算 (quantum computing)”的论文，设置每页返回 100 条结果，但最多只获取 50 篇论文。

    ```python title="高级搜索示例"
    from your_module import _Searcher_Tool

    tool = _Searcher_Tool()

    results = tool.execute(
        query="quantum computing", 
        size=100, 
        max_results=50
    )

    print(f"成功获取 {len(results)} 篇论文。")
    ```

=== "自定义返回数量"
    搜索关于“机器学习 (machine learning)”的论文，并指定最多返回 75 篇。

    ```python title="自定义返回数量示例"
    from your_module import _Searcher_Tool

    tool = _Searcher_Tool()

    results = tool.execute(
        query="machine learning", 
        max_results=75
    )

    print(f"成功获取 {len(results)} 篇论文。")
    ```

---

## 4. 内部实现逻辑

???+ info "执行流程详解 (点击展开)"
    `_Searcher_Tool` 的 `execute` 方法遵循以下步骤来完成一次搜索任务：

    1.  **参数验证与准备**:
        * 检查 `size` 参数是否在 `[25, 50, 100, 200]` 范围内。如果不是，则选择一个最接近的有效值。
        * 将 `max_results` 与内部上限 (100) 比较，取较小者作为最终的最大结果数。
        * 初始化一个空列表 `results` 用于存储结果，并设置起始索引 `start = 0` 用于分页。

    2.  **循环获取数据**:
        * 进入一个 `while` 循环，条件是 `len(results) < max_results`。
        * 在循环内部，构造一个包含查询参数的字典，用于 `requests.get` 调用。
        * 向 arXiv 的搜索接口 `https://arxiv.org/search/` 发送 GET 请求。

    3.  **HTML 解析与数据提取**:
        * 使用 `BeautifulSoup` 解析返回的 HTML 响应内容。
        * 查找所有 class 为 `arxiv-result` 的 `<li>` 标签，每个标签代表一篇论文。
        * 如果找不到任何论文，则中断循环。
        * 遍历每个论文标签，提取标题、作者、摘要和链接。
        * 对提取的文本进行清理，例如移除 "Authors: " 前缀和 "△ Less" 后缀。
        * 将提取的信息封装成一个字典，并添加到 `results` 列表中。

    4.  **分页处理**:
        * 每次循环结束后，将 `start` 索引增加 `size` 的值，以便在下一次请求中获取下一页的结果。

    5.  **异常处理**:
        * 整个网络请求和解析过程被包裹在 `try...except` 块中。如果发生任何异常（如网络错误），将记录错误日志并中断循环。

    6.  **返回结果**:
        * 循环结束后，返回 `results` 列表，并根据 `max_results` 对其进行切片，确保返回的论文数量不超过用户的要求。

---

## 5. 依赖项

该工具需要以下 Python 库才能正常运行：

- [x] `requests`: 用于发送 HTTP 请求。
- [x] `beautifulsoup4`: 用于解析 HTML 内容。
- [x] `re`: Python 内置的正则表达式模块，用于文本清理。
- [x] `logging`: Python 内置的日志模块。

您可以使用 pip 来安装所需的库：
```bash
pip install requests beautifulsoup4
```