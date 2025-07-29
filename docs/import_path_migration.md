# SAGE 导入路径迁移总结

## 🔄 路径变更概述

由于 `mmap_queue` 重命名为 `sage_queue` 并重新组织目录结构，所有相关的导入路径都需要更新。

## 📝 更改清单

### 1. 目录结构变化
```
旧路径: sage_ext/mmap_queue/
新路径: sage_ext/sage_queue/python/
```

### 2. 导入路径变化

#### 核心队列类
```python
# 旧导入
from sage_ext.mmap_queue.sage_queue import SageQueue
from sage_ext.mmap_queue import SageQueue

# 新导入  
from sage_ext.sage_queue.python.sage_queue import SageQueue
```

#### 后端名称变化
```python
# 旧后端名称
"sage_mmap_queue"

# 新后端名称
"sage_queue"
```

### 3. 修改的文件

#### 运行时模块
- ✅ `sage/runtime/router/router.py`
- ✅ `sage/runtime/service/base_service_task.py`  
- ✅ `sage/runtime/service/service_caller.py`
- ✅ `sage/runtime/task/ray_task.py`
- ✅ `sage/runtime/task/local_task.py`
- ✅ `sage/runtime/task/base_task.py`

#### 工具模块
- ✅ `sage/utils/queue_tool.py`
- ✅ `sage/utils/queue_adapter.py`
- ✅ `sage/utils/queue_config.py`

#### 扩展模块
- ✅ `sage_ext/sage_queue/python/sage_queue.py`
- ✅ `sage_ext/sage_queue/python/debug_queue.py`
- ✅ `sage_ext/sage_queue/python/sage_queue_manager.py`
- ✅ `sage_ext/sage_queue/python/sage_demo.py`

### 4. 环境变量映射

为了向后兼容，添加了映射逻辑：
```python
# 环境变量值 -> 实际后端
'sage' -> 'sage_queue'
'ray' -> 'ray_queue'  
'python' -> 'python_queue'
```

### 5. 后端检测更新

```python
# queue_adapter.py 中的变化
info["current_backend"] = "sage_queue"  # 旧: "sage_mmap_queue"
info["backends"].append("sage_queue")   # 旧: "sage_mmap_queue"
```

## 🔧 配置更新

### install.py
环境变量设置保持不变：
```bash
SAGE_QUEUE_BACKEND=sage  # minimal: ray, full: sage
```

### queue_config.py  
```python
backend: str = "auto"  # auto, sage_queue, ray_queue, python_queue
```

## ✅ 向后兼容性

1. **环境变量**: `SAGE_QUEUE_BACKEND=sage` 继续工作
2. **后端检测**: 自动映射到新的后端名称
3. **错误信息**: 更新为使用新名称

## 🚀 验证测试

### 基础导入测试
```python
from sage_ext.sage_queue.python.sage_queue import SageQueue
from sage.utils.queue_adapter import create_queue, get_queue_backend_info
```

### 后端创建测试
```python
# 这些都应该工作
queue1 = create_queue("sage_queue")     # 新格式
queue2 = create_queue("sage")           # 映射格式
queue3 = create_queue()                 # 自动选择
```

## 📋 剩余任务

1. **测试验证**: 确保所有导入路径在实际运行时正常工作
2. **文档更新**: 更新用户文档中的导入示例
3. **示例代码**: 更新所有示例代码使用新路径
4. **弃用警告**: 考虑为旧路径添加弃用警告（未来版本）

## 🎯 总结

- ✅ **完成**: 所有代码文件的导入路径已更新
- ✅ **兼容**: 保持环境变量和配置的向后兼容性  
- ✅ **一致**: 统一使用 `sage_queue` 作为后端名称
- ✅ **清晰**: 新的目录结构更加清晰和标准化

新的导入路径现在与重新组织的 CMake 构建系统保持一致！
