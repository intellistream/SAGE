# SAGE 测试重构说明

本文档说明了SAGE项目测试结构的重新组织，以支持更高效的自动化测试。

## 📁 新的测试结构

测试现在按模块组织，每个模块都有自己的`tests/`目录：

```
sage/
├── core/
│   ├── tests/                    # Core功能测试
│   │   ├── comap_test.py        # CoMap转换测试
│   │   ├── filter_test.py       # Filter转换测试
│   │   ├── flatmap_test.py      # FlatMap转换测试
│   │   ├── join_test.py         # Join转换测试
│   │   ├── keyby_test.py        # KeyBy转换测试
│   │   └── ...
│   └── function/
│       └── tests/               # 函数组件测试
│           ├── agent_tests/     # Agent功能测试
│           ├── io_tests/        # I/O功能测试
│           └── rag_tests/       # RAG功能测试
├── service/
│   ├── tests/                   # 服务层测试
│   │   ├── test_service_syntax.py
│   │   └── test_integrated_service_call.py
│   └── memory/
│       └── tests/               # 内存服务测试
│           ├── api_test/
│           └── core_test/
├── runtime/
│   └── tests/                   # 运行时测试
│       └── test_message_queue.py
├── utils/
│   └── tests/                   # 工具模块测试
│       ├── test_config_loader.py
│       ├── test_embedding.py
│       └── test_name_server.py
└── test_config.py              # 测试配置文件

frontend/
└── tests/                      # 前端测试
    └── test_sage_server_api.py

smart_test_runner.py            # 智能测试运行器
```

## 🎯 迁移映射

原始测试目录到新位置的映射：

| 原始位置 | 新位置 | 说明 |
|---------|--------|------|
| `sage/tests/core_tests/` | `sage/core/tests/` | Core API和转换测试 |
| `sage/tests/service_tests/` | `sage/service/tests/` | 服务相关测试 |
| `sage/tests/runtime_tests/` | `sage/runtime/tests/` | 运行时组件测试 |
| `sage/tests/utils_tests/` | `sage/utils/tests/` | 工具模块测试 |
| `sage/tests/frontend_tests/` | `frontend/tests/` | 前端API测试 |
| `sage/tests/memory_tests/` | `sage/service/memory/tests/` | 内存服务测试 |
| `sage/tests/function_tests/` | `sage/core/function/tests/` | 函数组件测试 |
| `sage/tests/vector_tests/` | `sage/utils/tests/` | 向量工具测试 |

## 🚀 智能测试运行器

新的`smart_test_runner.py`支持多种运行模式：

### 基本用法

```bash
# 运行所有测试
python smart_test_runner.py

# 基于git diff运行相关测试
python smart_test_runner.py --diff

# 运行特定模块测试
python smart_test_runner.py --module core
python smart_test_runner.py --module service
python smart_test_runner.py --module runtime

# 运行特定类别测试
python smart_test_runner.py --category unit
python smart_test_runner.py --category integration

# 列出所有测试模块
python smart_test_runner.py --list-modules
```

### 高级用法

```bash
# 基于与特定分支的diff运行测试
python smart_test_runner.py --diff --base-branch develop

# 运行特定模块的单元测试
python smart_test_runner.py --module core --category unit

# 组合使用
python smart_test_runner.py --diff --category integration --base-branch main
```

## 📊 测试类别

测试按以下类别组织：

- **unit**: 单元测试，测试单个组件
- **integration**: 集成测试，测试组件交互
- **e2e**: 端到端测试，测试完整工作流

## 🔧 配置文件

`sage/test_config.py`定义了：

- 测试模块映射关系
- 测试依赖关系
- 测试类别配置
- 智能测试选择逻辑

## 💡 优势

1. **模块化**: 测试与对应模块放在一起，更容易维护
2. **智能运行**: 基于git diff只运行相关测试，提高CI效率
3. **灵活性**: 支持按模块、类别、变更范围运行测试
4. **可扩展**: 易于添加新的测试模块和类别

## 🔨 迁移后的改动

1. **导入路径修复**: 所有测试文件的import路径已更新为正确的绝对路径
2. **测试发现**: 每个测试目录都有`__init__.py`文件，便于测试发现
3. **配置集中**: 测试配置统一管理，便于维护

## 📝 使用示例

### CI/CD集成

```yaml
# .github/workflows/test.yml
name: Smart Testing
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 0  # 获取完整历史以支持git diff
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run smart tests
        run: python smart_test_runner.py --diff --base-branch origin/main
```

### 开发工作流

```bash
# 开发过程中快速验证
python smart_test_runner.py --module core

# 提交前检查所有相关测试
python smart_test_runner.py --diff

# 发布前运行所有测试
python smart_test_runner.py
```

## 🚨 注意事项

1. 确保所有测试的import路径正确
2. 新添加的测试应放在对应模块的tests目录中
3. 更新`test_config.py`中的模块映射以支持新模块
4. 运行测试前确保Python路径配置正确

## 🤝 贡献指南

添加新测试时：

1. 将测试文件放在对应模块的`tests/`目录中
2. 使用正确的import路径（基于`sage.`的绝对路径）
3. 更新`test_config.py`中的映射关系（如果添加新模块）
4. 确保测试文件命名遵循约定（`test_*.py`或`*_test.py`）
