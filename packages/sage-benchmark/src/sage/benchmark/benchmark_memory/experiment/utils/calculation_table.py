"""计算相关的工具函数

用于各种阈值、分段等数值计算
"""


def calculate_test_thresholds(total_questions, segments):
    """计算测试阈值数组

    将总问题数均匀分成 segments 段，返回每段的结束位置作为测试触发点

    Args:
        total_questions: 总问题数
        segments: 分段数

    Returns:
        list: 测试阈值数组，例如 [10, 20, 30, ..., 100]

    Examples:
        >>> calculate_test_thresholds(100, 10)
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        >>> calculate_test_thresholds(25, 5)
        [5, 10, 15, 20, 25]
        >>> calculate_test_thresholds(214, 10)
        [21, 42, 64, 85, 107, 128, 149, 171, 192, 214]
        >>> calculate_test_thresholds(0, 10)
        []
    """
    if total_questions == 0:
        return []

    # 确保至少有1段
    segments = max(1, segments)

    # 使用更精确的浮点数计算，确保均匀分布
    thresholds = []
    for i in range(1, segments + 1):
        # 使用浮点数计算，然后四舍五入
        threshold = round(total_questions * i / segments)
        # 避免重复的阈值（当问题数小于分段数时可能出现）
        if not thresholds or threshold > thresholds[-1]:
            thresholds.append(threshold)

    return thresholds
