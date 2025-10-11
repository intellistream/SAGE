# SAGE Studio

**SAGE Studio** 是一个独立的低代码 Web UI 包，用于可视化开发和管理 SAGE 数据流水线。

> **版本**: 0.1.0  
> **包名**: `isage-studio`  
> **从 sage-tools 分离**: 2025-10-10

## 🎯 功能特性

- 🎨 **可视化编辑器**: 拖拽式的管道构建界面
- 📊 **实时监控**: 作业执行状态和性能指标
- 🔧 **代码编辑器**: 支持算子的在线编辑和调试
- 📦 **算子管理**: 内置丰富的预定义算子库
- 🚀 **任务管理**: 提交、暂停、恢复和停止作业

## 📦 安装

### 作为 SAGE 的一部分（推荐）

Studio 已包含在 SAGE 默认安装中：

```bash
# 完整安装 SAGE（包括 Studio）
pip install isage

# 或使用快速安装脚本
./quickstart.sh
```

### 独立安装

```bash
# 基础安装
pip install isage-studio

# 包含开发工具
pip install isage-studio[full]
```

### 开发模式安装

```bash
cd packages/sage-studio
pip install -e .
```

## 🚀 使用方式

Studio 通过 `sage` CLI 命令使用（CLI 集成在 `sage-tools` 包中）:

```bash
# 启动 Studio 服务
sage studio start

# 指定端口和主机
sage studio start --port 8080 --host 0.0.0.0

# 开发模式启动
sage studio start --dev

# 查看 Studio 状态
sage studio status

# 停止 Studio 服务
sage studio stop

# 重启 Studio
sage studio restart

# 安装前端依赖（首次使用前）
sage studio install

# 构建前端资源
sage studio build

# 在浏览器中打开
sage studio open

# 查看日志
sage studio logs
sage studio logs --follow  # 实时跟踪
sage studio logs --backend  # 后端日志

# 清理缓存
sage studio clean
```

默认访问地址: `http://localhost:4200`

## 📂 包结构

```
sage-studio/
├── src/sage/studio/
│   ├── __init__.py
│   ├── _version.py
│   ├── studio_manager.py    # 核心管理器
│   ├── config/              # 配置文件
│   │   └── backend/         # 后端 API
│   ├── data/                # 数据和算子定义
│   ├── docs/                # 文档
│   └── frontend/            # Angular 前端应用
├── tests/                   # 测试文件
├── pyproject.toml          # 包配置
└── README.md
```

## 🔧 架构说明

### 包分离设计

Studio 现在是一个独立的包，与 `sage-tools` 分离：

- **sage-studio**: 包含所有 Studio 功能（前端、后端、管理器）
- **sage-tools**: 提供 CLI 命令集成，导入并使用 `sage.studio.studio_manager`
- **sage**: 元包，默认依赖 `isage-studio`

### CLI 集成

虽然 Studio 是独立包，但 CLI 命令仍在 `sage-tools` 中：

```python
# sage-tools/src/sage/tools/cli/commands/studio.py
from sage.studio.studio_manager import StudioManager
```

这样设计的优点：
- ✅ Studio 功能独立，易于维护
- ✅ 可选安装（用户可以不安装 UI）
- ✅ CLI 命令统一在 `sage` 命令下
- ✅ 依赖关系清晰

## 🛠️ 开发

### 前端开发

前端基于 Angular 开发，位于 `frontend/` 目录:

```bash
# 进入前端目录
cd src/sage/studio/frontend

# 安装依赖
npm install

# 启动开发服务器
npm start

# 构建生产版本
npm run build
```

### 后端开发

后端 API 使用 FastAPI:

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_studio_cli.py

# 查看覆盖率
pytest --cov=sage.studio
```

## 📋 依赖关系

### 核心依赖
- `isage-common>=0.1.0` - 通用组件
- `isage-kernel>=0.1.0` - 核心引擎
- `isage-middleware>=0.1.0` - 中间件
- `isage-libs>=0.1.0` - 应用库

### Web 框架
- `fastapi>=0.115,<0.116` - Web 框架
- `uvicorn[standard]>=0.34.0` - ASGI 服务器
- `starlette>=0.40,<0.47` - Web 工具包
- `websockets>=11.0` - WebSocket 支持

### 前端（需要 Node.js）
- Angular 框架（通过 npm 管理）
- 详见 `frontend/package.json`

## 🔄 迁移说明

> **注意**: 如果你之前使用的是 `sage-tools` 中的 Studio，现在它已经移到独立包中。

### 从旧版本迁移

1. **导入路径变更**:
   ```python
   # 旧路径（已废弃）
   # from sage.tools.studio.studio_manager import StudioManager
   
   # 新路径
   from sage.studio.studio_manager import StudioManager
   ```

2. **CLI 命令不变**:
   ```bash
   # CLI 命令完全兼容，无需修改
   sage studio start
   ```

3. **安装方式**:
   ```bash
   # 升级到新版本
   pip install --upgrade isage isage-studio isage-tools
   
   # 或重新运行安装脚本
   ./quickstart.sh
   ```

## 📚 文档

- [Studio 使用指南](docs/STUDIO_GUIDE.md) - 详细使用说明
- [Studio 管理文档](docs/STUDIO_MANAGEMENT.md) - 管理和配置
- [SAGE 主文档](https://intellistream.github.io/SAGE-Pub/) - 完整文档

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE) 文件

---

**开发团队**: IntelliStream Team  
**项目主页**: https://github.com/intellistream/SAGE  
**文档**: https://intellistream.github.io/SAGE-Pub/
