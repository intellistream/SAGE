#!/usr/bin/env python3
"""
SAGE Interactive One-by-One Processing Example
==============================================

This     try:        
        env.submit(autostop=True)le demonstrates controlled one-by-one processing where:
- Only one data item in pipeline at any time
- Next data blocks until current processing completes
- Interactive prompts between each data item
- 2-second delay after each processing
- Uses SAGE's native BatchFunction architecture

Key Features:
- BatchFunction-based (matches hello_world pattern)
- Threading synchronization for flow control
- Interactive user control between data items
- True sequential processing with backpressure
"""

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger
import time
import threading

# 全局同步控制器：实现真正的"一个一个处理"
class OneByOneController:
    def __init__(self):
        self._processing_event = threading.Event()
        self._processing_event.set()  # 初始允许处理第一个数据
        self._current_processing = False
        
    def acquire_processing_slot(self):
        """获取处理槽位（阻塞直到获得）"""
        self._processing_event.wait()  # 等待可以处理
        self._current_processing = True
        self._processing_event.clear()  # 阻塞后续请求
        
    def release_processing_slot(self):
        """释放处理槽位（允许下一个数据处理）"""
        self._current_processing = False
        self._processing_event.set()  # 允许下一个数据处理
        
    def can_process(self):
        """检查是否可以立即处理（非阻塞）"""
        return self._processing_event.is_set()

# 全局控制器实例
global_controller = OneByOneController()

# 受控的一个一个批处理数据源 - 基于SAGE的BatchFunction
class OneByOneControlledBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 5      # 生成5条数据包后返回None
    
    def execute(self):
        # 如果已达到最大数量，结束
        if self.counter >= self.max_count:
            return None
        
        # 检查是否可以发射（一个一个处理的关键控制点）
        if not global_controller.can_process():
            # 如果当前有数据在处理中，返回None（阻塞）
            return None
            
        # 获取处理槽位，阻塞后续数据
        global_controller.acquire_processing_slot()
        
        # 发射新数据
        self.counter += 1
        print(f"📤 Batch #{self.counter}: Emitted 'Hello, World! #{self.counter}' (next blocked until completion)")
        return f"Hello, World! #{self.counter}"

# 交互式 MapFunction，处理数据并等待用户输入
class InteractiveUpperCaseMap(MapFunction):
    def execute(self, data):
        result = data.upper()
        print(f"🔤 Map: Processing '{data}' -> '{result}'")
        
        # 交互式提示
        print(f"✨ Processing completed: '{result}'")
        input("👉 Press Enter to continue to next data item... ")
        
        # 添加2秒延迟
        print("⏳ Waiting 2 seconds...")
        time.sleep(2)
        
        return result

# 处理完成后释放控制槽位的交互式Sink
class InteractiveCompletionSink(SinkFunction):
    def execute(self, data):
        print(f"📊 Sink: Final result: '{data}'")
        print(f"✅ Processing completed, enabling next data...")
        print("-" * 50)
        
        # 处理完成，释放控制槽位，允许下一个数据处理
        global_controller.release_processing_slot()

def main():
    env = LocalEnvironment("hello_onebyone_world_interactive")
    
    print("🚀 Starting Interactive One-by-One Processing Example")
    print("📝 This demonstrates SAGE-native controlled processing:")
    print("   - Uses BatchFunction (matches hello_world pattern)")
    print("   - Only one data item in pipeline at any time") 
    print("   - Interactive prompts between each data item")
    print("   - 2-second delay after each processing")
    print("   - True sequential data flow with user control\n")
    
    print("🔗 SAGE BatchFunction Architecture:")
    print("   - BatchFunction.execute() called repeatedly by BatchOperator")
    print("   - Returns None when no data available (blocking behavior)")
    print("   - User interaction controls processing flow")
    print("   - Sink completion releases next processing slot\n")
    
    print(f"🎬 Starting interactive processing of 5 items...")
    print("💡 You'll be prompted after each item is processed!")
    print("=" * 50)
    
    # 使用标准的SAGE BatchFunction管道
    env.from_batch(OneByOneControlledBatch).map(InteractiveUpperCaseMap).sink(InteractiveCompletionSink)
    
    try:
        print("🎬 Starting controlled one-by-one processing...")
        print("� Watch data being processed one at a time:\n")
        
        env.submit(autostop=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        
    finally:
        print("\n📋 Interactive One-by-One Processing Completed!")
        print("💡 This example demonstrated:")
        print("   - Interactive one-by-one processing with user control")
        print("   - SAGE BatchFunction with controlled emission")
        print("   - User prompts between each data item")
        print("   - 2-second delays for clear observation")
        print("   - Sequential data processing ensuring no overlap")
        print("\n🏗️  SAGE Architecture Benefits:")
        print("   - BatchFunction: Native SAGE pattern (like hello_world)")
        print("   - BatchOperator: Handles None returns for blocking")
        print("   - Controller: Manages one-at-a-time processing")
        print("   - Interactive: User-controlled processing flow")

if __name__ == "__main__":
    # 关闭日志输出以便看清示例输出
    CustomLogger.disable_global_console_debug()
    main()
