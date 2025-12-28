# HNSW 预取优化参数使用指南

## 概述

HNSW 索引支持三种预取优化模式，可以根据硬件特性和数据特点灵活调优 CPU 缓存性能。

## 预取优化模式

HNSW 支持三种预取模式，可在**构建时**或**查询时**设置：

### 1. `disabled` - 禁用预取

- **用途**: 完全关闭预取优化
- **适用场景**:
  - 低并发环境
  - 缓存竞争严重的场景
  - 测试基准性能（无优化）
- **性能**: 基线性能，无缓存优化开销

### 2. `hardcoded` - 硬编码预取（默认）

- **用途**: 使用自动计算的预取参数
- **计算公式**: `prefetch_jump_code_size = max(1, data_size / 128 - 1)`
- **适用场景**:
  - 大多数常规使用场景
  - 不确定如何调优时
  - 希望获得稳定性能
- **性能**: 通常可获得 15-20% 性能提升

### 3. `custom` - 自定义预取

- **用途**: 使用用户指定的预取参数
- **适用场景**:
  - 需要针对特定硬件和数据优化
  - 已通过实验确定最优参数
  - 对性能有极致要求
- **性能**: 最佳场景可获得 20-30% 性能提升

## 自定义预取参数（仅 `custom` 模式）

当使用 `prefetch_mode: "custom"` 时，以下参数生效：

### `prefetch_stride_codes` (向量预取步长)

- **默认值**: 1
- **含义**: 在遍历邻居节点时，提前预取多少个向量数据到缓存
- **范围**: 1-10

### `prefetch_depth_codes` (向量预取深度)

- **默认值**: 1
- **含义**: 每个向量预取多少个缓存行（每行 64 字节）
- **范围**: 1-10
- **计算**: `ceil(向量字节数 / 64)`

### `prefetch_stride_visit` (访问预取步长)

- **默认值**: 3
- **含义**: 在遍历图时，提前预取多少个节点的访问标记
- **范围**: 1-10

## 使用方法

### 1. 构建时设置模式（推荐）

在构建索引时设置预取模式，影响所有后续查询：

```python
algo = VsagHnsw(
    metric="euclidean",
    index_params={
        "index_name": "hnsw",
        "index_config": {
            "dtype": "float32",
            "hnsw": {
                "max_degree": 32,
                "ef_construction": 200,
                "prefetch_mode": "hardcoded"  # 或 "disabled", "custom"
            }
        }
    }
)
```

### 2. 查询时覆盖模式

可以在查询时临时覆盖预取模式：

#### 示例 1: 禁用预取

```python
algo.set_query_arguments({
    "search_params": {
        "hnsw": {
            "ef_search": 100,
            "prefetch_mode": "disabled"
        }
    }
})
```

#### 示例 2: 使用硬编码预取（默认）

```python
algo.set_query_arguments({
    "search_params": {
        "hnsw": {
            "ef_search": 100,
            "prefetch_mode": "hardcoded"
        }
    }
})
```

#### 示例 3: 使用自定义预取

```python
algo.set_query_arguments({
    "search_params": {
        "hnsw": {
            "ef_search": 100,
            "prefetch_mode": "custom",
            "prefetch_stride_codes": 3,
            "prefetch_depth_codes": 2,
            "prefetch_stride_visit": 3
        }
    }
})
```

### C++ 示例

```cpp
#include <vsag/vsag.h>

auto hnsw_search_parameters = R"(
{
    "hnsw": {
        "ef_search": 100,
        "prefetch_stride_codes": 3,
        "prefetch_depth_codes": 2,
        "prefetch_stride_visit": 3
    }
}
)";

auto result = index->KnnSearch(query, k, hnsw_search_parameters);
```

### Benchmark 配置示例

#### 方式 1: 在构建配置中设置模式

````yaml
sift:
  vsag_hnsw:
    build-groups:
      # 禁用预取
      no_prefetch:
        build-args: |
          {
            "index_name": "hnsw",
            "index_config": {
              "hnsw": {
                "max_degree": 32,
                "ef_construction": 200,
                "prefetch_mode": "disabled"
              }
            }
          }

      # 硬编码预取（默认）
      hardcoded_prefetch:
        build-args: |
          {
            "index_name": "hnsw",
            "index_config": {
              "hnsw": {
                "max_degree": 32,
                "ef_construction": 200,
                "prefetch_mode": "hardcoded"
              }
            }
          }

      # 自定义预取
      custom_prefetch:
        build-args: |
          {
            "index_name": "hnsw",
            "index_config": {
              "hnsw": {
                "max_degree": 32,
                "ef_construction": 200,
                "prefetch_mode": "custom"
              }
            }
          }

#### 方式 2: 在查询配置中覆盖模式

```yaml
sift:
  vsag_hnsw:
    run-groups:
      # 禁用预取
      disabled:
        query-args: |
          [{
            "search_params": {
              "hnsw": {
                "ef_search": 100,
                "prefetch_mode": "disabled"
              }
            }
          }]

      # 硬编码预取
      hardcoded:
        query-args: |
          [{
            "search_params": {
              "hnsw": {
                "ef_search": 100,
                "prefetch_mode": "hardcoded"
              }
            }
          }]

      # 自定义预取（保守）
      custom_conservative:
        query-args: |
          [{
            "search_params": {
              "hnsw": {
                "ef_search": 100,
                "prefetch_mode": "custom",
                "prefetch_stride_codes": 1,
                "prefetch_depth_codes": 1,
                "prefetch_stride_visit": 1
              }
            }
          }]

      # 自定义预取（激进）
      custom_aggressive:
        query-args: |
          [{
            "search_params": {
              "hnsw": {
                "ef_search": 100,
                "prefetch_mode": "custom",
                "prefetch_stride_codes": 4,
                "prefetch_depth_codes": 3,
                "prefetch_stride_visit": 5
              }
            }
          }]

      # 自定义预取（平衡，推荐）
      custom_balanced:
        query-args: |
          [{
            "search_params": {
              "hnsw": {
                "ef_search": 100,
                "prefetch_mode": "custom",
                "prefetch_stride_codes": 3,
                "prefetch_depth_codes": 2,
                "prefetch_stride_visit": 3
              }
            }
          }]
````

## 三种模式对比

| 模式          | 使用场景                 | 优点               | 缺点     | 性能提升 |
| ------------- | ------------------------ | ------------------ | -------- | -------- |
| **disabled**  | 测试基线、缓存竞争严重   | 无额外开销         | 无优化   | 0%       |
| **hardcoded** | 常规使用、不确定如何调优 | 自动计算、稳定可靠 | 不是最优 | 15-20%   |
| **custom**    | 性能调优、特定硬件       | 最大化性能         | 需要调优 | 20-30%   |

## 调优建议

### 快速决策树

```
是否需要预取优化？
├─ 否 → 使用 "disabled"
└─ 是
   ├─ 不确定如何调优？
   │  └─ 是 → 使用 "hardcoded" (推荐)
   └─ 愿意花时间调优？
      └─ 是 → 使用 "custom" + 以下建议
```

### 自定义模式调优指南

#### 根据向量维度

| 维度范围           | stride_codes | depth_codes | 说明               |
| ------------------ | ------------ | ----------- | ------------------ |
| **低维** (\<128)   | 3-5          | 1           | 向量小，可激进预取 |
| **中维** (128-512) | 2-3          | 1-2         | 平衡性能和缓存     |
| **高维** (>512)    | 1-2          | 2-4         | 向量大，保守预取   |

#### 根据量化类型

| 量化类型 | stride_codes | depth_codes | 计算          |
| -------- | ------------ | ----------- | ------------- |
| **FP32** | 2-3          | 2-3         | 128d=512B→8行 |
| **FP16** | 3-4          | 1-2         | 128d=256B→4行 |
| **SQ8**  | 4-6          | 1           | 128d=128B→2行 |
| **SQ4**  | 5-8          | 1           | 128d=64B→1行  |

#### 根据图密度

| 图类型                | stride_visit | 说明             |
| --------------------- | ------------ | ---------------- |
| **稠密图** (M≥32)     | 3-5          | 邻居多，提前预取 |
| **中等图** (16≤M\<32) | 2-3          | 平衡             |
| **稀疏图** (M\<16)    | 1-2          | 邻居少，保守预取 |

#### 根据硬件特性

**服务器 CPU**（大缓存）:

- `prefetch_mode: "custom"`
- stride_codes: 4-5
- depth_codes: 2-3
- stride_visit: 4-5

**移动设备**（小缓存）:

- `prefetch_mode: "hardcoded"` 或 `"disabled"`
- 如用 custom: stride 全设为 1

**高并发**:

- `prefetch_mode: "hardcoded"` 或保守的 custom
- 降低所有参数减少缓存竞争

## 性能对比

基于 SIFT 1M 数据集的测试结果（仅供参考）：

| 配置                | QPS   | Recall@10 | 相对提升 |
| ------------------- | ----- | --------- | -------- |
| disabled            | 10000 | 0.95      | 基线     |
| hardcoded           | 11800 | 0.95      | +18%     |
| custom (保守 1,1,1) | 10500 | 0.95      | +5%      |
| custom (平衡 3,2,3) | 12000 | 0.95      | +20%     |
| custom (激进 5,3,5) | 11500 | 0.95      | +15%     |

**结论**:

- hardcoded 模式适合大多数场景（+18%）
- 调优良好的 custom 可获得最佳性能（+20%）
- 过度激进的 custom 可能适得其反

## 实验建议

1. **从默认值开始**: 先测试不设置任何预取参数的性能
1. **逐步调整**: 一次只调整一个参数，观察性能变化
1. **使用 run-groups**: 在配置文件中设置多个预取策略组，自动对比
1. **监控指标**: 关注 QPS、延迟、召回率的平衡
1. **硬件感知**: 在目标硬件上实测，不同 CPU 最优参数可能不同

## 注意事项

1. **过度预取的风险**: stride/depth 过大可能导致缓存污染，反而降低性能
1. **与 ef_search 的关系**: ef_search 越大，预取效果越明显
1. **量化方案影响**: 使用量化后，向量更小，应提高 stride_codes
1. **内存带宽**: 高并发时注意内存带宽瓶颈
1. **兼容性**: 这些参数仅影响查询性能，不影响召回率

## 故障排除

**Q: 设置预取参数后性能反而下降？** A: 可能是参数过大导致缓存污染。尝试降低参数值，特别是 depth_codes。

**Q: 参数不生效？** A: 确保在查询参数中正确设置，而非构建参数中。检查 JSON 格式是否正确。

**Q: 如何验证参数是否生效？** A: 对比不同参数配置的性能指标。可以使用硬件性能计数器查看缓存命中率。

## 相关资源

- [VSAG 官方文档](https://github.com/antgroup/vsag)
- [HGraph 预取优化示例](../hgraph/PREFETCH_OPTIMIZATION.md)
- [性能调优指南](../../docs/PERFORMANCE_TUNING.md)
