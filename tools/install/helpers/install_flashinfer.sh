#!/bin/bash
# FlashInfer 安装辅助脚本
# FlashInfer 提供高性能的 vLLM 采样实现

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color
DIM='\033[2m'

# 使用环境变量或默认值（与其他安装脚本保持一致）
PYTHON_CMD="${PYTHON_CMD:-python3}"
PIP_CMD="${PIP_CMD:-pip3}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  FlashInfer 安装器 - 高性能 vLLM 采样加速${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查是否已安装
if $PYTHON_CMD -c "import flashinfer" 2>/dev/null; then
    FLASHINFER_VERSION=$($PYTHON_CMD -c "import flashinfer; print(flashinfer.__version__)" 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✅ FlashInfer $FLASHINFER_VERSION 已安装${NC}"
    exit 0
fi

# 检查 CUDA 版本
if ! $PYTHON_CMD -c "import torch" 2>/dev/null; then
    echo -e "${RED}❌ PyTorch 未安装，请先安装 PyTorch${NC}"
    exit 1
fi

CUDA_VERSION=$($PYTHON_CMD -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "")
if [ -z "$CUDA_VERSION" ]; then
    echo -e "${RED}❌ 未检测到 CUDA，FlashInfer 需要 CUDA 支持${NC}"
    exit 1
fi

CUDA_MAJOR=$(echo "$CUDA_VERSION" | cut -d. -f1)
echo -e "${DIM}检测到 CUDA 版本: $CUDA_VERSION${NC}"

# 获取 PyTorch 版本
TORCH_VERSION=$($PYTHON_CMD -c "import torch; print('.'.join(torch.__version__.split('.')[:2]))" 2>/dev/null || echo "")
TORCH_MAJOR_MINOR=$(echo "$TORCH_VERSION" | cut -d. -f1-2)
echo -e "${DIM}检测到 PyTorch 版本: $TORCH_VERSION${NC}"

# 确定 wheel 源
# FlashInfer wheel 源格式: https://flashinfer.ai/whl/cu{major}{minor}/torch{version}/
# 例如: cu124 对应 CUDA 12.4+, torch2.6 对应 PyTorch 2.6.x
# 确定 CUDA wheel tag - 优先使用匹配的 CUDA 版本
CUDA_MINOR=$(echo "$CUDA_VERSION" | cut -d. -f2)
if [ "$CUDA_MAJOR" -eq 12 ]; then
    if [ "$CUDA_MINOR" -ge 6 ]; then
        CUDA_TAG="cu126"
    elif [ "$CUDA_MINOR" -ge 4 ]; then
        CUDA_TAG="cu124"
    else
        CUDA_TAG="cu121"
    fi
elif [ "$CUDA_MAJOR" -ge 11 ]; then
    CUDA_TAG="cu118"
else
    echo -e "${RED}❌ CUDA $CUDA_VERSION 版本过低，FlashInfer 需要 CUDA >= 11.8${NC}"
    exit 1
fi

# 检测 PyTorch 版本并选择对应的 wheel
# FlashInfer 目前支持: torch2.4, torch2.5, torch2.6 (截至 2025-11)
case "$TORCH_MAJOR_MINOR" in
    "2.4")
        TORCH_TAG="torch2.4"
        ;;
    "2.5")
        TORCH_TAG="torch2.5"
        ;;
    "2.6")
        TORCH_TAG="torch2.6"
        ;;
    "2.7"|"2.8"|"2.9")
        # PyTorch 2.7+ 与 FlashInfer torch2.6 wheel 存在 ABI 不兼容
        echo -e "${YELLOW}⚠️  PyTorch $TORCH_VERSION 较新，FlashInfer 尚未发布兼容版本${NC}"
        echo -e "${DIM}   FlashInfer 当前最高支持 PyTorch 2.6.x${NC}"
        echo -e "${DIM}   vLLM 将使用 PyTorch 原生采样（性能略有下降但功能正常）${NC}"
        echo ""
        echo -e "${YELLOW}解决方案:${NC}"
        echo -e "  1. 等待 FlashInfer 发布支持 PyTorch $TORCH_VERSION 的版本"
        echo -e "  2. 或降级 PyTorch: pip install torch==2.6.* torchvision torchaudio"
        exit 0  # 正常退出，不是错误
        ;;
    *)
        echo -e "${YELLOW}⚠️  PyTorch $TORCH_VERSION 版本可能不受支持${NC}"
        echo -e "${DIM}   FlashInfer 支持 PyTorch 2.4-2.6${NC}"
        exit 0
        ;;
esac

WHEEL_INDEX="https://flashinfer.ai/whl/${CUDA_TAG}/${TORCH_TAG}/"

echo -e "${BLUE}正在从 $WHEEL_INDEX 安装 FlashInfer...${NC}"
echo ""

# 安装 FlashInfer
if $PIP_CMD install flashinfer-python -i "$WHEEL_INDEX"; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ FlashInfer 安装成功！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 验证安装
    FLASHINFER_VERSION=$($PYTHON_CMD -c "import flashinfer; print(flashinfer.__version__)" 2>/dev/null || echo "unknown")
    echo -e "${DIM}已安装版本: $FLASHINFER_VERSION${NC}"
else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ FlashInfer 安装失败${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}可能的原因:${NC}"
    echo -e "  1. CUDA 版本与 PyTorch CUDA 版本不匹配"
    echo -e "  2. 网络问题无法访问 flashinfer.ai"
    echo -e "  3. 系统不支持预编译的 wheel"
    echo ""
    echo -e "${DIM}手动安装命令:${NC}"
    echo -e "  $PIP_CMD install flashinfer-python -i $WHEEL_INDEX"
    exit 1
fi
