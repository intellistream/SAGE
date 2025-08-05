"""
BatchOperator vs SourceOperator 对比示例

展示新的批处理设计相对于原始设计的优势
"""

from typing import Any
from sage.api.function.source_function import SourceFunction, StopSignal
from sage.api.function.batch_function import SimpleBatchFunction


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
        def info(self, msg): print(f"INFO: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")
    
    data = ["item1", "item2", "item3", "item4", "item5"]
    
    print("=" * 60)
    print("批处理设计对比示例")
    print("=" * 60)
    
    # 1. 旧式实现
    print("\n1. 旧式 SourceFunction 实现:")
    print("   - 用户需要手动管理停止逻辑")
    print("   - 无内置进度跟踪")
    print("   - 停止信号在函数中发送")
    
    ctx1 = MockContext("old_style")
    old_func = OldStyleSourceFunction(data, ctx1)
    
    print(f"\n   处理数据 ({len(data)} 条记录):")
    for i in range(len(data) + 2):  # 多执行几次展示停止逻辑
        result = old_func.execute()
        if isinstance(result, StopSignal):
            print(f"   第{i+1}次执行: 收到停止信号 {result}")
            break
        else:
            print(f"   第{i+1}次执行: 处理数据 {result}")
    
    # 2. 新式实现
    print("\n" + "=" * 60)
    print("2. 新式 BatchFunction 实现:")
    print("   - 用户只需声明数据，不管停止逻辑") 
    print("   - 内置进度跟踪和状态管理")
    print("   - 停止信号由算子自动发送")
    
    ctx2 = MockContext("new_style")
    new_func = SimpleBatchFunction(data, ctx2)
    
    print(f"\n   处理数据 ({new_func.get_total_count()} 条记录):")
    i = 0
    while not new_func.is_finished():
        result = new_func.execute()
        current, total = new_func.get_progress()
        completion = new_func.get_completion_rate()
        
        if result is not None:
            print(f"   第{i+1}次执行: 处理数据 {result} - 进度 {current}/{total} ({completion:.0%})")
        i += 1
    
    print(f"   批处理完成状态: {new_func.is_finished()}")
    print(f"   最终完成率: {new_func.get_completion_rate():.0%}")
    
    # 3. 功能对比表
    print("\n" + "=" * 60)
    print("功能对比:")
    print("=" * 60)
    
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
        print(f"{row[0]:<20} | {row[1]:<23} | {row[2]}")
    
    # 4. 代码量对比
    print("\n" + "=" * 60)
    print("代码实现对比:")
    print("=" * 60)
    
    print("\n旧式实现 - 用户需要写的代码:")
    print('''
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
    ''')
    
    print("\n新式实现 - 用户只需要声明:")
    print('''
    # 直接使用内置实现
    batch_func = SimpleBatchFunction(data, ctx)
    
    # 或者自定义数据源
    class MyBatchFunction(BatchFunction):
        def get_total_count(self) -> int:
            return len(self.my_data)
        
        def get_data_source(self) -> Iterator[Any]:
            return iter(self.my_data)
    ''')
    
    print("\n" + "=" * 60)
    print("总结:")
    print("- 新设计大大简化了用户接口")
    print("- 提供了更好的进度可见性") 
    print("- 将复杂的停止逻辑从用户代码中抽象出来")
    print("- 支持更好的错误处理和监控")
    print("=" * 60)


if __name__ == "__main__":
    compare_implementations()
