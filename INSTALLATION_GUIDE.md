# SAGE 安装指南

## 问题说明

使用 `pip install .` 时，C源代码和共享库文件默认不会被包含在安装包中，这是因为：

1. **setuptools 默认行为**：只包含 Python 源文件
2. **缺少 MANIFEST.in**：没有明确告诉 setuptools 包含哪些非 Python 文件
3. **C扩展配置缺失**：setup.py 中没有配置 C 扩展编译

## 解决方案

### 1. 开发环境安装（推荐）

```bash
# 预编译C库
python3 pre_build.py

# 安装开发模式（代码修改立即生效）
pip install -e .
```

### 2. 生产环境安装

```bash
# 预编译C库
python3 pre_build.py

# 正常安装
pip install .
```

### 3. 从源码完整安装

```bash
# 清理之前的安装
pip uninstall sage -y

# 确保有编译工具
sudo apt-get install build-essential  # Ubuntu/Debian
# 或
yum install gcc make  # CentOS/RHEL

# 预编译
python3 pre_build.py

# 安装
pip install .
```

## 文件说明

### MANIFEST.in
告诉 setuptools 包含哪些非 Python 文件：
- C 源代码 (`*.c`, `*.h`)
- 编译脚本 (`Makefile`, `build.sh`)
- 预编译库 (`*.so`)
- 配置文件和文档

### setup.py 修改
1. **添加 C 扩展支持**：`build_c_extension()` 函数
2. **增强 package_data**：包含 mmap_queue 的所有必要文件
3. **自动编译**：尝试在安装时编译 C 库

### sage_queue.py 修改
增强库加载逻辑，支持：
- 开发环境路径
- 安装后的包路径
- 系统库路径
- 更详细的错误信息

## 验证安装

```python
# 测试导入
from sage_utils.mmap_queue import SageQueue

# 创建测试队列
queue = SageQueue("test_queue")
queue.put("hello")
print(queue.get())  # 应该输出: hello
queue.close()
```

## 故障排除

### 1. 编译失败
```bash
# 检查编译工具
gcc --version
make --version

# 手动编译
cd sage_utils/mmap_queue
gcc -shared -fPIC -O3 -o ring_buffer.so ring_buffer.c -lpthread
```

### 2. 库加载失败
```bash
# 检查库文件
find . -name "*.so" -type f

# 检查库依赖
ldd sage_utils/mmap_queue/ring_buffer.so
```

### 3. 权限问题
```bash
# 确保文件有执行权限
chmod +x sage_utils/mmap_queue/build.sh
chmod +x pre_build.py
```

## 分发包含C扩展的方法

### 方法1: 源码分发（推荐）
```bash
# 创建源码包
python setup.py sdist

# 用户安装时会自动编译
pip install sage-x.x.x.tar.gz
```

### 方法2: 预编译wheel
```bash
# 构建wheel（包含编译后的库）
pip install wheel
python setup.py bdist_wheel

# 分发wheel文件
pip install sage-x.x.x-py3-none-linux_x86_64.whl
```

### 方法3: 多平台wheel
```bash
# 使用cibuildwheel构建多平台wheel
pip install cibuildwheel
cibuildwheel --platform linux
```

## 最佳实践

1. **开发阶段**：使用 `pip install -e .` 安装开发模式
2. **CI/CD**：在构建脚本中加入 `pre_build.py`
3. **分发**：提供源码包，让用户环境编译
4. **文档**：明确说明系统依赖（gcc, pthread等）

## 注意事项

- C库需要pthread支持，确保系统有相应的开发库
- 不同操作系统可能需要不同的编译参数
- wheel包是平台相关的，需要为每个目标平台单独构建
