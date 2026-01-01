#!/bin/bash
# =============================================================================
# SAGE 分布式调度策略评测 - 运行所有实验
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}SAGE Distributed Scheduling Benchmark${NC}"
echo -e "${GREEN}============================================${NC}"

# 检查参数
QUICK_MODE=""
if [[ "$1" == "--quick" ]]; then
    QUICK_MODE="--quick"
    echo -e "${YELLOW}Running in QUICK mode${NC}"
fi

# 检查 JobManager 是否运行
check_jobmanager() {
    if ! nc -z localhost 19001 2>/dev/null; then
        echo -e "${RED}Warning: JobManager not running on port 19001${NC}"
        echo "Start it with: sage jobmanager start"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 运行实验1
run_exp1() {
    echo -e "\n${GREEN}[Experiment 1] Single Node vs Multi Node${NC}"
    echo "=========================================="
    cd "$SCRIPT_DIR/exp1_single_vs_multi"
    python run_experiment.py $QUICK_MODE
}

# 运行'ENDOFFILE'2
run_exp2() {
    echo -e "\n${GREEN}[Experiment 2] High Load Parallel Scheduling${NC}"
    echo "=============================================="
    cd "$SCRIPT_DIR/exp2_high_load_parallel"
    python run_experiment.py $QUICK_MODE
}

# 运行实验3
run_exp3() {
    echo -e "\n${GREEN}[Experiment 3] Latency and Throughput${NC}"
    echo "======================================="
    cd "$SCRIPT_DIR/exp3_latency_throughput"
    python run_experiment.py $QUICK_MODE
}

# 主逻辑
main() {
    echo ""
    echo "Select experiments to run:"
    echo "  1) Experiment 1: Single vs Multi Node"
    echo "  2) Experiment 2: High Load Parallel"
    echo "  3) Experiment 3: Latency & Throughput"
    echo "  a) All experiments"
    echo "  q) Quit"
    echo ""
    read -p "Enter choice [1/2/3/a/q]: " choice

    case $choice in
        1) check_jobmanager; run_exp1 ;;
        2) check_jobmanager; run_exp2 ;;
        3) check_jobmanager; run_exp3 ;;
        a)
            check_jobmanager
            run_exp1
            run_exp2
            run_exp3
            ;;
        q) echo "Exiting."; exit 0 ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac

    echo -e "\n${GREEN}All selected experiments completed.${NC}"
    echo "Results are in each experiment's results/ directory."
}

main
