# SAGE Framework 测试脚本使用示例

## 🧪 一键测试所有包

### 基本使用

```bash
# 测试所有包（默认设置）
./scripts/test_all_packages.sh

# 只测试指定的包
./scripts/test_all_packages.sh sage-core sage-frontend

# 快速测试主要包
./scripts/quick_test.sh
```

### 高级配置

```bash
# 使用8个并行任务，10分钟超时
./scripts/test_all_packages.sh -j 8 -t 600

# 详细输出模式
./scripts/test_all_packages.sh -v sage-kernel

# 静默模式，只显示结果
./scripts/test_all_packages.sh -q

# 只显示摘要结果
./scripts/test_all_packages.sh --summary
```

### 故障处理

```bash
# 重新运行失败的测试
./scripts/test_all_packages.sh --failed

# 遇到错误继续执行其他包
./scripts/test_all_packages.sh --continue-on-error

# 详细输出查看错误信息
./scripts/test_all_packages.sh --failed -v
```

### CI/CD 环境使用

```bash
# CI环境推荐配置（快速，有详细日志）
./scripts/test_all_packages.sh \
    --continue-on-error \
    --jobs 4 \
    --timeout 300 \
    --summary

# 夜间全面测试
./scripts/test_all_packages.sh \
    --jobs 8 \
    --timeout 1800 \
    --verbose \
    --continue-on-error
```

## 📊 输出说明

### 状态标识
- ✅ **通过**: 测试全部成功
- ❌ **失败**: 测试失败或出现错误
- ⚠️ **无测试**: 包中没有找到测试文件
- ❓ **未知**: 包状态未知

### 日志文件
每个包的测试会在包目录下的 `.testlogs/` 文件夹中生成：
- `{test_filename}.log` - 单个测试文件的详细日志
- `test_run_{timestamp}.log` - 测试运行的概要日志
- `failed_tests.txt` - 失败测试的记录
- `latest_status.txt` - 最新测试状态

### 性能调优

**推荐的并行任务数量：**
- 开发机器: `-j 2` 到 `-j 4`
- CI服务器: `-j 4` 到 `-j 8`
- 强力服务器: `-j 8` 到 `-j 16`

**超时时间设置：**
- 快速验证: `--timeout 120` (2分钟)
- 标准测试: `--timeout 300` (5分钟)
- 全面测试: `--timeout 600` (10分钟)

## 🔧 集成到开发工作流

### Git Hook 示例

在 `.git/hooks/pre-push` 中：
```bash
#!/bin/bash
echo "运行快速测试..."
./scripts/quick_test.sh --summary
if [ $? -ne 0 ]; then
    echo "❌ 测试失败，推送已取消"
    exit 1
fi
```

### Makefile 集成

```makefile
.PHONY: test test-quick test-all

test: test-quick

test-quick:
	@./scripts/quick_test.sh

test-all:
	@./scripts/test_all_packages.sh --continue-on-error

test-failed:
	@./scripts/test_all_packages.sh --failed --continue-on-error
```

### VS Code 任务配置

在 `.vscode/tasks.json` 中：
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "SAGE: Quick Test",
            "type": "shell",
            "command": "./scripts/quick_test.sh",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "SAGE: Test All",
            "type": "shell", 
            "command": "./scripts/test_all_packages.sh",
            "args": ["--continue-on-error"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "new"
            }
        }
    ]
}
```
