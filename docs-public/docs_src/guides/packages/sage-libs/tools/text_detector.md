# SAGE 工具文档: `Text_Detector_Tool`

!!! success "工具状态: 可用"
    **版本**: 1.0.0
    **描述**: 一个使用 `EasyOCR` 库来检测并识别图像中文字的工具。

---

## 1. 功能概述

`Text_Detector_Tool` 是一个强大的光学字符识别（OCR）工具，它封装了流行的 `EasyOCR` 库。该工具能够加载本地图像文件，并识别其中的文本内容。它支持多种语言，并内置了重试机制来处理常见的运行时问题，特别是 GPU 显存不足的情况。

!!! warning "核心依赖: EasyOCR"
    此工具的运行依赖于 `easyocr` 和 `torch` Python 包。如果您的环境中没有安装，工具在构建时会抛出 `ImportError`。

---

## 2. 参数详解

该工具通过 `execute` 方法接收参数来执行文本检测。

### 输入参数

| 参数名 (Parameter) | 类型 (Type) | 描述 | 默认值 |
|:-------------------|:------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------|:---------|
| `image` | `str` | **必需**。需要进行文本检测的本地图片文件的路径。 | 无 |
| `languages` | `list` | 指定 OCR 模型需要识别的语言代码列表。例如 `["en", "ch_sim"]`。 | `["en"]` |
| `detail` | `int` | 控制输出的详细程度。`1` 为详细输出（默认），`0` 为简化输出。此参数通过 `readtext` 方法的 `**kwargs` 传入。 | `1` |
| `clear_cuda_cache` | `bool` | 当发生 "CUDA out of memory" 错误时，是否尝试清空 CUDA 缓存。 | `False` |

### 输出格式

该工具的输出格式取决于传入 `execute` 方法的 `detail` 参数：

* **详细模式 (`detail=1`, 默认)**: 返回一个列表，每个元素代表一个识别出的文本块。每个文本块是一个元组，包含 `(bounding_box, text, confidence_score)`。
    * `bounding_box`: 一个包含四个 `[x, y]` 坐标点的列表，定义了文本的边界框。
    * `text`: 识别出的字符串文本。
    * `confidence_score`: 识别结果的置信度，浮点数，范围 0 到 1。
    ```json
    [
        [[[55, 62], [339, 62], [339, 103], [55, 103]], "This is a test", 0.98]
    ]
    ```

* **简化模式 (`detail=0`)**: 返回一个仅包含识别出的字符串文本的列表。
    ```json
    [
        "This is a test"
    ]
    ```

---

## 3. 使用示例

以下是一些演示如何调用 `Text_Detector_Tool` 的示例。

=== "基础用法 (英文)"
    检测一张图片中的英文文本。

    ```python title="基础用法示例"
    from your_module import text_detector # 请替换为实际的模块路径

    tool = text_detector()
    results = tool.execute(image="path/to/your/image.png", languages=["en"])
    print(results)
    ```

=== "多语言检测"
    同时检测图片中的英文和德文。

    ```python title="多语言检测示例"
    tool = text_detector()
    results = tool.execute(image="path/to/image.png", languages=["en", "de"])
    print(results)
    ```

=== "简化输出"
    只获取识别出的文本字符串，不包含坐标和置信度。

    ```python title="简化输出示例"
    tool = text_detector()
    results = tool.execute(image="path/to/image.png", languages=["en"], detail=0)
    print(results) # 输出: ['Detected text line 1', 'Another line']
    ```

---

## 4. 内部实现逻辑

???+ info "执行流程详解 (点击展开)"
    `execute` 方法的执行流程设计得相当健壮：

    1.  **重试循环**: 方法的核心是一个 `for` 循环，用于在发生可恢复的错误时进行重试（默认最多10次）。
    2.  **模型构建 (`build_tool`)**: 在每次循环尝试中，都会调用 `build_tool` 方法来初始化 `easyocr.Reader`。这确保了在某些错误后可以重新加载模型。如果 `easyocr` 未安装，此步骤会抛出 `ImportError`。
    3.  **文本读取**: 调用 `reader.readtext(image, **kwargs)` 来执行核心的 OCR 功能。
    4.  **结果清洗**: 如果是详细模式，工具会遍历结果，将 `numpy` 的数值类型转换为标准的 Python `int` 和 `float` 类型，以便于后续处理（如 JSON 序列化）。
    5.  **CUDA 内存错误处理**: 特别地，如果捕获到包含 "CUDA out of memory" 的 `RuntimeError`，工具会：
        * 如果 `clear_cuda_cache` 为 `True`，则调用 `torch.cuda.empty_cache()` 清理显存。
        * 否则，等待一段延迟时间 (`retry_delay`) 后继续下一次尝试。
    6.  **失败返回**: 如果所有重试都失败了，方法会打印一条失败信息并返回一个空列表 `[]`。

---

## 5. 依赖项与要求

* **Python 库**:
    - [x] `easyocr`: 核心的 OCR 引擎。
    - [x] `torch`: `easyocr` 的底层依赖，用于深度学习模型。
    - [x] `os`, `time`, `typing`, `warnings`: Python 标准库。

* **安装命令**:
    ```bash
    pip install easyocr torch
    ```

---

## 6. 常用语言参考

工具元数据中包含了一些常用的语言代码，方便用户参考：

| 代码 (Code) | 语言 (Language) |
|:------------|:--------------------|
| `en` | English |
| `ch_sim` | Simplified Chinese |
| `ch_tra` | Traditional Chinese |
| `ja` | Japanese |
| `de` | German |
| `fr` | French |
| `es` | Spanish |
| `hi` | Hindi |
