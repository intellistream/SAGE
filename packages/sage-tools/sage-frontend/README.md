# SAGE Frontend

SAGE Framework的Web前端和仪表板界面组件，提供可视化的数据处理管道管理和监控功能。

## 概述

SAGE Frontend 是一个完整的Web应用解决方案，包含：

- **Dashboard**: 基于Angular的现代化Web仪表板
- **API Server**: 基于FastAPI的后端服务器
- **Operators**: 数据处理操作符的Web界面管理
- **可视化**: 支持多种数据可视化和管道监控功能

## 功能特性

### 🌐 Web仪表板
- 现代化的Angular前端界面
- 响应式设计，支持多设备访问
- 实时数据监控和可视化
- 交互式管道编辑器

### 🚀 FastAPI后端
- 高性能的异步API服务器
- RESTful API设计
- WebSocket实时通信支持
- 文件上传和处理

### 📊 数据可视化
- 支持多种图表类型
- 实时数据流监控
- 管道执行状态可视化
- 性能指标展示

### 🔧 操作符管理
- 可视化操作符配置
- 拖拽式管道构建
- 参数调优界面
- 批处理任务管理

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-tools/sage-frontend

# 安装Python依赖
pip install -e .

# 安装前端依赖（需要Node.js和npm）
cd dashboard
npm install
npm run build
cd ..
```

### 使用pip安装

```bash
pip install sage-frontend
```

## 快速开始

### 启动后端服务器

```bash
# 使用命令行工具启动
sage-frontend --host 0.0.0.0 --port 8080

# 或者直接运行Python模块
python -m sage_frontend.sage_server.main --host 0.0.0.0 --port 8080
```

### 开发模式启动

```bash
# 启动后端开发服务器
cd sage_server
python main.py --host 0.0.0.0 --port 8080 --log-level debug

# 启动前端开发服务器（另一个终端）
cd dashboard
npm start
```

### 访问界面

- **Web仪表板**: http://localhost:4200
- **API文档**: http://localhost:8080/docs
- **API Redoc**: http://localhost:8080/redoc

## 项目结构

```
sage-frontend/
├── dashboard/              # Angular前端项目
│   ├── src/               # Angular源码
│   ├── package.json       # 前端依赖配置
│   └── angular.json       # Angular配置
├── sage_server/           # FastAPI后端
│   ├── main.py           # 主应用入口
│   ├── routers/          # API路由模块
│   ├── data/             # 数据文件
│   └── config.ini        # 服务器配置
├── operators/             # 操作符定义
└── pyproject.toml        # Python包配置
```

## 配置

### 环境变量

创建 `.env` 文件配置环境变量：

```env
# 服务器配置
HOST=0.0.0.0
PORT=8080
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///./sage.db

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 服务器配置

编辑 `sage_server/config.ini` 文件：

```ini
[server]
host = 0.0.0.0
port = 8080
debug = true

[cors]
allow_origins = ["http://localhost:4200"]
allow_methods = ["*"]
allow_headers = ["*"]
```

## API 端点

### 主要API路由

- `/api/job-info` - 作业信息管理
- `/api/batch-info` - 批处理信息
- `/api/operators` - 操作符管理
- `/api/pipeline` - 管道配置
- `/api/upload` - 文件上传
- `/api/signal` - 信号处理

### WebSocket端点

- `/ws/pipeline` - 管道状态实时更新
- `/ws/logs` - 日志实时推送

## 开发

### 前端开发

```bash
cd dashboard

# 安装依赖
npm install

# 启动开发服务器
ng serve --host 0.0.0.0 --port 4200

# 构建生产版本
ng build --prod
```

### 后端开发

```bash
cd sage_server

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black .
isort .

# 类型检查
mypy .
```

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t sage-frontend .

# 运行容器
docker run -p 8080:8080 sage-frontend
```

### 生产部署

```bash
# 安装生产依赖
pip install sage-frontend[monitoring,security]

# 使用Gunicorn部署
gunicorn sage_frontend.sage_server.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8080
```

## 可选依赖

```bash
# 安装可视化增强功能
pip install sage-frontend[visualization]

# 安装安全增强功能
pip install sage-frontend[security]

# 安装监控功能
pip install sage-frontend[monitoring]

# 安装所有可选功能
pip install sage-frontend[dev,visualization,security,monitoring]
```

## 贡献

欢迎贡献代码！请参考以下步骤：

1. Fork此仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用MIT许可证。详情请见 [LICENSE](../../../LICENSE) 文件。

## 支持

- **文档**: https://sage-docs.intellistream.cc/frontend
- **问题反馈**: https://github.com/intellistream/SAGE/issues
- **邮箱**: sage@intellistream.cc

## 相关项目

- [sage-kernel](../sage-kernel) - SAGE核心处理引擎
- [sage-cli](../sage-cli) - SAGE命令行工具
- [sage-dev-toolkit](../sage-dev-toolkit) - SAGE开发工具包
