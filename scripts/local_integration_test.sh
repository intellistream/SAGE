#!/bin/bash
# Local Docker Integration Test Script
# This script runs comprehensive tests including C++ extensions

set -e

echo "🐳 SAGE Docker Integration Test Suite"
echo "======================================"

# Configuration
TEST_MODES=("minimal" "full")
DOCKER_IMAGE="sage_test_image"
TEST_RESULTS_DIR="test_results"

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to run test and capture results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local result_file="$TEST_RESULTS_DIR/${test_name}.log"
    
    log "Running test: $test_name"
    
    if eval "$test_command" > "$result_file" 2>&1; then
        log "✅ $test_name: PASSED"
        return 0
    else
        log "❌ $test_name: FAILED (see $result_file)"
        return 1
    fi
}

# Test 1: C++ Extensions Build Test
log "Testing C++ extensions build..."

# Test sage_db
if run_test "sage_db_build" "cd sage_ext/sage_db && ./build.sh clean"; then
    SAGE_DB_OK=true
else
    SAGE_DB_OK=false
fi

# Test sage_queue  
if run_test "sage_queue_build" "cd sage_ext/sage_queue && ./build.sh clean"; then
    SAGE_QUEUE_OK=true
else
    SAGE_QUEUE_OK=false
fi

# Test 2: Docker Installation Tests
log "Testing Docker installations..."

for mode in "${TEST_MODES[@]}"; do
    if [[ "$mode" == "minimal" ]]; then
        test_cmd="python install.py --docker --minimal --test-only"
    else
        test_cmd="python install.py --docker --full --test-only"
    fi
    
    run_test "docker_install_${mode}" "$test_cmd"
done

# Test 3: Python Import Tests
log "Testing Python imports..."

# Test minimal install imports
run_test "import_minimal" "python -c '
import sage
from sage.core import *
from sage.lib import *
print(\"✅ Core imports successful\")
'"

# Test full install imports (if C++ extensions built successfully)
if [[ "$SAGE_DB_OK" == true && "$SAGE_QUEUE_OK" == true ]]; then
    run_test "import_full" "python -c '
import sage
from sage_ext.sage_db import VectorStore
from sage_ext.sage_queue.python.sage_queue import SageQueue
print(\"✅ Full imports with C++ extensions successful\")
'"
else
    log "⚠️  Skipping full import test due to C++ extension build failures"
fi

# Test 4: Backend Selection Tests
log "Testing backend selection..."

run_test "backend_ray" "python -c '
import os
os.environ[\"SAGE_QUEUE_BACKEND\"] = \"ray\"
from sage.utils.queue import get_queue_backend
assert get_queue_backend() == \"ray\"
print(\"✅ Ray backend working\")
'"

if [[ "$SAGE_QUEUE_OK" == true ]]; then
    run_test "backend_sage" "python -c '
import os
os.environ[\"SAGE_QUEUE_BACKEND\"] = \"sage\"
from sage.utils.queue import get_queue_backend
assert get_queue_backend() == \"sage\"
print(\"✅ Sage backend working\")
'"
else
    log "⚠️  Skipping Sage backend test due to build failure"
fi

# Test 5: Performance Tests (if available)
if [[ -f "scripts/performance_test.py" ]]; then
    log "Running performance tests..."
    run_test "performance" "python scripts/performance_test.py --quick"
fi

# Generate Test Report
log "Generating test report..."

REPORT_FILE="$TEST_RESULTS_DIR/integration_test_report.md"
cat > "$REPORT_FILE" << EOF
# SAGE Docker Integration Test Report

**Test Date**: $(date)
**Git Branch**: $(git branch --show-current)
**Git Commit**: $(git rev-parse --short HEAD)

## Test Summary

### C++ Extensions
- **sage_db**: $([ "$SAGE_DB_OK" == true ] && echo "✅ PASS" || echo "❌ FAIL")
- **sage_queue**: $([ "$SAGE_QUEUE_OK" == true ] && echo "✅ PASS" || echo "❌ FAIL")

### Docker Installation
- **Minimal Mode**: $([ -f "$TEST_RESULTS_DIR/docker_install_minimal.log" ] && echo "✅ TESTED" || echo "⚠️ SKIPPED")
- **Full Mode**: $([ -f "$TEST_RESULTS_DIR/docker_install_full.log" ] && echo "✅ TESTED" || echo "⚠️ SKIPPED")

### Backend Tests
- **Ray Backend**: $([ -f "$TEST_RESULTS_DIR/backend_ray.log" ] && echo "✅ TESTED" || echo "⚠️ SKIPPED")
- **Sage Backend**: $([ -f "$TEST_RESULTS_DIR/backend_sage.log" ] && echo "✅ TESTED" || echo "⚠️ SKIPPED")

## Detailed Results

EOF

# Add detailed results
for log_file in "$TEST_RESULTS_DIR"/*.log; do
    if [[ -f "$log_file" ]]; then
        test_name=$(basename "$log_file" .log)
        echo "### $test_name" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat "$log_file" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
done

# Final Summary
log "======================================"
log "🏁 Integration Test Complete"
log "======================================"
log "Report generated: $REPORT_FILE"

if [[ "$SAGE_DB_OK" == true && "$SAGE_QUEUE_OK" == true ]]; then
    log "✅ All C++ extensions built successfully"
    log "✅ Ready for production deployment"
    exit 0
else
    log "❌ Some C++ extensions failed to build"
    log "❌ Manual investigation required"
    exit 1
fi
