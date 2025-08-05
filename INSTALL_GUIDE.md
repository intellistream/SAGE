# SAGE 安装指南

## 📦 推荐安装方式

### 快速安装

```bash
# 安装完整 SAGE 框架
pip install intsage
```

### 验证安装

```bash
# 检查安装是否成功
python -c "import sage; print('SAGE 安装成功！版本:', sage.__version__)"
```

## 🚀 详细安装选项

### 从 PyPI 安装

```bash
# 1. 完整框架（推荐）
pip install intsage

# 2. 按需安装
pip install intsage-kernel      # 核心引擎
pip install intsage-userspace   # 用户空间（含示例）
pip install intsage-middleware  # 中间件服务
pip install intsage-dev-toolkit # 开发工具
pip install intsage-frontend    # Web前端
```

### 从源码安装（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 开发环境安装
pip install -e ".[dev]"

# 3. 或者仅安装核心包
pip install -e .
```

## 📚 快速上手

### 基础使用

```python
import sage

# 创建本地执行环境
env = sage.LocalEnvironment()

# 创建数据流
stream = env.from_collection([1, 2, 3, 4, 5])

# 应用转换操作
result = stream.map(lambda x: x * 2).collect()
print(result)  # [2, 4, 6, 8, 10]
```

### 使用内置示例

```python
# 访问教程示例
from sage.examples.tutorials import hello_world

# 访问 RAG 示例
from sage.examples.rag import qa_simple

# 访问智能体示例
from sage.examples.agents import multiagent_app

# 访问流处理示例
from sage.examples.streaming import kafka_query
```

### Web 前端使用

```bash
# 安装前端组件
pip install intsage-frontend

# 启动 Web 界面
sage-web --port 8080
```

## 🔧 开发工具

```bash
# 安装开发工具
pip install intsage-dev-toolkit

# 使用开发工具
sage-dev --help
sage-dev test
sage-dev analyze
```

## ⚡ CLI 工具快速上手

SAGE 提供了用户友好的独立CLI命令：

```bash
# JobManager 管理（支持 tab 补全）
sage-jobmanager start    # 启动 JobManager
sage-jobmanager status   # 查看状态
sage-jobmanager stop     # 停止

# 集群管理
sage-cluster start       # 启动集群
sage-cluster status      # 集群状态
sage-cluster stop        # 停止集群

# 作业管理
sage-job submit my_job.py  # 提交作业
sage-job status            # 查看作业状态
sage-job list              # 列出所有作业

# 其他工具
sage-worker start         # 启动 Worker 节点
sage-head start           # 启动 Head 节点
sage-deploy start         # 启动部署
sage-config show          # 显示配置
```

💡 **提示**: 使用 `sage-<TAB>` 可以查看所有可用的独立命令！
python tools/license/sage_license.py install <your-license-key>

# 3. 安装商业版组件
pip install -r requirements-commercial.txt

# 4. 验证安装
python tools/license/sage_license.py status
```

## 安装选项说明

| 文件 | 用途 | 包含内容 |
|------|------|----------|
| `requirements.txt` | 生产环境 | 核心SAGE包 |
| `requirements-dev.txt` | 开发环境 | 核心包 + 开发工具 |
| `requirements-commercial.txt` | 商业版 | 核心包 + 商业功能 |

## 包结构

```
SAGE/
├── packages/sage/              # 元包
├── packages/sage-kernel/       # 核心引擎
├── packages/sage-middleware/   # 中间件
├── packages/sage-userspace/    # 用户空间
├── packages/sage-tools/        # 工具集
│   ├── sage-cli/              # 命令行工具
│   └── sage-dev-toolkit/      # 开发工具
└── packages/commercial/        # 商业版组件 (需要许可证)
    ├── sage-kernel/
    ├── sage-middleware/
    └── sage-userspace/
```

## 商业版许可证管理

### 为客户生成许可证 (供应商使用)

```bash
# 生成新许可证 (默认365天有效期)
python tools/license/sage_license.py generate "Company ABC"

# 生成指定有效期的许可证
python tools/license/sage_license.py generate "Customer XYZ" 180

# 查看已生成的许可证
python tools/license/sage_license.py list
```

### 许可证安装和管理 (客户使用)

```bash
# 安装许可证
python tools/license/sage_license.py install SAGE-COMM-2025-A1B2-C3D4-E5F6

# 查看许可证状态
python tools/license/sage_license.py status

# 移除许可证
python tools/license/sage_license.py remove
```

## 验证安装

```bash
# 检查核心包
python -c "import sage; print('SAGE installed successfully')"

# 检查CLI工具
sage --version

# 检查商业版许可证 (如果适用)
python tools/license/sage_license.py status
```

## 故障排除

### 常见问题

1. **导入错误**: 确保使用editable install (`-e`)
2. **依赖冲突**: 建议使用虚拟环境
3. **商业版访问**: 检查许可证状态

### 开发者注意事项

- 所有包都使用editable install，修改代码后无需重新安装
- 商业版代码需要有效许可证才能访问
- 使用`requirements-dev.txt`获得最佳开发体验

# 立即测试
python -c "from sage.api import DataStream; ..."
```

### 验证安装
```bash
# 检查安装的包
pip list | grep sage

# 测试导入
python -c "import sage; print('SAGE Ready!')"
```

## 🏢 商业版本

如需商业版本功能，请使用许可管理工具：

```bash
# 安装商业许可
python tools/license/sage_license.py install YOUR-LICENSE-KEY

# 重新安装以获得商业功能
pip install --upgrade --force-reinstall -e .
```

## 💡 常见问题

### Q: 如何切换开发/生产模式？
```bash
# 开发模式 (包含测试工具)
pip install -e ".[dev]"

# 生产模式 (仅核心功能)
pip install -e .
```

### Q: 如何更新依赖？
```bash
# 重新安装所有依赖
pip install --upgrade --force-reinstall -e ".[dev]"
```

### Q: 如何卸载？
```bash
# 卸载SAGE相关包
pip uninstall sage sage-kernel sage-middleware sage-userspace sage-cli sage-dev-toolkit
```

---

**现在安装更简单了！推荐使用 `pip install -e ".[dev]"` 进行开发。** 🎯
