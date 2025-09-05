# SAGE Flow 故障排除指南

本文档提供了常见问题的诊断和解决方法。

## 🔍 问题诊断流程

### 1. 基本诊断步骤

```bash
# 1. 检查 Python 版本
python --version

# 2. 检查模块导入
python -c "import sage_flow_datastream as sfd; print('模块可用')"

# 3. 运行基本测试
python basic_stream_processing.py

# 4. 查看系统资源
python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, 内存: {psutil.virtual_memory().percent}%')"
```

### 2. 日志分析

```python
# 启用详细日志
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sage_flow_debug.log'),
        logging.StreamHandler()
    ]
)
```

## 🚨 常见错误及解决方案

### 错误 1: 模块未找到

**错误信息：**
```
ModuleNotFoundError: No module named 'sage_flow_datastream'
```

**可能原因：**
1. SAGE Flow Python 模块未编译
2. PYTHONPATH 设置不正确
3. 模块安装位置错误

**解决方案：**

```bash
# 1. 编译 Python 模块
cd packages/sage-middleware/src
python setup.py build_ext --inplace

# 2. 检查编译结果
ls -la sage_flow_datastream*.so

# 3. 设置 PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 4. 验证导入
python -c "import sage_flow_datastream as sfd; print('成功')"
```

### 错误 2: 依赖包缺失

**错误信息：**
```
ModuleNotFoundError: No module named 'psutil'
```

**解决方案：**

```bash
# 安装必需的包
pip install psutil

# 或者使用 conda
conda install psutil

# 验证安装
python -c "import psutil; print('psutil 版本:', psutil.__version__)"
```

### 错误 3: 内存不足

**错误信息：**
```
MemoryError: Unable to allocate memory
```

**可能原因：**
1. 处理的数据集过大
2. 内存泄漏
3. 系统内存不足

**解决方案：**

```python
# 1. 使用批处理
def process_in_batches(data, batch_size=1000):
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        process_batch(batch)
        # 强制垃圾回收
        import gc
        gc.collect()

# 2. 监控内存使用
import psutil
import os

def check_memory_usage():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    if memory_mb > 1000:  # 1GB 阈值
        print(f"警告: 内存使用过高 ({memory_mb:.1f} MB)")
        return True
    return False

# 3. 增加系统内存或使用更大的实例
```

### 错误 4: Kafka 连接失败

**错误信息：**
```
KafkaError: Connection refused
```

**可能原因：**
1. Kafka 服务未启动
2. 网络连接问题
3. 配置错误

**解决方案：**

```bash
# 1. 检查 Kafka 服务状态
sudo systemctl status kafka
# 或者
ps aux | grep kafka

# 2. 测试连接
telnet localhost 9092

# 3. 检查配置
cat /etc/kafka/server.properties | grep listeners

# 4. 重启 Kafka 服务
sudo systemctl restart kafka
```

### 错误 5: 文件权限错误

**错误信息：**
```
PermissionError: [Errno 13] Permission denied
```

**解决方案：**

```bash
# 1. 检查文件权限
ls -la /path/to/file

# 2. 修改权限
chmod 644 /path/to/file

# 3. 更改所有者
sudo chown $USER:$USER /path/to/file

# 4. 使用适当的用户运行
sudo -u sage_user python your_script.py
```

## ⚡ 性能问题排查

### 1. 吞吐量过低

**诊断步骤：**

```python
import time

def benchmark_processing(data_size=10000):
    # 生成测试数据
    data = [{"id": i, "value": i * 2} for i in range(data_size)]

    start_time = time.time()

    # 执行处理
    results = []
    for item in data:
        processed = process_item(item)
        results.append(processed)

    end_time = time.time()
    duration = end_time - start_time
    throughput = data_size / duration

    print(f"处理 {data_size} 项数据耗时: {duration:.2f} 秒")
    print(f"吞吐量: {throughput:.1f} items/秒")

    return throughput
```

**优化建议：**
1. 使用并发处理
2. 优化算法复杂度
3. 使用向量化操作
4. 缓存频繁访问的数据

### 2. CPU 使用率过高

**诊断脚本：**

```python
import psutil
import time

def monitor_cpu_usage(duration=60):
    """监控 CPU 使用率"""
    cpu_percentages = []

    for _ in range(duration):
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_percentages.append(cpu_percent)
        print(f"CPU 使用率: {cpu_percent}%")

    avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
    max_cpu = max(cpu_percentages)

    print(f"平均 CPU 使用率: {avg_cpu:.1f}%")
    print(f"最高 CPU 使用率: {max_cpu:.1f}%")

    return avg_cpu, max_cpu
```

**优化建议：**
1. 减少不必要的计算
2. 使用异步处理
3. 优化循环和递归
4. 考虑使用多进程

### 3. 内存泄漏检测

```python
import gc
import psutil
import os

def detect_memory_leak():
    """检测内存泄漏"""
    process = psutil.Process(os.getpid())

    # 记录初始内存
    initial_memory = process.memory_info().rss / 1024 / 1024

    # 执行一些操作
    for i in range(1000):
        data = [0] * 10000  # 创建大对象
        # 处理数据...
        del data  # 删除引用

    # 强制垃圾回收
    gc.collect()

    # 检查内存使用
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory

    print(f"初始内存: {initial_memory:.1f} MB")
    print(f"最终内存: {final_memory:.1f} MB")
    print(f"内存增加: {memory_increase:.1f} MB")

    if memory_increase > 50:  # 50MB 阈值
        print("警告: 可能存在内存泄漏")
        return True

    return False
```

## 🔧 配置问题

### 1. 环境变量配置

```bash
# SAGE Flow 相关
export SAGE_FLOW_HOME=/path/to/sage
export PYTHONPATH=$PYTHONPATH:$SAGE_FLOW_HOME/packages

# Kafka 相关
export KAFKA_BROKERS=localhost:9092,localhost:9093
export KAFKA_TOPIC=sage_flow_input

# 系统相关
export OMP_NUM_THREADS=4  # OpenMP 线程数
export MKL_NUM_THREADS=4  # MKL 线程数
```

### 2. Python 路径配置

```python
# 在脚本开头添加
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'packages'))

# 或者使用环境变量
sage_home = os.environ.get('SAGE_FLOW_HOME')
if sage_home:
    sys.path.insert(0, os.path.join(sage_home, 'packages'))
```

### 3. 日志配置

```python
import logging
import logging.config

# 日志配置
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'sage_flow.log',
            'formatter': 'standard',
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
}

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)
```

## 🚀 高级调试技巧

### 1. 使用调试器

```python
import pdb

def problematic_function():
    # 设置断点
    pdb.set_trace()

    # 你的代码
    result = process_data()
    return result

# 或者使用更现代的调试器
import ipdb
ipdb.set_trace()
```

### 2. 性能分析

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # 执行要分析的代码
    result = your_function()

    profiler.disable()

    # 输出分析结果
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # 显示前20个最耗时的函数

    return result
```

### 3. 内存分析

```python
import tracemalloc

def memory_analysis():
    tracemalloc.start()

    # 执行代码
    your_function()

    # 获取内存使用快照
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("内存使用最多的行:")
    for stat in top_stats[:10]:
        print(stat)
```

## 📞 获取帮助

### 1. 社区支持

- GitHub Issues: 报告 bug 和请求功能
- 讨论论坛: 与其他用户交流
- 邮件列表: 订阅更新通知

### 2. 诊断信息收集

```bash
# 收集系统信息
uname -a
python --version
pip list | grep -E "(sage|psutil|numpy)"

# 收集日志
tail -n 100 sage_flow_debug.log

# 收集性能指标
python -c "
import psutil
print('CPU 核心数:', psutil.cpu_count())
print('总内存:', psutil.virtual_memory().total / 1024 / 1024 / 1024, 'GB')
print('磁盘使用:', psutil.disk_usage('/').percent, '%')
"
```

### 3. 问题报告模板

提交问题时，请包含以下信息：

```
**环境信息:**
- OS: [e.g., Ubuntu 20.04]
- Python 版本: [e.g., 3.8.5]
- SAGE Flow 版本: [e.g., 1.0.0]

**问题描述:**
[详细描述问题]

**重现步骤:**
1. [步骤1]
2. [步骤2]
3. [步骤3]

**预期行为:**
[期望的结果]

**实际行为:**
[实际的结果]

**错误日志:**
```
[粘贴相关错误日志]
```

**附加信息:**
[任何其他相关信息]
```

## 📚 相关资源

- [用户指南](README.md)
- [API 参考](api_reference.md)
- [性能调优指南](performance_guide.md)
- [示例代码](../examples/)