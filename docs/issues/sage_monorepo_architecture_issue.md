# 🏗️ SAGE Monorepo 架构重构方案 - 支持商业化分层的包管理

## 📋 项目背景

SAGE作为dataflow-native LLM推理框架，需要支持：
1. **开源生态建设** - 培养社区用户和开发者
2. **商业化变现** - 高性能组件和企业级功能
3. **清晰的技术边界** - 开源与商业功能明确分离
4. **灵活的部署选项** - 从个人开发到企业集群

当前包结构存在问题：
- 测试代码埋在源码中，导致包污染
- 商业化边界不清晰
- 依赖关系复杂，难以维护
- 缺乏清晰的升级路径

## 🎯 设计目标

### 技术目标
- ✅ 清晰的分层架构：内核、中间件、用户态
- ✅ 标准化的测试结构：tests目录分离
- ✅ 灵活的商业化支持：开源/商业包并存
- ✅ 简化的依赖关系：单向依赖链
- ✅ 优雅的功能降级：自动检测最佳版本

### 商业目标
- 💰 多层次定价策略：社区版/专业版/企业版
- 🎯 技术竞争壁垒：核心性能组件闭源
- 🌱 生态系统友好：开源版本功能完整
- 📈 平滑升级路径：用户可逐步升级

## 🏗️ 新架构设计

### 总体项目结构
```
SAGE/
├── packages/                    # Monorepo包目录
│   ├── kernel/                 # 🔧 内核层包
│   ├── middleware/             # 🌉 中间件层包  
│   ├── userspace/              # 👤 用户态层包
│   ├── tools/                  # 🛠️ 工具和服务包
│   └── commercial/             # 💰 商业版包
├── tests/                      # 根级别集成测试
├── docs/                       # 文档
├── examples/                   # 示例代码
├── scripts/                    # 构建和部署脚本
└── pyproject.toml             # 工作空间配置
```

### 内核层 (Kernel Layer) 包设计

#### 🆓 开源内核包
```
packages/kernel/
├── sage-kernel-core/           # 核心API和基础算子
│   ├── src/sage/kernel/core/
│   │   ├── api/                # Environment, Pipeline等核心API
│   │   ├── function/           # Function抽象接口
│   │   ├── operator/           # Source, Sink, Map基础算子
│   │   └── pipeline/           # 管道构建和验证
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   └── pyproject.toml
│
├── sage-kernel-runtime/        # 本地执行环境
│   ├── src/sage/kernel/runtime/
│   │   ├── local/              # LocalEnvironment实现
│   │   ├── execution/          # 基础执行引擎
│   │   ├── scheduler/          # 简单任务调度
│   │   └── queue/              # 基础队列系统
│   ├── tests/
│   └── pyproject.toml
│
├── sage-kernel-jobmanager/     # 基础作业管理
│   ├── src/sage/kernel/jobmanager/
│   │   ├── client/             # JobManager客户端
│   │   ├── server/             # 基础JobManager服务
│   │   └── api/                # 作业管理API
│   ├── tests/
│   └── pyproject.toml
│
└── sage-kernel-utils/          # 基础工具
    ├── src/sage/kernel/utils/
    │   ├── config/             # 配置管理
    │   ├── logging/            # 日志系统
    │   ├── network/            # 基础网络工具
    │   └── serialization/      # 序列化工具
    ├── tests/
    └── pyproject.toml
```

#### 💰 商业内核包
```
packages/commercial/kernel/
├── sage-kernel-enterprise/     # 企业级运行时
│   ├── src/sage/kernel/enterprise/
│   │   ├── distributed/        # 分布式执行(Ray集成)
│   │   ├── optimization/       # 执行优化引擎
│   │   ├── reliability/        # 故障恢复和一致性
│   │   ├── monitoring/         # 高级监控和指标
│   │   └── security/           # 安全和权限控制
│   ├── tests/
│   └── pyproject.toml
│
└── sage-kernel-jobmanager-pro/ # 企业级作业管理
    ├── src/sage/kernel/jobmanager/
    │   ├── cluster/            # 集群管理
    │   ├── ha/                 # 高可用JobManager
    │   ├── load_balancing/     # 负载均衡
    │   └── enterprise/         # 企业级功能
    ├── tests/
    └── pyproject.toml
```

### 中间件层 (Middleware Layer) 包设计

#### 🆓 开源中间件包
```
packages/middleware/
├── sage-middleware-memory/     # 基础内存服务
│   ├── src/sage/middleware/memory/
│   │   ├── manager/            # MemoryManager
│   │   ├── collection/         # 集合操作
│   │   ├── vdb/                # 基础向量数据库
│   │   └── persistence/        # 数据持久化
│   ├── tests/
│   └── pyproject.toml
│
├── sage-middleware-database/   # 数据库连接器
│   ├── src/sage/middleware/database/
│   │   ├── connectors/         # SQLite, PostgreSQL等
│   │   ├── drivers/            # 数据库驱动
│   │   └── orm/                # 简单ORM支持
│   ├── tests/
│   └── pyproject.toml
│
└── sage-middleware-embedding/  # 嵌入模型服务
    ├── src/sage/middleware/embedding/
    │   ├── models/             # HuggingFace, OpenAI集成
    │   ├── cache/              # 嵌入缓存
    │   └── api/                # 统一嵌入API
    ├── tests/
    └── pyproject.toml
```

#### 💰 商业中间件包
```
packages/commercial/middleware/
├── sage-middleware-memory-pro/  # 企业级内存服务
│   ├── src/sage/middleware/memory/
│   │   ├── distributed/        # 分布式向量数据库
│   │   ├── optimization/       # 性能优化引擎
│   │   ├── replication/        # 数据复制和同步
│   │   └── enterprise/         # 企业级功能
│   ├── tests/
│   └── pyproject.toml
│
├── sage-middleware-database-pro/ # 企业级数据库
│   ├── src/sage/middleware/database/
│   │   ├── enterprise/         # Oracle, DB2等企业数据库
│   │   ├── optimization/       # 查询优化
│   │   ├── security/           # 数据加密和权限
│   │   └── analytics/          # 数据分析功能
│   ├── tests/
│   └── pyproject.toml
│
└── sage-middleware-extensions/  # C++高性能扩展
    ├── src/sage/middleware/extensions/
    │   ├── vectordb/           # 高性能向量计算
    │   ├── communication/      # 高性能通信引擎
    │   ├── algorithms/         # 优化算法库
    │   └── gpu/                # GPU加速支持
    ├── tests/cpp_tests/        # C++单元测试
    ├── tests/python_tests/     # Python集成测试
    ├── CMakeLists.txt
    └── pyproject.toml
```

### 用户态层 (Userspace Layer) 包设计

#### 🆓 开源用户态包
```
packages/userspace/
├── sage-userspace-rag/         # 基础RAG算子
│   ├── src/sage/userspace/rag/
│   │   ├── retrieval/          # 检索算子
│   │   ├── generation/         # 生成算子
│   │   ├── evaluation/         # 评估算子
│   │   └── prompting/          # 提示工程
│   ├── tests/
│   └── pyproject.toml
│
├── sage-userspace-agents/      # 开源智能代理
│   ├── src/sage/userspace/agents/
│   │   ├── basic/              # 基础Agent实现
│   │   ├── community/          # 社区贡献Agent
│   │   ├── tools/              # Agent工具集
│   │   └── strategies/         # 基础推理策略
│   ├── tests/
│   └── pyproject.toml
│
└── sage-userspace-operators/   # 高级算子
    ├── src/sage/userspace/operators/
    │   ├── window/             # 窗口算子
    │   ├── join/               # 连接算子
    │   ├── aggregation/        # 聚合算子
    │   └── routing/            # 路由算子
    ├── tests/
    └── pyproject.toml
```

#### 💰 商业用户态包
```
packages/commercial/userspace/
├── sage-userspace-rag-pro/     # 高级RAG算法
│   ├── src/sage/userspace/rag/
│   │   ├── advanced/           # 高级检索算法
│   │   ├── optimization/       # 性能优化
│   │   ├── multimodal/         # 多模态RAG
│   │   └── enterprise/         # 企业级RAG功能
│   ├── tests/
│   └── pyproject.toml
│
├── sage-userspace-agents-pro/  # 企业级智能代理
│   ├── src/sage/userspace/agents/
│   │   ├── advanced/           # 高级AI策略
│   │   ├── enterprise/         # 企业级Agent
│   │   ├── proprietary/        # 专有算法
│   │   └── multiagent/         # 多Agent协作
│   ├── tests/
│   └── pyproject.toml
│
└── sage-userspace-optimization/ # 性能优化算子
    ├── src/sage/userspace/optimization/
    │   ├── parallel/           # 并行优化算子
    │   ├── gpu/                # GPU加速算子
    │   ├── distributed/        # 分布式算子
    │   └── adaptive/           # 自适应优化
    ├── tests/
    └── pyproject.toml
```

### 工具和服务层 (Tools Layer) 包设计

> **设计原理**: 工具层提供横跨所有业务层的开发者工具和用户界面，不属于任何特定的业务层级。这些工具通常需要集成来自kernel、middleware、userspace的多种功能。

#### 🆓 开源工具包
```
packages/tools/
├── sage-cli/                   # 开源CLI工具
│   ├── src/sage/cli/
│   │   ├── commands/           # 基础命令
│   │   │   ├── kernel/         # 环境管理命令
│   │   │   ├── memory/         # 内存服务命令  
│   │   │   └── app/            # 应用部署命令
│   │   ├── dev/                # 开发工具
│   │   └── utils/              # CLI工具函数
│   ├── tests/
│   └── pyproject.toml
│
├── sage-frontend/              # 开源Dashboard
│   ├── src/sage/frontend/
│   │   ├── dashboard/          # 基础监控面板
│   │   ├── api/                # REST API
│   │   ├── components/         # 跨层级组件展示
│   │   └── static/             # 静态资源
│   ├── tests/
│   └── pyproject.toml
│
└── sage-plugins/               # 插件系统
    ├── src/sage/plugins/
    │   ├── registry/           # 插件注册
    │   ├── loader/             # 插件加载器
    │   └── examples/           # 示例插件
    ├── tests/
    └── pyproject.toml
```

#### 💰 商业工具包
```
packages/commercial/tools/
├── sage-cli-enterprise/        # 企业级CLI
│   ├── src/sage/cli/enterprise/
│   │   ├── cluster/            # 集群管理命令
│   │   ├── monitoring/         # 监控命令
│   │   ├── admin/              # 管理工具
│   │   └── security/           # 安全管理
│   ├── tests/
│   └── pyproject.toml
│
└── sage-frontend-enterprise/   # 企业级Dashboard
    ├── src/sage/frontend/enterprise/
    │   ├── advanced/           # 高级监控功能
    │   ├── analytics/          # 数据分析
    │   ├── security/           # 安全控制台
    │   └── reporting/          # 报告生成
    ├── tests/
    └── pyproject.toml
```

## 💼 商业化策略

### 版本分层
```
🆓 Community Edition (Apache 2.0)
├── 完整的核心功能
├── 基础RAG和Agent支持
├── 本地执行环境
├── 基础CLI和Dashboard
└── 社区支持

💰 Professional Edition (订阅制 $99/月)
├── Community Edition +
├── 分布式执行支持
├── 高性能算子优化
├── 企业级内存服务
├── 高级监控功能
└── 邮件技术支持

💰 Enterprise Edition (License + 支持)
├── Professional Edition +
├── C++性能扩展
├── 企业级可靠性保障
├── 多租户和权限管理
├── 专业咨询和定制开发
└── 7x24 SLA支持
```

### 安装示例
```bash
# 社区版 - 完全免费
pip install sage-community
# 等价于: pip install sage-kernel-core sage-kernel-runtime sage-userspace-rag

# 专业版 - 需要License Key
pip install sage-professional --license-key=your-key
# 自动安装优化组件

# 企业版 - 企业License
pip install sage-enterprise --license-file=enterprise.pem
# 包含所有商业组件
```

## 🔧 技术实现

### 1. 优雅降级机制
```python
# 自动检测并使用最佳可用版本
class EnvironmentFactory:
    @staticmethod
    def create_distributed_environment():
        try:
            from sage.kernel.enterprise import DistributedEnvironment
            return DistributedEnvironment()
        except ImportError:
            logger.warning("Distributed execution requires Professional/Enterprise edition")
            from sage.kernel.runtime import LocalEnvironment
            return LocalEnvironment()
```

### 2. License验证系统
```python
# 商业组件License检查
@requires_professional_license
class HighPerformanceOperator:
    def __init__(self):
        self.license_validator = LicenseValidator()
        self.license_validator.validate_professional()
    
    def execute(self, data):
        # 高性能算法实现
        pass
```

### 3. 统一的包依赖管理
```toml
# 工作空间根目录 pyproject.toml
[project.optional-dependencies]
# 预定义安装组合
community = [
    "sage-kernel-core", "sage-kernel-runtime", 
    "sage-middleware-memory", "sage-userspace-rag"
]

professional = [
    "sage-community", "sage-kernel-enterprise", 
    "sage-middleware-memory-pro", "sage-userspace-optimization"
]

enterprise = [
    "sage-professional", "sage-middleware-extensions",
    "sage-cli-enterprise", "sage-frontend-enterprise"
]
```

## 🚀 实施路径

### Phase 1: 测试结构重构 (1周)
- [ ] 迁移所有测试到标准 `tests/` 目录
- [ ] 修复pytest配置
- [ ] 验证测试发现和运行正常

### Phase 2: 开源包重构 (2周)
- [ ] 重构内核层开源包
- [ ] 重构中间件层开源包  
- [ ] 重构用户态层开源包
- [ ] 确保社区版功能完整

### Phase 3: 商业包开发 (4-6周)
- [ ] 开发高性能C++扩展
- [ ] 实现企业级可靠性功能
- [ ] 建立License验证系统
- [ ] 开发商业版特有功能

### Phase 4: 商业化部署 (2周)
- [ ] 建立销售和支持体系
- [ ] 部署License服务器
- [ ] 准备市场营销材料
- [ ] 建立客户支持流程

## 📊 预期收益

### 技术收益
- ✅ **架构清晰**: 分层设计便于理解和维护
- ✅ **测试稳定**: 标准化测试结构提升质量
- ✅ **包体积优化**: 测试代码不再污染发布包
- ✅ **依赖简化**: 单向依赖链降低维护成本

### 商业收益
- 💰 **多元化收入**: 支持订阅和License两种模式
- 🎯 **技术壁垒**: 核心性能组件形成竞争优势
- 🌱 **生态建设**: 开源版本培养用户群体
- 📈 **升级路径**: 平滑的付费升级体验

## ✅ 验收标准

### 功能验收
- [ ] 社区版功能完整可用
- [ ] 商业版优雅降级工作正常
- [ ] License验证系统稳定
- [ ] 所有包可独立安装和运行

### 质量验收
- [ ] 测试覆盖率 > 80%
- [ ] 包体积减少 > 30%
- [ ] 安装时间减少 > 50%
- [ ] 依赖冲突为零

---

**优先级**: 🔥 P0 - 架构基础
**里程碑**: Architecture 2.0
**预计工作量**: 8-12周
**负责团队**: 核心架构组

**下一步**: 开始Phase 1测试结构重构，为整个架构重构奠定基础。
