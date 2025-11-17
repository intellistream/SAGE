#!/bin/bash
# SAGE 安装检查点管理模块
# 实现安装进度保存、断点续传、自动回滚功能

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 检查点文件路径
CHECKPOINT_DIR=".sage/checkpoints"
CHECKPOINT_FILE="$CHECKPOINT_DIR/install_progress.json"
BACKUP_DIR="$CHECKPOINT_DIR/backups"
ROLLBACK_SCRIPT="$CHECKPOINT_DIR/rollback.sh"

# 安装阶段定义
declare -a INSTALL_PHASES=(
    "environment_setup"
    "submodule_sync"
    "python_deps"
    "sage_packages"
    "vllm_install"
    "verification"
    "cleanup"
)

# 初始化检查点系统
init_checkpoint_system() {
    mkdir -p "$CHECKPOINT_DIR" "$BACKUP_DIR"

    # 如果检查点文件不存在，创建初始状态
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        cat > "$CHECKPOINT_FILE" << EOF
{
    "install_id": "$(date +%Y%m%d_%H%M%S)",
    "start_time": "$(date -Iseconds)",
    "current_phase": "environment_setup",
    "completed_phases": [],
    "failed_phases": [],
    "install_mode": "",
    "install_vllm": false,
    "environment_name": "",
    "python_path": "",
    "backup_created": false,
    "can_rollback": false
}
EOF
    fi

    echo -e "${DIM}📋 检查点系统已初始化${NC}"
}

# 读取检查点状态
read_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        cat "$CHECKPOINT_FILE"
    else
        echo "{}"
    fi
}

# 更新检查点状态
update_checkpoint() {
    local phase="$1"
    local status="$2"  # "started", "completed", "failed"
    local additional_data="$3"

    local current_data=$(read_checkpoint)
    local install_id=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('install_id', 'unknown'))" 2>/dev/null || echo "unknown")

    # 使用 Python 更新 JSON（更可靠）
    python3 << EOF
import json
import sys
from datetime import datetime

try:
    with open("$CHECKPOINT_FILE", "r") as f:
        data = json.load(f)
except:
    data = {
        "install_id": "$install_id",
        "start_time": datetime.now().isoformat(),
        "current_phase": "environment_setup",
        "completed_phases": [],
        "failed_phases": [],
        "install_mode": "",
        "install_vllm": False,
        "environment_name": "",
        "python_path": "",
        "backup_created": False,
        "can_rollback": False
    }

# 更新状态
data["current_phase"] = "$phase"
data["last_update"] = datetime.now().isoformat()

if "$status" == "completed":
    if "$phase" not in data["completed_phases"]:
        data["completed_phases"].append("$phase")
    # 从失败列表中移除（如果存在）
    if "$phase" in data["failed_phases"]:
        data["failed_phases"].remove("$phase")
elif "$status" == "failed":
    if "$phase" not in data["failed_phases"]:
        data["failed_phases"].append("$phase")

# 添加额外数据
if "$additional_data":
    try:
        extra = json.loads('$additional_data')
        data.update(extra)
    except:
        pass

with open("$CHECKPOINT_FILE", "w") as f:
    json.dump(data, f, indent=2)

print(f"Checkpoint updated: {data['current_phase']} -> {data}")
EOF

    echo -e "${DIM}📝 检查点已更新: $phase -> $status${NC}"
}

# 检查是否可以恢复安装
can_resume_install() {
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        return 1
    fi

    local current_data=$(read_checkpoint)
    local completed_count=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('completed_phases', [])))" 2>/dev/null || echo "0")

    # 如果有已完成的阶段，可以恢复
    [ "$completed_count" -gt 0 ]
}

# 显示恢复选项
show_resume_options() {
    if ! can_resume_install; then
        return 1
    fi

    echo -e "${BLUE}${BOLD}🔄 检测到未完成的安装${NC}"
    echo ""

    local current_data=$(read_checkpoint)
    local install_id=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('install_id', 'unknown'))" 2>/dev/null)
    local current_phase=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('current_phase', 'unknown'))" 2>/dev/null)
    local completed_phases=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(', '.join(data.get('completed_phases', [])))" 2>/dev/null)

    echo -e "${DIM}安装 ID: $install_id${NC}"
    echo -e "${DIM}当前阶段: $current_phase${NC}"
    echo -e "${DIM}已完成阶段: $completed_phases${NC}"
    echo ""

    echo -e "${YELLOW}选择操作:${NC}"
    echo -e "  ${GREEN}1.${NC} 从断点继续安装 (推荐)"
    echo -e "  ${YELLOW}2.${NC} 重新开始安装"
    echo -e "  ${RED}3.${NC} 回滚并退出"
    echo ""

    read -p "请输入选择 [1-3]: " -r resume_choice

    case "$resume_choice" in
        1|"")
            return 0  # 继续
            ;;
        2)
            reset_checkpoint
            return 0  # 重新开始
            ;;
        3)
            if can_rollback; then
                perform_rollback
            else
                echo -e "${YELLOW}⚠️  无法回滚，将清理安装状态${NC}"
                reset_checkpoint
            fi
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择，退出安装${NC}"
            exit 1
            ;;
    esac
}

# 重置检查点
reset_checkpoint() {
    echo -e "${BLUE}🔄 重置安装状态...${NC}"
    rm -f "$CHECKPOINT_FILE"
    init_checkpoint_system
}

# 创建环境备份
create_environment_backup() {
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"

    echo -e "${BLUE}💾 创建环境备份...${NC}"

    mkdir -p "$backup_path"

    # 备份 pip 包列表
    if command -v pip &> /dev/null; then
        pip list --format=freeze > "$backup_path/pip_packages.txt" 2>/dev/null
        echo -e "${DIM}   已备份 pip 包列表${NC}"
    fi

    # 备份 conda 环境（如果在 conda 环境中）
    if [ -n "$CONDA_DEFAULT_ENV" ] && command -v conda &> /dev/null; then
        conda list --export > "$backup_path/conda_packages.txt" 2>/dev/null
        conda env export > "$backup_path/conda_env.yml" 2>/dev/null
        echo -e "${DIM}   已备份 conda 环境${NC}"
    fi

    # 创建回滚脚本
    cat > "$ROLLBACK_SCRIPT" << EOF
#!/bin/bash
# SAGE 自动生成的回滚脚本
# 创建时间: $(date)

set -e

echo "开始回滚 SAGE 安装..."

# 卸载 SAGE 相关包
echo "卸载 SAGE 包..."
pip uninstall -y sage-common sage-kernel sage-libs sage-middleware sage-benchmark sage 2>/dev/null || true

# 卸载 VLLM（如果安装了）
if pip show vllm &>/dev/null; then
    echo "卸载 VLLM..."
    pip uninstall -y vllm 2>/dev/null || true
fi

# 恢复备份的包环境（可选）
if [ -f "$backup_path/pip_packages.txt" ] && [ "\$1" = "--restore-packages" ]; then
    echo "恢复原始包环境..."
    pip install -r "$backup_path/pip_packages.txt"
fi

echo "回滚完成！"
EOF

    chmod +x "$ROLLBACK_SCRIPT"

    # 更新检查点状态
    update_checkpoint "backup" "completed" '{"backup_created": true, "can_rollback": true, "backup_path": "'$backup_path'"}'

    echo -e "${GREEN}   ✅ 环境备份已创建: $backup_path${NC}"
}

# 检查是否可以回滚
can_rollback() {
    [ -f "$ROLLBACK_SCRIPT" ]
}

# 执行回滚
perform_rollback() {
    if [ ! -f "$ROLLBACK_SCRIPT" ]; then
        echo -e "${RED}❌ 未找到回滚脚本${NC}"
        return 1
    fi

    echo -e "${YELLOW}${BOLD}🔄 开始回滚安装...${NC}"
    echo ""

    # 询问是否恢复包环境
    echo -e "${YELLOW}是否恢复到安装前的包环境？${NC} [${RED}y${NC}/${GREEN}N${NC}]"
    read -p "请输入选择: " -r restore_choice

    if [[ "$restore_choice" =~ ^[Yy]$ ]]; then
        bash "$ROLLBACK_SCRIPT" --restore-packages
    else
        bash "$ROLLBACK_SCRIPT"
    fi

    # 清理检查点文件
    rm -f "$CHECKPOINT_FILE"

    echo -e "${GREEN}✅ 回滚完成${NC}"
}

# 获取下一个安装阶段
get_next_phase() {
    local current_data=$(read_checkpoint)
    local completed_phases=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(' '.join(data.get('completed_phases', [])))" 2>/dev/null || echo "")

    for phase in "${INSTALL_PHASES[@]}"; do
        if [[ ! "$completed_phases" =~ $phase ]]; then
            echo "$phase"
            return 0
        fi
    done

    echo "completed"
}

# 标记阶段开始
mark_phase_start() {
    local phase="$1"
    echo -e "${BLUE}▶️  开始阶段: $phase${NC}"
    update_checkpoint "$phase" "started"
}

# 标记阶段完成
mark_phase_complete() {
    local phase="$1"
    echo -e "${GREEN}✅ 完成阶段: $phase${NC}"
    update_checkpoint "$phase" "completed"
}

# 标记阶段失败
mark_phase_failed() {
    local phase="$1"
    local error_msg="$2"
    echo -e "${RED}❌ 阶段失败: $phase${NC}"
    if [ -n "$error_msg" ]; then
        echo -e "${DIM}错误信息: $error_msg${NC}"
    fi
    update_checkpoint "$phase" "failed" '{"last_error": "'$(echo "$error_msg" | sed 's/"/\\"/g')'"}'
}

# 显示安装进度
show_install_progress() {
    local current_data=$(read_checkpoint)
    local completed_phases=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('completed_phases', []))" 2>/dev/null || echo "[]")
    local failed_phases=$(echo "$current_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('failed_phases', []))" 2>/dev/null || echo "[]")

    echo -e "${BLUE}📊 安装进度${NC}"

    local completed_count=$(echo "$completed_phases" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    local total_phases=${#INSTALL_PHASES[@]}
    local progress=$((completed_count * 100 / total_phases))

    echo -e "${DIM}   进度: $completed_count/$total_phases ($progress%)${NC}"

    for phase in "${INSTALL_PHASES[@]}"; do
        if echo "$completed_phases" | python3 -c "import sys, json; phases=json.load(sys.stdin); exit(0 if '$phase' in phases else 1)" 2>/dev/null; then
            echo -e "   ${GREEN}✅ $phase${NC}"
        elif echo "$failed_phases" | python3 -c "import sys, json; phases=json.load(sys.stdin); exit(0 if '$phase' in phases else 1)" 2>/dev/null; then
            echo -e "   ${RED}❌ $phase${NC}"
        else
            echo -e "   ${DIM}⏸️  $phase${NC}"
        fi
    done
}

# 清理检查点系统
cleanup_checkpoint_system() {
    local keep_backups="${1:-false}"

    if [ "$keep_backups" = "false" ]; then
        rm -rf "$CHECKPOINT_DIR"
        echo -e "${DIM}🧹 检查点系统已清理${NC}"
    else
        rm -f "$CHECKPOINT_FILE" "$ROLLBACK_SCRIPT"
        echo -e "${DIM}🧹 检查点文件已清理，备份保留${NC}"
    fi
}
