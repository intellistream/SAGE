# SAGE 闭源包发布配置文件
# SAGE Proprietary Package Publishing Configuration File

# ========================================
# 基础配置 Basic Configuration
# ========================================

# 默认输出目录 Default output directory
DEFAULT_OUTPUT_DIR="$HOME/.sage/dist"

# PyPI 配置 PyPI Configuration
PYPI_REPOSITORY="pypi"
TEST_PYPI_REPOSITORY="testpypi"

# ========================================
# 包配置 Package Configuration
# ========================================

# 包发布优先级 Package publishing priority (1=highest, 9=lowest)
declare -A PACKAGE_PRIORITY=(
    ["sage-kernel"]="1"
    ["sage-middleware"]="2"
    ["sage-core"]="3"
    ["sage-utils"]="4"
    ["sage-cli"]="5"
    ["sage-dev-toolkit"]="6"
    ["sage-frontend"]="7"
)

# 企业版包列表 Enterprise packages list
ENTERPRISE_PACKAGES=(
    "sage-kernel"
    "sage-middleware"
    "sage-core"
)

# 社区版包列表 Community packages list  
COMMUNITY_PACKAGES=(
    "sage-cli"
    "sage-utils"
    "sage-dev-toolkit"
    "sage-frontend"
)

# 包依赖关系 Package dependencies
declare -A PACKAGE_DEPENDENCIES=(
    ["sage-cli"]="sage-kernel,sage-middleware"
    ["sage-middleware"]="sage-kernel"
    ["sage-core"]="sage-kernel,sage-middleware"
    ["sage-utils"]="sage-kernel"
    ["sage-frontend"]="sage-kernel,sage-middleware,sage-utils"
    ["sage-dev-toolkit"]="sage-kernel,sage-middleware,sage-utils"
)

# ========================================
# 编译配置 Compilation Configuration  
# ========================================

# 编译排除模式 Compilation exclusion patterns
COMPILE_EXCLUDE_PATTERNS=(
    "*/tests/*"
    "*/test_*"
    "*_test.py"
    "*/docs/*"
    "*/examples/*"
    "*/benchmarks/*"
    "*/.git/*"
    "*/__pycache__/*"
    "*.md"
    "*.txt"
    "*.yml"
    "*.yaml"
    "*.json"
)

# 保留的源码文件 Source files to keep (for debugging)
KEEP_SOURCE_PATTERNS=(
    "*/cli/*"
    "*/api/*"
    "*/interface/*"
)

# ========================================
# 构建配置 Build Configuration
# ========================================

# 构建工具选项 Build tool options
BUILD_TOOL="build"  # 或者 "setuptools"
BUILD_OPTIONS=(
    "--wheel"
    "--no-isolation"
)

# ========================================
# 上传配置 Upload Configuration
# ========================================

# Twine 上传选项 Twine upload options
TWINE_OPTIONS=(
    "--verbose"
    "--non-interactive"
)

# 上传重试次数 Upload retry count
UPLOAD_RETRY_COUNT=3

# 上传超时时间（秒）Upload timeout (seconds)
UPLOAD_TIMEOUT=300

# ========================================
# 日志配置 Logging Configuration
# ========================================

# 日志级别 Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL="INFO"

# 日志文件路径 Log file path
LOG_FILE="$DEFAULT_OUTPUT_DIR/publish.log"

# 是否启用详细输出 Enable verbose output
ENABLE_VERBOSE=false

# ========================================
# 环境配置 Environment Configuration
# ========================================

# Python 可执行文件路径 Python executable path
PYTHON_EXECUTABLE="python3"

# 虚拟环境路径 Virtual environment path (可选)
VIRTUAL_ENV_PATH=""

# 环境变量设置 Environment variables
declare -A ENV_VARS=(
    ["PYTHONPATH"]="$PROJECT_ROOT:$PROJECT_ROOT/packages"
    ["SAGE_HOME"]="$HOME/.sage"
    ["SAGE_ENV"]="production"
)

# ========================================
# 安全配置 Security Configuration
# ========================================

# 是否启用代码混淆 Enable code obfuscation
ENABLE_OBFUSCATION=true

# 混淆级别 Obfuscation level (1-3, 3=highest)
OBFUSCATION_LEVEL=2

# 是否删除调试信息 Remove debug information
REMOVE_DEBUG_INFO=true

# 是否压缩字节码 Compress bytecode
COMPRESS_BYTECODE=true

# ========================================
# 通知配置 Notification Configuration
# ========================================

# 是否启用邮件通知 Enable email notification
ENABLE_EMAIL_NOTIFICATION=false
EMAIL_RECIPIENTS=""
EMAIL_SMTP_SERVER=""
EMAIL_SMTP_PORT="587"

# 是否启用Slack通知 Enable Slack notification
ENABLE_SLACK_NOTIFICATION=false
SLACK_WEBHOOK_URL=""

# 是否启用企业微信通知 Enable WeChat Work notification
ENABLE_WECHAT_NOTIFICATION=false
WECHAT_WEBHOOK_URL=""

# ========================================
# 验证配置 Validation Configuration
# ========================================

# 发布前检查项目 Pre-publish checks
ENABLE_LINT_CHECK=true
ENABLE_TEST_CHECK=true
ENABLE_SECURITY_CHECK=true
ENABLE_DEPENDENCY_CHECK=true

# 测试命令 Test command
TEST_COMMAND="python3 -m pytest tests/ -v"

# Lint 命令 Lint command  
LINT_COMMAND="python3 -m flake8 --max-line-length=120"

# ========================================
# 备份配置 Backup Configuration
# ========================================

# 是否启用构建备份 Enable build backup
ENABLE_BUILD_BACKUP=true

# 备份目录 Backup directory
BACKUP_DIR="$DEFAULT_OUTPUT_DIR/backups"

# 备份保留天数 Backup retention days
BACKUP_RETENTION_DAYS=30

# ========================================
# 性能配置 Performance Configuration
# ========================================

# 并行构建进程数 Parallel build processes
PARALLEL_BUILD_JOBS=4

# 构建内存限制（MB）Build memory limit (MB)
BUILD_MEMORY_LIMIT=2048

# 构建超时时间（秒）Build timeout (seconds)
BUILD_TIMEOUT=1800

# ========================================
# 调试配置 Debug Configuration
# ========================================

# 是否保留构建目录 Keep build directory
KEEP_BUILD_DIR=false

# 是否保留临时文件 Keep temporary files
KEEP_TEMP_FILES=false

# 调试输出级别 Debug output level
DEBUG_LEVEL=0

# ========================================
# 函数库 Function Library
# ========================================

# 加载包配置
load_package_config() {
    local package_name="$1"
    local config_file="$PROJECT_ROOT/packages/$package_name/.publish_config"
    
    if [[ -f "$config_file" ]]; then
        source "$config_file"
    fi
}

# 获取包优先级
get_package_priority() {
    local package_name="$1"
    echo "${PACKAGE_PRIORITY[$package_name]:-9}"
}

# 检查是否为企业版包
is_enterprise_package() {
    local package_name="$1"
    for pkg in "${ENTERPRISE_PACKAGES[@]}"; do
        if [[ "$pkg" == "$package_name" ]]; then
            return 0
        fi
    done
    return 1
}

# 获取包依赖
get_package_dependencies() {
    local package_name="$1"
    echo "${PACKAGE_DEPENDENCIES[$package_name]:-}"
}

# 设置环境变量
setup_environment() {
    for var_name in "${!ENV_VARS[@]}"; do
        export "$var_name"="${ENV_VARS[$var_name]}"
    done
}

# 验证配置
validate_config() {
    # 检查必要的目录
    mkdir -p "$DEFAULT_OUTPUT_DIR"
    mkdir -p "$BACKUP_DIR"
    
    # 检查Python可执行文件
    if ! command -v "$PYTHON_EXECUTABLE" &> /dev/null; then
        echo "错误: 未找到Python可执行文件: $PYTHON_EXECUTABLE"
        return 1
    fi
    
    # 检查必要的工具
    local required_tools=("twine" "build")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            echo "警告: 未找到工具: $tool"
        fi
    done
    
    return 0
}

# 日志初始化
init_logging() {
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "=== SAGE 闭源包发布日志 $(date) ===" >> "$LOG_FILE"
}

# 配置验证（脚本加载时执行）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    validate_config
    setup_environment
    init_logging
fi
