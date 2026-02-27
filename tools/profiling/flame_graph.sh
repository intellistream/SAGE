#!/usr/bin/env bash
# SAGE flame-graph collector — uses py-spy (SVG) + perf (Linux kernel stacks)
#
# Usage:
#   bash tools/profiling/flame_graph.sh [PATH] [OPTIONS]
#
# Arguments:
#   PATH          One of: scheduler communication dp_unlearning foundation_io all
#                 Default: all
#
# Options:
#   --duration N  py-spy sampling duration in seconds (default: 30)
#   --rate N      py-spy sampling rate in Hz (default: 100)
#   --no-pyspy    Skip py-spy (even if installed)
#   --perf        Also collect Linux perf mixed-stack flame graph (requires root)
#   --install     pip-install py-spy before running
#
# Outputs written to tools/profiling/reports/flamegraph/
#   <path>.svg         — py-spy flame graph
#   <path>_perf.svg    — perf + stackcollapse flame graph (Linux only, --perf)
#
# Dependencies:
#   py-spy>=0.3           (pip install py-spy)
#   FlameGraph scripts    (cloned automatically if missing, --perf only)
#   perf + linux-tools    (--perf only, requires sudo)
#
# Notes:
#   - py-spy flame graphs work without root on modern kernels (SYS_PTRACE cap)
#   - perf mixed-mode requires sudo and kernel.perf_event_paranoid <= 1
#   - On WSL2, use py-spy only (perf has limited support)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="$SCRIPT_DIR/reports/flamegraph"
WORKLOADS_DIR="$SCRIPT_DIR/workloads"

mkdir -p "$REPORTS_DIR"

# ----------------------------------------------------------------
# Defaults
# ----------------------------------------------------------------
SELECTED_PATH="${1:-all}"
DURATION=30
RATE=100
USE_PYSPY=true
USE_PERF=false
DO_INSTALL=false

for arg in "${@:2}"; do
    case "$arg" in
        --duration=*)  DURATION="${arg#*=}" ;;
        --rate=*)      RATE="${arg#*=}" ;;
        --no-pyspy)    USE_PYSPY=false ;;
        --perf)        USE_PERF=true ;;
        --install)     DO_INSTALL=true ;;
    esac
done

# ----------------------------------------------------------------
# Colors
# ----------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

log()  { echo -e "${GREEN}[flame_graph]${NC} $*"; }
warn() { echo -e "${YELLOW}[flame_graph] WARN:${NC} $*"; }
err()  { echo -e "${RED}[flame_graph] ERROR:${NC} $*"; }

# ----------------------------------------------------------------
# Install py-spy if requested
# ----------------------------------------------------------------
if $DO_INSTALL; then
    log "Installing py-spy..."
    python -m pip install --quiet py-spy
fi

# ----------------------------------------------------------------
# Check py-spy availability
# ----------------------------------------------------------------
PYSPY_CMD=""
if $USE_PYSPY; then
    if command -v py-spy &>/dev/null; then
        PYSPY_CMD="py-spy"
    elif python -m py_spy --version &>/dev/null 2>&1; then
        PYSPY_CMD="python -m py_spy"
    else
        warn "py-spy not found. Install with: pip install py-spy"
        warn "Falling back to cProfile runner only."
        USE_PYSPY=false
    fi
fi

# ----------------------------------------------------------------
# Workload scripts mapped by path name
# ----------------------------------------------------------------
declare -A WORKLOAD_SCRIPTS=(
    ["scheduler"]="$WORKLOADS_DIR/workload_scheduler.py"
    ["communication"]="$WORKLOADS_DIR/workload_communication.py"
    ["dp_unlearning"]="$WORKLOADS_DIR/workload_dp_unlearning.py"
    ["foundation_io"]="$WORKLOADS_DIR/workload_foundation_io.py"
)

declare -A WORKLOAD_ARGS=(
    ["scheduler"]="--iterations 500000"
    ["communication"]="--iterations 1000000 --payload-size 1024"
    ["dp_unlearning"]="--vectors 10000 --dim 128 --iterations 30"
    ["foundation_io"]="--batch-size 256 --iterations 100000"
)

# ----------------------------------------------------------------
# Determine which paths to profile
# ----------------------------------------------------------------
if [[ "$SELECTED_PATH" == "all" ]]; then
    PATHS=("scheduler" "communication" "dp_unlearning" "foundation_io")
else
    PATHS=("$SELECTED_PATH")
fi

# ----------------------------------------------------------------
# py-spy flame graph collector
# ----------------------------------------------------------------
collect_pyspy() {
    local path="$1"
    local script="${WORKLOAD_SCRIPTS[$path]}"
    local wargs="${WORKLOAD_ARGS[$path]}"
    local svg_out="$REPORTS_DIR/${path}.svg"

    log "py-spy flame graph: ${path} → ${svg_out}"

    # Run workload in background, capture PID
    python "$script" $wargs &
    local pid=$!

    $PYSPY_CMD record \
        --pid "$pid" \
        --output "$svg_out" \
        --duration "$DURATION" \
        --rate "$RATE" \
        --format speedscope \
        2>/dev/null || true

    # Also produce a raw SVG (flamegraph format)
    $PYSPY_CMD record \
        --pid "$pid" \
        --output "${REPORTS_DIR}/${path}_flamegraph.svg" \
        --duration "$DURATION" \
        --rate "$RATE" \
        2>/dev/null || true

    wait "$pid" 2>/dev/null || true
    log "py-spy done: ${svg_out}"
}

# ----------------------------------------------------------------
# perf + FlameGraph (Linux, requires root)
# ----------------------------------------------------------------
FLAMEGRAPH_DIR="/tmp/FlameGraph"

ensure_flamegraph_scripts() {
    if [[ ! -d "$FLAMEGRAPH_DIR" ]]; then
        log "Cloning FlameGraph scripts..."
        git clone --depth=1 https://github.com/brendangregg/FlameGraph "$FLAMEGRAPH_DIR"
    fi
}

collect_perf() {
    local path="$1"
    local script="${WORKLOAD_SCRIPTS[$path]}"
    local wargs="${WORKLOAD_ARGS[$path]}"
    local perf_data="$REPORTS_DIR/${path}.perf.data"
    local svg_out="$REPORTS_DIR/${path}_perf.svg"

    if ! command -v perf &>/dev/null; then
        warn "perf not available — skipping perf collection for ${path}"
        return
    fi
    if [[ $EUID -ne 0 ]]; then
        warn "perf mixed-mode requires root — skipping ${path}"
        return
    fi

    ensure_flamegraph_scripts
    log "perf flame graph: ${path} → ${svg_out}"

    perf record \
        -F "$RATE" \
        -g \
        -e cpu-clock \
        -o "$perf_data" \
        -- python "$script" $wargs

    perf script -i "$perf_data" \
        | "$FLAMEGRAPH_DIR/stackcollapse-perf.pl" \
        | "$FLAMEGRAPH_DIR/flamegraph.pl" > "$svg_out"

    log "perf done: ${svg_out}"
}

# ----------------------------------------------------------------
# cProfile fallback (always runs to produce .prof files)
# ----------------------------------------------------------------
collect_cprofile() {
    local path="$1"
    log "cProfile: ${path}"
    python "$SCRIPT_DIR/cprofile_runner.py" \
        --path "$path" \
        --heavy \
        --quiet 2>&1 || warn "cprofile_runner.py failed for ${path}"
}

# ----------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------
for path in "${PATHS[@]}"; do
    if [[ -z "${WORKLOAD_SCRIPTS[$path]+x}" ]]; then
        err "Unknown path: '$path'. Valid: ${!WORKLOAD_SCRIPTS[*]}"
        exit 1
    fi

    log "=== ${path} ==="
    collect_cprofile "$path"

    if $USE_PYSPY; then
        collect_pyspy "$path"
    fi

    if $USE_PERF; then
        collect_perf "$path"
    fi
done

# ----------------------------------------------------------------
# Generate Markdown report
# ----------------------------------------------------------------
if [[ -f "$SCRIPT_DIR/reports/full_summary.json" ]]; then
    log "Generating Markdown report..."
    python "$SCRIPT_DIR/report_generator.py" || warn "report_generator failed"
fi

echo ""
log "=== Done ==="
log "Reports   : $REPORTS_DIR"
log "Flamegraphs: $REPORTS_DIR/*.svg"
log ""
log "Open SVG in browser:  xdg-open $REPORTS_DIR/dp_unlearning_flamegraph.svg"
log "View .prof in snakeviz: snakeviz $SCRIPT_DIR/reports/dp_unlearning.prof"
log ""
log "Commit results:"
log "  cp $SCRIPT_DIR/reports/hot_path_report.md docs-public/profiling/"
log "  git add docs-public/profiling/hot_path_report.md"
