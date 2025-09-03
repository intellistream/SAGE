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

### 查看所有安装模式
```bash
python3 tools/install/install.py --list-profiles
```

## 📋 安装模式详解

### 1. Quick（快速安装）
```bash
python3 tools/install/install.py --profile quick
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-quick`
- ✅ 安装requirements: `requirements.txt`
  - 仅安装4个核心SAGE包（开发模式）
  - 无外部依赖，最精简配置
- ❌ 跳过Git子模块
- ✅ 验证安装（可选）

**适用场景：** 快速体验、CI/CD测试、容器环境

### 2. Standard（标准安装）
```bash
python3 tools/install/install.py --profile standard
# 或者直接运行（默认选项）
python3 tools/install/install.py
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-standard` 
- ✅ 安装requirements: `requirements-dev.txt`
  - 安装4个核心SAGE包（开发模式）
  - 包含开发工具和前端功能
- ✅ 初始化Git子模块
- ✅ 安装Jupyter扩展
- ✅ 设置IPython配置
- ✅ 验证安装

**适用场景：** 日常使用、学习研究、轻度开发

### 3. Development（开发环境）
```bash
python3 tools/install/install.py --dev
# 或者
python3 tools/install/install.py --profile development
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-dev`
- ✅ 安装requirements: `requirements-dev.txt`
  - 安装4个核心SAGE包（开发模式）
  - 包含完整开发工具链
- ✅ 初始化Git子模块
- ✅ 安装开发工具
- ✅ 设置pre-commit钩子
- ✅ 安装Jupyter扩展
- ✅ 设置IPython配置
- ✅ 构建项目文档
- ✅ 验证安装

**适用场景：** 核心开发、代码贡献、调试测试

### 4. Minimal（最小安装）
```bash
python3 tools/install/install.py --minimal
# 或者
python3 tools/install/install.py --profile minimal
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-minimal`
- ✅ 安装requirements: `requirements.txt`
  - 仅安装必需的核心包
  - 跳过可选依赖
- ❌ 跳过Git子模块
- ❌ 跳过Jupyter
- ✅ 最小化验证

**适用场景：** 资源受限环境、嵌入式部署、微服务

### 5. Research（科研环境）
```bash
python3 tools/install/install.py --profile research
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-research`
- ✅ 安装Conda包：`numpy`, `pandas`, `matplotlib`, `scipy`, `scikit-learn`, `seaborn`, `jupyter`, `jupyterlab`, `statsmodels`, `networkx`
- ✅ 安装Pip包：相同的科学计算库（作为备用）
- ✅ 安装4个核心SAGE包（开发模式）
- ✅ 初始化Git子模块
- ✅ 安装Jupyter扩展
- ✅ 设置JupyterLab
- ✅ 安装科研工具
- ✅ 验证安装

**适用场景：** 数据科学、机器学习、学术研究

### 6. Production（生产环境）
```bash
python3 tools/install/install.py --prod
# 或者
python3 tools/install/install.py --profile production
```
**关键步骤：**
- ✅ 系统依赖检查
- ✅ 创建conda环境 `sage-prod`
- ✅ 安装requirements: `requirements.txt`
  - 精简的生产环境包
  - 优化性能配置
- ✅ 初始化Git子模块
- ❌ 跳过开发工具
- ❌ 跳过Jupyter
- ✅ 启用日志记录
- ✅ 验证安装

**适用场景：** 生产部署、服务器环境、性能优先

## 🔄 安装流程对比

| 步骤 | Quick | Standard | Development | Minimal | Research | Production |
|------|-------|----------|-------------|---------|----------|------------|
| 依赖检查 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Conda环境 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Requirements文件 | requirements.txt | requirements-dev.txt | requirements-dev.txt | requirements.txt | - | requirements.txt |
| Conda包 | - | - | - | - | 10个科学计算包 | - |
| Pip包 | - | - | - | - | 14个科学计算包 | - |
| SAGE核心包 | 4个 | 4个 | 4个 | 4个 | 4个 | 4个 |
| Git子模块 | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 开发工具 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Jupyter | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| 文档构建 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |

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

## � 使用建议

### 选择合适的安装模式

- **首次体验SAGE**: 使用 `quick` 模式
- **日常使用**: 使用 `standard` 模式（默认）
- **参与开发**: 使用 `development` 模式
- **服务器部署**: 使用 `production` 模式
- **数据科学研究**: 使用 `research` 模式
- **资源受限**: 使用 `minimal` 模式

### 常用命令组合

```bash
# 强制重新安装开发环境
python3 tools/install/install.py --dev --force

# 静默安装生产环境
python3 tools/install/install.py --prod --quiet

# 跳过验证的快速安装
python3 tools/install/install.py --quick --skip-validation

# 自定义环境名的研究环境
python3 tools/install/install.py --profile research --env-name sage-ml
```

## 🔍 故障排除

### 常见问题

1. **Conda环境已存在**
   ```bash
   # 使用 --force 强制重新创建
   python3 tools/install/install.py --force
   ```

2. **网络连接问题**
   ```bash
   # 检查conda channels配置
   conda config --show channels
   
   # 添加国内镜像源
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
   ```

3. **权限问题**
   ```bash
   # 确保有conda写权限
   conda info --envs
   
   # 检查目录权限
   ls -la $CONDA_PREFIX
   ```

4. **包安装失败**
   ```bash
   # 查看详细错误日志
   cat install.log
   
   # 手动激活环境后安装
   conda activate sage-dev
   pip install -e packages/sage-common
   ```

### 日志和调试

- **安装日志**: `install.log` 文件包含详细的安装过程
- **验证报告**: 安装完成后会显示验证结果
- **环境检查**: 使用 `conda info` 和 `pip list` 检查环境状态

### 清理和重置

```bash
# 删除SAGE环境
conda env remove -n sage-dev

# 清理pip缓存
pip cache purge

# 重置Git子模块
git submodule deinit --all
```

## �📝 相关链接

- [GitHub Issue #454](https://github.com/intellistream/SAGE/issues/454)
- [原始quickstart.sh分析](../../quickstart.sh)
- [安装文档](../../docs/PYPI_INSTALLATION_GUIDE.md)
