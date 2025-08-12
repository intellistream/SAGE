# SAGE Memory-Mapped Queue 测试套件

这个目录包含了 SAGE Memory-Mapped Queue 的完整测试套件，涵盖功能测试、性能测试、安全测试和集成测试。

## 📁 文件结构

```
tests/
├── __init__.py                         # 测试套件初始化
├── README.md                          # 本文档
├── run_all_tests.py                   # 测试运行器（推荐使用）
├── generate_test_report.py            # 测试报告生成器
│
├── test_quick_validation.py           # 快速验证测试
├── test_basic_functionality.py        # 基本功能测试
├── test_safety.py                     # 安全测试套件
├── test_performance_benchmark.py      # 性能基准测试
├── test_comprehensive.py              # 综合测试套件
├── test_multiprocess_concurrent.py    # 多进程并发测试
└── test_ray_integration.py            # Ray Actor集成测试
```

## 🚀 快速开始

### 前置条件

1. **编译C库**（必需）:
   ```bash
   cd ..  # 回到 sage.utils/mmap_queue 目录
   ./build.sh
   ```

2. **安装依赖**（可选，用于部分测试）:
   ```bash
   pip install psutil ray
   ```

### 运行所有测试

使用测试运行器（推荐）:
```bash
python run_all_tests.py
```

这将：
- 按顺序运行所有测试模块
- 显示详细的执行结果
- 生成测试汇总报告
- 保存结果到JSON文件
- 自动生成详细的测试报告

### 运行单个测试

```bash
# 快速验证
python test_quick_validation.py

# 基本功能测试
python test_basic_functionality.py

# 安全测试
python test_safety.py

# 性能测试
python test_performance_benchmark.py

# 综合测试
python test_comprehensive.py

# 多进程测试
python test_multiprocess_concurrent.py

# Ray集成测试
python test_ray_integration.py
```

## 📋 测试模块说明

### 1. test_quick_validation.py
**快速验证测试** - 用于验证基本安装和配置
- 验证库导入
- 基本队列操作
- 状态检查
- 统计信息获取

**运行时间**: ~5秒

### 2. test_basic_functionality.py  
**基本功能测试** - 核心功能的全面测试
- 基本队列操作 (put/get)
- 队列状态检查 (empty/full/qsize)
- 队列引用传递
- 多进程通信
- 性能测试

**运行时间**: ~30秒

### 3. test_safety.py
**安全测试套件** - 测试边界条件和错误处理
- 队列容量限制
- 数据完整性验证（31种数据类型）
- 错误条件处理
- 线程安全测试
- 资源清理测试

**运行时间**: ~45秒

### 4. test_performance_benchmark.py
**性能基准测试** - 专业的性能评估
- 吞吐量测试（不同消息大小）
- 延迟测试（统计分析）
- 并发访问性能
- 内存效率测试
- 多进程性能测试

**运行时间**: ~60秒

### 5. test_comprehensive.py
**综合测试套件** - 高级功能和边界条件
- 边界条件测试
- 并发访问测试
- 内存泄漏测试
- 持久性测试
- 压力性能测试
- 多进程健壮性测试

**运行时间**: ~90秒

### 6. test_multiprocess_concurrent.py
**多进程并发测试** - 复杂的多进程场景
- 多进程生产者-消费者模式
- 并发读写混合操作
- 队列引用跨进程传递
- 进程间通信稳定性

**运行时间**: ~60秒

### 7. test_ray_integration.py
**Ray Actor集成测试** - 分布式计算框架集成
- 简单生产者-消费者模式
- 多Actor并发通信
- 流水线处理模式
- Actor间队列引用传递

**运行时间**: ~45秒（需要安装Ray）

## 📊 测试报告

### 自动生成的报告文件

运行测试后会生成以下文件：

- `test_results_<timestamp>.json` - 详细的测试结果数据
- `sage_queue_test_report_<timestamp>.json` - 完整的测试报告（JSON格式）
- `sage_queue_test_report_<timestamp>.md` - 可读的测试报告（Markdown格式）

### 手动生成报告

```bash
python generate_test_report.py
```

## ⚡ 性能指标

基于我们的测试结果，SAGE Memory-Mapped Queue 的性能表现：

### 吞吐量
- **64字节消息**: 304K msg/s 写入, 203K msg/s 读取
- **256字节消息**: 279K msg/s 写入, 203K msg/s 读取  
- **1KB消息**: 233K msg/s 写入, 188K msg/s 读取
- **4KB消息**: 132K msg/s 写入, 161K msg/s 读取, **516 MB/s 带宽**

### 延迟
- **写入延迟**: 平均 0.003ms
- **读取延迟**: 平均 0.005ms
- **往返延迟**: 平均 0.008ms, P95 0.013ms

### 内存效率
- **大缓冲区利用率**: 接近 100%
- **存储效率**: ~89%

## 🔧 故障排查

### 常见问题

1. **ImportError: 找不到C库**
   ```
   解决方案: 运行 ../build.sh 编译C库
   ```

2. **测试超时**
   ```
   解决方案: 检查系统负载，增加超时时间
   ```

3. **多进程测试失败**
   ```
   解决方案: 确保有足够的共享内存和文件描述符限制
   ```

4. **Ray测试失败**
   ```
   解决方案: pip install ray
   ```

### 调试模式

设置环境变量启用详细输出：
```bash
export SAGE_QUEUE_DEBUG=1
python test_basic_functionality.py
```

### 清理共享内存

如果测试异常中断，可能需要清理共享内存：
```bash
# 查看共享内存
ls /dev/shm/sage_*

# 手动清理（谨慎操作）
rm /dev/shm/sage_*
```

## 📈 持续集成

### CI/CD 集成

在CI环境中运行测试：
```bash
# 只运行必需的测试
python test_quick_validation.py
python test_basic_functionality.py
python test_safety.py

# 或使用测试运行器（推荐）
python run_all_tests.py
```

### 性能回归测试

定期运行性能测试并比较结果：
```bash
python test_performance_benchmark.py > performance_$(date +%Y%m%d).log
```

## 🎯 测试覆盖范围

我们的测试套件覆盖了：

- ✅ **功能完整性**: 100% API覆盖
- ✅ **数据类型支持**: 31种Python数据类型
- ✅ **并发安全**: 多线程、多进程测试
- ✅ **性能验证**: 吞吐量、延迟、内存效率
- ✅ **错误处理**: 超时、异常、边界条件
- ✅ **资源管理**: 内存泄漏、资源清理
- ✅ **集成测试**: Ray Actor分布式场景
- ✅ **平台兼容**: Linux共享内存机制

## 📞 支持

如果遇到测试相关问题：

1. 查看测试输出中的错误信息
2. 检查 `test_results_<timestamp>.json` 文件
3. 运行单个测试模块进行调试
4. 确保满足所有前置条件

---

**注意**: 这些测试需要在Linux环境下运行，因为依赖于POSIX共享内存机制。
