# SAGE 脚本架构现代化迁移计划

## 🎯 目标

将分散在 `scripts/` 目录下的bash脚本功能整合到 `sage-common` 包中，
实现 `quickstart.sh` 和 `pypi_installer.py` 的功能共享。

## 📋 当前状况分析

### scripts/ 目录下的文件分类：

#### 🔧 核心工具脚本 (需要迁移)
1. **logging.sh** → `unified_tools.py` (Logger类) ✅ 已完成
2. **common_utils.sh** → `unified_tools.py` (SystemChecker, FileManager) ✅ 已完成  
3. **conda_utils.sh** → `unified_tools.py` (CondaManager) ✅ 已完成

#### 🚀 构建和发布脚本 (保留在scripts/)
- `check_packages_status.sh` - 包状态检查
- `test_all_packages.sh` - 全包测试
- `update_sage_packages.sh` - 包更新
- `version_manager.sh` - 版本管理
- 发布相关脚本

#### 🔧 特定工具脚本 (可选迁移)
- `diagnose_sage.py` - 已经是Python ✅
- `check_compatibility.py` - 已经是Python ✅
- `fix_conda_tos.sh` - 特定问题修复，可保留

#### 📦 安装脚本 (需要重构)
- `install-sage-conda.sh` - 可以整合到quickstart逻辑
- `sage-conda.sh` - 可以整合到conda管理
- `sage-jobmanager.sh` - 可以整合到JobManager CLI

## 🔄 迁移步骤

### Phase 1: 创建统一工具模块 ✅ 已完成
- [x] `unified_tools.py` - 核心工具类
- [x] `pypi_installer.py` - 使用统一工具
- [x] `quickstart_helper.py` - 为quickstart.sh提供Python支持

### Phase 2: 修改quickstart.sh使用Python工具 ✅ 已完成
- [x] 创建 `python_bridge.sh` - Python/Bash桥接层
- [x] 修改quickstart.sh支持混合模式（Python优先，bash fallback）
- [x] 改进系统检查功能使用Python增强
- [x] 改进conda环境检查使用Python工具

### Phase 3: 移除重复的bash工具
- [ ] 删除 `logging.sh` (功能已在unified_tools.py)
- [ ] 删除 `common_utils.sh` (功能已在unified_tools.py)
- [ ] 删除 `conda_utils.sh` (功能已在unified_tools.py)

### Phase 4: 可选优化
- [ ] 将特定安装脚本整合到统一框架
- [ ] 创建更多Python helper命令
- [ ] 优化构建和测试脚本

## 🏗️ 新架构图

```
SAGE/
├── quickstart.sh                    # 开发环境入口 (bash)
│   └── 调用 → packages/sage-common/src/sage/common/utils/
│                ├── unified_tools.py       # 统一工具模块
│                ├── quickstart_helper.py   # quickstart辅助工具
│                └── pypi_installer.py      # PyPI用户工具
├── scripts/                         # 保留的构建/发布脚本
│   ├── build相关.sh
│   ├── test相关.sh  
│   └── publish相关.sh
└── packages/sage-common/            # 用户安装的包
    └── 包含所有通用工具
```

## ✅ 优势

1. **功能共享**: quickstart.sh 和 pypi_installer.py 使用相同的底层工具
2. **维护性**: Python代码比bash更易维护和测试
3. **跨平台**: Python工具在Windows/Linux/Mac都能正常工作
4. **扩展性**: 更容易添加新功能和改进
5. **一致性**: 统一的日志输出和用户交互体验

## 🚧 实施风险与对策

### 风险1: quickstart.sh依赖bash特性
**对策**: 保持bash作为主控制脚本，只将计算密集和复杂逻辑迁移到Python

### 风险2: 用户环境差异
**对策**: Python helper有良好的错误处理和fallback机制

### 风险3: 迁移期间的兼容性
**对策**: 分阶段迁移，保持向后兼容

## 📅 时间线

- **Week 1**: Phase 1 ✅ 完成
- **Week 2**: Phase 2 - 修改quickstart.sh
- **Week 3**: Phase 3 - 清理旧脚本
- **Week 4**: Phase 4 - 测试和优化

## 🧪 测试计划

1. **单元测试**: 为unified_tools.py创建测试
2. **集成测试**: 测试quickstart.sh + Python helper
3. **兼容性测试**: 在不同操作系统上测试
4. **用户验收测试**: 真实用户场景测试

这个迁移计划将显著提升SAGE安装和开发体验的一致性和可维护性。
