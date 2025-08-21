#!/bin/bash

# SAGE ChromaDB 集成快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$SCRIPT_DIR"
CONFIG_DIR="$(dirname "$EXAMPLES_DIR")/config"

echo "=== SAGE ChromaDB 集成快速启动 ==="
echo ""

# 检查 ChromaDB 是否已安装
echo "检查依赖..."
if ! python -c "import chromadb" 2>/dev/null; then
    echo "❌ ChromaDB 未安装"
    echo ""
    echo "安装 ChromaDB:"
    echo "  pip install chromadb"
    echo ""
    echo "或者安装完整版本:"
    echo "  pip install 'chromadb[all]'"
    echo ""
    read -p "是否现在安装 ChromaDB? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在安装 ChromaDB..."
        pip install chromadb
        echo "✓ ChromaDB 安装完成"
    else
        echo "请手动安装 ChromaDB 后重新运行"
        exit 1
    fi
else
    echo "✓ ChromaDB 已安装"
fi

# 检查其他依赖
echo "检查 SAGE 依赖..."
missing_deps=()

if ! python -c "import faiss" 2>/dev/null; then
    missing_deps+=("faiss-cpu")
fi

if ! python -c "import openai" 2>/dev/null; then
    missing_deps+=("openai")
fi

if ! python -c "import sentence_transformers" 2>/dev/null; then
    missing_deps+=("sentence-transformers")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "❌ 缺少依赖: ${missing_deps[*]}"
    echo "请安装缺少的依赖:"
    for dep in "${missing_deps[@]}"; do
        echo "  pip install $dep"
    done
    exit 1
else
    echo "✓ 所有依赖已满足"
fi

echo ""

# 选择测试模式
echo "选择测试模式:"
echo "1. ChromaDB 基本功能测试"
echo "2. ChromaDB vs FAISS 性能对比"
echo "3. 运行 RAG 问答系统 (ChromaDB)"
echo "4. 运行 RAG 问答系统 (FAISS)"
echo "5. 创建测试配置文件"

read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "=== 运行 ChromaDB 基本功能测试 ==="
        cd "$EXAMPLES_DIR"
        python test_chroma_integration.py
        ;;
    2)
        echo ""
        echo "=== 运行性能对比测试 ==="
        cd "$EXAMPLES_DIR"
        python test_chroma_integration.py
        ;;
    3)
        echo ""
        echo "=== 运行 RAG 问答系统 (ChromaDB) ==="
        
        # 检查配置文件
        if [ ! -f "$CONFIG_DIR/config_multi_backend.yaml" ]; then
            echo "❌ 配置文件不存在: $CONFIG_DIR/config_multi_backend.yaml"
            echo "请先运行选项 5 创建配置文件"
            exit 1
        fi
        
        cd "$EXAMPLES_DIR"
        SAGE_CONFIG=config_multi_backend.yaml python qa_openai.py
        ;;
    4)
        echo ""
        echo "=== 运行 RAG 问答系统 (FAISS) ==="
        
        # 检查配置文件
        if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
            echo "❌ 配置文件不存在: $CONFIG_DIR/config.yaml"
            exit 1
        fi
        
        cd "$EXAMPLES_DIR"
        python qa_openai.py
        ;;
    5)
        echo ""
        echo "=== 创建测试配置文件 ==="
        
        # 创建简单的 ChromaDB 测试配置
        mkdir -p "$CONFIG_DIR"
        
        cat > "$CONFIG_DIR/config_chroma_test.yaml" << 'EOF'
# ChromaDB 测试配置
source:
  data_path: "../data/queries.jsonl"

retriever:
  backend: "chroma"
  dimension: 128
  top_k: 3
  
  chroma:
    persistence_path: "./test_chroma_db"
    collection_name: "test_documents"
    use_embedding_query: true
    metadata:
      "hnsw:space": "cosine"
  
  embedding:
    method: "mockembedder"
    model_config:
      fixed_dim: 128

promptor:
  template: |
    基于以下检索到的相关文档，回答用户问题：
    
    相关文档：
    {retrieved_documents}
    
    用户问题：{query}
    
    请提供准确、有用的回答：

generator:
  vllm:
    model_name: "gpt-3.5-turbo"
    api_key: "${OPENAI_API_KEY}"
    max_tokens: 500
    temperature: 0.7

sink:
  enable_log: true
EOF

        echo "✓ 创建 ChromaDB 测试配置: $CONFIG_DIR/config_chroma_test.yaml"
        
        # 创建测试查询文件
        mkdir -p "$(dirname "$CONFIG_DIR")/data"
        cat > "$(dirname "$CONFIG_DIR")/data/queries.jsonl" << 'EOF'
{"query": "什么是ChromaDB？"}
{"query": "如何使用向量数据库进行文档检索？"}
{"query": "RAG系统的工作原理是什么？"}
EOF

        echo "✓ 创建测试查询文件: $(dirname "$CONFIG_DIR")/data/queries.jsonl"
        echo ""
        echo "配置文件创建完成！现在可以运行其他测试选项。"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "=== 测试完成 ==="

# 显示有用的信息
echo ""
echo "有用的信息："
echo "- ChromaDB 数据库文件位置: ./test_chroma_db/"
echo "- 配置文件位置: $CONFIG_DIR/"
echo "- 文档和示例: $EXAMPLES_DIR/CHROMADB_DEPLOYMENT_GUIDE.md"
echo ""
echo "环境变量设置："
echo "  export OPENAI_API_KEY='your-api-key'"
echo "  export SAGE_CONFIG='config_chroma_test.yaml'"
echo ""
echo "手动运行命令："
echo "  cd $EXAMPLES_DIR"
echo "  python test_chroma_integration.py"
echo "  SAGE_CONFIG=config_chroma_test.yaml python qa_openai.py"
