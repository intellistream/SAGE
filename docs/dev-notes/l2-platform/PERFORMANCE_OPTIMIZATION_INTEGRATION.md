# SAGE 性能优化功能集成指南

本文档说明如何使用新增的性能优化功能（进度条和镜像选择器）。

## 📋 概述

在本次改进中，我们创建了以下性能优化工具：

1. **进度条可视化** (`tools/install/display_tools/progress_bar.sh`)
1. **网络镜像自动选择** (`tools/install/examination_tools/mirror_selector.sh`)

这些工具已经创建并测试完成，但**暂未集成到主安装流程中**，以避免对现有稳定流程造成影响。本文档提供集成指南供未来使用。

______________________________________________________________________

## 🎨 1. 进度条功能

### 功能说明

`progress_bar.sh` 提供纯 bash 实现的进度条，无需任何外部依赖（如 tqdm）。

### 可用函数

```bash
# 基础进度条
show_progress_bar <current> <total> [prefix]

# 阶段进度条（用于安装阶段）
show_phase_progress  # 自动根据当前阶段显示

# 旋转动画
show_spinner <message>
stop_spinner

# 下载进度
show_download_progress <downloaded_mb> <total_mb> <speed>

# 包安装进度
show_package_install_progress <current> <total> <package_name>
```

### 集成示例

#### 示例 1: 在安装脚本中显示包安装进度

```bash
# 在 core_installer.sh 中
source "$SAGE_ROOT/tools/install/display_tools/progress_bar.sh"

# 安装多个包时显示进度
local packages=("sage-common" "sage-kernel" "sage-libs")
local total=${#packages[@]}
local current=0

for package in "${packages[@]}"; do
    current=$((current + 1))
    show_package_install_progress "$current" "$total" "$package"
    pip install -e "packages/$package" --no-deps
done
```

#### 示例 2: 显示阶段进度

```bash
# 在 checkpoint_manager.sh 中
source "$SAGE_ROOT/tools/install/display_tools/progress_bar.sh"

# 在每个阶段开始时调用
mark_phase_start() {
    local phase="$1"
    show_phase_progress  # 自动计算并显示进度
    echo -e "${BLUE}▶️  开始阶段: $phase${NC}"
}
```

### 注意事项

- ✅ 纯 bash 实现，无外部依赖
- ✅ 支持 Unicode 字符（█ ░）
- ⚠️ 需要终端支持 ANSI 转义序列
- ⚠️ 在 CI 环境中可能需要禁用

______________________________________________________________________

## 🚀 2. 网络镜像自动选择

### 功能说明

`mirror_selector.sh` 自动测试多个 PyPI 镜像的响应速度，选择最快的镜像源。

### 可用功能

```bash
# 自动选择最快镜像
bash tools/install/examination_tools/mirror_selector.sh auto

# 交互式选择
bash tools/install/examination_tools/mirror_selector.sh interactive

# 获取 pip 命令参数
pip_args=$(bash tools/install/examination_tools/mirror_selector.sh args)
```

### 集成示例

#### 示例 1: 在安装前自动选择镜像

```bash
# 在 quickstart.sh 开头添加
if [ "$use_mirror" = "true" ]; then
    source "$TOOLS_DIR/examination_tools/mirror_selector.sh"

    echo -e "${INFO} 正在测试 PyPI 镜像速度..."
    FASTEST_MIRROR=$(auto_select_fastest_mirror "pip" "true")

    if [ -n "$FASTEST_MIRROR" ]; then
        export PIP_INDEX_URL="$FASTEST_MIRROR"
        echo -e "${GREEN}✓ 已配置使用最快镜像: $FASTEST_MIRROR${NC}"
    fi
fi
```

#### 示例 2: 提供镜像选择选项

```bash
# 在 argument_parser.sh 中添加参数
--auto-mirror)
    USE_AUTO_MIRROR="true"
    shift
    ;;

# 在主安装流程中
if [ "$USE_AUTO_MIRROR" = "true" ]; then
    source "$TOOLS_DIR/examination_tools/mirror_selector.sh"
    MIRROR_URL=$(auto_select_fastest_mirror "pip" "false")
    PIP_EXTRA_ARGS="$(get_pip_mirror_args "$MIRROR_URL")"
fi
```

#### 示例 3: 配置永久镜像

```bash
# 为用户配置永久 pip 镜像
source tools/install/examination_tools/mirror_selector.sh

# 自动选择并配置
MIRROR_URL=$(auto_select_fastest_mirror)
configure_pip_mirror "$MIRROR_URL" "true"  # true = 永久配置
```

### 支持的镜像源

- 官方源: https://pypi.org/simple
- 清华大学: https://pypi.tuna.tsinghua.edu.cn/simple
- 阿里云: https://mirrors.aliyun.com/pypi/simple
- 腾讯云: https://mirrors.cloud.tencent.com/pypi/simple
- 华为云: https://repo.huaweicloud.com/repository/pypi/simple
- 豆瓣: https://pypi.doubanio.com/simple
- 中国科技大学: https://pypi.mirrors.ustc.edu.cn/simple

### 注意事项

- ✅ 自动测试响应时间（毫秒级）
- ✅ 支持交互式和自动两种模式
- ⚠️ 需要 curl 或 wget
- ⚠️ 网络受限环境可能测试不准确

______________________________________________________________________

## 🔧 3. 推荐的集成方式

### 阶段 1: 实验性功能（当前）

```bash
# 用户可以手动测试这些功能
bash tools/install/examination_tools/mirror_selector.sh auto
bash tools/install/display_tools/progress_bar.sh  # 查看示例
```

### 阶段 2: 可选功能（下一版本）

```bash
# 在 quickstart.sh 中添加选项
./quickstart.sh --auto-mirror     # 自动选择镜像
./quickstart.sh --show-progress   # 显示详细进度条
```

### 阶段 3: 默认启用（稳定后）

```bash
# 默认使用这些优化功能
# 用户可以通过选项禁用
./quickstart.sh --no-auto-mirror
./quickstart.sh --no-progress-bar
```

______________________________________________________________________

## 📊 4. 性能对比

### 镜像自动选择

| 场景     | 不使用镜像选择     | 使用自动镜像选择   | 改进       |
| -------- | ------------------ | ------------------ | ---------- |
| 国内网络 | 慢速下载（国外源） | 快速下载（国内源） | **5-10x**  |
| 国外网络 | 正常速度           | 正常速度           | 1x         |
| 企业代理 | 可能失败           | 自动适配           | 稳定性提升 |

### 进度条显示

| 场景       | 无进度条       | 有进度条           | 用户体验   |
| ---------- | -------------- | ------------------ | ---------- |
| 长时间安装 | 不知道进度     | 清晰了解进度       | ⭐⭐⭐⭐⭐ |
| 网络问题   | 不知道是否卡住 | 可以看到是否有进展 | ⭐⭐⭐⭐⭐ |
| 快速安装   | 影响不大       | 略有帮助           | ⭐⭐⭐     |

______________________________________________________________________

## 🧪 5. 测试验证

### 测试镜像选择器

```bash
# 测试自动选择
bash tools/install/examination_tools/mirror_selector.sh auto

# 测试交互式选择
bash tools/install/examination_tools/mirror_selector.sh interactive

# 测试特定镜像
bash tools/install/examination_tools/mirror_selector.sh test \
    "https://pypi.tuna.tsinghua.edu.cn/simple"
```

### 测试进度条

```bash
# 查看所有示例
bash tools/install/display_tools/progress_bar.sh

# 在脚本中测试
source tools/install/display_tools/progress_bar.sh

# 测试基础进度条
for i in {1..100}; do
    show_progress_bar $i 100 "测试进度"
    sleep 0.05
done

# 测试包安装进度
show_package_install_progress 3 10 "sage-kernel"
```

______________________________________________________________________

## 📝 6. 未来计划

### 短期（v0.1.7）

- [ ] 添加 `--auto-mirror` 和 `--show-progress` 选项
- [ ] 在 CI 环境中自动禁用进度条
- [ ] 添加镜像测试结果缓存

### 中期（v0.1.8）

- [ ] 默认启用自动镜像选择（国内用户）
- [ ] 集成进度条到所有长时间操作
- [ ] 支持自定义镜像配置文件

### 长期（v1.0）

- [ ] 智能镜像切换（失败时自动重试其他镜像）
- [ ] 下载进度实时显示（集成 pip 下载回调）
- [ ] 多线程下载支持

______________________________________________________________________

## ❓ 常见问题

### Q1: 为什么这些功能没有默认启用？

**A**: 为了保证稳定性和兼容性：

- 进度条在某些终端可能显示异常
- 镜像自动选择需要额外的网络请求
- 需要更多用户反馈和测试

### Q2: 如何手动使用这些功能？

**A**: 直接调用对应的脚本即可，参见上面的示例。

### Q3: 这些功能会影响安装速度吗？

**A**:

- 镜像选择：初次测试需要 5-10 秒，但可以显著加快后续下载
- 进度条：几乎无性能影响（纯 bash 实现）

### Q4: CI/CD 环境中可以使用吗？

**A**:

- 镜像选择：可以，有助于提高 CI 稳定性
- 进度条：不推荐，可能干扰日志输出

______________________________________________________________________

## 🔗 相关文档

- [安装指南](../docs-public/docs_src/getting-started/installation.md)
- [性能优化](./DEPENDENCY_OPTIMIZATION.md)
- [开发者文档](../DEVELOPER.md)

______________________________________________________________________

**最后更新**: 2025-11-15\
**维护者**: SAGE Development Team
