"""
Control signals for SAGE pipelines.

This module provides control signal classes used across all layers of SAGE.
"""

import time


class StopSignal:
    """
    停止信号类 - 用于通知流处理停止

    StopSignal 是一个特殊的信号类，用于在流处理管道中传递停止指令。
    当某个算子需要停止处理或遇到特殊条件时，可以发送 StopSignal 来通知下游算子。

    为了保持向后兼容性，第一个参数同时作为 message 和 name 使用。

    Attributes:
        message: 停止信号的消息内容
        name: 停止信号的名称（与 message 相同，用于兼容）
        source: 停止信号的来源
        payload: 可选的附加数据
        timestamp: 停止信号创建时的纳秒级时间戳
    """

    def __init__(self, message: str = "Stop", source: str | None = None, payload=None):
        """
        创建停止信号

        Args:
            message: 停止信号的消息内容，默认为 "Stop"
            source: 停止信号的来源，如果为 None 则使用 message
            payload: 可选的附加数据
        """
        # 第一个参数同时作为 message 和 name（兼容旧代码）
        self.message = message
        self.name = message  # 兼容旧的 .name 属性访问

        # source 参数处理
        self.source = source if source is not None else message

        # 兼容旧的 payload 参数
        self.payload = payload

        self.timestamp = time.time_ns()

    def __str__(self):
        """
        返回停止信号的字符串表示

        Returns:
            str: 停止信号的简短描述
        """
        return f"StopSignal({self.message})"

    def __repr__(self):
        """
        返回停止信号的详细字符串表示

        Returns:
            str: 停止信号的详细描述
        """
        return f"StopSignal(message='{self.message}', source='{self.source}')"
