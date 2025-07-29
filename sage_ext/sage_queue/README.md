# SAGE Queue

High-performance memory-mapped queue implementation for inter-process communication in the SAGE framework.

## Directory Structure

```
sage_queue/
├── CMakeLists.txt          # CMake build configuration
├── build.sh                # Legacy build script (now calls CMake)
├── build_cmake.sh          # New CMake build script
├── auto_compile.sh         # Auto-compilation for CI
├── include/                # Header files
│   ├── ring_buffer.h
│   └── concurrentqueue.h
├── src/                    # Source files
│   └── ring_buffer.cpp
├── bindings/               # Python bindings (pybind11)
│   └── sage_queue_bindings.cpp
├── python/                 # Python interface files
│   ├── sage_queue.py
│   └── sage_queue_manager.py
├── tests/                  # Test files
│   └── test_basic.cpp
└── build/                  # CMake build output (generated)
```

## Building

### Using CMake (Recommended)

```bash
# Release build
./build_cmake.sh

# Debug build with AddressSanitizer
./build_cmake.sh debug

# Clean build
./build_cmake.sh clean

# Debug clean build
./build_cmake.sh debug clean
```

### Using Legacy Script

The original `build.sh` script is still available for compatibility:

```bash
# Release build
./build.sh

# Debug build
./build.sh debug
```

## Build Options

The CMake build system supports the following options:

- `BUILD_DEBUG`: Enable debug symbols and AddressSanitizer
- `BUILD_TESTS`: Build test programs (default: ON)
- `BUILD_PYTHON_BINDINGS`: Build Python bindings with pybind11 (default: ON)
- `USE_OPENMP`: Enable OpenMP support (default: ON)

## Output

- **Library**: `build/libring_buffer.so`
- **Compatibility symlinks**: `ring_buffer.so` and `libring_buffer.so` in the root directory
- **Tests**: `build/test_sage_queue` (if `BUILD_TESTS=ON`)
- **Python bindings**: `build/sage_queue_bindings.so` (if `BUILD_PYTHON_BINDINGS=ON`)

## Features

- Memory-mapped ring buffer for high-performance IPC
- Thread-safe concurrent queue implementation
- Debug builds with AddressSanitizer support
- CMake-based build system for consistency with other SAGE components
- Automatic testing and validation

## Integration

This module integrates with the main SAGE installation system and follows the same CMake patterns as other components in `sage_ext/`.

## Original Features (Preserved)

- 🚀 **高性能**: 基于mmap的零拷贝内存映射，原子操作无锁设计
- 🔄 **兼容性**: 完全兼容Python标准`queue.Queue`接口
- 🌐 **跨进程**: 支持多进程间高效通信
- 🎭 **Ray集成**: 原生支持Ray Actor间通信
- 📦 **可序列化**: 队列引用支持pickle序列化，可在Actor间传递
- 🔧 **灵活配置**: 支持自定义缓冲区大小和清理策略
- 📊 **监控统计**: 提供详细的性能统计和诊断信息
chmod +x build.sh
./build.sh
```

### 基本使用

```python
from sage.utils.mmap_queue import SageQueue

# 创建队列
queue = SageQueue("my_queue", maxsize=64*1024)

# 生产者
queue.put({"message": "Hello, SAGE!", "data": [1, 2, 3]})
queue.put("Simple string message")

# 消费者
item1 = queue.get()  # {"message": "Hello, SAGE!", "data": [1, 2, 3]}
item2 = queue.get()  # "Simple string message"

# 检查状态
print(f"队列大小: {queue.qsize()}")
print(f"队列为空: {queue.empty()}")
print(f"队列已满: {queue.full()}")

queue.close()
```

### Ray Actor集成

```python
import ray
from sage.utils.mmap_queue import SageQueue

@ray.remote
class Producer:
    def produce(self, queue_ref):
        queue = queue_ref.get_queue()
        for i in range(100):
            queue.put(f"Message {i}")

@ray.remote  
class Consumer:
    def consume(self, queue_ref, count):
        queue = queue_ref.get_queue()
        results = []
        for _ in range(count):
            results.append(queue.get(timeout=5.0))
        return results

# 使用
ray.init()
queue = SageQueue("actor_queue", maxsize=1024*1024)
queue_ref = queue.get_reference()

producer = Producer.remote()
consumer = Consumer.remote()

# 启动任务
producer.produce.remote(queue_ref)
results = ray.get(consumer.consume.remote(queue_ref, 100))

print(f"消费了 {len(results)} 条消息")
ray.shutdown()
```

## 核心组件

### SageQueue
主要的队列类，提供完整的Queue接口:

- `put(item, block=True, timeout=None)` - 添加元素
- `get(block=True, timeout=None)` - 获取元素  
- `put_nowait(item)` - 非阻塞添加
- `get_nowait()` - 非阻塞获取
- `qsize()` - 队列大小
- `empty()` - 是否为空
- `full()` - 是否已满
- `get_reference()` - 获取可序列化引用
- `get_stats()` - 获取统计信息

### SageQueueRef
可序列化的队列引用，用于跨进程传递:

- `get_queue()` - 从引用创建队列实例
- 支持pickle序列化/反序列化

## 架构设计

### 内存布局
```
┌─────────────────────────────────────────────────────────┐
│                    Ring Buffer Header                    │
├─────────────────────────────────────────────────────────┤
│ Magic | Version | Size | Head | Tail | Readers | Writers │
├─────────────────────────────────────────────────────────┤
│           RefCount | ProcessCount | Mutex | Name          │  
├─────────────────────────────────────────────────────────┤
│                      Statistics                         │
├─────────────────────────────────────────────────────────┤
│                    Data Buffer                          │
│                    (Ring Buffer)                        │
└─────────────────────────────────────────────────────────┘
```

### 核心算法
- **环形缓冲区**: 使用2的幂次大小，通过位运算优化模操作
- **原子操作**: 使用C11原子操作实现无锁并发访问
- **内存映射**: 基于POSIX共享内存(shm_open/mmap)实现跨进程访问
- **引用计数**: 自动管理共享内存生命周期

### 性能特性
- **零拷贝**: 数据直接在共享内存中传递
- **无锁设计**: 读写操作使用原子指令，避免锁竞争
- **批处理**: 支持批量读写操作提高吞吐量
- **缓存友好**: 内存布局优化，减少伪共享

## 性能测试

运行性能和功能测试:

```bash
# 基础功能测试
python3 test_sage_queue.py

# Ray Actor集成测试  
python3 test_ray_integration.py
```

典型性能指标(在现代多核CPU上):
- **吞吐量**: >1M messages/second (小消息)
- **延迟**: <1μs (本地队列操作)
- **内存开销**: 最小128B头部 + 数据缓冲区
- **并发**: 支持多读多写无锁访问

## 最佳实践

### 缓冲区大小选择
```python
# 高频小消息
queue = SageQueue("small_msgs", maxsize=64*1024)    # 64KB

# 大数据传输  
queue = SageQueue("large_data", maxsize=16*1024*1024)  # 16MB

# 批处理场景
queue = SageQueue("batch", maxsize=256*1024*1024)   # 256MB
```

### 错误处理
```python
from queue import Empty, Full

try:
    item = queue.get(timeout=1.0)
except Empty:
    print("队列为空")

try:
    queue.put(large_item, timeout=1.0)  
except Full:
    print("队列已满")
```

### 资源管理
```python
# 使用上下文管理器
with SageQueue("temp_queue") as queue:
    queue.put("data")
    item = queue.get()
# 自动关闭

# 手动管理
queue = SageQueue("persistent_queue")
try:
    # 使用队列
    pass
finally:
    queue.close()  # 关闭但保留共享内存
    # queue.destroy()  # 删除共享内存
```

## 故障排除

### 编译问题
```bash
# 检查依赖
sudo apt-get install build-essential

# 手动编译
gcc -std=c11 -Wall -Wextra -O3 -fPIC -shared -o ring_buffer.so ring_buffer.cpp -lrt -lpthread
```

### 权限问题  
```bash
# 检查共享内存权限
ls -la /dev/shm/sage_ringbuf_*

# 清理残留共享内存
sudo rm -f /dev/shm/sage_ringbuf_*
```

### 调试信息
```python
# 获取详细统计
stats = queue.get_stats()
print(f"缓冲区使用率: {stats['utilization']:.2%}")
print(f"读写计数: R={stats['readers']}, W={stats['writers']}")  
print(f"总传输: {stats['total_bytes_written']} bytes")
```

## API参考

### 完整API文档请参考源代码中的docstring

### 依赖项
- Python 3.6+
- GCC编译器  
- POSIX兼容系统(Linux/macOS)
- Ray (可选，用于Actor集成)

## 许可证

与SAGE项目保持一致的开源许可证。
