# VSAG HNSW 参数-优化对应指南

本说明文档帮助你通过 `bench/algorithms/vsag_hnsw/config.yaml` 中的参数，开启或组合 VSAG HNSW 的不同优化技术。示例配置位于 `random-xs`
与 `sift` 节点，可直接复制到新的 run-group 进行对比实验。

## 配置结构概览

```yaml
<dataset>:
  vsag_hnsw:
    run-groups:
      <group-name>:
        args:  |  # 索引构建&运行期优化
          [{"index_name": "hnsw", "index_config": { ... }}]
        query-args: |  # 查询期优化
          [{"search_params": { ... }}]
```

- `args[0].index_name`：索引工厂名称，HNSW 场景固定为 `"hnsw"`。
- `args[0].index_config`：VSAG HNSW JSON 配置，控制构建期和存储优化。
- `query-args[0].search_params`：查询期/运行期优化入口，会在 `set_query_arguments()` 里覆盖默认值。

## 构建期/结构优化 (`index_config`)

| 参数                                                                             | 优化能力                             | 建议/说明                                                        |
| -------------------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------- |
| `hnsw.max_degree`                                                                | 调整图的出度 (M) 决定邻居上限        | 大图/高召回使用 48/64；低资源场景 16/32                          |
| `hnsw.ef_construction`                                                           | 构建过程搜索宽度                     | 数值越高图越致密，建图更慢但召回更好                             |
| `hnsw.use_static`                                                                | 启用静态图                           | 仅适合纯离线批量；流式插入需保持 `false`                         |
| `hnsw.use_reversed_edges`                                                        | 反向边存储                           | 提升查询遍历命中率，需额外内存                                   |
| `hnsw.skip_ratio`                                                                | 分层 Skip-Layer                      | >0 时跳过部分层以减少构建成本，如 `0.1`                          |
| `hnsw.support_duplicate`                                                         | 允许重复向量                         | streaming 去重策略中可设 `true`                                  |
| `optimizer.prefetch_stride_codes / prefetch_stride_visit / prefetch_depth_codes` | CPU 预取调优                         | 减少 cache miss；2~3 常见组合，可作为 run-group 变量             |
| `optimizer.use_elp_optimizer`                                                    | 自动调参器                           | `true` 时让 VSAG 根据硬件自适应上述预取参数                      |
| `index_config.metric_type`                                                       | 距离度量 (l2/ip/cosine)              | 自动从 `@metric` 继承，除非需要手动覆盖                          |
| `index_config.dtype`                                                             | 存储类型 (`float32`/`int8`/`sparse`) | 与数据集 dtype 一致即可；想要 PQ/INT8 可改 `int8` 并提供量化数据 |
| `index_config.max_elements`                                                      | 最大容量                             | 默认跟随 runbook `max_pts`，可手动上调给出余量                   |

## 查询期优化 (`search_params`)

| 参数                                                                        | 优化能力        | 建议/说明                                                                                     |
| --------------------------------------------------------------------------- | --------------- | --------------------------------------------------------------------------------------------- |
| `hnsw.ef_search`                                                            | 查询宽度        | 召回越高、延迟越大；基准常用 80/128/200                                                       |
| `hnsw.searcher_type`                                                        | 搜索器实现      | `basic`：单线程；`parallel`：多线程；`optimized`：带优化器版本。示例中 `sift` 使用 `parallel` |
| `hnsw.prefetch_stride_visit / prefetch_stride_codes / prefetch_depth_codes` | 查询期预取      | 若构建期未固定，可在此与 optimizer 配合做在线微调                                             |
| `hnsw.use_conjugate_graph_search`                                           | 共轭图辅助查询  | `true` 可提升召回，需构建期启用共轭图数据                                                     |
| `hnsw.iterator_filter` 相关参数                                             | 迭代式过滤/分片 | 配合属性过滤或时间戳需求使用                                                                  |

`search_params` 支持 VSAG HNSW JSON 的全部键，未列出的可按 VSAG 官方文档扩展。

## 操作建议

1. **分 Run-group 评估**：在 `config.yaml` 的同一 dataset 下添加多个 `run-groups`（如 `"prefetch-2-1"`,
   `"parallel-search"`），将不同参数组合写入 `args`/`query-args`，运行基准时用 `--run-group` 指定即可。
1. **与 runbook 配合**：`runbooks/algo_optimizations/vsag_hnsw.yaml` 提供了中小规模流式场景，可复制修改
   `batchSize`/`eventRate` 来评估不同动态压力下的优化策略。
1. **增量对比**：
   - 只改 `optimizer.*` 可以观察预取策略对吞吐的影响；
   - 只改 `search_params.hnsw.ef_search` 可以衡量召回-延迟曲线；
   - 启动 `searcher_type = parallel` 后，再调高 `max_degree`/`skip_ratio`，对高维/高并发场景通常收益明显。

通过以上参数映射，你可以快速定位想要实验的 VSAG HNSW 优化技术，并在基准框架中完成自动化对比。\*\*\* End of File
