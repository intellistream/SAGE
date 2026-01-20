#!/bin/bash
# =============================================================================
# SAGE Scale Up 实验脚本 - LLM 和 RAG Service Pipeline 扩展性测试
# =============================================================================
#
# 实验目标：验证 LLM 和 RAG Service Pipeline 在不同节点数下的扩展性
#
# 使用方法：
#   ./run_scale_up.sh                              # 运行全部配置
#   ./run_scale_up.sh --quick                      # 快速测试模式 (100任务)
#   ./run_scale_up.sh --pipeline llm               # 仅运行 LLM pipeline
#   ./run_scale_up.sh --pipeline rag_service       # 仅运行 RAG Service pipeline
#   ./run_scale_up.sh --nodes "1,2,4"              # 仅运行指定节点规模
#   ./run_scale_up.sh --quick --pipeline llm --nodes "1,2"  # 组合使用
#
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# 配置参数
# -----------------------------------------------------------------------------

# 实验结果目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_ROOT="results/scale_up_${TIMESTAMP}"
OUTPUT_DIR="${RESULTS_ROOT}"
LOG_FILE="${OUTPUT_DIR}/scale_up_log.txt"

# Python 脚本路径
EXP_BASE="packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments"
EXP_SCRIPT="${EXP_BASE}/exp1_single_vs_multi/run_experiment.py"

# 默认参数
DEFAULT_TASKS=5000           # 论文级别任务数
QUICK_TASKS=100              # 快速测试任务数
DEFAULT_NODES="1,2,4,8"      # 默认节点规模
DEFAULT_PIPELINES="llm,rag_service"  # 默认 pipeline 类型

# 运行时参数
TASKS=$DEFAULT_TASKS
NODES=$DEFAULT_NODES
PIPELINES=$DEFAULT_PIPELINES
QUICK_MODE=false

# -----------------------------------------------------------------------------
# 命令行参数解析
# -----------------------------------------------------------------------------

print_usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --quick                  快速测试模式（任务数降为 100）"
    echo "  --pipeline <list>        选择 pipeline 类型（逗号分隔）"
    echo "                           可选: llm, rag_service, all"
    echo "  --nodes <list>           选择节点规模（逗号分隔）"
    echo "                           可选: 1, 2, 4, 8"
    echo "  --tasks <num>            自定义任务数（覆盖默认值）"
    echo "  -h, --help               显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                              运行全部配置（5000任务）"
    echo "  $0 --quick                      快速测试模式（100任务）"
    echo "  $0 --pipeline llm               仅运行 LLM pipeline"
    echo "  $0 --pipeline rag_service       仅运行 RAG Service pipeline"
    echo "  $0 --nodes \"1,2,4\"              仅测试 1/2/4 节点"
    echo "  $0 --quick --pipeline llm       快速测试 LLM pipeline"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            TASKS=$QUICK_TASKS
            shift
            ;;
        --pipeline)
            if [[ "$2" == "all" ]]; then
                PIPELINES=$DEFAULT_PIPELINES
            else
                PIPELINES="$2"
            fi
            shift 2
            ;;
        --nodes)
            NODES="$2"
            shift 2
            ;;
        --tasks)
            TASKS="$2"
            shift 2
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

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------

# 日志记录
log_message() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] ${message}" | tee -a "${LOG_FILE}"
}

# 资源清理
cleanup_resources() {
    echo ""
    log_message "[Cleanup] 正在清理集群资源..."
    echo "y" | sage job cleanup 2>/dev/null || true
    sleep 3
    log_message "[Cleanup] 清理完成"
    echo ""
}

# 打印进度
print_progress() {
    local pipeline="$1"
    local nodes="$2"
    local current="$3"
    local total="$4"
    echo ""
    echo "==========================================================================="
    echo " [${current}/${total}] Pipeline: ${pipeline}, Nodes: ${nodes}"
    echo " 任务数: ${TASKS}"
    echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "==========================================================================="
    echo ""
}

# 实验完成标记
mark_done() {
    local pipeline="$1"
    local nodes="$2"
    local output_dir="$3"
    log_message "[DONE] ${pipeline}_nodes${nodes} 完成，结果保存至: ${output_dir}"
}

# 错误处理
handle_error() {
    local exp_name="$1"
    log_message "[ERROR] ${exp_name} 执行失败，继续下一个实验..."
    cleanup_resources
}

# 计算总实验数
count_experiments() {
    local total=0
    IFS=',' read -ra PIPELINE_ARRAY <<< "$PIPELINES"
    IFS=',' read -ra NODE_ARRAY <<< "$NODES"
    for pipeline in "${PIPELINE_ARRAY[@]}"; do
        for node in "${NODE_ARRAY[@]}"; do
            ((total++)) || true
        done
    done
    echo $total
}

# 运行单个实验
run_experiment() {
    local pipeline="$1"
    local nodes="$2"
    local exp_output_dir="${OUTPUT_DIR}/${pipeline}_nodes${nodes}"

    log_message "开始实验: pipeline=${pipeline}, nodes=${nodes}, tasks=${TASKS}"

    python "${EXP_SCRIPT}" \
        --nodes "${nodes}" \
        --tasks "${TASKS}" \
        --pipeline "${pipeline}" \
        --output "${exp_output_dir}" \
        || { handle_error "${pipeline}_nodes${nodes}"; return 1; }

    mark_done "${pipeline}" "${nodes}" "${exp_output_dir}"
    cleanup_resources
    return 0
}

# -----------------------------------------------------------------------------
# 主执行逻辑
# -----------------------------------------------------------------------------

# 切换到项目根目录
cd /home/sage/SAGE

# 确保输出目录存在
mkdir -p "${OUTPUT_DIR}"

# 初始化日志
echo "=============================================================================" | tee "${LOG_FILE}"
echo " SAGE Scale Up 实验 - LLM 和 RAG Service Pipeline 扩展性测试" | tee -a "${LOG_FILE}"
echo " 开始时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "${LOG_FILE}"
echo " 结果目录: ${OUTPUT_DIR}" | tee -a "${LOG_FILE}"
echo " 快速模式: ${QUICK_MODE}" | tee -a "${LOG_FILE}"
echo " 任务数: ${TASKS}" | tee -a "${LOG_FILE}"
echo " Pipeline: ${PIPELINES}" | tee -a "${LOG_FILE}"
echo " 节点规模: ${NODES}" | tee -a "${LOG_FILE}"
echo "=============================================================================" | tee -a "${LOG_FILE}"
echo ""

# 解析 pipeline 和节点列表
IFS=',' read -ra PIPELINE_ARRAY <<< "$PIPELINES"
IFS=',' read -ra NODE_ARRAY <<< "$NODES"

# 计算总实验数
TOTAL_EXPS=$(count_experiments)
CURRENT_EXP=0

log_message "将运行 ${TOTAL_EXPS} 个实验配置"
echo ""

# 记录实验开始
EXPERIMENT_START_TIME=$(date +%s)

# 按 pipeline 类型依次运行
for pipeline in "${PIPELINE_ARRAY[@]}"; do
    # 去除空格
    pipeline=$(echo "$pipeline" | xargs)

    echo ""
    log_message "========== 开始 ${pipeline} Pipeline 扩展性测试 =========="
    echo ""

    for nodes in "${NODE_ARRAY[@]}"; do
        # 去除空格
        nodes=$(echo "$nodes" | xargs)

        ((CURRENT_EXP++)) || true
        print_progress "${pipeline}" "${nodes}" "${CURRENT_EXP}" "${TOTAL_EXPS}"

        run_experiment "${pipeline}" "${nodes}"
    done

    log_message "========== ${pipeline} Pipeline 测试完成 =========="
done

# 计算总耗时
EXPERIMENT_END_TIME=$(date +%s)
TOTAL_DURATION=$((EXPERIMENT_END_TIME - EXPERIMENT_START_TIME))
DURATION_MINUTES=$((TOTAL_DURATION / 60))
DURATION_SECONDS=$((TOTAL_DURATION % 60))

# 完成汇总
echo ""
echo "============================================================================="
log_message "Scale Up 实验完成"
log_message "总耗时: ${DURATION_MINUTES}分${DURATION_SECONDS}秒"
log_message "结果目录: ${OUTPUT_DIR}"
echo "============================================================================="
echo ""

# 列出生成的结果目录
echo "生成的结果目录:"
ls -la "${OUTPUT_DIR}/" | grep "^d" | awk '{print "  - " $NF}'
echo ""

log_message "日志文件: ${LOG_FILE}"
