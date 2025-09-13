# 遗留脚本存档

本目录包含已被 `sage dev test` 命令替代的旧测试脚本。

## 📁 文件说明

### 已迁移的脚本
- `run_tests.py` - Python 集成测试运行器 → `sage dev test`
- `test_all_packages.sh` - 完整包测试脚本 → `sage dev test`  
- `quick_test.sh` - 快速测试脚本 → `sage dev test --test-type quick`
- `optimized_test_runner.sh` - 优化测试运行器 → `sage dev test`

## 🔄 功能映射

所有功能已完整迁移到 `sage dev test` 命令：

```bash
# 旧：./test_all_packages.sh -j 8 -t 600 --verbose
# 新：sage dev test --jobs 8 --timeout 600 --verbose

# 旧：./quick_test.sh --summary  
# 新：sage dev test --test-type quick --summary

# 旧：python run_tests.py --unit --integration
# 新：sage dev test --test-type unit && sage dev test --test-type integration
```

## ⚠️ 重要说明

**这些脚本已弃用**，仅作为备份保留。请使用新的 `sage dev test` 命令。

如果遇到问题需要回退，可以临时使用这些脚本，但请及时报告问题以便修复新系统。

---
*迁移完成时间: 2025-09-13*