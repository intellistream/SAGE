#!/bin/bash
# ==============================================================================
# SAGE Cluster Code Sync Script
# 同步 head 节点代码到所有 worker 节点
#
# 用法:
#   ./tools/maintenance/sync-cluster-code.sh              # 同步所有包
#   ./tools/maintenance/sync-cluster-code.sh --quick      # 快速同步（仅运行时关键包）
#   ./tools/maintenance/sync-cluster-code.sh --package sage-kernel  # 同步指定包
#   ./tools/maintenance/sync-cluster-code.sh --dry-run    # 仅显示将执行的命令
#   ./tools/maintenance/sync-cluster-code.sh --clean-logs # 清理所有节点的日志文件
#
# ==============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLUSTER_CONFIG="$SAGE_ROOT/config/cluster.yaml"

# 运行时关键包（--quick 模式）
QUICK_PACKAGES=(
    "sage-platform"
    "sage-kernel"
    "sage-common"
)

# 所有包
ALL_PACKAGES=(
    "sage-common"
    "sage-platform"
    "sage-kernel"
    "sage-libs"
    "sage-middleware"
    "sage-apps"
    "sage-benchmark"
    "sage-cli"
    "sage-tools"
)

# 解析命令行参数
DRY_RUN=false
QUICK_MODE=false
SPECIFIC_PACKAGE=""
VERBOSE=false
CLEAN_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --package|-p)
            SPECIFIC_PACKAGE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --clean-logs)
            CLEAN_LOGS=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick, -q          Quick sync (sage-platform, sage-kernel, sage-common only)"
            echo "  --package, -p NAME   Sync specific package only"
            echo "  --dry-run            Show commands without executing"
            echo "  --clean-logs         Clean log files on all nodes (~/.sage/logs)"
            echo "  --verbose, -v        Verbose output"
            echo "  --help, -h           Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                   # Sync all packages"
            echo "  $0 --quick           # Sync runtime-critical packages"
            echo "  $0 -p sage-kernel    # Sync only sage-kernel"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# 从 cluster.yaml 解析 worker 节点
parse_workers() {
    if [[ ! -f "$CLUSTER_CONFIG" ]]; then
        echo -e "${RED}Error: Cluster config not found: $CLUSTER_CONFIG${NC}"
        exit 1
    fi

    # 使用 Python 解析 YAML（更可靠）
    python3 -c "
import yaml
with open('$CLUSTER_CONFIG') as f:
    config = yaml.safe_load(f)
workers = config.get('ssh', {}).get('workers', [])
user = config.get('ssh', {}).get('user', 'sage')
for w in workers:
    print(f\"{user}@{w['host']}\")
"
}

# 清理单个节点的日志文件
clean_logs_on_node() {
    local node="$1"
    local log_dir="~/SAGE/.sage/logs"
    local cmd="ssh $node 'rm -rf $log_dir/*' 2>/dev/null"

    if $DRY_RUN; then
        echo "  [DRY-RUN] $cmd"
        return 0
    else
        if eval "$cmd"; then
            return 0
        else
            return 1
        fi
    fi
}

# 清理所有节点的日志
clean_all_logs() {
    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       SAGE Cluster Log Cleanup                 ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""

    if $DRY_RUN; then
        echo -e "${YELLOW}[DRY-RUN MODE - No changes will be made]${NC}"
    fi
    echo ""

    # 获取 worker 节点列表
    echo -e "${BLUE}Parsing cluster configuration...${NC}"
    local workers
    workers=$(parse_workers)

    if [[ -z "$workers" ]]; then
        echo -e "${RED}Error: No worker nodes found in $CLUSTER_CONFIG${NC}"
        exit 1
    fi

    local worker_count=$(echo "$workers" | wc -l)
    echo -e "Found ${GREEN}$worker_count${NC} worker node(s)"
    echo ""

    local success_count=0
    local fail_count=0

    for node in $workers; do
        local hostname=$(echo "$node" | cut -d@ -f2)
        echo -ne "${BLUE}Cleaning logs on $hostname...${NC} "

        if clean_logs_on_node "$node"; then
            echo -e "${GREEN}✓${NC}"
            success_count=$((success_count + 1))
        else
            echo -e "${RED}✗${NC}"
            fail_count=$((fail_count + 1))
        fi
    done

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✅ Log cleanup completed: $success_count/$worker_count nodes${NC}"
    else
        echo -e "${YELLOW}⚠ Log cleanup completed with errors: $success_count/$worker_count nodes succeeded${NC}"
        exit 1
    fi
}

# 同步单个包到单个节点
sync_package() {
    local node="$1"
    local package="$2"
    local src_base="$SAGE_ROOT/packages/$package/src/sage"
    local dst_base="~/SAGE/packages/$package/src/sage"

    if [[ ! -d "$src_base" ]]; then
        if $VERBOSE; then
            echo -e "  ${YELLOW}⚠ Skipping $package (src dir not found)${NC}"
        fi
        return 0
    fi

    # 同步 sage/ 目录下的所有子目录（不包括 __init__.py）
    local synced=false
    for subdir in "$src_base"/*/; do
        if [[ -d "$subdir" ]]; then
            local dirname=$(basename "$subdir")
            local cmd="scp -rq $subdir $node:$dst_base/"

            if $DRY_RUN; then
                echo "  [DRY-RUN] $cmd"
            else
                if $VERBOSE; then
                    echo "  Syncing: $package/src/sage/$dirname/"
                fi
                if ! eval "$cmd" 2>/dev/null; then
                    return 1
                fi
            fi
            synced=true
        fi
    done

    if ! $synced; then
        if $VERBOSE; then
            echo -e "  ${YELLOW}⚠ Skipping $package (no subdirs)${NC}"
        fi
    fi
    return 0
}

# 主函数
main() {
    # 如果只是清理日志，执行清理并退出
    if $CLEAN_LOGS; then
        clean_all_logs
        exit 0
    fi

    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       SAGE Cluster Code Sync                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""

    # 确定要同步的包
    local packages_to_sync=()

    if [[ -n "$SPECIFIC_PACKAGE" ]]; then
        packages_to_sync=("$SPECIFIC_PACKAGE")
        echo -e "${YELLOW}Mode: Single package ($SPECIFIC_PACKAGE)${NC}"
    elif $QUICK_MODE; then
        packages_to_sync=("${QUICK_PACKAGES[@]}")
        echo -e "${YELLOW}Mode: Quick sync (${#QUICK_PACKAGES[@]} packages)${NC}"
    else
        packages_to_sync=("${ALL_PACKAGES[@]}")
        echo -e "${YELLOW}Mode: Full sync (${#ALL_PACKAGES[@]} packages)${NC}"
    fi

    if $DRY_RUN; then
        echo -e "${YELLOW}[DRY-RUN MODE - No changes will be made]${NC}"
    fi
    echo ""

    # 获取 worker 节点列表
    echo -e "${BLUE}Parsing cluster configuration...${NC}"
    local workers
    workers=$(parse_workers)

    if [[ -z "$workers" ]]; then
        echo -e "${RED}Error: No worker nodes found in $CLUSTER_CONFIG${NC}"
        exit 1
    fi

    local worker_count=$(echo "$workers" | wc -l)
    echo -e "Found ${GREEN}$worker_count${NC} worker node(s)"
    echo ""

    # 同步到每个节点
    local success_count=0
    local fail_count=0

    for node in $workers; do
        local hostname=$(echo "$node" | cut -d@ -f2)
        echo -e "${BLUE}━━━ Syncing to $hostname ━━━${NC}"

        local node_success=true
        for package in "${packages_to_sync[@]}"; do
            if ! sync_package "$node" "$package"; then
                echo -e "  ${RED}✗ Failed: $package${NC}"
                node_success=false
            else
                if $VERBOSE || $DRY_RUN; then
                    echo -e "  ${GREEN}✓ $package${NC}"
                fi
            fi
        done

        if $node_success; then
            echo -e "  ${GREEN}✓ Done${NC}"
            success_count=$((success_count + 1))
        else
            echo -e "  ${RED}✗ Some packages failed${NC}"
            fail_count=$((fail_count + 1))
        fi
        echo ""
    done

    # 总结
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✅ Sync completed: $success_count/$worker_count nodes${NC}"
        echo -e "${GREEN}   Packages synced: ${#packages_to_sync[@]}${NC}"
    else
        echo -e "${YELLOW}⚠ Sync completed with errors: $success_count/$worker_count nodes succeeded${NC}"
        exit 1
    fi

    if ! $DRY_RUN; then
        echo ""
        echo -e "${YELLOW}💡 Tip: Restart Flownet cluster to apply changes:${NC}"
        echo -e "   sage cluster restart"
    fi
}

main
