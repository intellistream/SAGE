# 基础教程

欢迎来到SAGE的基础教程！本教程将通过一系列循序渐进的示例，帮助您掌握SAGE数据流编程的基础知识。每个示例都包含完整的代码和详细的解释。

## 🎯 学习目标

完成本教程后，您将能够：
- 理解SAGE数据流编程的基本概念
- 使用SAGE API构建简单的数据处理流水线
- 掌握常用的数据转换操作
- 了解如何处理不同类型的数据源和输出

## 📋 准备工作

### 安装SAGE

```bash
pip install sage-framework
```

### 导入必要的模块

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.remote_environment import RemoteEnvironment
from sage.lib.io_utils.source import FileSource, ListSource
from sage.lib.io_utils.sink import FileSink, ConsoleSink
import time
```

## 📚 教程1：第一个数据流程序

让我们从最简单的例子开始 - 处理一个数字列表：

```python
def tutorial_01_hello_sage():
    """第一个SAGE程序：处理数字列表"""
    
    # 创建本地执行环境
    env = LocalEnvironment()
    
    # 创建数据源
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # 构建数据流水线
    result = (env
        .from_batch(numbers)                    # 从列表创建数据流
         - [数据流开发指南](../guides/dataflow_development.md) - 更深入的开发技巧
   - [自定义算子开发](../guides/custom_operators.md) - 扩展SAGE功能map(lambda x: x * 2)                   # 每个数字乘以2
        .filter(lambda x: x > 10)               # 过滤大于10的数字
        .map(lambda x: f"Result: {x}")          # 格式化输出
        .sink(ConsoleSink())                    # 输出到控制台
    )
    
    # 执行流水线
    env.submit()
    print("第一个SAGE程序执行完成！")

# 运行示例
tutorial_01_hello_sage()
```

**输出结果：**
```
Result: 12
Result: 14
Result: 16
Result: 18
Result: 20
第一个SAGE程序执行完成！
```

**解释：**
- `from_batch()`: 从Python列表创建数据流
- `map()`: 对每个数据项应用转换函数
- `filter()`: 根据条件过滤数据
- `sink()`: 指定数据输出目标
- `submit()`: 开始执行流水线

## 📚 教程2：文件处理

处理文本文件是常见需求，让我们学习如何读取和处理文件：

```python
def tutorial_02_file_processing():
    """文件处理：读取文本文件并统计单词"""
    
    # 准备测试文件
    test_content = """Hello World
    This is SAGE tutorial
    We are learning dataflow programming
    SAGE makes data processing easy"""
    
    with open("test_input.txt", "w") as f:
        f.write(test_content)
    
    # 创建环境
    env = LocalEnvironment()
    
    # 文本处理函数
    def process_line(line):
        """处理单行文本"""
        # 清理和分词
        words = line.strip().lower().split()
        return {
            'line': line.strip(),
            'word_count': len(words),
            'words': words
        }
    
    def extract_words(processed_line):
        """提取单词列表"""
        return processed_line['words']
    
    # 构建文件处理流水线
    word_stream = (env
        .from_source(FileSource, "test_input.txt")  # 读取文件
        .filter(lambda line: line.strip())          # 过滤空行
        .map(process_line)                          # 处理每一行
        .flatmap(extract_words)                     # 展开单词列表
        .filter(lambda word: len(word) > 2)         # 过滤短单词
        .sink(FileSink, "processed_words.txt")      # 输出到文件
    )
    
    # 执行流水线
    env.submit()
    
    # 读取并显示结果
    with open("processed_words.txt", "r") as f:
        words = f.readlines()
        print(f"处理完成，共提取 {len(words)} 个单词")
        print("前10个单词:", words[:10])

# 运行示例
tutorial_02_file_processing()
```

**新概念：**
- `from_source()`: 从文件源创建数据流
- `flatmap()`: 一对多映射，将列表展开为多个数据项
- `FileSink`: 文件输出汇

## 📚 教程3：数据聚合和统计

学习如何对数据进行聚合计算：

```python
def tutorial_03_data_aggregation():
    """数据聚合：统计分析示例"""
    
    # 模拟用户行为数据
    user_events = [
        {'user_id': 'user1', 'action': 'click', 'timestamp': 1000, 'value': 10},
        {'user_id': 'user2', 'action': 'view', 'timestamp': 1001, 'value': 5},
        {'user_id': 'user1', 'action': 'purchase', 'timestamp': 1002, 'value': 100},
        {'user_id': 'user3', 'action': 'click', 'timestamp': 1003, 'value': 8},
        {'user_id': 'user2', 'action': 'click', 'timestamp': 1004, 'value': 15},
        {'user_id': 'user1', 'action': 'view', 'timestamp': 1005, 'value': 3},
    ]
    
    env = LocalEnvironment()
    
    # 用户活动统计函数
    def aggregate_by_user(events):
        """按用户聚合统计"""
        from collections import defaultdict
        
        user_stats = defaultdict(lambda: {
            'user_id': '', 'total_events': 0, 'total_value': 0, 'actions': []
        })
        
        for event in events:
            user_id = event['user_id']
            user_stats[user_id]['user_id'] = user_id
            user_stats[user_id]['total_events'] += 1
            user_stats[user_id]['total_value'] += event['value']
            user_stats[user_id]['actions'].append(event['action'])
        
        return list(user_stats.values())
    
    def format_user_stats(stats):
        """格式化用户统计信息"""
        return {
            'user_id': stats['user_id'],
            'total_events': stats['total_events'],
            'total_value': stats['total_value'],
            'avg_value': stats['total_value'] / stats['total_events'],
            'unique_actions': len(set(stats['actions']))
        }
    
    # 构建聚合流水线
    user_stats_stream = (env
        .from_batch(user_events)                    # 加载事件数据
        .keyBy(lambda event: event['user_id'])      # 按用户ID分组
        .window(count_window=100)                   # 窗口聚合（这里用计数窗口）
        .reduce(lambda acc, event: acc + [event] if isinstance(acc, list) else [acc, event])  # 收集事件
        .map(aggregate_by_user)                     # 聚合统计
        .flatmap(lambda user_list: user_list)       # 展开用户列表
        .map(format_user_stats)                     # 格式化结果
        .sink(ConsoleSink())                        # 输出结果
    )
    
    env.submit()

# 运行示例
tutorial_03_data_aggregation()
```

**新概念：**
- `keyBy()`: 按键分组数据流
- `window()`: 创建时间或计数窗口
- `reduce()`: 聚合操作

## 📚 教程4：异步处理

学习如何处理需要异步操作的场景：

```python
import asyncio
import aiohttp
import json

def tutorial_04_async_processing():
    """异步处理：模拟API调用"""
    
    # 模拟API处理函数
    class MockAPIProcessor:
        def __init__(self, delay=0.1):
            self.delay = delay
            
        async def __call__(self, data):
            """异步处理函数"""
            # 模拟API延迟
            await asyncio.sleep(self.delay)
            
            # 模拟API响应
            response = {
                'input': data,
                'processed': data * 2 if isinstance(data, (int, float)) else f"processed_{data}",
                'timestamp': time.time(),
                'status': 'success'
            }
            
            return response
    
    # 批量处理函数
    async def batch_api_call(batch_data):
        """批量API调用"""
        processor = MockAPIProcessor(delay=0.05)  # 批处理延迟更短
        results = []
        
        # 并行处理批次中的所有项目
        tasks = [processor(item) for item in batch_data]
        results = await asyncio.gather(*tasks)
        
        return results
    
    env = LocalEnvironment()
    
    # 测试数据
    test_data = list(range(1, 21))  # 1到20的数字
    
    # 构建异步处理流水线
    async_stream = (env
        .from_batch(test_data)                      # 加载测试数据
        .batch(size=5)                              # 5个一批
        .map(batch_api_call)                        # 批量异步处理
        .flatmap(lambda batch_result: batch_result) # 展开批处理结果
        .filter(lambda result: result['status'] == 'success')  # 过滤成功结果
        .map(lambda result: {                       # 提取有用信息
            'input': result['input'],
            'output': result['processed'],
            'processing_time': time.time() - result['timestamp']
        })
        .sink(ConsoleSink())                        # 输出结果
    )
    
    print("开始异步处理...")
    start_time = time.time()
    env.submit()
    end_time = time.time()
    
    print(f"异步处理完成，总用时: {end_time - start_time:.2f}秒")

# 运行示例
tutorial_04_async_processing()
```

**新概念：**
- 异步函数：使用`async def`定义的处理函数
- `batch()`: 将数据打包成批次
- 并行处理：使用`asyncio.gather()`并行执行多个异步任务

## 📚 教程5：错误处理

学习如何在数据流中处理错误和异常：

```python
def tutorial_05_error_handling():
    """错误处理：容错数据处理"""
    
    # 可能出错的处理函数
    def risky_processor(data):
        """可能抛出异常的处理器"""
        if data % 3 == 0:  # 模拟处理失败
            raise ValueError(f"处理失败: {data}")
        return data * 10
    
    # 容错处理函数
    def safe_processor(data):
        """安全的处理器"""
        try:
            result = risky_processor(data)
            return {'status': 'success', 'data': data, 'result': result}
        except Exception as e:
            return {'status': 'error', 'data': data, 'error': str(e)}
    
    # 重试处理器
    def retry_processor(data, max_retries=2):
        """带重试的处理器"""
        for attempt in range(max_retries + 1):
            try:
                result = risky_processor(data)
                return {'status': 'success', 'data': data, 'result': result, 'attempts': attempt + 1}
            except Exception as e:
                if attempt == max_retries:
                    return {'status': 'failed', 'data': data, 'error': str(e), 'attempts': attempt + 1}
                time.sleep(0.1 * (attempt + 1))  # 指数退避
    
    env = LocalEnvironment()
    
    # 测试数据（包含会导致错误的数据）
    test_data = list(range(1, 16))  # 3, 6, 9, 12, 15 会出错
    
    print("=== 基本错误处理示例 ===")
    basic_error_stream = (env
        .from_batch(test_data)
        .map(safe_processor)                        # 安全处理
        .sink(ConsoleSink())
    )
    env.submit()
    
    print("\n=== 重试机制示例 ===")
    env = LocalEnvironment()  # 创建新环境
    retry_stream = (env
        .from_batch(test_data)
        .map(retry_processor)                       # 重试处理
        .sink(ConsoleSink())
    )
    env.submit()
    
    print("\n=== 错误过滤和统计 ===")
    env = LocalEnvironment()  # 创建新环境
    
    def collect_stats(results):
        """统计处理结果"""
        success_count = len([r for r in results if r['status'] == 'success'])
        error_count = len([r for r in results if r['status'] == 'error'])
        
        return {
            'total': len(results),
            'success': success_count,
            'errors': error_count,
            'success_rate': success_count / len(results) if results else 0
        }
    
    stats_stream = (env
        .from_batch(test_data)
        .map(safe_processor)                        # 安全处理
        .collect()                                  # 收集所有结果
        .map(collect_stats)                         # 统计
        .sink(ConsoleSink())
    )
    env.submit()

# 运行示例
tutorial_05_error_handling()
```

**新概念：**
- 异常处理：在处理函数中捕获和处理异常
- 重试机制：对失败的操作进行重试
- `collect()`: 收集所有数据项到一个列表中

## 📚 教程6：多流连接

学习如何处理多个数据流的连接：

```python
def tutorial_06_stream_joining():
    """多流连接：用户数据关联"""
    
    # 用户基本信息
    users = [
        {'user_id': 1, 'name': 'Alice', 'age': 25},
        {'user_id': 2, 'name': 'Bob', 'age': 30},
        {'user_id': 3, 'name': 'Charlie', 'age': 35},
    ]
    
    # 用户订单信息
    orders = [
        {'order_id': 101, 'user_id': 1, 'amount': 100, 'product': 'Book'},
        {'order_id': 102, 'user_id': 2, 'amount': 200, 'product': 'Phone'},
        {'order_id': 103, 'user_id': 1, 'amount': 50, 'product': 'Coffee'},
        {'order_id': 104, 'user_id': 4, 'amount': 300, 'product': 'Laptop'},  # 用户不存在
    ]
    
    env = LocalEnvironment()
    
    # 创建用户流和订单流
    user_stream = env.from_batch(users)
    order_stream = env.from_batch(orders)
    
    # 连接两个流
    def join_user_orders(user_data, order_data):
        """连接用户和订单数据"""
        user_dict = {u['user_id']: u for u in user_data}
        
        joined_results = []
        for order in order_data:
            user_id = order['user_id']
            if user_id in user_dict:
                user = user_dict[user_id]
                joined_results.append({
                    'user_id': user_id,
                    'user_name': user['name'],
                    'user_age': user['age'],
                    'order_id': order['order_id'],
                    'amount': order['amount'],
                    'product': order['product']
                })
            else:
                # 处理找不到用户的订单
                joined_results.append({
                    'user_id': user_id,
                    'user_name': 'Unknown',
                    'user_age': None,
                    'order_id': order['order_id'],
                    'amount': order['amount'],
                    'product': order['product'],
                    'status': 'orphaned_order'
                })
        
        return joined_results
    
    # 使用connect进行流连接
    connected_stream = user_stream.connect(order_stream)
    
    # 处理连接后的数据
    result_stream = (connected_stream
        .comap(join_user_orders)                    # 协同处理两个流的数据
        .flatmap(lambda results: results)          # 展开结果列表
        .sink(ConsoleSink())                        # 输出结果
    )
    
    print("=== 流连接示例 ===")
    env.submit()
    
    # 另一种连接方式：使用窗口连接
    print("\n=== 窗口连接示例 ===")
    env = LocalEnvironment()
    
    # 模拟时间序列数据
    user_actions = [
        {'user_id': 1, 'action': 'login', 'timestamp': 1000},
        {'user_id': 2, 'action': 'view_product', 'timestamp': 1001},
        {'user_id': 1, 'action': 'add_to_cart', 'timestamp': 1002},
    ]
    
    user_profiles = [
        {'user_id': 1, 'segment': 'premium', 'timestamp': 999},
        {'user_id': 2, 'segment': 'regular', 'timestamp': 1000},
    ]
    
    action_stream = env.from_batch(user_actions)
    profile_stream = env.from_batch(user_profiles)
    
    # 基于时间窗口的连接
    def time_window_join(actions, profiles):
        """基于时间窗口连接用户行为和档案"""
        profile_dict = {p['user_id']: p for p in profiles}
        
        enriched_actions = []
        for action in actions:
            user_id = action['user_id']
            if user_id in profile_dict:
                profile = profile_dict[user_id]
                # 简单的时间匹配（实际应用中会更复杂）
                if abs(action['timestamp'] - profile['timestamp']) <= 10:
                    enriched_actions.append({
                        **action,
                        'user_segment': profile['segment']
                    })
        
        return enriched_actions
    
    windowed_stream = (action_stream.connect(profile_stream)
        .comap(time_window_join)
        .flatmap(lambda results: results)
        .sink(ConsoleSink())
    )
    
    env.submit()

# 运行示例
tutorial_06_stream_joining()
```

**新概念：**
- `connect()`: 连接两个数据流
- `comap()`: 协同处理连接的数据流
- 时间窗口连接：基于时间戳进行数据关联

## 📚 教程7：状态管理

学习如何在数据流中维护状态：

```python
def tutorial_07_stateful_processing():
    """有状态处理：运行统计和会话管理"""
    
    # 有状态计数器
    class StatefulCounter:
        def __init__(self):
            self.counts = {}
        
        def __call__(self, item):
            key = item.get('category', 'default')
            self.counts[key] = self.counts.get(key, 0) + 1
            
            return {
                'item': item,
                'category_count': self.counts[key],
                'total_categories': len(self.counts)
            }
    
    # 滑动窗口平均
    class MovingAverageCalculator:
        def __init__(self, window_size=5):
            self.window_size = window_size
            self.window = []
        
        def __call__(self, value):
            self.window.append(value)
            if len(self.window) > self.window_size:
                self.window.pop(0)  # 移除最旧的元素
            
            avg = sum(self.window) / len(self.window)
            return {
                'value': value,
                'moving_average': avg,
                'window_size': len(self.window)
            }
    
    # 会话管理器
    class SessionManager:
        def __init__(self, timeout=10):
            self.sessions = {}
            self.timeout = timeout
        
        def __call__(self, event):
            user_id = event['user_id']
            current_time = event['timestamp']
            
            # 检查现有会话
            if user_id in self.sessions:
                last_activity = self.sessions[user_id]['last_activity']
                if current_time - last_activity > self.timeout:
                    # 会话超时，开始新会话
                    self.sessions[user_id] = {
                        'session_id': f"session_{current_time}",
                        'start_time': current_time,
                        'last_activity': current_time,
                        'event_count': 1
                    }
                else:
                    # 更新现有会话
                    self.sessions[user_id]['last_activity'] = current_time
                    self.sessions[user_id]['event_count'] += 1
            else:
                # 新用户会话
                self.sessions[user_id] = {
                    'session_id': f"session_{current_time}",
                    'start_time': current_time,
                    'last_activity': current_time,
                    'event_count': 1
                }
            
            session_info = self.sessions[user_id].copy()
            session_info.update({
                'user_id': user_id,
                'event': event['action'],
                'session_duration': current_time - session_info['start_time']
            })
            
            return session_info
    
    env = LocalEnvironment()
    
    print("=== 有状态计数器示例 ===")
    counter = StatefulCounter()
    
    # 测试数据
    items = [
        {'name': 'item1', 'category': 'A'},
        {'name': 'item2', 'category': 'B'},
        {'name': 'item3', 'category': 'A'},
        {'name': 'item4', 'category': 'C'},
        {'name': 'item5', 'category': 'A'},
        {'name': 'item6', 'category': 'B'},
    ]
    
    counter_stream = (env
        .from_batch(items)
        .map(counter)                               # 有状态计数
        .sink(ConsoleSink())
    )
    env.submit()
    
    print("\n=== 滑动窗口平均示例 ===")
    env = LocalEnvironment()
    moving_avg = MovingAverageCalculator(window_size=3)
    
    values = [10, 15, 20, 12, 18, 25, 8, 30]
    
    avg_stream = (env
        .from_batch(values)
        .map(moving_avg)                            # 滑动窗口平均
        .sink(ConsoleSink())
    )
    env.submit()
    
    print("\n=== 会话管理示例 ===")
    env = LocalEnvironment()
    session_mgr = SessionManager(timeout=5)
    
    # 模拟用户事件（包含会话超时）
    events = [
        {'user_id': 'user1', 'action': 'login', 'timestamp': 1000},
        {'user_id': 'user1', 'action': 'view', 'timestamp': 1002},
        {'user_id': 'user2', 'action': 'login', 'timestamp': 1003},
        {'user_id': 'user1', 'action': 'click', 'timestamp': 1004},
        {'user_id': 'user1', 'action': 'purchase', 'timestamp': 1015},  # 超时，新会话
        {'user_id': 'user2', 'action': 'logout', 'timestamp': 1016},
    ]
    
    session_stream = (env
        .from_batch(events)
        .map(session_mgr)                           # 会话管理
        .sink(ConsoleSink())
    )
    env.submit()

# 运行示例
tutorial_07_stateful_processing()
```

**新概念：**
- 有状态处理：处理函数维护内部状态
- 滑动窗口：维护固定大小的历史数据窗口
- 会话管理：基于时间和用户行为管理会话状态

## 📚 教程8：综合示例 - 简单的RAG系统

现在让我们构建一个综合示例，展示如何使用SAGE构建一个简单的RAG（检索增强生成）系统：

```python
def tutorial_08_simple_rag_system():
    """综合示例：简单的RAG系统"""
    
    # 模拟知识库
    knowledge_base = [
        {"id": 1, "content": "Python是一种高级编程语言", "category": "programming"},
        {"id": 2, "content": "机器学习是人工智能的一个分支", "category": "ai"},
        {"id": 3, "content": "数据流编程是一种编程范式", "category": "programming"},
        {"id": 4, "content": "SAGE是一个数据流处理框架", "category": "framework"},
        {"id": 5, "content": "异步编程可以提高程序性能", "category": "programming"},
    ]
    
    # 查询嵌入器（简化版）
    class SimpleEmbedder:
        def __call__(self, text):
            """简单的文本嵌入（使用关键词匹配）"""
            keywords = text.lower().split()
            return {
                'text': text,
                'keywords': keywords,
                'embedding': keywords  # 简化：直接使用关键词作为嵌入
            }
    
    # 检索器
    class SimpleRetriever:
        def __init__(self, knowledge_base, top_k=2):
            self.knowledge_base = knowledge_base
            self.top_k = top_k
            
        def __call__(self, query_data):
            """检索相关文档"""
            query_keywords = set(query_data['keywords'])
            scores = []
            
            for doc in self.knowledge_base:
                doc_keywords = set(doc['content'].lower().split())
                # 简单的相似度计算（交集大小）
                similarity = len(query_keywords & doc_keywords)
                scores.append({
                    'document': doc,
                    'similarity': similarity
                })
            
            # 按相似度排序并返回top-k
            scores.sort(key=lambda x: x['similarity'], reverse=True)
            top_docs = scores[:self.top_k]
            
            return {
                'query': query_data['text'],
                'retrieved_docs': [item['document'] for item in top_docs],
                'similarities': [item['similarity'] for item in top_docs]
            }
    
    # 生成器
    class SimpleGenerator:
        def __call__(self, retrieval_result):
            """基于检索结果生成回答"""
            query = retrieval_result['query']
            docs = retrieval_result['retrieved_docs']
            
            if not docs or all(sim == 0 for sim in retrieval_result['similarities']):
                return {
                    'query': query,
                    'answer': "抱歉，我无法找到相关信息来回答您的问题。",
                    'sources': []
                }
            
            # 简单的答案生成
            context = " ".join([doc['content'] for doc in docs])
            answer = f"根据相关资料：{context}。这些信息可能对您的问题 '{query}' 有所帮助。"
            
            return {
                'query': query,
                'answer': answer,
                'sources': [doc['id'] for doc in docs],
                'context_length': len(context)
            }
    
    # 查询质量过滤器
    def query_filter(query):
        """过滤查询质量"""
        return len(query.strip()) > 3 and not query.strip().isdigit()
    
    # 结果格式化器
    def format_response(result):
        """格式化最终响应"""
        return f"""
问题: {result['query']}
回答: {result['answer']}
参考文档: {', '.join(map(str, result['sources'])) if result['sources'] else '无'}
上下文长度: {result.get('context_length', 0)} 字符
---"""
    
    env = LocalEnvironment()
    
    # 测试查询
    queries = [
        "什么是Python？",
        "机器学习是什么",
        "SAGE框架介绍",
        "异步编程",
        "xyz",  # 低质量查询
        "123",  # 数字查询
    ]
    
    # 创建处理组件
    embedder = SimpleEmbedder()
    retriever = SimpleRetriever(knowledge_base, top_k=2)
    generator = SimpleGenerator()
    
    print("=== 简单RAG系统示例 ===")
    
    # 构建RAG处理流水线
    rag_pipeline = (env
        .from_batch(queries)                        # 输入查询
        .filter(query_filter)                       # 过滤低质量查询
        .map(embedder)                              # 查询嵌入
        .map(retriever)                             # 文档检索
        .map(generator)                             # 答案生成
        .map(format_response)                       # 格式化响应
        .sink(ConsoleSink())                        # 输出结果
    )
    
    env.submit()
    
    print("\n=== 带错误处理的RAG系统 ===")
    
    # 带错误处理的RAG系统
    def safe_rag_step(step_func, step_name):
        """为RAG步骤添加错误处理"""
        def wrapper(data):
            try:
                result = step_func(data)
                return {'status': 'success', 'data': result, 'step': step_name}
            except Exception as e:
                return {'status': 'error', 'error': str(e), 'step': step_name, 'input': data}
        return wrapper
    
    def extract_successful_data(result):
        """提取成功处理的数据"""
        if result['status'] == 'success':
            return result['data']
        else:
            print(f"步骤 {result['step']} 失败: {result['error']}")
            return None
    
    env = LocalEnvironment()
    safe_rag_pipeline = (env
        .from_batch(queries)
        .filter(query_filter)
        .map(safe_rag_step(embedder, "embedding"))
        .map(extract_successful_data)
        .filter(lambda x: x is not None)
        .map(safe_rag_step(retriever, "retrieval"))
        .map(extract_successful_data)
        .filter(lambda x: x is not None)
        .map(safe_rag_step(generator, "generation"))
        .map(extract_successful_data)
        .filter(lambda x: x is not None)
        .map(format_response)
        .sink(ConsoleSink())
    )
    
    env.submit()

# 运行示例
tutorial_08_simple_rag_system()
```

## 🎓 总结

恭喜您完成了SAGE基础教程！您已经学会了：

### 核心概念
- **数据流编程模型**：声明式的数据处理方式
- **算子链式调用**：使用map、filter、sink等构建处理流水线
- **执行环境**：LocalEnvironment的使用

### 基本操作
- **数据源**：from_batch、from_source等创建数据流
- **转换操作**：map、filter、flatmap等数据转换
- **输出操作**：sink到不同目标（控制台、文件等）

### 高级特性
- **批处理**：提升处理效率
- **异步处理**：处理I/O密集型操作
- **错误处理**：构建健壮的数据处理系统
- **多流连接**：处理复杂的数据关联
- **状态管理**：维护处理状态和上下文

### 实际应用
- **文件处理**：读取和处理文本文件
- **数据聚合**：统计和分析数据
- **RAG系统**：检索增强生成的完整实现

## 📚 下一步学习

现在您可以：

1. **深入学习**：
   - <!-- [数据流开发指南](./dataflow_development.md) -->
数据流开发 - 更深入的开发技巧
   - <!-- [自定义算子开发](./custom_operators.md) -->
自定义算子 - 扩展系统功能
   - <!-- [性能调优](./performance_tuning.md) -->
性能调优 - 优化系统性能

2. **实践项目**：
   - 构建更复杂的RAG系统
   - 实现实时数据处理流水线
   - 开发多模态数据处理应用

3. **探索高级特性**：
   - 分布式处理
   - 可视化监控
   - 生产环境部署

继续探索SAGE的强大功能，构建属于您的智能数据处理应用吧！
