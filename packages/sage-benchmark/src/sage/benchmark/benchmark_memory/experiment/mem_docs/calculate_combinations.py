#!/usr/bin/env python3
"""
计算 SAGE Memory Pipeline 的合理排列组合数量

根据文档 Memory_Pipeline_Dev_Archive.md 的五维度分类和兼容性约束
"""


# ==================== 维度定义 ====================

# D1: Memory Service（数据结构）
D1_SERVICES = [
    "short_term_memory",
    "vector_hash_memory",
    "neuromem_vdb",
    "graph_memory",
    "hierarchical_memory",
    "hybrid_memory",
]

# D2: PreInsert（插入前处理）
D2_PRE_INSERT = [
    "none",
    "transform.summarize",
    "transform.chunking",
    "transform.segment",
    "extract.keyword",
    "extract.entity",
    "extract.noun",
    "extract.triple",
    "score.importance",
    "score.heat",
]

# D3: PostInsert（插入后处理）
D3_POST_INSERT = [
    "none",
    "distillation",
    "crud",
    "link_evolution",
    "migrate",
    "forgetting.ebbinghaus",
    "forgetting.heat_based",
    "forgetting.time_based",
]

# D4: PreRetrieval（检索前处理）
D4_PRE_RETRIEVAL = [
    "none",
    "embedding",
    "optimize.keyword_extract",
    "optimize.expand",
    "optimize.rewrite",
    "validate",
]

# D5: PostRetrieval（检索后处理）
D5_POST_RETRIEVAL = [
    "none",
    "rerank.semantic",
    "rerank.time_weighted",
    "rerank.ppr",
    "rerank.weighted",
    "filter.token_budget",
    "filter.threshold",
    "filter.top_k",
    "merge.link_expand",
    "merge.multi_query",
    "augment.persona",
    "augment.traits",
    "augment.summary",
    "augment.metadata",
]

# ==================== 兼容性约束 ====================

# D3 PostInsert 依赖 D1 Service 的约束
D3_CONSTRAINTS: dict[str, list[str]] = {
    "link_evolution": ["graph_memory"],
    "migrate": ["hierarchical_memory"],
    "forgetting.ebbinghaus": ["hierarchical_memory"],
    "forgetting.heat_based": ["hierarchical_memory"],
    "forgetting.time_based": ["hierarchical_memory"],
    "crud": ["graph_memory", "hybrid_memory"],
}

# D1 Service 允许的 D3 PostInsert Actions
D1_ALLOWS_D3: dict[str, list[str]] = {
    "short_term_memory": ["none"],
    "vector_hash_memory": ["none", "distillation"],
    "neuromem_vdb": ["none", "distillation"],
    "graph_memory": ["none", "link_evolution", "crud"],
    "hierarchical_memory": [
        "none",
        "distillation",
        "migrate",
        "forgetting.ebbinghaus",
        "forgetting.heat_based",
        "forgetting.time_based",
    ],
    "hybrid_memory": ["none", "distillation", "crud"],
}

# ==================== 计算函数 ====================


def is_compatible(service: str, post_insert: str) -> bool:
    """检查 D1 Service 和 D3 PostInsert 是否兼容"""
    return post_insert in D1_ALLOWS_D3.get(service, [])


def count_valid_combinations() -> dict:
    """计算所有有效的组合数量"""

    # 理论最大组合数（不考虑约束）
    theoretical_max = (
        len(D1_SERVICES)
        * len(D2_PRE_INSERT)
        * len(D3_POST_INSERT)
        * len(D4_PRE_RETRIEVAL)
        * len(D5_POST_RETRIEVAL)
    )

    # 计算实际有效组合
    valid_count = 0
    invalid_count = 0

    # 按 Service 分组统计
    service_stats = {}

    for d1 in D1_SERVICES:
        service_valid = 0
        for d2 in D2_PRE_INSERT:
            for d3 in D3_POST_INSERT:
                # 检查 D1-D3 兼容性
                if not is_compatible(d1, d3):
                    invalid_count += len(D4_PRE_RETRIEVAL) * len(D5_POST_RETRIEVAL)
                    continue

                for d4 in D4_PRE_RETRIEVAL:
                    for d5 in D5_POST_RETRIEVAL:
                        valid_count += 1
                        service_valid += 1

        service_stats[d1] = service_valid

    return {
        "theoretical_max": theoretical_max,
        "valid_combinations": valid_count,
        "invalid_combinations": invalid_count,
        "service_stats": service_stats,
        "dimensions": {
            "D1_services": len(D1_SERVICES),
            "D2_pre_insert": len(D2_PRE_INSERT),
            "D3_post_insert": len(D3_POST_INSERT),
            "D4_pre_retrieval": len(D4_PRE_RETRIEVAL),
            "D5_post_retrieval": len(D5_POST_RETRIEVAL),
        },
    }


def print_statistics(stats: dict):
    """打印统计结果"""
    print("=" * 70)
    print("SAGE Memory Pipeline 排列组合统计")
    print("=" * 70)

    print("\n【维度统计】")
    dims = stats["dimensions"]
    print(f"  D1 (Service):       {dims['D1_services']} 种")
    print(f"  D2 (PreInsert):     {dims['D2_pre_insert']} 种")
    print(f"  D3 (PostInsert):    {dims['D3_post_insert']} 种")
    print(f"  D4 (PreRetrieval):  {dims['D4_pre_retrieval']} 种")
    print(f"  D5 (PostRetrieval): {dims['D5_post_retrieval']} 种")

    print("\n【组合数量】")
    print(f"  理论最大组合数:     {stats['theoretical_max']:,}")
    print(f"  实际有效组合数:     {stats['valid_combinations']:,}")
    print(f"  无效组合数:         {stats['invalid_combinations']:,}")
    print(
        f"  有效率:             {stats['valid_combinations'] / stats['theoretical_max'] * 100:.1f}%"
    )

    print("\n【按 Service 分组统计】")
    for service, count in stats["service_stats"].items():
        percentage = count / stats["valid_combinations"] * 100
        print(f"  {service:25s} {count:6,} ({percentage:5.1f}%)")

    print("\n【约束说明】")
    print("  • short_term_memory:   只能使用 none（无后处理）")
    print("  • vector_hash_memory:  支持 none, distillation")
    print("  • neuromem_vdb:        支持 none, distillation")
    print("  • graph_memory:        支持 none, link_evolution, crud")
    print("  • hierarchical_memory: 支持 none, distillation, migrate, forgetting(*3)")
    print("  • hybrid_memory:       支持 none, distillation, crud")

    print("\n【典型配置示例】")
    print("  • TiM:        vector_hash_memory + extract.triple + distillation + embedding + rerank")
    print("  • MemoryBank: hierarchical_memory + none + forgetting + embedding + augment")
    print("  • HippoRAG:   graph_memory + extract.triple + link_evolution + optimize + none")
    print(
        "  • MemoryOS:   hierarchical_memory + score + migrate+forgetting + embedding + merge+augment"
    )

    print("=" * 70)


def generate_compatibility_matrix():
    """生成兼容性矩阵"""
    print("\n【D1-D3 兼容性矩阵】")
    print("-" * 70)

    # 表头
    header = "Service".ljust(25)
    for d3 in D3_POST_INSERT:
        header += f" {d3[:4]}"
    print(header)
    print("-" * 70)

    # 表体
    for d1 in D1_SERVICES:
        row = d1[:24].ljust(25)
        for d3 in D3_POST_INSERT:
            row += " ✓  " if is_compatible(d1, d3) else " ✗  "
        print(row)
    print("-" * 70)


if __name__ == "__main__":
    stats = count_valid_combinations()
    print_statistics(stats)
    generate_compatibility_matrix()
