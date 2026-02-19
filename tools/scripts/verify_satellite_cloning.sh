#!/bin/bash
# SAGE 卫星仓库克隆功能验证脚本
# 使用方法: bash tools/scripts/verify_satellite_cloning.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo ""
echo -e "${BLUE}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║  SAGE 卫星仓库克隆功能验证${NC}"
echo -e "${BLUE}${BOLD}║  Satellite Repository Cloning Verification${NC}"
echo -e "${BLUE}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test counter
total_tests=0
passed_tests=0

# Helper function
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    total_tests=$((total_tests + 1))
    echo -ne "[$total_tests] Testing: $test_name ... "

    if eval "$test_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        passed_tests=$((passed_tests + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

# ============================================================================
# Test 1: File existence
# ============================================================================
echo -e "${BLUE}📋 Test Suite 1: File Structure${NC}"
echo ""

run_test "clone_satellite_repos.sh exists" \
    "[ -f 'tools/install/download_tools/clone_satellite_repos.sh' ]"

run_test "argument_parser.sh exists" \
    "[ -f 'tools/install/download_tools/argument_parser.sh' ]"

run_test "colors.sh exists" \
    "[ -f 'tools/install/display_tools/colors.sh' ]"

run_test "SAGE.code-workspace exists" \
    "[ -f 'SAGE.code-workspace' ]"

run_test "quickstart.sh exists" \
    "[ -f 'quickstart.sh' ]"

echo ""

# ============================================================================
# Test 2: Function exports
# ============================================================================
echo -e "${BLUE}📋 Test Suite 2: Function Exports${NC}"
echo ""

# Source the module
source tools/install/display_tools/colors.sh
source tools/install/download_tools/clone_satellite_repos.sh

run_test "load_repos_from_workspace exported" \
    "declare -f load_repos_from_workspace >/dev/null"

run_test "get_repo_url exported" \
    "declare -f get_repo_url >/dev/null"

run_test "clone_single_repo exported" \
    "declare -f clone_single_repo >/dev/null"

run_test "clone_all_public_repos exported" \
    "declare -f clone_all_public_repos >/dev/null"

run_test "interactive_clone_repos exported" \
    "declare -f interactive_clone_repos >/dev/null"

echo ""

# ============================================================================
# Test 3: Workspace parsing
# ============================================================================
echo -e "${BLUE}📋 Test Suite 3: Workspace Parsing${NC}"
echo ""

# Test parsing
repos=$(load_repos_from_workspace "$SAGE_ROOT/SAGE.code-workspace" 2>/dev/null || echo "")
repo_count=$(echo "$repos" | grep -c '|' || echo "0")

if [ "$repo_count" -eq 11 ]; then
    echo -ne "[6] Testing: Workspace parsing (found $repo_count repos) ... "
    echo -e "${GREEN}✅ PASS${NC}"
    total_tests=$((total_tests + 1))
    passed_tests=$((passed_tests + 1))
else
    echo -ne "[6] Testing: Workspace parsing (found $repo_count repos, expected 11) ... "
    echo -e "${RED}❌ FAIL${NC}"
    total_tests=$((total_tests + 1))
fi

run_test "Workspace contains sage-examples" \
    "load_repos_from_workspace '$SAGE_ROOT/SAGE.code-workspace' | grep -q 'sage-examples'"

run_test "Workspace contains sage-studio" \
    "load_repos_from_workspace '$SAGE_ROOT/SAGE.code-workspace' | grep -q 'sage-studio'"

echo ""

# ============================================================================
# Test 4: URL generation
# ============================================================================
echo -e "${BLUE}📋 Test Suite 4: URL Generation${NC}"
echo ""

# Source argument parser for parameter handling
source tools/install/download_tools/argument_parser.sh

test_url=$(get_repo_url "sage-examples")
expected_url="https://github.com/intellistream/sage-examples.git"

echo -ne "[9] Testing: URL format (generated) ... "
if [ "$test_url" = "$expected_url" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    total_tests=$((total_tests + 1))
    passed_tests=$((passed_tests + 1))
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "     Expected: $expected_url"
    echo "     Got:      $test_url"
    total_tests=$((total_tests + 1))
fi

echo ""

# ============================================================================
# Test 5: Parameter parsing
# ============================================================================
echo -e "${BLUE}📋 Test Suite 5: Parameter Parsing${NC}"
echo ""

# Test parameter parsing
test_params=(
    "--clone-satellites:true"
    "--clone-repos:true"
    "--satellites:true"
    "--no-clone-satellites:false"
)

test_num=10
for param_test in "${test_params[@]}"; do
    param=$(echo "$param_test" | cut -d: -f1)
    expected=$(echo "$param_test" | cut -d: -f2)

    CLONE_SATELLITE_REPOS="false"
    parse_clone_satellites_option "$param"
    result=$(should_clone_satellite_repos)

    echo -ne "[$test_num] Testing: Parameter '$param' → '$result' ... "
    if [ "$result" = "$expected" ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
    total_tests=$((total_tests + 1))
    test_num=$((test_num + 1))
done

echo ""

# ============================================================================
# Test 6: Branch switching capability
# ============================================================================
echo -e "${BLUE}📋 Test Suite 6: Branch Switching Capability${NC}"
echo ""

run_test "clone_single_repo includes branch detection" \
    "grep -q 'git rev-parse --verify main-dev' tools/install/download_tools/clone_satellite_repos.sh"

run_test "clone_single_repo includes branch creation logic" \
    "grep -q 'checkout -b main-dev' tools/install/download_tools/clone_satellite_repos.sh"

run_test "clone_single_repo handles existing repos" \
    "grep -q 'if \[ -d \"\$repo_path\" \]' tools/install/download_tools/clone_satellite_repos.sh"

echo ""

# ============================================================================
# Test 7: Integration check
# ============================================================================
echo -e "${BLUE}📋 Test Suite 7: Integration Check${NC}"
echo ""

run_test "quickstart.sh imports clone_satellite_repos" \
    "grep -q 'clone_satellite_repos.sh' quickstart.sh"

run_test "quickstart.sh calls clone_all_public_repos" \
    "grep -q 'clone_all_public_repos' quickstart.sh"

run_test "argument_parser includes clone-satellites option" \
    "grep -q 'clone-satellites' tools/install/download_tools/argument_parser.sh"

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Test Results: ${GREEN}${BOLD}$passed_tests / $total_tests${NC} passed"
echo ""

if [ "$passed_tests" -eq "$total_tests" ]; then
    echo -e "${GREEN}${BOLD}✅ All tests passed! System is ready to use.${NC}"
    echo ""
    echo -e "${YELLOW}You can now use:${NC}"
    echo -e "  ${BLUE}./quickstart.sh --full --clone-satellites --yes${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}❌ Some tests failed. Please review the errors above.${NC}"
    echo ""
    exit 1
fi
