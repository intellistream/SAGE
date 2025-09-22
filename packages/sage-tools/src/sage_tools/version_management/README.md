# SAGE 版本管理系统

## 🎯 核心思想

**单一数据源 + 动态加载 = 零维护负担**

所有包从项目根目录的 `_version.py` 动态读取版本信息，不再需要手动维护96个文件中的硬编码版本号。

## 🚀 日常使用

### 发布新版本（唯一需要的操作）
```bash
# 编辑项目根目录的版本文件
nano /home/shuhao/SAGE/_version.py

# 修改版本号
__version__ = "0.2.0"  # 只需要修改这一行！

# 保存 - 完成！所有包自动使用新版本号
```

### 验证更新
```bash
python -c "
import sys
sys.path.insert(0, 'packages/sage/src')
import sage
print(f'当前版本: {sage.__version__}')
"
```

## 📁 文件结构

```
SAGE/
├── _version.py                    # 🎯 版本信息的唯一源头
├── packages/*/src/**/__init__.py  # 动态加载版本（96个文件）
└── tools/version-management/
    ├── README.md                  # 本文档
    ├── sage_version.py           # 扩展版本管理工具
    └── templates/                # 动态加载模板
```

## 🔧 工作原理

每个包的 `__init__.py` 包含动态加载逻辑：

```python
def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 计算到项目根目录的路径
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent  # 根据层级调整
    version_file = root_dir / "_version.py"
    
    # 动态执行 _version.py 获取信息
    if version_file.exists():
        version_globals = {}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return {
            'version': version_globals.get('__version__', '0.1.4'),
            'author': version_globals.get('__author__', 'SAGE Team'),
            'email': version_globals.get('__email__', 'shuhao_zhang@hust.edu.cn')
        }
    
    # 容错：找不到文件时使用默认值
    return {'version': '0.1.4', 'author': 'SAGE Team', 'email': 'shuhao_zhang@hust.edu.cn'}

# 加载并设置模块属性
_info = _load_version()
__version__ = _info['version']
__author__ = _info['author']
__email__ = _info['email']
```

## 🛠️ 扩展工具

如需更复杂的版本管理操作，可使用 `sage_version.py`：

```bash
# 显示当前版本信息
python sage_version.py show

# 设置新版本（推荐直接编辑 _version.py）
python sage_version.py set 0.2.0

# 更新项目元数据（邮箱、作者等）
python sage_version.py update-info

# 检查项目信息一致性
python sage_version.py check
```

## ✅ 解决的问题

**之前的痛点**:
- 🔴 96个文件中硬编码版本号
- 🔴 发布新版本需要手动查找替换
- 🔴 容易遗漏或产生版本不一致
- 🔴 维护负担重

**现在的优势**:
- ✅ 单一数据源，一处修改全局生效
- ✅ 动态加载，无需手动维护
- ✅ 容错设计，找不到文件时使用默认值
- ✅ 零维护负担

## 🎉 部署状态

- ✅ **动态版本加载系统已部署**
- ✅ **96个 `__init__.py` 文件已更新**
- ✅ **硬编码版本号已完全消除**
- ✅ **系统测试通过，运行正常**

---

**现在发布新版本只需要修改一个文件：`_version.py`！** 🚀
