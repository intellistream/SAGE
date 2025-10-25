# text_detector_test.py

# ================================
# 重要提示：此测试文件依赖 pytest-mock 插件。
# 如果遇到 "fixture 'mocker' not found" 的错误，请运行以下命令安装：
# pip install pytest-mock
# ================================

from unittest.mock import MagicMock

import pytest

# ================================
# 关键修改：根据您的项目结构更新 import 语句
# 源文件位于 sage.libs.tools.text_detector
# ================================
from sage.libs.tools.text_detector import text_detector


# ================================
# 1. Fixture: 创建可复用的工具实例
# ================================
@pytest.fixture
def detector_tool():
    """
    这是一个 Fixture，为每个测试提供一个干净的 text_detector 实例。
    """
    return text_detector()


# ================================
# 2. 核心功能测试（使用 Mocking）
# ================================


def test_initialization(detector_tool):
    """
    测试：工具初始化时，其元数据是否正确。
    """
    assert detector_tool.tool_name == "Text_Detector_Tool"
    assert "image" in detector_tool.input_types


def test_execute_success_detail_1(detector_tool, mocker):
    """
    测试：成功执行并返回详细结果（detail=1 格式）。
    """
    # --- 准备 (Arrange) ---
    # 模拟 easyocr.readtext 返回的详细结果
    mock_raw_result = [
        ([[0, 0], [100, 0], [100, 20], [0, 20]], "Hello", 0.99),
        ([[10, 30], [120, 30], [120, 50], [10, 50]], "World", 0.95),
    ]

    # 模拟 easyocr 库和它的 Reader
    mock_reader_instance = MagicMock()
    mock_reader_instance.readtext.return_value = mock_raw_result
    mock_easyocr = MagicMock()
    mock_easyocr.Reader.return_value = mock_reader_instance

    # 因为 easyocr 是在方法内动态导入的，我们需要在 sys.modules 中模拟它
    mocker.patch.dict("sys.modules", {"easyocr": mock_easyocr})

    # --- 执行 (Act) ---
    result = detector_tool.execute(image="fake/path.png")

    # --- 断言 (Assert) ---
    assert len(result) == 2
    # 检查结果是否被正确清理（例如，浮点数被四舍五入）
    assert result[0] == ([[0, 0], [100, 0], [100, 20], [0, 20]], "Hello", 0.99)
    assert result[1][1] == "World"
    mock_reader_instance.readtext.assert_called_once_with("fake/path.png")


def test_execute_success_detail_0(detector_tool, mocker):
    """
    测试：成功执行并返回简单结果（detail=0 格式）。
    """
    # --- 准备 (Arrange) ---
    # 模拟 easyocr.readtext 返回的简单结果
    mock_raw_result = ["Hello", "World"]

    mock_reader_instance = MagicMock()
    mock_reader_instance.readtext.return_value = mock_raw_result
    mock_easyocr = MagicMock()
    mock_easyocr.Reader.return_value = mock_reader_instance
    mocker.patch.dict("sys.modules", {"easyocr": mock_easyocr})

    # --- 执行 (Act) ---
    # 源代码中的清理逻辑会失败，然后返回原始结果
    result = detector_tool.execute(image="fake/path.png")

    # --- 断言 (Assert) ---
    assert result == ["Hello", "World"]


def test_build_tool_import_error(detector_tool, mocker):
    """
    测试：当 easyocr 未安装时，build_tool 是否会抛出 ImportError。
    """
    # --- 准备 (Arrange) ---
    # 从 sys.modules 中移除 easyocr 来模拟它未安装的情况
    mocker.patch.dict("sys.modules", {"easyocr": None})

    # --- 执行 & 断言 (Act & Assert) ---
    with pytest.raises(ImportError, match="Please install the EasyOCR package"):
        detector_tool.build_tool()


def test_cuda_out_of_memory_with_retry_and_clear_cache(detector_tool, mocker):
    """
    测试：当遇到 CUDA out of memory 错误时，是否会重试并清理缓存。
    """
    # --- 准备 (Arrange) ---
    # [修正]：直接 patch 在被测模块中使用的 torch 对象，而不是通过 sys.modules。
    # 这是因为被测模块在顶层已经导入了 torch，我们需要替换那个已经被导入的引用。
    mock_torch = mocker.patch("sage.libs.tools.text_detector.torch")

    # 模拟 easyocr，让它第一次调用抛出 CUDA 错误，第二次成功
    mock_reader_instance = MagicMock()
    mock_reader_instance.readtext.side_effect = [
        RuntimeError("CUDA out of memory: Tried to allocate ..."),
        [([[0, 0]], "Success", 0.9)],
    ]
    mock_easyocr = MagicMock()
    mock_easyocr.Reader.return_value = mock_reader_instance
    mocker.patch.dict("sys.modules", {"easyocr": mock_easyocr})

    # --- 执行 (Act) ---
    result = detector_tool.execute(image="fake/path.png", clear_cuda_cache=True)

    # --- 断言 (Assert) ---
    assert len(result) == 1
    assert result[0][1] == "Success"
    # 验证 torch.cuda.empty_cache 被调用了一次
    mock_torch.cuda.empty_cache.assert_called_once()
    # 验证 readtext 被调用了两次
    assert mock_reader_instance.readtext.call_count == 2


# def test_fails_after_max_retries(detector_tool, mocker):
#     """
#     测试：当错误持续发生，超过最大重试次数后，是否返回空列表。
#     """
#     # --- 准备 (Arrange) ---
#     # [修正]：同样，直接 patch 在被测模块中使用的 torch 对象。
#     mocker.patch('sage.libs.tools.text_detector.torch')

#     # 模拟一个总是失败的 easyocr.readtext
#     mock_reader_instance = MagicMock()
#     mock_reader_instance.readtext.side_effect = RuntimeError("CUDA out of memory")
#     mock_easyocr = MagicMock()
#     mock_easyocr.Reader.return_value = mock_reader_instance
#     mocker.patch.dict('sys.modules', {'easyocr': mock_easyocr})

#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     # 使用较小的重试次数以加快测试
#     result = detector_tool.execute(image="fake/path.png", max_retries=3)

#     # --- 断言 (Assert) ---
#     assert result == []
#     # 验证 readtext 被调用了3次
#     assert mock_reader_instance.readtext.call_count == 3
#     # 验证 sleep 被调用了3次（因为 clear_cuda_cache=False）
#     assert mock_sleep.call_count == 3
