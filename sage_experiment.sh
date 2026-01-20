#!/bin/bash
# =============================================================================
# SAGE 分布式 LLM 推理编排系统 - 论文实验脚本
# =============================================================================
#
# 实验目标：
#   1. 水平扩展性：节点数增加时吞吐量近线性增长
#   2. 调度效率：不同调度策略在异构负载下的性能差异
#   3. 尾延迟控制：通过负载均衡降低 P99 延迟
#   4. 多租户隔离：并发执行多个 pipeline 时的资源隔离
#
# 硬件环境：
#   - 集群规模：16 节点 (sage-node-1 为 head，sage-node-2..16 为 worker)
#   - 每节点配置：8 CPU 核心，32GB 内存
#   - GPU 服务：独立 A100 (80GB) 服务器，通过 vLLM 提供 LLM 推理
#   - 网络：节点间千兆互联
#
# 使用方法：
#   ./run_experiments_tmux.sh           # 通过 tmux 运行（推荐）
#   ./sage_experiment.sh                # 直接运行
#   ./sage_experiment.sh --quick        # 快速测试模式
#   ./sage_experiment.sh --exp 1        # 仅运行实验1
#   ./sage_experiment.sh --exp 1,3,5    # 运行指定实验
#
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# 配置参数
# -----------------------------------------------------------------------------

# 实验结果根目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_ROOT="results/paper_experiments_${TIMESTAMP}"

# Python 脚本路径
EXP_BASE="packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments"
EXP1_SCRIPT="${EXP_BASE}/exp1_single_vs_multi/run_experiment.py"
EXP2_SCRIPT="${EXP_BASE}/exp2_high_load_parallel/run_experiment.py"
EXP3_SCRIPT="${EXP_BASE}/exp3_latency_throughput/run_experiment.py"
EXP4_SCRIPT="${EXP_BASE}/exp4_parallel_jobs/run_experiment.py"

# 默认实验规模（论文级别）
SCALABILITY_TASKS=5000      # 横向扩展实验任务数
SCHEDULER_TASKS=5000        # 调度策略实验任务数
CONCURRENCY_TASKS=5000      # 并发实验任务数
ISOLATION_TASKS=5000        # 隔离实验每 pipeline 任务数
STRESS_TASKS=10000          # 压力测试任务数

# 快速测试模式参数
QUICK_SCALABILITY_TASKS=500
QUICK_SCHEDULER_TASKS=500
QUICK_CONCURRENCY_TASKS=500
QUICK_ISOLATION_TASKS=500
QUICK_STRESS_TASKS=1000

# 实验开关（默认全部运行）
RUN_EXP1=true   # 横向扩展
RUN_EXP2=true   # 调度策略
RUN_EXP3=true   # 负载级别
RUN_EXP4=true   # 并发与延迟
RUN_EXP5=true   # 多管道隔离
RUN_EXP6=false  # 压力测试（默认关闭，需显式启用）

# 快速模式标志
QUICK_MODE=false

# -----------------------------------------------------------------------------
# 命令行参数解析
# -----------------------------------------------------------------------------

print_usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --quick           快速测试模式（减少任务数和节点数）"
    echo "  --exp <list>      指定要运行的实验（逗号分隔，如 1,3,5）"
    echo "  --stress          启用压力测试（实验6）"
    echo "  --all             运行所有实验（包括压力测试）"
    echo "  -h, --help        显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    运行全部实验（实验1-5）"
    echo "  $0 --quick            快速测试模式"
    echo "  $0 --exp 1,2          仅运行实验1和实验2"
    echo "  $0 --all              运行所有实验（包括压力测试）"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --exp)
            # 解析实验列表
            RUN_EXP1=false
            RUN_EXP2=false
            RUN_EXP3=false
            RUN_EXP4=false
            RUN_EXP5=false
            RUN_EXP6=false
            IFS=',' read -ra EXPS <<< "$2"
            for exp in "${EXPS[@]}"; do
                case $exp in
                    1) RUN_EXP1=true ;;
                    2) RUN_EXP2=true ;;
                    3) RUN_EXP3=true ;;
                    4) RUN_EXP4=true ;;
                    5) RUN_EXP5=true ;;
                    6) RUN_EXP6=true ;;
                    *) echo "警告: 未知实验编号 $exp" ;;
                esac
            done
            shift 2
            ;;
        --stress)
            RUN_EXP6=true
            shift
            ;;
        --all)
            RUN_EXP1=true
            RUN_EXP2=true
            RUN_EXP3=true
            RUN_EXP4=true
            RUN_EXP5=true
            RUN_EXP6=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "错误: 未知选项 $1"
            print_usage
            exit 1
            ;;
    esac
done

# 快速模式：调整参数
if [ "$QUICK_MODE" = true ]; then
    SCALABILITY_TASKS=$QUICK_SCALABILITY_TASKS
    SCHEDULER_TASKS=$QUICK_SCHEDULER_TASKS
    CONCURRENCY_TASKS=$QUICK_CONCURRENCY_TASKS
    ISOLATION_TASKS=$QUICK_ISOLATION_TASKS
    STRESS_TASKS=$QUICK_STRESS_TASKS
    RESULTS_ROOT="results/quick_test_${TIMESTAMP}"
    echo ">>> 快速测试模式已启用"
fi

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------

# 资源清理
cleanup_resources() {
    echo ""
    echo "[Cleanup] 正在清理集群资源..."
    echo "y" | sage job cleanup 2>/dev/null || true
    sleep 3
    echo "[Cleanup] 清理完成"
    echo ""
}

# 打印进度
print_progress() {
    local exp_name="$1"
    local exp_num="$2"
    local total="$3"
    echo ""
    echo "==========================================================================="
    echo " 实验 ${exp_num}/${total}: ${exp_name}"
    echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "==========================================================================="
    echo ""
}

# 实验完成标记
mark_experiment_done() {
    local exp_name="$1"
    local output_dir="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ${exp_name} 完成" >> "${RESULTS_ROOT}/experiment_log.txt"
    echo "[DONE] ${exp_name} 结果保存至: ${output_dir}"
}

# 错误处理
handle_error() {
    local exp_name="$1"
    echo "[ERROR] ${exp_name} 执行失败" >> "${RESULTS_ROOT}/experiment_log.txt"
    echo "[ERROR] ${exp_name} 执行失败，继续下一个实验..."
    cleanup_resources
}

# -----------------------------------------------------------------------------
# 初始化
# -----------------------------------------------------------------------------

mkdir -p "${RESULTS_ROOT}"
echo "=============================================================================" | tee "${RESULTS_ROOT}/experiment_log.txt"
echo " SAGE 论文实验套件" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo " 开始时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo " 结果目录: ${RESULTS_ROOT}" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo " 快速模式: ${QUICK_MODE}" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo "=============================================================================" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo ""

# 统计要运行的实验数量
TOTAL_EXPS=0
[[ "$RUN_EXP1" = true ]] && ((TOTAL_EXPS++)) || true
[[ "$RUN_EXP2" = true ]] && ((TOTAL_EXPS++)) || true
[[ "$RUN_EXP3" = true ]] && ((TOTAL_EXPS++)) || true
[[ "$RUN_EXP4" = true ]] && ((TOTAL_EXPS++)) || true
[[ "$RUN_EXP5" = true ]] && ((TOTAL_EXPS++)) || true
[[ "$RUN_EXP6" = true ]] && ((TOTAL_EXPS++)) || true
CURRENT_EXP=0

echo "将运行 ${TOTAL_EXPS} 个实验"
echo ""

# =============================================================================
# 实验1: 横向扩展实验（Horizontal Scalability）
# =============================================================================
# 目的：验证系统的水平扩展性，证明吞吐量随节点数近线性增长
#
# 设计原理：
#   - 固定任务数，变化节点数 (1→4→8→16)
#   - 使用 compute pipeline 排除 I/O 影响，测试纯调度性能
#   - 使用 rag pipeline 测试真实工作负载
#   - 每个配置重复测试以确保统计显著性
#
# 关键指标：
#   - 吞吐量 (tasks/sec)
#   - 加速比 = 多节点吞吐量 / 单节点吞吐量
#   - P99 延迟
#   - 节点负载均衡度
#
# 预期结果：
#   - 理想加速比为 N（N 为节点数）
#   - 实际因调度开销可能达到 0.85N-0.95N
# =============================================================================

if [ "$RUN_EXP1" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "横向扩展实验 (Horizontal Scalability)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP1_OUTPUT="${RESULTS_ROOT}/exp1_scalability"
    mkdir -p "$EXP1_OUTPUT"

    # 1a. Compute Pipeline 扩展性测试（排除 I/O 影响）
    echo ">>> 1a. Compute Pipeline 横向扩展测试"
    for nodes in 1 4 8 16; do
        echo "    - 测试 ${nodes} 节点, ${SCALABILITY_TASKS} 任务 (compute)"
        python "${EXP1_SCRIPT}" \
            --nodes "${nodes}" \
            --tasks "${SCALABILITY_TASKS}" \
            --pipeline compute \
            --output "${EXP1_OUTPUT}/compute_nodes${nodes}" \
            || handle_error "exp1_compute_${nodes}nodes"
        cleanup_resources
    done

    # 1b. RAG Pipeline 扩展性测试（真实工作负载）
    echo ">>> 1b. RAG Pipeline 横向扩展测试"
    for nodes in 1 4 8 16; do
        echo "    - 测试 ${nodes} 节点, ${SCALABILITY_TASKS} 任务 (rag)"
        python "${EXP1_SCRIPT}" \
            --nodes "${nodes}" \
            --tasks "${SCALABILITY_TASKS}" \
            --pipeline rag \
            --output "${EXP1_OUTPUT}/rag_nodes${nodes}" \
            || handle_error "exp1_rag_${nodes}nodes"
        cleanup_resources
    done

    # 1c. Mixed Pipeline 扩展性测试（异构工作负载）
    echo ">>> 1c. Mixed Pipeline 横向扩展测试"
    for nodes in 4 8 16; do
        echo "    - 测试 ${nodes} 节点, ${SCALABILITY_TASKS} 任务 (mixed)"
        python "${EXP1_SCRIPT}" \
            --nodes "${nodes}" \
            --tasks "${SCALABILITY_TASKS}" \
            --pipeline mixed \
            --output "${EXP1_OUTPUT}/mixed_nodes${nodes}" \
            || handle_error "exp1_mixed_${nodes}nodes"
        cleanup_resources
    done

    mark_experiment_done "实验1: 横向扩展" "$EXP1_OUTPUT"
fi

# =============================================================================
# 实验2: 调度策略对比（Scheduling Strategy Analysis）
# =============================================================================
# 目的：对比不同调度策略的性能差异，验证 LoadAware 调度器的优势
#
# 设计原理：
#   - 固定节点数和任务数，对比 FIFO/LoadAware/RoundRobin/Priority
#   - 在不同负载级别下测试各调度器表现
#   - LoadAware 支持 spread（负载均衡）和 pack（资源集中）两种策略
#
# 关键指标：
#   - 吞吐量
#   - 节点负载均衡度（标准差）
#   - 调度开销（scheduling latency）
#   - 尾延迟（P95/P99）
#
# 预期结果：
#   - LoadAware(spread) 在负载均衡和尾延迟上表现最佳
#   - FIFO 有最低调度开销但负载不均
#   - Priority 在优先级差异大时表现优异
# =============================================================================

if [ "$RUN_EXP2" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "调度策略对比实验 (Scheduling Strategy)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP2_OUTPUT="${RESULTS_ROOT}/exp2_scheduling"
    mkdir -p "$EXP2_OUTPUT"

    # 2a. 4节点集群调度策略对比（使用 high 级别：2500任务，8节点，64并行）
    echo ">>> 2a. 调度策略对比 (high 级别: 2500任务, 8节点)"
    python "${EXP2_SCRIPT}" \
        --schedulers fifo load_aware_spread load_aware_pack round_robin priority \
        --load-level high \
        --output "${EXP2_OUTPUT}/high_schedulers" \
        || handle_error "exp2_high_schedulers"
    cleanup_resources

    # 2b. 16节点集群调度策略对比（使用 extreme 级别：5000任务，16节点，128并行）
    echo ">>> 2b. 调度策略对比 (extreme 级别: 5000任务, 16节点)"
    python "${EXP2_SCRIPT}" \
        --schedulers fifo load_aware_spread load_aware_pack round_robin priority \
        --load-level extreme \
        --output "${EXP2_OUTPUT}/extreme_schedulers" \
        || handle_error "exp2_extreme_schedulers"
    cleanup_resources

    mark_experiment_done "实验2: 调度策略" "$EXP2_OUTPUT"
fi

# =============================================================================
# 实验3: 负载级别与系统容量（Load Levels and System Capacity）
# =============================================================================
# 目的：测试系统在不同负载级别下的表现，找到系统容量边界
#
# 设计原理（论文级别规模）：
#   - 低负载：并行度 4，2节点，500任务
#   - 中负载：并行度 16，4节点，1000任务
#   - 高负载：并行度 64，8节点，2500任务
#   - 极高负载：并行度 128，16节点，5000任务
#
# 关键指标：
#   - 吞吐量随负载变化的曲线
#   - 排队延迟（queue latency）
#   - 系统资源利用率
#
# 预期结果：
#   - 低负载时资源利用率低，吞吐量线性增长
#   - 高负载时开始出现排队，延迟上升
#   - 极高负载时可能触发背压或拒绝
# =============================================================================

if [ "$RUN_EXP3" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "负载级别实验 (Load Levels)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP3_OUTPUT="${RESULTS_ROOT}/exp3_load_levels"
    mkdir -p "$EXP3_OUTPUT"

    # 3a. 负载级别对比
    echo ">>> 3a. 负载级别对比（低/中/高/极高）"
    python "${EXP2_SCRIPT}" \
        --load-levels low medium high extreme \
        --output "${EXP3_OUTPUT}/load_levels" \
        || handle_error "exp3_load_levels"
    cleanup_resources

    # 3b. 流水线深度对比（使用 extreme 级别：5000任务）
    echo ">>> 3b. 流水线深度对比（2/3/5阶段, extreme 级别: 5000任务）"
    python "${EXP2_SCRIPT}" \
        --depths shallow medium deep \
        --load-level extreme \
        --output "${EXP3_OUTPUT}/pipeline_depths" \
        || handle_error "exp3_pipeline_depths"
    cleanup_resources

    mark_experiment_done "实验3: 负载级别" "$EXP3_OUTPUT"
fi

# =============================================================================
# 实验4: 并发级别与延迟特性（Concurrency and Latency）
# =============================================================================
# 目的：找到系统最优并发度，分析吞吐量-延迟权衡曲线
#
# 设计原理：
#   - 变化并发度 (1/2/4/8/16/32/64)
#   - 固定节点数（8节点）和任务数
#   - 测量每个并发度下的吞吐量和延迟分布
#
# 关键指标：
#   - 吞吐量-延迟曲线（找到拐点）
#   - 最优工作点（吞吐量/延迟比最大）
#   - 延迟分解（调度延迟 vs 排队延迟 vs 执行延迟）
#
# 预期结果：
#   - 低并发：延迟低但吞吐量受限
#   - 中并发：吞吐量和延迟达到平衡
#   - 高并发：吞吐量饱和，延迟急剧上升
# =============================================================================

if [ "$RUN_EXP4" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "并发级别与延迟特性实验 (Concurrency and Latency)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP4_OUTPUT="${RESULTS_ROOT}/exp4_concurrency"
    mkdir -p "$EXP4_OUTPUT"

    # 4a. 并发度扩展（compute pipeline，排除 I/O）
    echo ">>> 4a. 并发度扩展测试 (compute)"
    python "${EXP3_SCRIPT}" \
        --concurrency 1 2 4 8 16 32 64 \
        --tasks "${CONCURRENCY_TASKS}" \
        --pipeline compute \
        --output "${EXP4_OUTPUT}/concurrency_compute" \
        || handle_error "exp4_concurrency_compute"
    cleanup_resources

    # 4b. 并发度扩展（rag pipeline，真实负载）
    echo ">>> 4b. 并发度扩展测试 (rag)"
    python "${EXP3_SCRIPT}" \
        --concurrency 1 2 4 8 16 32 \
        --tasks "${CONCURRENCY_TASKS}" \
        --pipeline rag \
        --output "${EXP4_OUTPUT}/concurrency_rag" \
        || handle_error "exp4_concurrency_rag"
    cleanup_resources

    # 4c. 延迟分解实验（light/medium/heavy 任务复杂度）
    echo ">>> 4c. 延迟分解实验（light/medium/heavy, ${CONCURRENCY_TASKS} 任务）"
    python "${EXP3_SCRIPT}" \
        --latency-breakdown \
        --tasks "${CONCURRENCY_TASKS}" \
        --nodes 8 \
        --parallelism 32 \
        --output "${EXP4_OUTPUT}/latency_breakdown" \
        || handle_error "exp4_latency_breakdown"
    cleanup_resources

    # 4d. 调度器开销对比
    echo ">>> 4d. 调度器开销对比（${CONCURRENCY_TASKS} 任务）"
    python "${EXP3_SCRIPT}" \
        --scheduler-overhead \
        --schedulers fifo load_aware round_robin priority \
        --tasks "${CONCURRENCY_TASKS}" \
        --parallelism 32 \
        --output "${EXP4_OUTPUT}/scheduler_overhead" \
        || handle_error "exp4_scheduler_overhead"
    cleanup_resources

    mark_experiment_done "实验4: 并发与延迟" "$EXP4_OUTPUT"
fi

# =============================================================================
# 实验5: 多管道隔离（Multi-Pipeline Isolation）
# =============================================================================
# 目的：测试多个 pipeline 同时运行时的隔离性和资源竞争
#
# 设计原理：
#   - 多个不同类型的 pipeline 同时运行
#   - 对比同时启动 vs 交错启动（Admission Control）
#   - 测量各 pipeline 之间的相互影响
#
# Pipeline 类型：
#   - compute: 纯计算任务（快速，排除 I/O）
#   - llm: LLM 推理任务（GPU 依赖）
#   - rag: 标准 RAG 检索+生成
#   - rag_service: RAG 服务模式（通过服务调用）
#   - adaptive_rag: 自适应 RAG（动态迭代，较慢）
#
# 场景：
#   - 场景A：异构 pipeline 组合（rag_service + compute + llm）
#   - 场景B：同构 pipeline 竞争（rag × 3）
#   - 场景C：交错启动策略对比
#   - 场景D：作业数量扩展性
#   - 场景E：大规模异构（compute + llm + adaptive_rag + rag）
#
# 关键指标：
#   - 各 pipeline 的吞吐量方差（越小越好）
#   - P99 延迟的一致性
#   - 资源隔离效果
#
# 预期结果：
#   - 交错启动可降低资源竞争，提高公平性
#   - 异构 pipeline 可能有更好的资源利用率
#   - adaptive_rag 因迭代特性，需要更多资源隔离
# =============================================================================

if [ "$RUN_EXP5" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "多管道隔离实验 (Multi-Pipeline Isolation)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP5_OUTPUT="${RESULTS_ROOT}/exp5_isolation"
    mkdir -p "$EXP5_OUTPUT"

    # 5a. 异构 pipeline 同时运行（包含 rag_service 服务模式）
    echo ">>> 5a. 异构 pipeline 同时运行 (rag_service + compute + llm)"
    python "${EXP4_SCRIPT}" \
        --pipelines rag_service compute llm \
        --delay 0.0 \
        --tasks "${ISOLATION_TASKS}" \
        --nodes 8 \
        --output "${EXP5_OUTPUT}/heterogeneous_concurrent" \
        || handle_error "exp5_heterogeneous_concurrent"
    cleanup_resources

    # 5b. 同构 pipeline 竞争
    echo ">>> 5b. 同构 pipeline 竞争 (rag x 3)"
    python "${EXP4_SCRIPT}" \
        --pipelines rag rag rag \
        --delay 0.0 \
        --tasks "${ISOLATION_TASKS}" \
        --nodes 8 \
        --output "${EXP5_OUTPUT}/homogeneous_concurrent" \
        || handle_error "exp5_homogeneous_concurrent"
    cleanup_resources

    # 5c. 交错启动 vs 同时启动对比
    echo ">>> 5c. Admission Control 对比 (延迟: 0s, 1s, 2s, 5s)"
    python "${EXP4_SCRIPT}" \
        --experiment staggered \
        --pipelines rag compute llm \
        --tasks "${ISOLATION_TASKS}" \
        --nodes 8 \
        --output "${EXP5_OUTPUT}/staggered_comparison" \
        || handle_error "exp5_staggered_comparison"
    cleanup_resources

    # 5d. 作业数量扩展性
    echo ">>> 5d. 作业数量扩展性 (1/2/4/8 并发作业)"
    python "${EXP4_SCRIPT}" \
        --experiment scaling \
        --base-pipeline rag \
        --num-jobs 1 2 4 8 \
        --tasks "${ISOLATION_TASKS}" \
        --nodes 16 \
        --output "${EXP5_OUTPUT}/job_scaling" \
        || handle_error "exp5_job_scaling"
    cleanup_resources

    # 5e. 大规模异构负载（包含 adaptive_rag 自适应 RAG）
    echo ">>> 5e. 大规模异构负载 (compute + llm + adaptive_rag + rag)"
    python "${EXP4_SCRIPT}" \
        --pipelines compute llm adaptive_rag rag \
        --delay 1.0 \
        --tasks "${ISOLATION_TASKS}" "${ISOLATION_TASKS}" "${ISOLATION_TASKS}" "${ISOLATION_TASKS}" \
        --nodes 16 \
        --output "${EXP5_OUTPUT}/large_scale_heterogeneous" \
        || handle_error "exp5_large_scale_heterogeneous"
    cleanup_resources

    mark_experiment_done "实验5: 多管道隔离" "$EXP5_OUTPUT"
fi

# =============================================================================
# 实验6: 极限压力测试（Stress Test）[可选]
# =============================================================================
# 目的：测试系统在极限负载下的稳定性和恢复能力
#
# 警告：此实验可能导致系统资源耗尽，请确保：
#   - 有足够的监控手段
#   - 可以手动停止实验
#   - 系统有自动恢复机制
#
# 测试项：
#   - 最大节点数 + 最大任务数
#   - 持续高负载
#   - 错误率和恢复能力
# =============================================================================

if [ "$RUN_EXP6" = true ]; then
    ((CURRENT_EXP++)) || true
    print_progress "极限压力测试 (Stress Test)" "$CURRENT_EXP" "$TOTAL_EXPS"

    EXP6_OUTPUT="${RESULTS_ROOT}/exp6_stress"
    mkdir -p "$EXP6_OUTPUT"

    echo ">>> 6a. 最大规模压力测试 (16节点, ${STRESS_TASKS}任务, compute)"
    python "${EXP1_SCRIPT}" \
        --nodes 16 \
        --tasks "${STRESS_TASKS}" \
        --pipeline compute \
        --output "${EXP6_OUTPUT}/max_scale_compute" \
        || handle_error "exp6_max_scale_compute"
    cleanup_resources

    echo ">>> 6b. 最大规模 RAG 压力测试 (16节点, ${STRESS_TASKS}任务, rag)"
    python "${EXP1_SCRIPT}" \
        --nodes 16 \
        --tasks "${STRESS_TASKS}" \
        --pipeline rag \
        --output "${EXP6_OUTPUT}/max_scale_rag" \
        || handle_error "exp6_max_scale_rag"
    cleanup_resources

    echo ">>> 6c. 高并发压力测试 (并发度 128)"
    python "${EXP3_SCRIPT}" \
        --concurrency 64 128 \
        --tasks "${STRESS_TASKS}" \
        --pipeline compute \
        --output "${EXP6_OUTPUT}/high_concurrency" \
        || handle_error "exp6_high_concurrency"
    cleanup_resources

    mark_experiment_done "实验6: 压力测试" "$EXP6_OUTPUT"
fi

# =============================================================================
# 实验完成
# =============================================================================

echo ""
echo "==========================================================================="
echo " 全部实验已完成."
echo " 完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo " 结果目录: ${RESULTS_ROOT}"
echo "==========================================================================="

# 生成实验摘要
echo ""
echo "实验摘要:" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo "----------------------------------------" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
ls -la "${RESULTS_ROOT}/" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo "----------------------------------------" | tee -a "${RESULTS_ROOT}/experiment_log.txt"
echo ""
echo "查看详细结果:"
echo "  cat ${RESULTS_ROOT}/experiment_log.txt"
echo ""
echo "查看各实验结果:"
for dir in "${RESULTS_ROOT}"/exp*; do
    if [ -d "$dir" ]; then
        echo "  $dir"
    fi
done
echo ""