# SAGE 工具文档: `URL_Text_Extractor_Tool`

!!! success "工具状态: 可用"
    **版本**: 1.0.0
    **描述**: 一个从给定的 URL 中提取所有文本内容的工具。

---

## 1. 功能概述

`URL_Text_Extractor_Tool` 是一个网页内容抓取工具，其核心功能是访问一个给定的网页链接，并提取出其中所有可读的文本内容。它利用 `requests` 库获取网页的 HTML，再通过 `BeautifulSoup` 解析并提取纯文本，为后续的文本分析任务提供原始素材。

!!! tip "特殊处理: arXiv 链接"
    该工具内置了一个针对 arXiv 网站的优化：它会自动将指向 PDF 文件的链接 (`/pdf/`) 替换为指向摘要页的链接 (`/abs/`)，因为摘要页的 HTML 格式更易于提取文本。

---

## 2. 参数详解

该工具通过 `execute` 方法接收参数来执行文本提取。

### 输入参数

| 参数名 (Parameter) | 类型 (Type) | 描述 |
|:-------------------|:------------|:-------------------------------------------|
| `url` | `str` | **必需**。需要提取文本的网页 URL。 |

### 输出格式

`execute` 方法返回一个字典，包含以下两个键：

| 键 (Key) | 类型 (Type) | 描述 |
|:-----------------|:------------|:-------------------------------------------------------------------------------------------------------------------------------------|
| `url` | `str` | 原始输入的 URL。 |
| `extracted_text` | `str` | 从 URL 中提取的文本内容。如果提取过程中发生错误（如网络问题），这里会包含相应的错误信息。提取的文本内容上限为 10,000 个字符。 |

---

## 3. 使用示例

以下是一些演示如何调用 `URL_Text_Extractor_Tool` 的示例。

=== "提取普通网站"
    从一个常规网站提取文本。

    ```python title="基础用法示例"
    from your_module import URL_Text_Extractor_Tool # 请替换为实际的模块路径

    tool = URL_Text_Extractor_Tool()
    results = tool.execute(url="[https://www.python.org/](https://www.python.org/)")

    print(results['extracted_text'][:500]) # 打印前 500 个字符
    ```

=== "提取维基百科"
    从维基百科的一个词条页面提取文本。

    ```python title="维基百科示例"
    tool = URL_Text_Extractor_Tool()
    url = "[https://en.wikipedia.org/wiki/Python_(programming_language](https://en.wikipedia.org/wiki/Python_(programming_language))"
    results = tool.execute(url=url)
    print(results)
    ```

---

## 4. 内部实现逻辑

???+ info "执行流程详解 (点击展开)"
    `execute` 方法的逻辑非常直接，主要依赖于其辅助方法 `extract_text_from_url`：

    1.  **URL 预处理**: 首先，检查 URL 是否为 arXiv 的 PDF 链接，如果是，则将其转换为摘要页链接。
    2.  **获取网页内容**: 使用 `requests.get(url)` 发送 HTTP GET 请求来下载网页的 HTML 内容。
    3.  **解析与提取**:
        * 使用 `BeautifulSoup` 将获取到的 HTML 内容进行解析。
        * 调用 `soup.get_text(separator='\n', strip=True)` 方法。这个方法会提取出页面中所有的文本节点，并用换行符 `\n` 分隔，同时移除多余的空白。
    4.  **内容截断**: 为了防止文本内容过长，工具会将提取出的文本截断，只保留前 **10,000** 个字符。
    5.  **异常处理**: 整个过程被包裹在 `try...except` 块中。
        * 如果发生 `requests.RequestException`（如网络连接失败、DNS 错误、404 Not Found 等），方法会返回一个包含具体网络错误信息的字符串。
        * 如果发生其他任何异常（如解析错误），则返回一个通用的错误信息字符串。
    6.  **结果封装**: `execute` 方法最后将提取出的文本（或错误信息）与原始 URL 一起封装到一个字典中并返回。

---

## 5. 依赖项与要求

* **Python 库**:
    - [x] `requests`: 用于发送 HTTP 请求。
    - [x] `beautifulsoup4`: 用于解析 HTML 内容。
    - [x] `os`: 用于文件路径操作（在 `if __name__ == "__main__"` 中使用）。

* **安装命令**:
    ```bash
    pip install requests beautifulsoup4
    ```

---

## 6. 限制与注意事项

!!! danger "重要限制"
    * **动态内容**: 此工具对于使用 JavaScript 动态加载内容的网站（单页应用，SPA）效果不佳，因为它只能获取到初始加载的 HTML 中的文本。
    * **文本噪音**: `get_text()` 会提取页面上所有的文本，包括导航栏、页脚、广告、样式脚本等“噪音”，可能会干扰后续处理。
    * **字符限制**: 存在 10,000 个字符的硬性限制，对于非常长的文章，内容会被截断。
    * **访问限制**: 某些网站可能有反爬虫机制，可能会阻止此工具的请求。