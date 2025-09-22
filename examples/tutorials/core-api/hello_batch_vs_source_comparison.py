"""
import logging
BatchOperator vs SourceOperator 对比示例

展示新的批处理设计相对于原始设计的优势
"""

from typing import Any, Iterator

from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.source_function import SourceFunction
from sage.kernel.runtime.communication.router.packet import StopSignal


class SimpleBatchFunction(BatchFunction):
    """
    简单的批处理函数实现
    直接处理提供的数据列表
    """

    def __init__(self, data, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data = data
        self.index = 0

    def get_total_count(self) -> int:
        return len(self.data)

    def get_data_source(self) -> Iterator[Any]:
        return iter(self.data)

    def execute(self) -> Any:
        if self.index >= len(self.data):
            return None

        result = self.data[self.index]
        self.index += 1
        return result

    def get_progress(self):
        return self.index, len(self.data)

    def get_completion_rate(self) -> float:
        return self.index / len(self.data) if self.data else 1.0

    def is_finished(self) -> bool:
        return self.index >= len(self.data)


class OldStyleSourceFunction(SourceFunction):
    """
    旧式源函数 - 需要手动管理停止逻辑
    用户需要在函数中处理停止信号的发送
    """

    def __init__(self, data, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data = data
        self.index = 0

    def execute(self) -> Any:
        if self.index >= len(self.data):
            # 用户需要手动返回停止信号
            return StopSignal("old_style_source")

        result = self.data[self.index]
        self.index += 1
        return result


def compare_implementations():
    """
    对比新旧实现的差异
    """

    # 创建模拟context
    class MockContext:
        def __init__(self, name):
            self.name = name
            self.logger = MockLogger()

    class MockLogger:
        def info(self, msg):
            logging.info(f"INFO: {msg}")

        def debug(self, msg):
            logging.info(f"DEBUG: {msg}")

    data = ["item1", "item2", "item3", "item4", "item5"]

    logging.info("=" * 60)
    logging.info("批处理设计对比示例")
    logging.info("=" * 60)

    # 1. 旧式实现
    logging.info("\n1. 旧式 SourceFunction 实现:")
    logging.info("   - 用户需要手动管理停止逻辑")
    logging.info("   - 无内置进度跟踪")
    logging.info("   - 停止信号在函数中发送")

    ctx1 = MockContext("old_style")
    old_func = OldStyleSourceFunction(data, ctx1)

    logging.info(f"\n   处理数据 ({len(data)} 条记录):")
    for i in range(len(data) + 2):  # 多执行几次展示停止逻辑
        result = old_func.execute()
        if isinstance(result, StopSignal):
            logging.info(f"   第{i+1}次执行: 收到停止信号 {result}")
            break
        else:
            logging.info(f"   第{i+1}次执行: 处理数据 {result}")

    # 2. 新式实现
    logging.info("\n" + "=" * 60)
    logging.info("2. 新式 BatchFunction 实现:")
    logging.info("   - 用户只需声明数据，不管停止逻辑")
    logging.info("   - 内置进度跟踪和状态管理")
    logging.info("   - 停止信号由算子自动发送")

    ctx2 = MockContext("new_style")
    new_func = SimpleBatchFunction(data, ctx2)

    logging.info(f"\n   处理数据 ({new_func.get_total_count()} 条记录):")
    i = 0
    while not new_func.is_finished():
        result = new_func.execute()
        current, total = new_func.get_progress()
        completion = new_func.get_completion_rate()

        if result is not None:
            logging.info(
                f"   第{i+1}次执行: 处理数据 {result} - 进度 {current}/{total} ({completion:.0%})"
            )
        i += 1

    logging.info(f"   批处理完成状态: {new_func.is_finished()}")
    logging.info(f"   最终完成率: {new_func.get_completion_rate():.0%}")

    # 3. 功能对比表
    logging.info("\n" + "=" * 60)
    logging.info("功能对比:")
    logging.info("=" * 60)

    comparison_table = [
        ["功能", "旧式 SourceFunction", "新式 BatchFunction"],
        ["-" * 20, "-" * 25, "-" * 25],
        ["停止信号管理", "用户手动处理", "算子自动管理"],
        ["进度跟踪", "无", "内置支持"],
        ["完成状态", "无", "自动跟踪"],
        ["错误处理", "用户负责", "算子统一处理"],
        ["用户接口复杂度", "高(需处理停止)", "低(声明式)"],
        ["代码可维护性", "一般", "好"],
        ["调试友好性", "一般", "好(丰富日志)"],
    ]

    for row in comparison_table:
        logging.info(f"{row[0]:<20} | {row[1]:<23} | {row[2]}")

    # 4. 代码量对比
    logging.info("\n" + "=" * 60)
    logging.info("代码实现对比:")
    logging.info("=" * 60)

    logging.info("\n旧式实现 - 用户需要写的代码:")
    logging.info(
        """
    class MySourceFunction(SourceFunction):
        def __init__(self, data, ctx=None, **kwargs):
            super().__init__(ctx, **kwargs)
            self.data = data
            self.index = 0
        
        def execute(self) -> Any:
            if self.index >= len(self.data):
                return StopSignal("my_source")  # 手动管理停止
            
            result = self.data[self.index]
            self.index += 1
            return result
    """
    )

    logging.info("\n新式实现 - 用户只需要声明:")
    logging.info(
        """
    # 直接使用内置实现
    batch_func = SimpleBatchFunction(data, ctx)
    
    # 或者自定义数据源
    class MyBatchFunction(BatchFunction):
        def get_total_count(self) -> int:
            return len(self.my_data)
        
        def get_data_source(self) -> Iterator[Any]:
            return iter(self.my_data)
    """
    )

    logging.info("\n" + "=" * 60)
    logging.info("总结:")
    logging.info("- 新设计大大简化了用户接口")
    logging.info("- 提供了更好的进度可见性")
    logging.info("- 将复杂的停止逻辑从用户代码中抽象出来")
    logging.info("- 支持更好的错误处理和监控")
    logging.info("=" * 60)


if __name__ == "__main__":
    compare_implementations()
