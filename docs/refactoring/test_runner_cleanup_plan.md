# SAGE Test Runner统一清理计划

## 当前状况分析

### ✅ 优秀的模板 (已保留)
- `packages/sage-common/src/sage/common/dev/tools/enhanced_test_runner.py` ⭐️
  - 功能最全面：多种运行模式、智能变更检测、失败缓存、并行执行
  - 统一日志到`.sage/logs`
  - 支持覆盖率报告
  - **这是标准模板**

### ✅ 重复/低质量的工具 (已删除)
1. ~~`packages/sage-kernel/run_tests.py`~~ ❌ **已删除**
   - 功能重复，质量不如enhanced_test_runner
   
2. ~~`packages/sage-kernel/tests/unit/core/run_tests.py`~~ ❌ **已删除**
   - 功能单一，只针对core模块
   
3. ~~`packages/sage-kernel/tests/unit/kernel/runtime/run_runtime_tests.py`~~ ❌ **已删除**
   - 功能单一，只针对runtime模块
   
4. ~~`packages/sage-kernel/tests/unit/kernel/runtime/service/run_queue_refactor_tests.py`~~ ❌ **已删除**
   - 功能过于具体
   
5. ~~`packages/sage-kernel/src/sage/kernel/enterprise/sage_queue/tests/run_*.py`~~ ❌ **已删除**
   - enterprise特定的测试工具

### ✅ 整合的工具 (已清理)
- ~~`packages/sage-common/src/sage/common/dev/tools/one_click_setup.py`~~ ❌ **已删除**
  - 功能重复：setup功能已有quickstart.sh和pypi_installer.py
  - 测试功能重复enhanced_test_runner

## ✅ 已完成的统一方案

### 1. ✅ 保留和完善
- **enhanced_test_runner.py** 作为唯一的测试运行器
- 确保所有包使用统一的`.sage/logs/{package}/`日志目录

### 2. ✅ 删除重复工具
- 删除所有包级别的分散test runner
- 删除功能重复的测试脚本

### 3. ✅ 统一接口
```bash
# 通过sage-common运行任何包的测试
python -c "
import sys
sys.path.insert(0, 'packages/sage-common/src')
from sage.common.dev.tools.enhanced_test_runner import EnhancedTestRunner
runner = EnhancedTestRunner('/home/shuhao/SAGE')
runner.run_tests(mode='package', package='sage-kernel')
runner.run_tests(mode='package', package='sage-middleware')  
runner.run_tests(mode='diff')
runner.run_tests(mode='failed')
"
```

### 4. ✅ 各包配置标准化
- 统一pytest.ini配置 ✅
- 统一pyproject.toml的测试配置 ✅ 
- 统一日志和报告输出 ✅

## ✅ 额外发现和修复

### JobManager日志问题
**发现**: `.sage/logs/`中有很多`jobmanager_*`目录，这些不是测试日志，而是JobManager运行时日志

**原因**: JobManager使用`Path.home() / ".sage" / "logs"`，导致运行时日志和测试日志混合

**修复**: 
- 修改JobManager使用`{project}/.sage/logs/jobmanager/session_{id}`目录
- 支持`SAGE_PROJECT_ROOT`环境变量指定项目根目录
- 将现有日志移动到专门的jobmanager子目录

## 最终目录结构

```
.sage/logs/
├── kernel/           # sage-kernel测试日志
├── middleware/       # sage-middleware测试日志
├── common/          # sage-common测试日志
├── libs/            # sage-libs测试日志
└── jobmanager/      # JobManager运行时日志
    ├── session_20250811_215641/
    └── session_20250811_220001/
```

## 使用方法

```python
# 统一的测试运行器
from sage.common.dev.tools.enhanced_test_runner import EnhancedTestRunner

runner = EnhancedTestRunner('/path/to/project')

# 运行特定包的测试
result = runner.run_tests(mode='package', package='sage-kernel')

# 运行diff测试（基于git变更）
result = runner.run_tests(mode='diff', base_branch='main')

# 重新运行失败的测试
result = runner.run_tests(mode='failed')

# 运行所有测试
result = runner.run_tests(mode='all')
```

所有测试日志自动保存到`.sage/logs/{package}/`目录中。
