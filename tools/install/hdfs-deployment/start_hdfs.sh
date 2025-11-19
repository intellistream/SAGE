#!/bin/bash
################################################################################
# HDFS Docker 交互式管理脚本 (增强版)
#
# 功能:
#   - 交互式菜单界面
#   - 详细的错误处理和诊断
#   - 启动状态监控和验证
#   - 多轮对话式操作
################################################################################

set -e

# ==================== 配置变量 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
DATA_DIR="$SCRIPT_DIR/data"
CONFIG_DIR="$SCRIPT_DIR/config"
LOG_FILE="$SCRIPT_DIR/hdfs_operation.log"

# ==================== 颜色定义 ====================
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# ==================== 日志函数 ====================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓ SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗ ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${CYAN}[→ STEP]${NC} $1" | tee -a "$LOG_FILE"
}

log_debug() {
    if [ "${DEBUG:-0}" == "1" ]; then
        echo -e "${MAGENTA}[DEBUG]${NC} $1" | tee -a "$LOG_FILE"
    fi
}

# ==================== 错误处理 ====================
error_exit() {
    log_error "$1"
    echo ""
    log_info "查看详细日志: cat $LOG_FILE"
    exit 1
}

# 捕获错误并提供诊断信息
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_no=$2
    log_error "脚本在第 $line_no 行出错 (退出码: $exit_code)"
    log_info "尝试运行以下命令诊断问题:"
    echo "  1. sudo docker ps -a | grep hdfs"
    echo "  2. sudo docker logs hdfs-namenode"
    echo "  3. sudo docker logs hdfs-datanode"
    exit $exit_code
}

# ==================== 环境检查 ====================
check_docker() {
    log_step "检查 Docker 环境..."

    if ! command -v docker &> /dev/null; then
        error_exit "Docker 未安装! 请先安装 Docker: https://docs.docker.com/get-docker/"
    fi

    if ! docker info &> /dev/null; then
        error_exit "Docker 服务未运行或无权限! 请运行: sudo systemctl start docker"
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error_exit "Docker Compose 未安装! 请先安装 Docker Compose"
    fi

    # 检查是否需要 sudo
    if ! docker ps &> /dev/null; then
        log_warn "需要 sudo 权限运行 Docker 命令"
        export DOCKER_CMD="sudo docker"
        export COMPOSE_CMD="sudo docker compose"
    else
        export DOCKER_CMD="docker"
        export COMPOSE_CMD="docker compose"
    fi

    log_success "Docker 环境检查通过 ✓"
}


# ==================== Docker Compose 配置管理 ====================
create_docker_compose_file() {
    log_step "检查并创建 Docker Compose 配置文件..."

    # 检查是否需要创建或更新配置
    local need_update=false

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_info "Docker Compose 配置文件不存在,将创建"
        need_update=true
    else
        # 检查是否包含 user: "0:0" 配置
        if ! grep -q 'user: "0:0"' "$COMPOSE_FILE"; then
            log_warn "Docker Compose 配置缺少用户权限设置,将更新"
            need_update=true
        fi
    fi

    if [ "$need_update" = true ]; then
        cat > "$COMPOSE_FILE" << 'EOF'
services:
  namenode:
    image: apache/hadoop:3
    container_name: hdfs-namenode
    hostname: namenode
    user: "0:0"  # 以root用户运行,避免权限问题
    ports:
      - "9870:9870"
      - "9000:9000"
    environment:
      - CLUSTER_NAME=sage-hdfs
    volumes:
      - ./data/namenode:/opt/hadoop/data/nameNode
      - ./config/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
      - ./config/hdfs-site.xml:/opt/hadoop/etc/hadoop/hdfs-site.xml:ro
    networks:
      - hadoop
    command: >
      bash -c "
      if [ ! -d /opt/hadoop/data/nameNode/current ]; then
        hdfs namenode -format -force;
      fi &&
      hdfs namenode
      "

  datanode:
    image: apache/hadoop:3
    container_name: hdfs-datanode
    hostname: datanode
    user: "0:0"  # 以root用户运行,避免权限问题
    ports:
      - "9864:9864"
    volumes:
      - ./data/datanode:/opt/hadoop/data/dataNode
      - ./config/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
      - ./config/hdfs-site.xml:/opt/hadoop/etc/hadoop/hdfs-site.xml:ro
    networks:
      - hadoop
    depends_on:
      - namenode
    command: >
      bash -c "
      sleep 15 &&
      hdfs datanode
      "

networks:
  hadoop:
    driver: bridge
EOF
        log_success "Docker Compose 配置文件已创建/更新 ✓"
    else
        log_success "Docker Compose 配置文件检查通过 ✓"
    fi
}
check_requirements() {
    log_step "检查系统要求..."

    # 检查磁盘空间
    local available_space=$(df "$SCRIPT_DIR" | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 1048576 ]; then  # 小于 1GB
        log_warn "磁盘空间不足 1GB,可能影响 HDFS 运行"
    fi

    # 检查配置文件
    if [ ! -d "$CONFIG_DIR" ]; then
        log_warn "配置目录不存在,将自动创建"
        create_config_files
    fi

    # 检查并创建 docker-compose 文件
    create_docker_compose_file

    log_success "系统要求检查通过 ✓"
}

# ==================== 配置文件管理 ====================
create_config_files() {
    log_step "创建 Hadoop 配置文件..."

    mkdir -p "$CONFIG_DIR"

    # 创建 core-site.xml
    cat > "$CONFIG_DIR/core-site.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>fs.defaultFS</name>
    <value>hdfs://namenode:9000</value>
    <description>HDFS 默认文件系统地址</description>
  </property>
  <property>
    <name>hadoop.tmp.dir</name>
    <value>/tmp/hadoop</value>
  </property>
</configuration>
EOF

    # 创建 hdfs-site.xml
    cat > "$CONFIG_DIR/hdfs-site.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>dfs.replication</name>
    <value>1</value>
    <description>数据块副本数量(单节点模式为1)</description>
  </property>
  <property>
    <name>dfs.permissions.enabled</name>
    <value>false</value>
    <description>禁用权限检查,方便测试</description>
  </property>
  <property>
    <name>dfs.namenode.name.dir</name>
    <value>file:///opt/hadoop/data/nameNode</value>
    <description>NameNode 元数据存储路径</description>
  </property>
  <property>
    <name>dfs.datanode.data.dir</name>
    <value>file:///opt/hadoop/data/dataNode</value>
    <description>DataNode 数据块存储路径</description>
  </property>
</configuration>
EOF

    chmod 644 "$CONFIG_DIR"/*.xml
    log_success "配置文件创建完成 ✓"
}

# ==================== 数据目录管理 ====================
prepare_data_dir() {
    log_step "准备数据目录..."

    mkdir -p "$DATA_DIR/namenode"
    mkdir -p "$DATA_DIR/datanode"

    # 设置权限 (避免容器内权限问题)
    chmod -R 777 "$DATA_DIR"

    log_success "数据目录准备完成: $DATA_DIR ✓"
}

# ==================== HDFS 启动 ====================
start_hdfs() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}    启动 HDFS 集群${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""

    # 环境检查
    check_docker
    check_requirements
    prepare_data_dir

    # 检查是否已经运行
    if $DOCKER_CMD ps | grep -q hdfs-namenode; then
        log_warn "HDFS 集群已经在运行中"
        read -p "是否重启集群? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            stop_hdfs
            sleep 2
        else
            return 0
        fi
    fi

    # 启动容器
    log_step "启动 Docker 容器..."
    if docker compose version &> /dev/null; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" up -d 2>&1 | tee -a "$LOG_FILE"
    else
        sudo docker-compose -f "$COMPOSE_FILE" up -d 2>&1 | tee -a "$LOG_FILE"
    fi

    if [ $? -ne 0 ]; then
        error_exit "容器启动失败! 查看日志: $LOG_FILE"
    fi

    # 等待服务就绪
    wait_for_hdfs_ready

    # 初始化 HDFS 目录
    initialize_hdfs

    # 显示状态
    echo ""
    show_status

    echo ""
    log_success "🎉 HDFS 集群启动成功!"
    echo ""
    echo -e "${CYAN}访问地址:${NC}"
    echo "  • NameNode Web UI: http://localhost:9870"
    echo "  • NameNode RPC:    hdfs://localhost:9000"
    echo "  • DataNode Web UI: http://localhost:9864"
    echo ""
}

wait_for_hdfs_ready() {
    log_step "等待 HDFS 服务就绪..."

    local max_wait=90
    local waited=0
    local check_interval=3

    # 进度条
    echo -n "  "

    while [ $waited -lt $max_wait ]; do
        # 检查 NameNode 是否就绪
        if $DOCKER_CMD exec hdfs-namenode hdfs dfsadmin -report &> /dev/null; then
            echo ""
            log_success "NameNode 已就绪 ✓"
            break
        fi

        # 检查容器是否异常退出
        if ! $DOCKER_CMD ps | grep -q hdfs-namenode; then
            echo ""
            log_error "NameNode 容器异常退出!"
            diagnose_container_failure "hdfs-namenode"
            error_exit "NameNode 启动失败"
        fi

        echo -n "."
        sleep $check_interval
        waited=$((waited + check_interval))
    done

    if [ $waited -ge $max_wait ]; then
        echo ""
        log_error "等待超时 (${max_wait}秒)"
        diagnose_container_failure "hdfs-namenode"
        error_exit "HDFS 启动超时"
    fi

    # 等待 DataNode 注册
    log_step "等待 DataNode 注册..."
    sleep 5

    if ! $DOCKER_CMD ps | grep -q hdfs-datanode; then
        log_warn "DataNode 容器未运行,正在诊断..."
        diagnose_container_failure "hdfs-datanode"
    else
        log_success "DataNode 已就绪 ✓"
    fi
}

diagnose_container_failure() {
    local container_name=$1

    echo ""
    log_error "诊断 $container_name 容器问题:"
    echo ""

    # 检查容器状态
    echo -e "${YELLOW}容器状态:${NC}"
    $DOCKER_CMD ps -a --filter "name=$container_name" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    # 显示最后的日志
    echo -e "${YELLOW}最后 20 行日志:${NC}"
    $DOCKER_CMD logs --tail 20 "$container_name" 2>&1 | sed 's/^/  /'
    echo ""

    # 常见错误提示
    echo -e "${CYAN}常见问题排查:${NC}"
    echo "  1. 权限问题: sudo chmod -R 777 $DATA_DIR"
    echo "  2. 端口占用: sudo lsof -i :9000,9870,9864"
    echo "  3. 配置错误: 检查 $CONFIG_DIR/*.xml"
    echo "  4. 查看完整日志: sudo docker logs $container_name"
    echo ""
}

# ==================== HDFS 初始化 ====================
initialize_hdfs() {
    log_step "初始化 HDFS 目录结构..."

    # 创建项目目录
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -mkdir -p /sage 2>/dev/null || true
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -mkdir -p /sage/data 2>/dev/null || true
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -mkdir -p /sage/checkpoints 2>/dev/null || true
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -mkdir -p /user 2>/dev/null || true

    # 设置权限
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -chmod -R 777 /sage 2>/dev/null || true
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -chmod -R 777 /user 2>/dev/null || true

    log_success "HDFS 目录初始化完成 ✓"
}

# ==================== HDFS 停止 ====================
stop_hdfs() {
    check_docker  # 确保 DOCKER_CMD 已初始化
    log_step "停止 HDFS 集群..."

    if ! $DOCKER_CMD ps 2>/dev/null | grep -q "hdfs-namenode"; then
        log_warn "HDFS 集群未运行"
        return 0
    fi

    if docker compose version &> /dev/null; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" down 2>&1 | tee -a "$LOG_FILE"
    else
        sudo docker-compose -f "$COMPOSE_FILE" down 2>&1 | tee -a "$LOG_FILE"
    fi

    log_success "HDFS 已停止 ✓"
}

# ==================== HDFS 重启 ====================
restart_hdfs() {
    echo ""
    log_info "重启 HDFS 集群..."
    stop_hdfs
    sleep 3
    start_hdfs
}

# ==================== 状态查看 ====================
show_status() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}    HDFS 集群状态${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""

    # 容器状态
    if $DOCKER_CMD ps --filter "name=hdfs-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep hdfs- > /dev/null; then
        echo -e "${CYAN}容器状态:${NC}"
        $DOCKER_CMD ps --filter "name=hdfs-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""

        # HDFS 集群报告
        echo -e "${CYAN}HDFS 集群报告:${NC}"
        if $DOCKER_CMD exec hdfs-namenode hdfs dfsadmin -report 2>/dev/null; then
            :
        else
            log_warn "无法获取 HDFS 报告 (服务可能未完全启动)"
        fi

        echo ""
        echo -e "${CYAN}访问地址:${NC}"
        echo "  • NameNode RPC:    hdfs://localhost:9000"
        echo "  • NameNode Web UI: http://localhost:9870"
        echo "  • DataNode Web UI: http://localhost:9864"

        echo ""
        echo -e "${CYAN}Python 连接示例:${NC}"
        echo "  export HDFS_NAMENODE_HOST=localhost"
        echo "  export HDFS_NAMENODE_PORT=9000"
    else
        log_warn "HDFS 容器未运行"
        echo ""
        echo "使用以下命令启动 HDFS:"
        echo "  bash $0 start"
    fi
    echo ""
}

# ==================== HDFS 测试 ====================
test_hdfs() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}    测试 HDFS 功能${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""

    # 检查容器状态
    if ! $DOCKER_CMD ps --filter "name=hdfs-namenode" --format "{{.Names}}" | grep hdfs-namenode > /dev/null; then
        error_exit "HDFS NameNode 容器未运行! 请先启动: bash $0 start"
    fi

    local test_file="/sage/test_$(date +%s).txt"
    local test_content="Hello HDFS from Docker! 测试时间: $(date)"

    # 测试 1: 写入文件
    log_step "测试 1/4: 写入文件到 HDFS..."
    echo "$test_content" | $DOCKER_CMD exec -i hdfs-namenode hdfs dfs -put - "$test_file"
    log_success "✓ 文件写入成功: $test_file"

    # 测试 2: 读取文件
    log_step "测试 2/4: 从 HDFS 读取文件..."
    local read_content=$($DOCKER_CMD exec hdfs-namenode hdfs dfs -cat "$test_file" 2>/dev/null)
    if [ "$read_content" == "$test_content" ]; then
        log_success "✓ 文件读取成功,内容匹配"
    else
        log_error "✗ 文件读取失败或内容不匹配"
        return 1
    fi

    # 测试 3: 列出文件
    log_step "测试 3/4: 列出 HDFS 文件..."
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -ls /sage/ | grep test
    log_success "✓ 文件列表获取成功"

    # 测试 4: 删除文件
    log_step "测试 4/4: 删除测试文件..."
    $DOCKER_CMD exec hdfs-namenode hdfs dfs -rm "$test_file" &>/dev/null
    log_success "✓ 文件删除成功"

    echo ""
    log_success "🎉 所有测试通过! HDFS 运行正常"
    echo ""
}

# ==================== 查看日志 ====================
show_logs() {
    echo ""
    echo -e "${CYAN}选择要查看的日志:${NC}"
    echo "  1) NameNode 日志"
    echo "  2) DataNode 日志"
    echo "  3) 所有容器日志 (实时)"
    echo "  4) 返回"
    echo ""
    read -p "请选择 [1-4]: " choice

    case $choice in
        1)
            echo ""
            log_info "显示 NameNode 日志 (最后 50 行, Ctrl+C 退出)..."
            $DOCKER_CMD logs --tail 50 -f hdfs-namenode
            ;;
        2)
            echo ""
            log_info "显示 DataNode 日志 (最后 50 行, Ctrl+C 退出)..."
            $DOCKER_CMD logs --tail 50 -f hdfs-datanode
            ;;
        3)
            echo ""
            log_info "显示所有容器日志 (Ctrl+C 退出)..."
            if docker compose version &> /dev/null; then
                $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f
            else
                sudo docker-compose -f "$COMPOSE_FILE" logs -f
            fi
            ;;
        4)
            return
            ;;
        *)
            log_error "无效选择"
            ;;
    esac
}

# ==================== 清理数据 ====================
clean_all() {
    echo ""
    echo -e "${RED}${BOLD}⚠️  警告: 这将删除所有 HDFS 数据!${NC}"
    echo ""
    echo "将要删除:"
    echo "  • HDFS 容器和卷"
    echo "  • 数据目录: $DATA_DIR"
    echo "  • 所有存储在 HDFS 中的文件"
    echo ""
    read -p "确认继续? 输入 'yes' 确认: " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "取消操作"
        return 0
    fi

    log_step "清理 HDFS 环境..."

    # 停止并删除容器
    if docker compose version &> /dev/null; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" down -v 2>&1 | tee -a "$LOG_FILE"
    else
        sudo docker-compose -f "$COMPOSE_FILE" down -v 2>&1 | tee -a "$LOG_FILE"
    fi

    # 删除数据目录
    if [ -d "$DATA_DIR" ]; then
        rm -rf "$DATA_DIR"
        log_success "数据目录已删除"
    fi

    log_success "清理完成 ✓"
    echo ""
}

# ==================== 高级操作菜单 ====================
advanced_menu() {
    while true; do
        echo ""
        echo -e "${BOLD}========================================${NC}"
        echo -e "${BOLD}    高级操作${NC}"
        echo -e "${BOLD}========================================${NC}"
        echo ""
        echo "  1) 进入 NameNode 容器"
        echo "  2) 进入 DataNode 容器"
        echo "  3) 查看配置文件"
        echo "  4) 重新创建配置文件"
        echo "  5) 查看数据目录"
        echo "  6) 导出操作日志"
        echo "  7) 返回主菜单"
        echo ""
        read -p "请选择 [1-7]: " choice

        case $choice in
            1)
                log_info "进入 NameNode 容器 (输入 exit 退出)..."
                $DOCKER_CMD exec -it hdfs-namenode bash
                ;;
            2)
                log_info "进入 DataNode 容器 (输入 exit 退出)..."
                $DOCKER_CMD exec -it hdfs-datanode bash
                ;;
            3)
                echo ""
                echo -e "${CYAN}core-site.xml:${NC}"
                cat "$CONFIG_DIR/core-site.xml"
                echo ""
                echo -e "${CYAN}hdfs-site.xml:${NC}"
                cat "$CONFIG_DIR/hdfs-site.xml"
                ;;
            4)
                log_info "重新创建配置文件..."
                create_config_files
                log_success "配置文件已更新,需要重启 HDFS 才能生效"
                ;;
            5)
                echo ""
                log_info "数据目录内容:"
                ls -lah "$DATA_DIR"
                ;;
            6)
                local export_file="$SCRIPT_DIR/hdfs_log_$(date +%Y%m%d_%H%M%S).txt"
                cp "$LOG_FILE" "$export_file"
                log_success "日志已导出到: $export_file"
                ;;
            7)
                return
                ;;
            *)
                log_error "无效选择"
                ;;
        esac
    done
}

# ==================== 主菜单 ====================
show_main_menu() {
    while true; do
        echo ""
        echo -e "${BOLD}╔════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}║   HDFS Docker 集群管理工具             ║${NC}"
        echo -e "${BOLD}╚════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "  ${GREEN}1)${NC} 🚀 启动 HDFS 集群"
        echo -e "  ${YELLOW}2)${NC} 🛑 停止 HDFS 集群"
        echo -e "  ${CYAN}3)${NC} 🔄 重启 HDFS 集群"
        echo -e "  ${BLUE}4)${NC} 📊 查看集群状态"
        echo -e "  ${MAGENTA}5)${NC} 🧪 测试 HDFS 功能"
        echo -e "  ${CYAN}6)${NC} 📝 查看日志"
        echo -e "  ${YELLOW}7)${NC} 🧹 清理所有数据"
        echo -e "  ${BLUE}8)${NC} ⚙️  高级操作"
        echo -e "  ${RED}9)${NC} 📖 查看帮助"
        echo -e "  ${RED}0)${NC} 🚪 退出"
        echo ""
        read -p "请选择操作 [0-9]: " choice

        case $choice in
            1) start_hdfs ;;
            2) stop_hdfs ;;
            3) restart_hdfs ;;
            4) show_status ;;
            5) test_hdfs ;;
            6) show_logs ;;
            7) clean_all ;;
            8) advanced_menu ;;
            9) show_help ;;
            0)
                echo ""
                log_info "感谢使用! 再见 👋"
                echo ""
                exit 0
                ;;
            *)
                log_error "无效选择,请输入 0-9"
                ;;
        esac

        # 操作完成后暂停
        echo ""
        read -p "按 Enter 继续..." dummy
    done
}

# ==================== 帮助信息 ====================
show_help() {
    cat <<-EOF

${BOLD}HDFS Docker 集群管理工具${NC}

${CYAN}使用方式:${NC}
  交互模式: bash $0
  命令模式: bash $0 <命令>

${CYAN}可用命令:${NC}
  start       - 启动 HDFS 集群
  stop        - 停止 HDFS 集群
  restart     - 重启 HDFS 集群
  status      - 查看集群状态
  test        - 测试 HDFS 功能
  logs        - 查看日志
  clean       - 清理所有数据
  help        - 显示此帮助

${CYAN}示例:${NC}
  # 交互式启动
  bash $0

  # 直接启动集群
  bash $0 start

  # 查看状态
  bash $0 status

  # 测试功能
  bash $0 test

${CYAN}配置文件:${NC}
  • Docker Compose: $COMPOSE_FILE
  • Hadoop 配置:   $CONFIG_DIR/
  • 数据目录:      $DATA_DIR/
  • 操作日志:      $LOG_FILE

${CYAN}访问地址:${NC}
  • NameNode Web UI: http://localhost:9870
  • NameNode RPC:    hdfs://localhost:9000
  • DataNode Web UI: http://localhost:9864

${CYAN}常见问题:${NC}
  1. 容器启动失败?
     → 检查端口占用: sudo lsof -i :9000,9870,9864
     → 查看日志: sudo docker logs hdfs-namenode

  2. 权限问题?
     → 运行: sudo chmod -R 777 $DATA_DIR

  3. 连接失败?
     → 确认容器运行: bash $0 status
     → 等待服务就绪(约15-30秒)

${CYAN}相关文档:${NC}
  • 启动机制说明: $SCRIPT_DIR/HDFS_启动机制说明.md
  • 官方文档: https://hadoop.apache.org/docs/stable/

EOF
}

# ==================== 主程序入口 ====================
main() {
    # 初始化日志文件
    echo "=== HDFS Docker 管理日志 ===" > "$LOG_FILE"
    echo "时间: $(date)" >> "$LOG_FILE"
    echo "================================" >> "$LOG_FILE"

    # 如果有命令行参数,执行对应命令
    if [ $# -gt 0 ]; then
        case "$1" in
            start) start_hdfs ;;
            stop) stop_hdfs ;;
            restart) restart_hdfs ;;
            status) show_status ;;
            test) test_hdfs ;;
            logs) show_logs ;;
            clean) clean_all ;;
            help|--help|-h) show_help ;;
            *)
                log_error "未知命令: $1"
                show_help
                exit 1
                ;;
        esac
    else
        # 交互式菜单模式
        show_main_menu
    fi
}

# 执行主程序
main "$@"
