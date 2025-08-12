# SAGE Installation Modules

这个目录包含SAGE项目的模块化安装系统，旨在替代复杂的单体`quickstart.sh`脚本。

## 🎯 设计目标

- **模块化**: 将安装逻辑分解为独立的、可测试的模块
- **可维护性**: 每个模块负责单一职责，易于理解和修改
- **可重用性**: 安装组件可以被其他工具和脚本复用
- **向后兼容**: 保持现有`quickstart.sh`接口不变

## 📁 目录结构

```
tools/install/
├── README.md                    # 本文档
├── install.py                   # 主安装入口点
├── core/                        # 核心安装模块
│   ├── __init__.py
│   ├── environment_manager.py  # Conda环境管理
│   ├── package_installer.py    # 包安装管理
│   ├── dependency_checker.py   # 依赖检查
│   └── submodule_manager.py    # Git子模块管理
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── progress_tracker.py     # 进度跟踪
│   ├── user_interface.py       # 用户交互
│   └── validator.py           # 验证工具
└── config/                      # 配置文件
    ├── __init__.py
    ├── defaults.py             # 默认配置
    └── profiles.py             # 安装配置文件
```

## 🚀 使用方法

### 基本安装
```bash
python3 tools/install/install.py
```

### 开发模式安装
```bash
python3 tools/install/install.py --dev
```

### 生产模式安装
```bash
python3 tools/install/install.py --prod
```

### 指定环境名称
```bash
python3 tools/install/install.py --env-name my-sage-env
```

## 🔧 模块说明

### Core Modules

#### `environment_manager.py`
- Conda环境的创建、激活、删除
- 环境状态检查和验证
- 环境配置管理

#### `package_installer.py`
- Python包的安装和更新
- 进度跟踪和错误处理
- 不同安装模式支持

#### `dependency_checker.py`
- 系统依赖检查
- 版本兼容性验证
- 环境准备状态检查

#### `submodule_manager.py`
- Git子模块的初始化和更新
- 子模块状态检查
- 选择性子模块管理

### Utils Modules

#### `progress_tracker.py`
- 安装进度显示
- 状态更新和通知
- 错误状态跟踪

#### `user_interface.py`
- 用户输入处理
- 交互式菜单
- 错误提示和帮助信息

#### `validator.py`
- 安装结果验证
- 配置有效性检查
- 环境健康检查

## 🧪 测试

每个模块都应该有对应的单元测试：

```bash
# 运行所有测试
python3 -m pytest tools/install/tests/

# 运行特定模块测试
python3 -m pytest tools/install/tests/test_environment_manager.py
```

## 🔄 迁移策略

1. **Phase 1**: 创建基础模块结构
2. **Phase 2**: 从`quickstart.sh`提取逻辑到各个模块
3. **Phase 3**: 实现`install.py`主入口点
4. **Phase 4**: 更新`quickstart.sh`为简单的委托脚本
5. **Phase 5**: 添加测试和文档

## 📊 进度跟踪

- [ ] 基础目录结构创建
- [ ] 核心模块框架实现
- [ ] 工具模块框架实现
- [ ] 主入口点实现
- [ ] 单元测试覆盖
- [ ] 集成测试验证
- [ ] 文档更新
- [ ] `quickstart.sh`简化

## 🤝 贡献指南

1. 每个模块应该有清晰的接口定义
2. 添加充分的错误处理和日志记录
3. 编写单元测试覆盖主要功能
4. 更新相关文档

## 📝 相关链接

- [GitHub Issue #454](https://github.com/intellistream/SAGE/issues/454)
- [原始quickstart.sh分析](../../quickstart.sh)
- [安装文档](../../docs/PYPI_INSTALLATION_GUIDE.md)
