# pip 安装进度显示改进

## 问题描述

在 `quickstart.sh` 安装过程中，用户反映下载速度慢但看不到具体原因：

```
  → 正在收集: lazy-loader  
    ⬇ 下载中... [9 个文件]  
   [已运行 367s，处理了 672 行输出]
    ⬇ 下载中... [20 个文件]  
   [已运行 429s，处理了 683 行输出]
    ⬇ 下载中... [43 个文件]  
   [已运行 623s，处理了 706 行输出]
    ⬇ 下载中... [51 个文件]  
   [已运行 684s，处理了 714 行输出]
```

**核心问题**：只显示文件数量，没有显示：

- 文件大小
- 下载速度
- 网络性能状态
- 为什么这么慢

## 解决方案

修改 `tools/install/display_tools/logging.sh` 中的 `log_pip_install_with_verbose_progress` 函数。

### 改进 1: 实时显示文件大小和下载速度

**之前**:

```bash
⬇ 下载中... [20 个文件]
```

**之后**:

```bash
⬇ 下载中... [20 个文件, 125.3 MB 已下载, 0.45 MB/s]
```

**实现**：

- 从 pip 输出中提取文件大小（正则：`\(([0-9.]+)[[:space:]]*(kB|MB|GB)\)`）
- 统一转换为 MB
- 计算累计下载大小
- 实时计算下载速度（总大小 / 已用时间）

### 改进 2: 每60秒显示网络性能评估

**之前**:

```bash
[已运行 367s，处理了 672 行输出]
```

**之后**:

```bash
[已运行 367s，处理了 672 行输出，已下载 245.6 MB @ 0.67 MB/s | 正常网络 (0.5-2 MB/s)]
```

如果速度 < 0.3 MB/s，还会显示：

```bash
提示: 下载速度较慢（0.28 MB/s），可能需要检查网络连接或使用镜像源
```

**网络性能分类**：

- **慢速网络**: < 0.5 MB/s（黄色警告）
- **正常网络**: 0.5-2 MB/s（青色）
- **快速网络**: > 2 MB/s（绿色）

### 改进 3: 安装完成后显示总体统计

**新增**:

```bash
📊 安装统计: 共 51 个文件, 328.4 MB, 耗时 684s, 平均 0.48 MB/s
```

## 技术细节

### 文件大小提取

```bash
# 正则匹配 pip 输出中的文件大小
if [[ "$line" =~ \(([0-9.]+)[[:space:]]*(kB|MB|GB)\) ]]; then
    local size="${BASH_REMATCH[1]}"
    local unit="${BASH_REMATCH[2]}"

    # 统一转换为 MB
    case "$unit" in
        kB) last_file_size=$(echo "scale=2; $size / 1024" | bc) ;;
        MB) last_file_size="$size" ;;
        GB) last_file_size=$(echo "scale=2; $size * 1024" | bc) ;;
    esac
fi
```

### 速度计算

```bash
# 实时计算下载速度
local elapsed=$(($(date +%s) - download_start_time))
if [ $elapsed -gt 0 ]; then
    speed_mb=$(echo "scale=2; $total_downloaded_mb / $elapsed" | bc)
fi
```

### 性能评估逻辑

```bash
# bc 命令用于浮点数比较
if [ "$(echo "$avg_speed < 0.5" | bc)" = "1" ]; then
    network_status="${YELLOW}慢速网络${NC}"
elif [ "$(echo "$avg_speed < 2" | bc)" = "1" ]; then
    network_status="${CYAN}正常网络${NC}"
else
    network_status="${GREEN}快速网络${NC}"
fi
```

## 使用场景

这个改进会在以下情况自动生效：

1. **quickstart.sh 安装**:

   - 安装 SAGE 核心依赖时
   - 安装可选依赖（如 vLLM）时

1. **手动 pip 安装**:

   ```bash
   source tools/install/display_tools/logging.sh
   log_pip_install_with_verbose_progress "CONTEXT" "PHASE" "pip install torch"
   ```

## 测试

运行测试脚本验证改进：

```bash
bash tools/install/test_progress_display.sh
```

测试内容：

1. 小包安装（requests）- 验证文件大小和速度显示
1. 大包安装（pandas）- 验证多文件下载和统计

## 预期效果

### 场景 1: 网络正常（1 MB/s）

```
  → 正在收集: torch
    ⬇ 下载中... [8 个文件, 245.3 MB 已下载, 1.02 MB/s]
   [已运行 245s，处理了 156 行输出，已下载 245.3 MB @ 1.00 MB/s | 正常网络 (0.5-2 MB/s)]
    ⬇ 下载中... [15 个文件, 512.8 MB 已下载, 0.98 MB/s]

📊 安装统计: 共 15 个文件, 512.8 MB, 耗时 523s, 平均 0.98 MB/s
```

### 场景 2: 网络慢（0.2 MB/s）

```
  → 正在收集: torch
    ⬇ 下载中... [3 个文件, 45.2 MB 已下载, 0.18 MB/s]
   [已运行 251s，处理了 89 行输出，已下载 45.2 MB @ 0.18 MB/s | 慢速网络 (<0.5 MB/s)]
   提示: 下载速度较慢（0.18 MB/s），可能需要检查网络连接或使用镜像源
```

## 相关文件

- `tools/install/display_tools/logging.sh` - 核心实现
- `tools/install/test_progress_display.sh` - 测试脚本
- `quickstart.sh` - 主安装脚本（自动使用）

## 依赖

- `bc` 命令（浮点数计算）- 大多数 Linux 发行版自带
- Bash 4.0+ （用于正则匹配）

## 后续优化建议

1. **预估剩余时间**: 根据剩余包数量和平均速度估算 ETA
1. **镜像源自动切换**: 检测到慢速时自动建议切换到国内镜像
1. **并行下载统计**: 如果 pip 支持并行下载，统计并行度
1. **历史性能对比**: 记录历史安装速度，对比本次性能
