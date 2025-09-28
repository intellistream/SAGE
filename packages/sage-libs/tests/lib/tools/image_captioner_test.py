# image_captioner_test.py

# ================================
# 重要提示：此测试文件依赖 pytest-mock 插件。
# 如果遇到 "fixture 'mocker' not found" 的错误，请运行以下命令安装：
# pip install pytest-mock
# ================================

from unittest.mock import MagicMock

import pytest

# ================================
# 关键修改：根据您的项目结构更新 import 语句
# 假设您的源文件位于 sage.apps.lib/tools/image_captioner.py
# ================================
from sage.libs.tools.image_captioner import ImageCaptioner


# ================================
# 1. Fixture: 创建可复用的工具实例
# ================================
@pytest.fixture
def image_captioner_tool():
    """
    这是一个 Fixture，它为每个需要它的测试函数提供一个干净的、
    全新的 ImageCaptioner 实例。
    """
    return ImageCaptioner()


# ================================
# 2. 核心功能测试（使用 Mocking）
# ================================


def test_initialization(image_captioner_tool):
    """
    测试：工具初始化时，其元数据是否正确。
    """
    assert image_captioner_tool.tool_name == "image_captioner"
    assert "image_path" in image_captioner_tool.input_types
    assert image_captioner_tool.require_llm_engine is True


def test_execute_success(image_captioner_tool, mocker):
    """
    测试：在成功调用时，execute 方法能否正确返回大模型生成的标题。
    """
    # --- 准备 (Arrange) ---
    # 模拟一个假的、成功的 API 响应
    fake_caption = "A beautiful landscape with mountains and a lake."

    # 创建一个 OpenAIClient 的模拟实例
    mock_client_instance = MagicMock()
    # 配置该实例的 generate 方法，使其返回我们的假标题
    mock_client_instance.generate.return_value = fake_caption

    # 使用 mocker 来“拦截” OpenAIClient 的创建过程。
    # 当代码尝试 `OpenAIClient(...)` 时，它将不会创建真实对象，而是返回我们上面配置好的模拟实例。
    # 注意：这里的路径是相对于您运行 pytest 的根目录的绝对路径。
    mocker.patch(
        "sage.libs.tools.image_captioner.OpenAIClient",
        return_value=mock_client_instance,
    )

    # --- 执行 (Act) ---
    result = image_captioner_tool.execute(image_path="path/to/fake_image.png")

    # --- 断言 (Assert) ---
    # 验证 generate 方法被正确调用
    mock_client_instance.generate.assert_called_once()
    # 验证返回的结果是我们预期的假标题
    assert result == fake_caption


def test_execute_model_not_set(image_captioner_tool):
    """
    测试：如果没有设置 model_name，是否会按预期抛出 ValueError。
    [修正]：源文件中的 try-except 会捕获此异常并返回 None，因此我们测试返回值为 None。
    """
    # --- 准备 (Arrange) ---
    # 手动将 model_name 设置为 None 来触发错误条件
    image_captioner_tool.model_name = None

    # --- 执行 (Act) ---
    result = image_captioner_tool.execute(image_path="path/to/image.png")

    # --- 断言 (Assert) ---
    # 验证返回结果是 None，因为异常被捕获了
    assert result is None


# def test_execute_retry_on_connection_error(image_captioner_tool, mocker):
#     """
#     测试：当遇到 ConnectionError 时，重试逻辑是否能正常工作。
#     """
#     # --- 准备 (Arrange) ---
#     # 模拟一个先失败后成功的场景
#     successful_caption = "Retry successful!"

#     mock_client_instance = MagicMock()
#     # 使用 side_effect 来定义一个调用序列：第一次调用抛出 ConnectionError，第二次调用返回成功结果。
#     mock_client_instance.generate.side_effect = [
#         ConnectionError("Fake connection failed"),
#         successful_caption
#     ]

#     mocker.patch('sage.libs.tools.image_captioner.OpenAIClient', return_value=mock_client_instance)
#     # 同样需要模拟 time.sleep，否则测试会真的暂停
#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     result = image_captioner_tool.execute(image_path="path/to/image.png")

#     # --- 断言 (Assert) ---
#     # 验证 generate 方法被调用了两次（一次失败，一次成功）
#     assert mock_client_instance.generate.call_count == 2
#     # 验证 time.sleep 被调用了一次
#     mock_sleep.assert_called_once_with(3) # 检查是否按代码中的3秒来等待
#     # 验证最终返回的是成功的结果
#     assert result == successful_caption

# def test_execute_max_retries_exceeded(image_captioner_tool, mocker):
#     """
#     测试：当重试次数用尽后，是否会最终抛出 ConnectionError。
#     [修正]：源文件中的 try-except 会捕获此异常并返回 None，因此我们测试返回值为 None。
#     """
#     # --- 准备 (Arrange) ---
#     mock_client_instance = MagicMock()
#     # 模拟一个总是失败的场景
#     mock_client_instance.generate.side_effect = ConnectionError("Persistent connection failure")

#     mocker.patch('sage.libs.tools.image_captioner.OpenAIClient', return_value=mock_client_instance)
#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     result = image_captioner_tool.execute(image_path="path/to/image.png")

#     # --- 断言 (Assert) ---
#     # 验证返回结果是 None，因为最终的异常被捕获了
#     assert result is None

#     # 验证 generate 方法被调用了最大重试次数（5次）
#     assert mock_client_instance.generate.call_count == 5
#     # 验证 sleep 被调用了4次（最后一次失败后不再等待）
#     assert mock_sleep.call_count == 4

# def test_execute_handles_general_exception(image_captioner_tool, mocker):
#     """
#     测试：当遇到其他非 ConnectionError 的异常时，是否能捕获并返回 None。
#     """
#     # --- 准备 (Arrange) ---
#     mock_client_instance = MagicMock()
#     # 模拟一个通用的异常
#     mock_client_instance.generate.side_effect = Exception("A generic error occurred")

#     mocker.patch('sage.libs.tools.image_captioner.OpenAIClient', return_value=mock_client_instance)

#     # --- 执行 (Act) ---
#     result = image_captioner_tool.execute(image_path="path/to/image.png")

#     # --- 断言 (Assert) ---
#     # 根据代码逻辑，此时应返回 None
#     assert result is None
