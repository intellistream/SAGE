# SAGE 闭源包发布脚本套件

## 概述

这个脚本套件基于 sage-dev-toolkit 的功能，提供了自动化的闭源包编译、打包和发布流程。套件包含三个主要脚本：

1. **`proprietary_publish.sh`** - 主要的发布脚本，提供完整的闭源包发布功能
2. **`quick_publish.sh`** - 快捷包装脚本，提供预定义的发布方案
3. **`proprietary_publish_config.sh`** - 配置文件，包含所有可配置的参数

## 功能特性

### 核心功能
- 🔒 **闭源编译**: 将Python源代码编译为字节码，保护知识产权
- 📦 **自动打包**: 使用标准的Python build工具生成wheel包
- 🚀 **一键发布**: 自动上传到PyPI或Test PyPI
- 🎯 **智能依赖**: 按包依赖关系顺序发布
- 🧹 **清理管理**: 自动清理构建缓存和临时文件

### 高级功能
- 🔍 **预演模式**: 支持dry-run模式，预览发布过程
- 📊 **详细报告**: 生成发布过程的详细报告
- ⚡ **并行处理**: 支持多包并行编译和发布
- 🛡️ **安全验证**: 发布前进行代码检查和测试
- 📧 **通知系统**: 支持邮件、Slack、企业微信通知
- 💾 **备份管理**: 自动备份构建文件

## 快速开始

### 1. 环境准备

确保已安装必要的依赖：

```bash
# 安装sage-dev-toolkit
cd /path/to/SAGE
pip install -e packages/sage-dev-toolkit

# 安装构建和发布工具
pip install build twine

# 配置PyPI凭据
pip install keyring
```

### 2. 使用快捷脚本（推荐）

```bash
# 开发测试 - 预演模式发布到Test PyPI
./scripts/quick_publish.sh dev-test

# 预发布 - 发布核心包到Test PyPI  
./scripts/quick_publish.sh staging

# 生产发布 - 发布所有包到PyPI
./scripts/quick_publish.sh production

# 单包发布
./scripts/quick_publish.sh single sage-kernel --test-pypi

# 交互模式
./scripts/quick_publish.sh custom
```

### 3. 使用主脚本

```bash
# 预演模式发布所有包
./scripts/proprietary_publish.sh --dry-run --all

# 发布指定包
./scripts/proprietary_publish.sh --force sage-kernel sage-middleware

# 发布到测试PyPI
./scripts/proprietary_publish.sh --test-pypi --output /tmp/builds sage-cli

# 清理缓存并详细输出
./scripts/proprietary_publish.sh --clean --verbose sage-core
```

## 脚本详细说明

### 主脚本 `proprietary_publish.sh`

主要的发布脚本，提供完整的命令行接口。

#### 选项参数

| 选项 | 说明 |
|------|------|
| `-h, --help` | 显示帮助信息 |
| `-d, --dry-run` | 预演模式，不实际发布 |
| `-f, --force` | 强制发布，跳过确认 |
| `-o, --output DIR` | 指定输出目录 |
| `-t, --test-pypi` | 发布到测试PyPI |
| `-a, --all` | 发布所有包 |
| `-v, --verbose` | 详细输出 |
| `-c, --clean` | 清理构建缓存 |
| `--no-compile` | 跳过编译步骤 |
| `--no-upload` | 只编译打包，不上传 |

#### 使用示例

```bash
# 基本用法
./scripts/proprietary_publish.sh sage-kernel

# 预演模式发布所有包
./scripts/proprietary_publish.sh --dry-run --all

# 强制发布到测试PyPI
./scripts/proprietary_publish.sh --force --test-pypi sage-middleware

# 详细输出并清理缓存
./scripts/proprietary_publish.sh --verbose --clean --all

# 只编译不上传
./scripts/proprietary_publish.sh --no-upload --output /tmp/build sage-core
```

### 快捷脚本 `quick_publish.sh`

提供预定义的发布方案，简化常用操作。

#### 预定义方案

| 方案 | 说明 |
|------|------|
| `dev-test` | 开发测试 - 预演模式发布所有包到Test PyPI |
| `staging` | 预发布 - 发布核心包到Test PyPI |
| `production` | 生产发布 - 发布所有包到PyPI |
| `core-only` | 仅核心包 - 发布核心包到PyPI |
| `enterprise` | 企业版 - 发布企业版包 |
| `community` | 社区版 - 发布社区版包 |
| `single <package>` | 单包发布 - 发布指定单个包 |
| `custom` | 自定义 - 交互模式 |

#### 使用示例

```bash
# 开发测试
./scripts/quick_publish.sh dev-test

# 生产发布
./scripts/quick_publish.sh production

# 企业版发布
./scripts/quick_publish.sh enterprise --force

# 单包发布到测试环境
./scripts/quick_publish.sh single sage-kernel --test-pypi

# 交互模式选择
./scripts/quick_publish.sh custom
```

### 配置文件 `proprietary_publish_config.sh`

包含所有可配置的参数和函数库。

#### 主要配置项

- **基础配置**: 输出目录、PyPI仓库等
- **包配置**: 包优先级、依赖关系、分类等
- **编译配置**: 排除模式、保留源码等
- **构建配置**: 构建工具选项、并行设置等
- **上传配置**: Twine选项、重试机制等
- **安全配置**: 代码混淆、压缩设置等
- **通知配置**: 邮件、Slack、企业微信等

#### 自定义配置

可以在项目根目录或包目录下创建 `.publish_config` 文件来覆盖默认配置：

```bash
# 在包目录下创建配置文件
echo 'ENABLE_OBFUSCATION=false' > packages/sage-kernel/.publish_config
echo 'OBFUSCATION_LEVEL=1' >> packages/sage-kernel/.publish_config
```

## 包依赖关系

脚本会按照以下依赖关系顺序发布包：

```
sage-kernel (优先级1)
├── sage-middleware (优先级2) 
├── sage-core (优先级3)
├── sage-utils (优先级4)
│   ├── sage-cli (优先级5)
│   ├── sage-dev-toolkit (优先级6)
│   └── sage-frontend (优先级7)
```

## 发布流程

1. **环境检查**: 验证Python版本、依赖工具等
2. **包验证**: 检查包路径、配置文件等  
3. **依赖分析**: 确定发布顺序
4. **确认发布**: 显示发布计划，等待用户确认
5. **清理缓存**: 清理旧的构建文件
6. **编译源码**: 将Python源码编译为字节码
7. **构建包**: 使用build工具生成wheel包
8. **上传发布**: 使用twine上传到PyPI
9. **生成报告**: 生成详细的发布报告
10. **清理临时**: 清理临时文件和目录

## 安全特性

### 源码保护
- 将所有Python源文件编译为字节码(.pyc)
- 支持多级代码混淆
- 自动删除调试信息和注释
- 可配置的文件排除规则

### 发布安全
- 支持dry-run预演模式
- 强制确认机制
- 失败回滚机制
- 构建文件备份

## 日志和报告

### 日志文件
默认日志文件位置: `~/.sage/dist/publish.log`

### 发布报告
每次发布后会生成详细报告，包含：
- 发布时间和模式
- 包列表和版本信息
- 构建文件清单
- 环境信息
- 错误和警告信息

## 故障排除

### 常见问题

1. **编译失败**
   ```bash
   # 检查Python版本和依赖
   python3 --version
   pip list | grep sage
   ```

2. **上传失败**
   ```bash
   # 检查PyPI凭据配置
   keyring get https://upload.pypi.org/legacy/ __token__
   
   # 手动上传测试
   twine upload --repository testpypi dist/*.whl
   ```

3. **权限问题**
   ```bash
   # 确保脚本可执行
   chmod +x scripts/*.sh
   
   # 检查输出目录权限
   ls -la ~/.sage/dist/
   ```

### 调试模式

启用详细输出来调试问题：

```bash
# 启用详细输出
./scripts/proprietary_publish.sh --verbose --dry-run sage-kernel

# 保留构建文件进行检查
KEEP_BUILD_DIR=true ./scripts/proprietary_publish.sh --dry-run sage-kernel
```

## 开发和扩展

### 添加新包

1. 在 `packages/` 目录下创建新包
2. 更新配置文件中的包列表和依赖关系
3. 测试发布流程

### 自定义编译逻辑

可以在包目录下创建 `.compile_hook.sh` 脚本来定制编译过程：

```bash
#!/bin/bash
# packages/sage-example/.compile_hook.sh

# 自定义编译前处理
pre_compile() {
    echo "执行自定义预处理..."
}

# 自定义编译后处理  
post_compile() {
    echo "执行自定义后处理..."
}
```

### 添加通知渠道

在配置文件中添加新的通知函数：

```bash
# 自定义通知函数
send_custom_notification() {
    local message="$1"
    # 实现自定义通知逻辑
}
```

## 许可证

本脚本套件遵循 Apache-2.0 许可证。

## 支持

如有问题或建议，请提交 Issue 或 Pull Request。

---

**注意**: 闭源发布涉及知识产权保护，请确保遵循相关法律法规和公司政策。
