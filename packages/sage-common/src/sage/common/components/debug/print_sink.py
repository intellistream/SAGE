"""
Internal Print Sink - 内置打印汇聚函数

Layer: L3 (Kernel - Internal)
Dependencies: sage.kernel.api.function (L3 internal)

这是 kernel 内置的打印功能，用于支持 DataStream.print() 方法。
不依赖 sage-libs，保持 kernel 的独立性。

Note:
    这是内部实现，用户不应直接使用此类。
    用户应使用 DataStream.print() 方法。
"""

import logging
from typing import Any

from sage.common.core.functions import SinkFunction


class PrintSink(SinkFunction):
    """
    内置打印汇聚函数 - 支持 DataStream.print()

    提供便捷的调试和数据查看功能，无需依赖外部库。

    Features:
    - 智能数据格式化
    - 可配置前缀和分隔符
    - 日志集成

    Note:
        这是 kernel 内部实现，不应被用户代码直接导入。
        用户应使用 stream.print() 方法。
    """

    def __init__(
        self,
        prefix: str = "",
        separator: str = " | ",
        colored: bool = True,
        quiet: bool = False,
        **kwargs,
    ):
        """
        初始化打印汇聚函数

        Args:
            prefix: 输出前缀
            separator: 前缀与内容之间的分隔符
            colored: 是否启用彩色输出（当前未实现）
            quiet: 静默模式 - 不打印首次输出提示
            **kwargs: 传递给基类的其他参数
        """
        super().__init__(**kwargs)
        self.prefix = prefix
        self.separator = separator
        self.colored = colored
        self.quiet = quiet
        self._logger = logging.getLogger(__name__)
        self._first_output = True

    def execute(self, data: Any) -> None:
        """
        执行打印操作

        Args:
            data: 要打印的数据
        """
        # 格式化数据
        formatted = self._format_data(data)

        # 添加前缀
        if self.prefix:
            output = f"{self.prefix}{self.separator}{formatted}"
        else:
            output = formatted

        # 处理首次输出
        if self._first_output:
            if not self.quiet:
                print(f"🔍 Stream output: {output}")
                print("   (Further outputs logged. Check logs for details.)")
            else:
                print(output)
            self._first_output = False
        else:
            # 后续输出仅记录到日志
            self._logger.debug(f"Stream output: {output}")

    def _format_data(self, data: Any) -> str:
        """
        格式化数据为可读字符串

        Args:
            data: 输入数据

        Returns:
            str: 格式化后的字符串
        """
        # 处理常见类型
        if data is None:
            return "None"

        if isinstance(data, str):
            return data

        if isinstance(data, (int, float, bool)):
            return str(data)

        if isinstance(data, dict):
            # 字典：格式化为 key=value 形式
            items = [f"{k}={v}" for k, v in data.items()]
            return ", ".join(items)

        if isinstance(data, (list, tuple)):
            # 列表/元组：显示前几个元素
            if len(data) == 0:
                return "[]"
            elif len(data) <= 5:
                return str(data)
            else:
                preview = ", ".join(str(x) for x in data[:5])
                return f"[{preview}, ... (+{len(data) - 5} more)]"

        # 尝试检测常见的数据对象
        if hasattr(data, "__dict__"):
            # 对象：显示类名和主要属性
            class_name = data.__class__.__name__
            attrs = getattr(data, "__dict__", {})
            if attrs:
                attr_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
                return f"{class_name}({attr_str})"
            return f"{class_name}()"

        # 其他类型：使用 str() 转换
        try:
            return str(data)
        except Exception:
            return f"<Unprintable: {type(data).__name__}>"

    def __repr__(self) -> str:
        """字符串表示"""
        return f"InternalPrintSink(prefix='{self.prefix}')"
