# 测试工具存档

这个目录包含了SAGE项目的完整测试工具集，被移到这里以保持项目根目录的整洁。

## 📂 存档内容

### 🚀 高级测试脚本
- **`run_all_tests.py`** - Python完整功能测试脚本
- **`quick_test.sh`** - Bash快捷测试脚本
- **`demo_complete_testing.sh`** - 综合功能演示脚本

### ⚙️ 配置文件
- **`test_config.toml`** - 测试系统配置文件

### 📖 文档
- **`TEST_AUTOMATION_README.md`** - 详细使用文档
- **`COMPLETE_TESTING_SYSTEM_SUMMARY.md`** - 完整系统总结

### 🎭 演示工具
- **`demo_test_environment.sh`** - 环境演示脚本

## 💡 使用说明

如果你需要更高级的测试功能，可以从这个目录中复制相应的脚本到项目根目录使用：

```bash
# 复制高级测试脚本
cp testing_archive/run_all_tests.py .
cp testing_archive/quick_test.sh .

# 使用高级功能
python run_all_tests.py --interactive
./quick_test.sh --interactive
```

## 🎯 推荐使用

对于日常使用，推荐使用项目根目录的 `one_click_setup_and_test.py`，它提供了最简洁和实用的功能。

只有在需要以下高级功能时，才考虑使用存档中的工具：
- 交互式测试菜单
- 详细的测试配置管理
- GitHub Actions复杂模拟
- 自定义测试套件

---
*这些工具已经过完整测试，可以随时使用*
