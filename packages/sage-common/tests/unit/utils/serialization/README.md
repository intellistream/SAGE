# 序列化测试

本目录包含 sage-common 包中序列化功能的完整测试套件。

## 测试文件说明

### test_dill_reference_integrity.py
专门测试对象引用完整性的测试文件，主要验证 **GitHub issue #254** 的修复。

**修复的问题：**
在复杂的对象引用结构中（如 A->B,C B->D C->D），序列化前共享的对象在反序列化后变成了不同的对象实例，破坏了引用完整性。

**测试场景：**
- 基本共享引用（issue #254 原始场景）
- 循环引用处理
- 多个共享对象
- 列表/字典中的共享对象
- 深度嵌套的共享结构

### test_dill_basic.py
通用的序列化功能测试，包括：
- 基本数据类型序列化
- 复杂对象序列化
- 属性过滤（include/exclude）
- 黑名单对象排除
- 嵌套对象处理
- 错误处理

## 运行测试

在 sage-common 包根目录下运行：

```bash
# 运行所有序列化测试
python -m pytest tests/unit/utils/serialization/ -v

# 只运行引用完整性测试
python -m pytest tests/unit/utils/serialization/test_dill_reference_integrity.py -v

# 只运行基本功能测试
python -m pytest tests/unit/utils/serialization/test_dill_basic.py -v
```

## 修复详情

### 问题原因
在 `_preprocess_for_dill()` 函数中，处理复杂对象时使用了 `obj_class.__new__(obj_class)` 创建新实例，每次遇到共享对象时都会创建新的实例，导致引用去重失效。

### 解决方案
1. **对象映射表**：添加 `_object_map` 参数，维护原始对象ID到新对象的映射关系
2. **引用复用**：在创建新对象之前，先检查映射表中是否已存在对应的新对象
3. **循环引用处理**：正确处理循环引用场景，确保不会无限递归

### 修复的核心代码
```python
def _preprocess_for_dill(obj, _seen=None, _object_map=None):
    # 检查是否已经处理过这个对象（引用去重）
    if obj_id in _object_map:
        return _object_map[obj_id]
    
    # 创建新对象并加入映射表
    cleaned_obj = obj_class.__new__(obj_class)
    _object_map[obj_id] = cleaned_obj
    
    # ... 递归处理属性
```

这确保了相同的原始对象始终映射到同一个新对象，保持引用完整性。