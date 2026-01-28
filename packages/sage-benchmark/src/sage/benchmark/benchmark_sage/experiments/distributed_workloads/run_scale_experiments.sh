#!/bin/bash
################################################################################
# Workload 4 规模化实验执行脚本
# 
# 用途: 自动化执行不同节点规模 (1, 2, 4, 8) 的 Workload 4 实验
# 输出: 每次实验的指标数据和日志
#
# 用法:
#   ./run_scale_experiments.sh                    # 运行完整实验套件
#   ./run_scale_experiments.sh --quick            # 快速测试模式
#   ./run_scale_experiments.sh --nodes "1 2 4"    # 仅测试指定节点数
#   ./run_scale_experiments.sh --scheduler fifo   # 指定调度器
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# 配置参数
# =============================================================================

# 实验基础配置
EXPERIMENT_NAME="workload4_scale"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_BASE_DIR="/tmp/sage_experiments/${EXPERIMENT_NAME}_${TIMESTAMP}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 默认参数
NODE_SCALES="1 2 4 8"           # 要测试的节点规模
SCHEDULER="load_aware"          # 调度器类型
NUM_TASKS=200                   # 任务数量
DURATION=300                    # 运行时长（秒）
QUERY_QPS=40                    # 查询流 QPS
DOC_QPS=25                      # 文档流 QPS
REPETITIONS=3                   # 每个配置重复次数

# 快速测试模式
QUICK_MODE=0

# =============================================================================
# 函数定义
# =============================================================================

print_banner() {
    echo -e "${BLUE}"
    echo "=============================================================================="
    echo "$1"
    echo "=============================================================================="
    echo -e "${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=1
                NODE_SCALES="1"
                NUM_TASKS=50
                DURATION=60
                REPETITIONS=1
                shift
                ;;
            --nodes)
                NODE_SCALES="$2"
                shift 2
                ;;
            --scheduler)
                SCHEDULER="$2"
                shift 2
                ;;
            --tasks)
                NUM_TASKS="$2"
                shift 2
                ;;
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --repetitions)
                REPETITIONS="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
    --quick             快速测试模式（1-2节点，50任务，1次重复）
    --nodes "N1 N2..."  指定测试的节点规模（默认: 1 2 4 8）
    --scheduler NAME    调度器类型（默认: load_aware）
                        可选: fifo, load_aware, priority, adaptive
    --tasks N           任务数量（默认: 200）
    --duration N        运行时长（秒，默认: 300）
    --repetitions N     每个配置重复次数（默认: 3）
    --help              显示此帮助信息

示例:
    $0                                    # 完整实验（1,2,4,8节点 × 3次）
    $0 --quick                            # 快速测试
    $0 --nodes "1 4 8" --repetitions 5    # 自定义节点和重复次数
    $0 --scheduler fifo --tasks 500       # FIFO调度器，500任务
EOF
}

# 检查前置条件
check_prerequisites() {
    print_info "检查前置条件..."
    
    # 检查 Python 脚本是否存在
    if [[ ! -f "${SCRIPT_DIR}/run_workload4.py" ]]; then
        print_error "找不到 run_workload4.py"
        exit 1
    fi
    
    # 检查 Ray 集群状态
    if ! command -v ray &> /dev/null; then
        print_error "Ray 未安装"
        exit 1
    fi
    
    ray status &> /dev/null || {
        print_warning "Ray 集群未启动，尝试启动..."
        sage jobmanager start || {
            print_error "无法启动 Ray 集群"
            exit 1
        }
    }
    
    # 检查服务可用性
    print_info "检查 Embedding 服务..."
    curl -s -f http://11.11.11.7:8090/v1/models &> /dev/null || {
        print_warning "Embedding 服务可能未启动 (http://11.11.11.7:8090)"
    }
    
    print_info "检查 LLM 服务..."
    curl -s -f http://11.11.11.7:8904/v1/models &> /dev/null || {
        print_warning "LLM 服务可能未启动 (http://11.11.11.7:8904)"
    }
    
    print_info "✓ 前置条件检查完成"
}

# 创建输出目录
setup_directories() {
    print_info "创建输出目录: ${OUTPUT_BASE_DIR}"
    
    mkdir -p "${OUTPUT_BASE_DIR}/logs"
    mkdir -p "${OUTPUT_BASE_DIR}/metrics"
    mkdir -p "${OUTPUT_BASE_DIR}/configs"
    mkdir -p "${OUTPUT_BASE_DIR}/results"
    
    # 保存实验配置
    cat > "${OUTPUT_BASE_DIR}/experiment_config.yaml" << EOF
# Workload 4 规模化实验配置
# 生成时间: ${TIMESTAMP}

experiment:
  name: ${EXPERIMENT_NAME}
  timestamp: ${TIMESTAMP}
  quick_mode: ${QUICK_MODE}

parameters:
  node_scales: [${NODE_SCALES// /, }]
  scheduler: ${SCHEDULER}
  num_tasks: ${NUM_TASKS}
  duration: ${DURATION}
  query_qps: ${QUERY_QPS}
  doc_qps: ${DOC_QPS}
  repetitions: ${REPETITIONS}

output:
  base_dir: ${OUTPUT_BASE_DIR}
  logs_dir: ${OUTPUT_BASE_DIR}/logs
  metrics_dir: ${OUTPUT_BASE_DIR}/metrics
  results_dir: ${OUTPUT_BASE_DIR}/results
EOF
    
    print_info "✓ 目录结构创建完成"
}

# 运行单次实验
run_single_experiment() {
    local num_nodes=$1
    local rep=$2
    
    local exp_id="nodes${num_nodes}_rep${rep}"
    local log_file="${OUTPUT_BASE_DIR}/logs/${exp_id}.log"
    local metrics_dir="${OUTPUT_BASE_DIR}/metrics/${exp_id}"
    local config_file="${OUTPUT_BASE_DIR}/configs/${exp_id}.yaml"
    
    print_banner "实验 ${exp_id}: ${num_nodes} 节点 (第 ${rep}/${REPETITIONS} 次)"
    
    # 生成配置文件
    cat > "${config_file}" << EOF
# Workload 4 配置 - ${exp_id}
num_tasks: ${NUM_TASKS}
duration: ${DURATION}
use_remote: true
num_nodes: ${num_nodes}

# 双流配置
query_qps: ${QUERY_QPS}
doc_qps: ${DOC_QPS}

# 调度器配置
scheduler_type: ${SCHEDULER}
scheduler_strategy: adaptive

# 输出配置
metrics_output_dir: ${metrics_dir}
enable_profiling: true
enable_detailed_metrics: true
EOF
    
    print_info "配置文件: ${config_file}"
    print_info "日志文件: ${log_file}"
    print_info "指标目录: ${metrics_dir}"
    
    # 清理旧的指标文件
    rm -rf "${metrics_dir}"
    mkdir -p "${metrics_dir}"
    
    # 运行实验
    local start_time=$(date +%s)
    
    print_info "开始运行 (预计时长: ${DURATION}秒)..."
    
    if python "${SCRIPT_DIR}/run_workload4.py" \
        --config "${config_file}" \
        --verbose \
        > "${log_file}" 2>&1; then
        
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        
        print_info "✓ 实验完成 (用时: ${elapsed}秒)"
        
        # 检查指标文件
        local metric_files=$(find "${metrics_dir}" -name "metrics_*.jsonl" 2>/dev/null | wc -l)
        print_info "收集到 ${metric_files} 个指标文件"
        
        return 0
    else
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        
        print_error "实验失败 (用时: ${elapsed}秒)"
        print_error "详见日志: ${log_file}"
        
        return 1
    fi
}

# 收集和汇总结果
collect_results() {
    print_banner "收集实验结果"
    
    local summary_file="${OUTPUT_BASE_DIR}/results/summary.csv"
    local report_file="${OUTPUT_BASE_DIR}/results/REPORT.md"
    
    print_info "生成汇总报告..."
    
    # CSV 表头
    echo "experiment_id,num_nodes,repetition,total_tasks,success_count,fail_count,elapsed_sec,throughput_tps,avg_latency_ms,p50_latency_ms,p95_latency_ms,p99_latency_ms" > "${summary_file}"
    
    # 遍历所有实验结果
    local total_experiments=0
    local successful_experiments=0
    
    for num_nodes in ${NODE_SCALES}; do
        for rep in $(seq 1 ${REPETITIONS}); do
            local exp_id="nodes${num_nodes}_rep${rep}"
            local metrics_dir="${OUTPUT_BASE_DIR}/metrics/${exp_id}"
            
            total_experiments=$((total_experiments + 1))
            
            # 查找 summary 文件
            local summary_files=$(find "${metrics_dir}" -name "metrics_*.jsonl" 2>/dev/null)
            
            if [[ -n "${summary_files}" ]]; then
                # 提取最后一行（summary）
                for file in ${summary_files}; do
                    local summary_line=$(grep '"type":"summary"' "${file}" | tail -1)
                    
                    if [[ -n "${summary_line}" ]]; then
                        # 使用 Python 解析 JSON
                        python3 << EOF >> "${summary_file}"
import json
import sys

try:
    data = json.loads('''${summary_line}''')
    
    print(f"${exp_id},${num_nodes},${rep},"
          f"{data.get('total_tasks', 0)},"
          f"{data.get('success_count', 0)},"
          f"{data.get('fail_count', 0)},"
          f"{data.get('elapsed_seconds', 0):.2f},"
          f"{data.get('throughput', 0):.2f},"
          f"{data.get('avg_latency_ms', 0):.2f},"
          f"0,0,0")  # P50/P95/P99 需要从详细数据计算
except Exception as e:
    print(f"${exp_id},${num_nodes},${rep},ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,0,0,0", file=sys.stderr)
EOF
                        successful_experiments=$((successful_experiments + 1))
                    fi
                done
            else
                print_warning "未找到指标文件: ${exp_id}"
                echo "${exp_id},${num_nodes},${rep},N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "${summary_file}"
            fi
        done
    done
    
    print_info "✓ 汇总完成: ${summary_file}"
    print_info "成功实验: ${successful_experiments}/${total_experiments}"
    
    # 生成 Markdown 报告
    generate_report "${report_file}" "${summary_file}" ${successful_experiments} ${total_experiments}
}

# 生成 Markdown 报告
generate_report() {
    local report_file=$1
    local summary_file=$2
    local successful=$3
    local total=$4
    
    cat > "${report_file}" << EOF
# Workload 4 规模化实验报告

## 实验信息

- **实验名称**: ${EXPERIMENT_NAME}
- **时间戳**: ${TIMESTAMP}
- **输出目录**: \`${OUTPUT_BASE_DIR}\`

## 实验配置

| 参数 | 值 |
|------|-----|
| 节点规模 | ${NODE_SCALES} |
| 调度器 | ${SCHEDULER} |
| 任务数量 | ${NUM_TASKS} |
| 运行时长 | ${DURATION}s |
| 查询流 QPS | ${QUERY_QPS} |
| 文档流 QPS | ${DOC_QPS} |
| 重复次数 | ${REPETITIONS} |

## 实验结果

**完成状态**: ${successful}/${total} 成功

### 详细结果

详见汇总文件: \`${summary_file}\`

\`\`\`bash
# 查看 CSV 结果
cat ${summary_file}

# 使用 pandas 分析（Python）
python3 << 'PYEOF'
import pandas as pd

df = pd.read_csv("${summary_file}")
print(df.groupby("num_nodes").agg({
    "throughput_tps": ["mean", "std"],
    "avg_latency_ms": ["mean", "std"]
}))
PYEOF
\`\`\`

## 目录结构

\`\`\`
${OUTPUT_BASE_DIR}/
├── configs/          # 每次实验的配置文件
├── logs/             # 每次实验的日志
├── metrics/          # 每次实验的原始指标数据
└── results/          # 汇总结果
    ├── summary.csv   # CSV 汇总表
    └── REPORT.md     # 本报告
\`\`\`

## 后续分析

### 1. 可视化

\`\`\`bash
cd ${SCRIPT_DIR}
python visualize_scale_results.py ${OUTPUT_BASE_DIR}
\`\`\`

### 2. 详细分析

\`\`\`bash
python analyze_workload4_metrics.py \\
    --metrics-dir ${OUTPUT_BASE_DIR}/metrics \\
    --output ${OUTPUT_BASE_DIR}/results/detailed_analysis.json
\`\`\`

### 3. 调度器对比

\`\`\`bash
python compare_schedulers.py \\
    --exp1 ${OUTPUT_BASE_DIR}/metrics/nodes8_rep1 \\
    --exp2 <另一个调度器的结果目录>
\`\`\`

## 生成时间

$(date)
EOF
    
    print_info "✓ 报告生成: ${report_file}"
}

# =============================================================================
# 主执行流程
# =============================================================================

main() {
    # 解析命令行参数
    parse_args "$@"
    
    print_banner "Workload 4 规模化实验"
    
    echo "实验配置:"
    echo "  节点规模: ${NODE_SCALES}"
    echo "  调度器: ${SCHEDULER}"
    echo "  任务数: ${NUM_TASKS}"
    echo "  时长: ${DURATION}s"
    echo "  重复: ${REPETITIONS}次"
    echo "  输出: ${OUTPUT_BASE_DIR}"
    
    if [[ ${QUICK_MODE} -eq 1 ]]; then
        echo ""
        print_warning "快速测试模式 (缩小规模)"
    fi
    
    echo ""
    read -p "继续实验？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "实验取消"
        exit 0
    fi
    
    # 检查前置条件
    check_prerequisites
    
    # 创建目录结构
    setup_directories
    
    # 执行所有实验
    local experiment_count=0
    local success_count=0
    local fail_count=0
    
    for num_nodes in ${NODE_SCALES}; do
        for rep in $(seq 1 ${REPETITIONS}); do
            experiment_count=$((experiment_count + 1))
            
            echo ""
            print_info "进度: ${experiment_count}/$(($(echo ${NODE_SCALES} | wc -w) * REPETITIONS))"
            
            if run_single_experiment ${num_nodes} ${rep}; then
                success_count=$((success_count + 1))
            else
                fail_count=$((fail_count + 1))
                print_warning "继续下一个实验..."
            fi
            
            # 等待一小段时间让系统恢复
            if [[ ${experiment_count} -lt $(($(echo ${NODE_SCALES} | wc -w) * REPETITIONS)) ]]; then
                print_info "等待 10 秒后继续..."
                sleep 10
            fi
        done
    done
    
    # 收集结果
    echo ""
    collect_results
    
    # 最终摘要
    print_banner "实验完成"
    
    echo "实验统计:"
    echo "  总计: ${experiment_count}"
    echo "  成功: ${success_count}"
    echo "  失败: ${fail_count}"
    echo ""
    echo "结果位置:"
    echo "  目录: ${OUTPUT_BASE_DIR}"
    echo "  报告: ${OUTPUT_BASE_DIR}/results/REPORT.md"
    echo "  数据: ${OUTPUT_BASE_DIR}/results/summary.csv"
    echo ""
    
    print_info "查看报告: cat ${OUTPUT_BASE_DIR}/results/REPORT.md"
    print_info "查看数据: cat ${OUTPUT_BASE_DIR}/results/summary.csv"
}

# 执行主函数
main "$@"
