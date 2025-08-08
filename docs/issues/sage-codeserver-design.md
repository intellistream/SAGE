# SAGE 源代码服务器 (SAGE CodeServer) 设计方案

## 📋 背景与目标

SAGE项目在 `scripts/` 目录中积累了多个高质量的源代码分析和管理工具，包括：

- **测试工具**: `test_runner.py` - 智能测试运行器，支持并行测试和差异化测试
- **依赖分析**: `advanced_dependency_analyzer_with_sage_mapping.py` - 高级依赖关系分析器
- **包管理**: `sage-package-manager.py` - 包管理和安装工具
- **代码检查**: `check_package_dependencies.py` - 包依赖检查工具
- **开发工具**: `setup-ide-support.py` - IDE支持配置工具

目前这些工具相互独立，缺乏统一的入口和协调机制。我们需要构建一个**SAGE源代码服务器**，将这些功能整合成一个统一的Web服务，提供：

- 🚀 一键测试运行和报告生成
- 📊 实时依赖关系分析和可视化
- 📦 包管理和构建状态监控
- 🔍 代码质量检查和建议
- 📈 持续集成支持和历史追踪

## 🏗️ 系统架构设计

### 核心组件

```
SAGE CodeServer
├── 🌐 Web API Server (FastAPI)
│   ├── /api/test        - 测试管理API
│   ├── /api/analysis    - 依赖分析API  
│   ├── /api/packages    - 包管理API
│   ├── /api/status      - 系统状态API
│   └── /api/reports     - 报告生成API
│
├── 🖥️ Web Dashboard (React/Vue)
│   ├── 测试中心        - 运行测试、查看结果
│   ├── 依赖图谱        - 可视化依赖关系
│   ├── 包管理中心      - 包状态、构建监控
│   ├── 代码质量        - 质量检查报告
│   └── 系统监控        - 资源使用、历史数据
│
├── 🔧 Task Engine (Celery/RQ)
│   ├── 测试任务调度
│   ├── 依赖分析任务
│   ├── 包构建任务
│   └── 报告生成任务
│
├── 💾 Data Layer
│   ├── SQLite/PostgreSQL - 存储分析结果
│   ├── Redis - 任务队列和缓存
│   └── 文件存储 - 测试报告、日志文件
│
└── 🧩 Tool Integrations
    ├── TestRunner - 集成现有test_runner.py
    ├── DependencyAnalyzer - 集成依赖分析器
    ├── PackageManager - 集成包管理器
    └── CodeChecker - 集成代码检查工具
```

### 技术栈选择

**后端技术栈:**
- **FastAPI** - 现代Python Web框架，自动生成API文档
- **Celery + Redis** - 异步任务队列，处理耗时操作
- **SQLAlchemy + SQLite/PostgreSQL** - ORM和数据存储
- **Pydantic** - 数据验证和序列化

**前端技术栈:**
- **React + TypeScript** - 现代前端框架
- **Ant Design/Material-UI** - UI组件库
- **D3.js/Vis.js** - 依赖关系图可视化
- **Chart.js** - 数据图表展示

## 🚀 功能特性设计

### 1. 测试中心 (Test Center)

**功能特性:**
- ✅ 一键运行全量测试或智能差异测试
- ✅ 实时显示测试进度和结果
- ✅ 支持包级别和文件级别的测试选择
- ✅ 测试历史记录和趋势分析
- ✅ 失败测试的详细错误信息和建议

**API设计:**
```python
POST /api/test/run
{
    "type": "all|diff|package",
    "target": "sage-kernel",  # 可选，指定包名
    "base_branch": "main",  # diff模式的基准分支
    "parallel_workers": 4
}

GET /api/test/status/{task_id}
GET /api/test/results/{task_id}
GET /api/test/history?package=sage-kernel&limit=50
```

### 2. 依赖分析中心 (Dependency Analysis)

**功能特性:**
- 📊 实时生成包依赖关系图
- 🔍 检测循环依赖和潜在问题
- 📈 分析依赖健康度和复杂度
- 🎯 提供重构建议和优化方案
- 📋 导出多种格式的分析报告

**可视化功能:**
- 交互式依赖关系图（支持缩放、过滤）
- 包结构树状图
- 循环依赖高亮显示
- 依赖深度热力图

**API设计:**
```python
POST /api/analysis/dependencies
{
    "scope": "all|package",
    "package": "sage-kernel",  # 可选
    "include_external": true
}

GET /api/analysis/circular-deps
GET /api/analysis/graph-data?format=json|graphml
```

### 3. 包管理中心 (Package Management)

**功能特性:**
- 📦 显示所有包的状态和版本信息
- 🔧 一键安装、构建、清理包
- 📋 包依赖关系树显示
- 🚀 支持批量操作和构建流水线
- 📊 构建历史和性能监控

**API设计:**
```python
GET /api/packages/list
POST /api/packages/install
{
    "packages": ["sage-kernel", "sage-utils"],
    "mode": "development|production"
}

POST /api/packages/build/{package_name}
GET /api/packages/status/{package_name}
```

### 4. 代码质量中心 (Code Quality)

**功能特性:**
- 🔍 静态代码分析（集成pylint、mypy、black）
- 📏 代码复杂度和覆盖率统计
- 🎯 代码规范检查和自动修复建议
- 📈 质量趋势分析和历史对比
- 🚨 质量问题预警和通知

### 5. 系统监控 (System Monitoring)

**功能特性:**
- 📊 实时系统资源监控（CPU、内存、磁盘）
- 📈 任务执行统计和性能分析
- 🔔 异常情况报警和通知
- 📋 操作审计日志
- 🎯 性能优化建议

## 🛠️ 实现计划

### Phase 1: 核心框架搭建 (Week 1-2)
- [ ] FastAPI服务器基础架构
- [ ] 数据库模型设计和迁移
- [ ] 任务队列系统集成
- [ ] 基础Web界面框架

### Phase 2: 测试中心实现 (Week 3-4)
- [ ] 集成现有test_runner.py
- [ ] 测试任务API和调度
- [ ] 测试结果存储和查询
- [ ] 测试中心前端界面

### Phase 3: 依赖分析功能 (Week 5-6)
- [ ] 集成dependency_analyzer
- [ ] 依赖关系图生成API
- [ ] 可视化组件开发
- [ ] 循环依赖检测和报告

### Phase 4: 包管理集成 (Week 7-8)
- [ ] 集成sage-package-manager
- [ ] 包操作API和界面
- [ ] 构建状态监控
- [ ] 批量操作支持

### Phase 5: 代码质量和监控 (Week 9-10)
- [ ] 代码质量检查集成
- [ ] 系统监控功能
- [ ] 报告生成和导出
- [ ] 通知和预警系统

### Phase 6: 优化和部署 (Week 11-12)
- [ ] 性能优化和压力测试
- [ ] Docker容器化部署
- [ ] CI/CD集成配置
- [ ] 文档和用户指南

## 📁 项目结构

```
packages/sage-codeserver/
├── src/sage/codeserver/
│   ├── __init__.py
│   ├── api/                 # FastAPI路由
│   │   ├── __init__.py
│   │   ├── test.py         # 测试相关API
│   │   ├── analysis.py     # 依赖分析API
│   │   ├── packages.py     # 包管理API
│   │   └── monitoring.py   # 监控API
│   ├── core/               # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── test_runner.py  # 测试运行核心
│   │   ├── analyzer.py     # 依赖分析核心
│   │   └── package_mgr.py  # 包管理核心
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   ├── test.py
│   │   ├── analysis.py
│   │   └── package.py
│   ├── tasks/              # 异步任务
│   │   ├── __init__.py
│   │   ├── test_tasks.py
│   │   └── analysis_tasks.py
│   ├── utils/              # 工具函数
│   │   ├── __init__.py
│   │   ├── integrations.py # 现有工具集成
│   │   └── helpers.py
│   └── static/             # 静态资源
│       ├── index.html
│       ├── css/
│       └── js/
├── tests/                  # 测试文件
├── docker/                 # Docker配置
├── docs/                   # 文档
├── requirements.txt
└── pyproject.toml
```

## 🎯 价值与效益

### 开发效率提升
- **统一入口**: 一个界面管理所有开发工具
- **自动化**: 减少手动执行重复任务的时间
- **可视化**: 直观展示项目状态和问题

### 代码质量保障
- **持续监控**: 实时发现代码质量问题
- **趋势分析**: 跟踪质量变化趋势
- **智能建议**: 提供改进建议和最佳实践

### 团队协作增强
- **统一标准**: 标准化的测试和分析流程
- **透明度**: 项目状态对所有成员可见
- **知识共享**: 集中化的工具和文档

## 🔮 未来扩展方向

1. **AI辅助**: 集成LLM进行代码审查和重构建议
2. **多项目支持**: 支持管理多个相关项目
3. **插件系统**: 允许第三方工具集成
4. **移动端**: 开发移动端监控应用
5. **云端部署**: 支持云原生部署和扩展

---

**优先级**: 🔥 高优先级
**预估工期**: 12周
**负责人**: 待分配
**标签**: `enhancement`, `tooling`, `infrastructure`, `web-service`
