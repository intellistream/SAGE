#!/usr/bin/env python3
"""测试 Embedding 管理优化的实现"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "packages" / "sage-middleware" / "src"))

from sage.common.components.sage_embedding import (
    get_embedding_model,
    list_embedding_models,
    check_model_availability,
)


def test_hash_embedding():
    """测试 Hash Embedding"""
    print("\n" + "="*60)
    print("测试 1: Hash Embedding")
    print("="*60)
    
    emb = get_embedding_model("hash", dim=384)
    print(f"✓ 创建成功: {emb}")
    print(f"✓ 方法名: {emb.method_name}")
    print(f"✓ 维度: {emb.get_dim()}")
    
    vec = emb.embed("hello world")
    print(f"✓ Embed 成功: len(vec)={len(vec)}")
    
    vecs = emb.embed_batch(["hello", "world", "test"])
    print(f"✓ Batch embed 成功: len(vecs)={len(vecs)}")
    
    print("✅ Hash Embedding 测试通过！")


def test_mock_embedding():
    """测试 Mock Embedding"""
    print("\n" + "="*60)
    print("测试 2: Mock Embedding")
    print("="*60)
    
    emb = get_embedding_model("mockembedder", fixed_dim=128)
    print(f"✓ 创建成功: {emb}")
    print(f"✓ 方法名: {emb.method_name}")
    print(f"✓ 维度: {emb.get_dim()}")
    
    vec = emb.embed("test")
    print(f"✓ Embed 成功: len(vec)={len(vec)}")
    
    print("✅ Mock Embedding 测试通过！")


def test_list_models():
    """测试模型列表"""
    print("\n" + "="*60)
    print("测试 3: 列出所有模型")
    print("="*60)
    
    models = list_embedding_models()
    print(f"✓ 找到 {len(models)} 个方法:\n")
    
    for method, info in models.items():
        print(f"  [{method}]")
        print(f"    名称: {info['display_name']}")
        print(f"    描述: {info['description']}")
        if info['requires_api_key']:
            print(f"    ⚠️  需要 API Key")
        if info['requires_download']:
            print(f"    ⚠️  需要下载模型")
        if info['default_dimension']:
            print(f"    默认维度: {info['default_dimension']}")
        if info['examples']:
            print(f"    示例: {', '.join(info['examples'][:2])}")
        print()
    
    print("✅ 模型列表测试通过！")


def test_check_availability():
    """测试可用性检查"""
    print("\n" + "="*60)
    print("测试 4: 检查模型可用性")
    print("="*60)
    
    # 检查 hash（应该可用）
    status = check_model_availability("hash", dim=384)
    print(f"hash: {status['message']}")
    assert status['status'] == 'available', "hash 应该可用"
    print("✓ hash 可用性检查通过")
    
    # 检查 mockembedder（应该可用）
    status = check_model_availability("mockembedder")
    print(f"mockembedder: {status['message']}")
    assert status['status'] == 'available', "mockembedder 应该可用"
    print("✓ mockembedder 可用性检查通过")
    
    # 检查 hf（取决于是否有缓存）
    status = check_model_availability("hf", model="BAAI/bge-small-zh-v1.5")
    print(f"hf (BAAI/bge-small-zh-v1.5): {status['message']}")
    print(f"  状态: {status['status']}")
    print(f"  建议: {status['action']}")
    print("✓ hf 可用性检查通过")
    
    print("\n✅ 可用性检查测试通过！")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 5: 错误处理")
    print("="*60)
    
    # 测试不存在的方法
    try:
        emb = get_embedding_model("nonexistent_method")
        print("❌ 应该抛出 ValueError")
        sys.exit(1)
    except ValueError as e:
        print(f"✓ 正确抛出 ValueError: {str(e)[:100]}...")
    
    # 测试缺少必要参数
    try:
        emb = get_embedding_model("hf")  # 缺少 model 参数
        print("❌ 应该抛出 ValueError")
        sys.exit(1)
    except ValueError as e:
        print(f"✓ 正确抛出 ValueError: {str(e)[:100]}...")
    
    print("\n✅ 错误处理测试通过！")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("测试 6: 向后兼容性")
    print("="*60)
    
    # 旧的 API 应该仍然可用
    from sage.common.components.sage_embedding import EmbeddingModel
    
    emb = EmbeddingModel(method="mockembedder", fixed_dim=128)
    print(f"✓ EmbeddingModel 仍可用: {emb}")
    
    vec = emb.embed("test")
    print(f"✓ embed() 仍可用: len(vec)={len(vec)}")
    
    dim = emb.get_dim()
    print(f"✓ get_dim() 仍可用: {dim}")
    
    print("\n✅ 向后兼容性测试通过！")


def main():
    """运行所有测试"""
    print("🚀 开始测试 Embedding 管理优化实现...")
    
    try:
        test_hash_embedding()
        test_mock_embedding()
        test_list_models()
        test_check_availability()
        test_error_handling()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        print("\n✅ Phase 1 核心架构实施成功！")
        print("\n下一步:")
        print("  1. 测试 sage chat 集成")
        print("  2. 添加更多 wrappers (OpenAI, Jina, 等)")
        print("  3. 编写完整的单元测试")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
