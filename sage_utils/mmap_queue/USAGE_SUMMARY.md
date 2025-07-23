
# SAGE Memory-Mapped Queue 多进程使用方法总结

## 核心概念

SAGE Memory-Mapped Queue 基于共享内存实现跨进程通信，支持：
- 高性能内存映射环形缓冲区
- 跨进程零拷贝数据传递
- 线程安全的并发读写操作
- 可序列化的队列引用传递

## 使用方法

### 1. 基本队列创建和使用

```python
from sage_queue import SageQueue, destroy_queue

# 创建队列
queue_name = "my_shared_queue"
queue = SageQueue(queue_name, maxsize=64*1024)  # 64KB 缓冲区

# 写入数据
queue.put({"message": "Hello, World!", "data": [1, 2, 3]})

# 读取数据
message = queue.get()
print(message)  # {'message': 'Hello, World!', 'data': [1, 2, 3]}

# 关闭队列
queue.close()

# 销毁共享内存（可选，程序结束时自动清理）
destroy_queue(queue_name)
```

### 2. 多进程共享队列（方法一：通过队列名称）

```python
import multiprocessing
from sage_queue import SageQueue

def worker_process(queue_name, worker_id):
    # 通过名称连接到同一个共享队列
    queue = SageQueue(queue_name)
    
    # 写入数据
    for i in range(10):
        queue.put(f"Worker-{worker_id} Message-{i}")
    
    queue.close()

if __name__ == "__main__":
    queue_name = "shared_queue_example"
    
    # 创建主队列
    main_queue = SageQueue(queue_name, maxsize=128*1024)
    main_queue.close()  # 关闭句柄但保留共享内存
    
    # 启动多个进程
    processes = []
    for i in range(4):
        p = multiprocessing.Process(target=worker_process, args=(queue_name, i))
        p.start()
        processes.append(p)
    
    # 等待所有进程完成
    for p in processes:
        p.join()
    
    # 读取所有消息
    read_queue = SageQueue(queue_name)
    while not read_queue.empty():
        print(read_queue.get())
    read_queue.close()
    
    destroy_queue(queue_name)
```

### 3. 多进程引用传递（方法二：序列化引用）

```python
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from sage_queue import SageQueue

def ref_worker_process(queue_ref_dict, worker_id):
    # 从序列化引用重建队列引用
    from sage_queue import SageQueueRef
    
    ref = SageQueueRef.__new__(SageQueueRef)
    ref.__setstate__(queue_ref_dict)
    
    # 获取队列实例
    queue = ref.get_queue()
    
    # 使用队列
    for i in range(5):
        queue.put(f"RefWorker-{worker_id} Data-{i}")
    
    queue.close()
    return f"Worker-{worker_id} completed"

if __name__ == "__main__":
    # 创建队列并获取引用
    queue = SageQueue("ref_example", maxsize=64*1024)
    queue_ref = queue.get_reference()
    queue_ref_dict = queue_ref.__getstate__()  # 序列化为字典
    queue.close()
    
    # 使用 ProcessPoolExecutor 传递引用
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(3):
            future = executor.submit(ref_worker_process, queue_ref_dict, i)
            futures.append(future)
        
        # 收集结果
        for future in futures:
            print(future.result())
    
    # 读取结果
    result_queue = SageQueue("ref_example")
    while not result_queue.empty():
        print(result_queue.get())
    result_queue.close()
    
    destroy_queue("ref_example")
```

### 4. 生产者-消费者模式

```python
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

def producer_worker(queue_name, producer_id, num_messages):
    queue = SageQueue(queue_name)
    for i in range(num_messages):
        message = {
            'producer_id': producer_id,
            'message_id': i,
            'content': f'Message from Producer-{producer_id}',
            'timestamp': time.time()
        }
        queue.put(message)
    queue.close()
    return f"Producer-{producer_id} sent {num_messages} messages"

def consumer_worker(queue_name, consumer_id, max_messages):
    queue = SageQueue(queue_name)
    consumed = 0
    messages = []
    
    while consumed < max_messages:
        try:
            message = queue.get(timeout=5.0)
            messages.append(message)
            consumed += 1
        except:
            break  # 超时或队列为空
    
    queue.close()
    return f"Consumer-{consumer_id} consumed {consumed} messages"

# 使用示例
if __name__ == "__main__":
    queue_name = "prod_cons_example"
    SageQueue(queue_name, maxsize=256*1024).close()  # 创建队列
    
    with ProcessPoolExecutor() as executor:
        # 启动生产者
        producer_futures = [
            executor.submit(producer_worker, queue_name, i, 20) 
            for i in range(2)
        ]
        
        # 启动消费者
        consumer_futures = [
            executor.submit(consumer_worker, queue_name, i, 20) 
            for i in range(2)
        ]
        
        # 等待完成
        for future in producer_futures + consumer_futures:
            print(future.result())
    
    destroy_queue(queue_name)
```

## 关键要点

### 1. Worker 函数必须在模块顶层
```python
# ✓ 正确：定义在模块顶层
def my_worker(queue_name, data):
    queue = SageQueue(queue_name)
    # ... 处理逻辑
    queue.close()

def main():
    # ✗ 错误：不能在函数内部定义 worker
    def inner_worker(queue_name):  # 这会导致 pickle 错误
        pass
    
    # 使用 my_worker 而不是 inner_worker
    process = multiprocessing.Process(target=my_worker, args=("queue", "data"))
    process.start()
```

### 2. 队列生命周期管理
```python
# 创建队列
queue = SageQueue("my_queue", maxsize=64*1024)

# 使用完毕后关闭
queue.close()  # 关闭句柄，共享内存仍存在

# 彻底销毁（可选）
destroy_queue("my_queue")  # 删除共享内存
```

### 3. 错误处理
```python
from queue import Empty, Full

try:
    # 非阻塞操作
    message = queue.get_nowait()
except Empty:
    print("队列为空")

try:
    queue.put_nowait(data)
except Full:
    print("队列已满")

# 带超时的操作
try:
    message = queue.get(timeout=5.0)
except Empty:
    print("获取超时")
```

### 4. 性能优化建议

- 选择合适的缓冲区大小（maxsize）
- 避免频繁的小数据传输
- 使用批量操作减少系统调用
- 适当的错误处理和重试机制
- 及时清理不使用的队列

## 测试结果示例

根据基准测试结果，SAGE Memory-Mapped Queue 可以达到：
- 吞吐量：200K+ ops/sec (读写)
- 延迟：3-5ms (平均往返延迟)
- 内存效率：>90% 缓冲区利用率
- 并发性能：支持多进程无锁并发访问

## 常见问题

1. **"Can't pickle local object" 错误**
   - 确保 worker 函数定义在模块顶层，不在其他函数内部

2. **队列满或空的处理**
   - 使用 timeout 参数避免无限阻塞
   - 合理设计生产者和消费者的速度匹配

3. **共享内存清理**
   - 正常情况下程序结束时自动清理
   - 异常退出可能需要手动调用 destroy_queue()

4. **跨进程数据一致性**
   - SAGE Queue 保证数据的原子性读写
   - 复杂的数据结构会被序列化，注意性能影响
