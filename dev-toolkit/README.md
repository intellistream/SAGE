# SAGE开发工具包目录结构

```
dev-toolkit/
├── README.md                           # 开发工具包主要文档
├── setup.py                           # 安装脚本
├── pyproject.toml                     # 项目配置
├── requirements.txt                   # 依赖列表
├── sage_dev_toolkit.py               # 主入口脚本（CLI）
│
├── src/                              # 源代码目录
│   └── sage_dev_toolkit/             # 主包
│       ├── __init__.py               # 包初始化
│       ├── core/                     # 核心组件
│       │   ├── __init__.py
│       │   ├── config.py             # 配置管理
│       │   ├── logger.py             # 日志系统
│       │   ├── toolkit.py            # 主工具包类
│       │   └── exceptions.py         # 异常定义
│       │
│       ├── tools/                    # 工具模块
│       │   ├── __init__.py
│       │   ├── base.py               # 工具基类
│       │   ├── test_runner.py        # 测试运行器
│       │   ├── dependency_analyzer.py # 依赖分析器
│       │   ├── package_manager.py    # 包管理器
│       │   ├── code_analyzer.py      # 代码分析器
│       │   └── report_generator.py   # 报告生成器
│       │
│       ├── cli/                      # 命令行界面
│       │   ├── __init__.py
│       │   ├── main.py               # 主CLI入口
│       │   ├── commands/             # 命令实现
│       │   │   ├── __init__.py
│       │   │   ├── test.py           # 测试命令
│       │   │   ├── analyze.py        # 分析命令
│       │   │   ├── package.py        # 包管理命令
│       │   │   └── report.py         # 报告命令
│       │   └── interactive.py        # 交互模式
│       │
│       └── utils/                    # 工具函数
│           ├── __init__.py
│           ├── file_utils.py         # 文件操作
│           ├── git_utils.py          # Git相关
│           ├── path_utils.py         # 路径处理
│           └── format_utils.py       # 格式化工具
│
├── config/                           # 配置文件
│   ├── default.yaml                  # 默认配置
│   ├── development.yaml              # 开发环境配置
│   ├── production.yaml               # 生产环境配置
│   └── schemas/                      # 配置模式
│       └── config_schema.yaml
│
├── templates/                        # 模板文件
│   ├── reports/                      # 报告模板
│   │   ├── html_report.jinja2
│   │   ├── markdown_report.jinja2
│   │   └── json_report.jinja2
│   └── configs/                      # 配置模板
│       └── project_config.yaml.template
│
├── tests/                           # 测试文件
│   ├── __init__.py
│   ├── conftest.py                  # pytest配置
│   ├── unit/                        # 单元测试
│   │   ├── test_config.py
│   │   ├── test_toolkit.py
│   │   └── test_tools/
│   │       ├── test_test_runner.py
│   │       ├── test_dependency_analyzer.py
│   │       └── test_package_manager.py
│   ├── integration/                 # 集成测试
│   │   ├── test_cli.py
│   │   └── test_workflows.py
│   └── fixtures/                    # 测试数据
│       ├── sample_project/
│       └── expected_outputs/
│
├── docs/                           # 文档
│   ├── user_guide.md               # 用户指南
│   ├── developer_guide.md          # 开发者指南
│   ├── api_reference.md            # API参考
│   ├── configuration.md            # 配置说明
│   ├── extending.md                # 扩展指南
│   └── examples/                   # 示例
│       ├── basic_usage.md
│       ├── advanced_workflows.md
│       └── custom_tools.md
│
└── scripts/                        # 辅助脚本
    ├── install.sh                  # 安装脚本
    ├── test.sh                     # 测试脚本
    ├── build.sh                    # 构建脚本
    └── migrate_from_scripts.py     # 从旧scripts迁移
```

## 主要设计原则

### 1. 模块化设计
- **核心层** (`core/`): 提供基础功能和配置管理
- **工具层** (`tools/`): 具体的开发工具实现
- **接口层** (`cli/`): 用户交互界面
- **工具层** (`utils/`): 通用工具函数

### 2. 可扩展性
- 工具模块采用插件式设计，继承自`base.py`中的基类
- 支持通过配置文件动态加载工具
- 提供清晰的扩展接口

### 3. 配置驱动
- 分环境配置支持
- 配置模式验证
- 运行时配置重载

### 4. 测试完备性
- 单元测试覆盖所有核心功能
- 集成测试验证工作流
- 测试数据和期望输出分离

### 5. 文档完整性
- 用户指南和开发指南分离
- API文档自动生成
- 丰富的使用示例

## 迁移策略

1. **Phase 1**: 创建基础结构，迁移核心类
2. **Phase 2**: 重构scripts中的工具为独立模块
3. **Phase 3**: 完善CLI界面和交互模式
4. **Phase 4**: 添加测试和文档
