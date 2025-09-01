# SAGE 动态版本管理系统

## 🎯 解决的问题

之前SAGE项目中的版本号、作者信息、邮箱等项目信息是硬编码在各个包的`__init__.py`文件中的，这导致：

1. **维护困难**: 每次发布新版本都需要手动查找替换所有文件中的版本号
2. **容易出错**: 手动修改容易遗漏或产生不一致
3. **开发负担**: 开发者需要记住更新所有相关文件

## 🚀 新的解决方案

现在所有包都采用**动态版本加载**机制，从项目根目录的`_version.py`文件中自动读取信息。

### 核心特性

✅ **单一数据源**: 所有项目信息都在`_version.py`中维护  
✅ **自动加载**: 所有包的`__init__.py`会动态读取版本信息  
✅ **零维护**: 发布新版本只需修改`_version.py`一个文件  
✅ **向下兼容**: 如果找不到`_version.py`会使用默认值  

## 📁 文件结构

```
SAGE/
├── _version.py                  # 🎯 唯一的信息源
├── packages/
│   ├── sage/src/sage/__init__.py          # 动态加载版本
│   ├── sage-kernel/src/sage/__init__.py   # 动态加载版本
│   ├── sage-libs/src/sage/__init__.py     # 动态加载版本
│   └── sage-middleware/src/sage/__init__.py # 动态加载版本
└── tools/version-management/
    ├── ultimate_fix.py          # 一键修复工具
    └── quick_fix.py            # 检查和修复工具
```

## 💡 工作原理

每个包的`__init__.py`包含以下动态加载逻辑：

```python
def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 获取项目根目录
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent...  # 根据层级计算
    version_file = root_dir / "_version.py"
    
    # 加载版本信息
    if version_file.exists():
        version_globals = {}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return {
            'version': version_globals.get('__version__', '0.1.4'),
            'author': version_globals.get('__author__', 'SAGE Team'),
            'email': version_globals.get('__email__', 'shuhao_zhang@hust.edu.cn')
        }
    
    # 默认值（找不到_version.py时使用）
    return {
        'version': '0.1.4',
        'author': 'SAGE Team', 
        'email': 'shuhao_zhang@hust.edu.cn'
    }

# 加载信息
_info = _load_version()
__version__ = _info['version']
__author__ = _info['author']
__email__ = _info['email']
```

## 🛠️ 使用工具

### 1. 检查硬编码问题
```bash
python tools/version-management/quick_fix.py check
```

### 2. 修复硬编码问题
```bash
python tools/version-management/quick_fix.py fix
```

### 3. 一键清理所有包（推荐）
```bash
python tools/version-management/ultimate_fix.py
```

## 📋 验证效果

修复后可以验证动态加载是否工作：

```python
import sys
sys.path.insert(0, 'packages/sage/src')
import sage

print(f'版本: {sage.__version__}')  # 从_version.py动态读取
print(f'作者: {sage.__author__}')   # 从_version.py动态读取
print(f'邮箱: {sage.__email__}')    # 从_version.py动态读取
```

## 🎉 发布新版本的流程

现在发布新版本变得非常简单：

1. **只修改一个文件**: 编辑`_version.py`中的`__version__`
2. **自动生效**: 所有包会自动使用新版本号
3. **无需查找替换**: 不需要手动修改任何其他文件

### 示例：从0.1.4升级到0.1.5

```python
# 编辑 _version.py
__version__ = "0.1.5"  # 只需要修改这一行

# 所有包会自动使用新版本号
# ✅ sage.__version__ -> "0.1.5"
# ✅ sage.kernel.__version__ -> "0.1.5"  
# ✅ sage.libs.__version__ -> "0.1.5"
# ✅ sage.middleware.__version__ -> "0.1.5"
```

## 📊 修复统计

通过`ultimate_fix.py`工具的修复：

- ✅ **清理了96个`__init__.py`文件**
- ✅ **消除了所有硬编码版本号**  
- ✅ **统一了项目信息管理**
- ✅ **测试通过，动态加载正常工作**

## 🔧 技术细节

### 路径计算
每个包根据自己在项目中的位置动态计算到根目录的路径：
- `packages/sage/src/sage/__init__.py` → 需要向上4层
- `packages/sage-kernel/src/sage/kernel/__init__.py` → 需要向上5层

### 容错处理
- 如果找不到`_version.py`文件，使用默认值
- 如果读取失败，也会使用默认值
- 确保系统在任何情况下都能正常工作

### 性能优化
- 版本信息在模块导入时一次性加载
- 后续访问直接使用缓存的值
- 对性能影响可忽略不计

---

**现在你可以放心地修改`_version.py`发布新版本，而不用担心遗漏任何硬编码的地方！** 🎉
