"""
SAGE Memory Backend 示例

展示如何直接使用重构后的 neuromem 服务
（SessionManager 的记忆后端 API 正在适配重构后的 neuromem）
"""

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.partitional.fifo_queue_service import (
    FIFOQueueService,
)


def demo_short_term_memory():
    """演示短期记忆后端 - 使用重构后的 FIFOQueueService"""
    print("\n" + "=" * 50)
    print("Demo 1: Short-Term Memory Backend (FIFO Queue)")
    print("=" * 50)

    # 创建 UnifiedCollection
    collection = UnifiedCollection(name="short_term_memory")

    # 创建 FIFO 队列服务，只保留最近3条记录
    service = FIFOQueueService(collection, config={"max_size": 3})

    print("Created FIFO queue service with max_size=3")

    # 存储5轮对话
    dialogs = [
        ("你好", "您好！有什么可以帮您的吗？"),
        ("今天天气怎么样", "今天天气晴朗，温度适宜。"),
        ("明天呢", "明天预计多云，气温会略有下降。"),
        ("推荐穿什么衣服", "建议穿长袖外套，早晚温差较大。"),
        ("谢谢", "不客气，很高兴能帮到您！"),
    ]

    for i, (user_msg, assistant_msg) in enumerate(dialogs, 1):
        # 插入用户消息和助手回复
        dialog_text = f"User: {user_msg}\nAssistant: {assistant_msg}"
        service.insert(dialog_text, metadata={"round": i})
        print(f"Stored dialog {i}: {user_msg}")

    # 检索历史（只会返回最近3轮，因为 max_size=3）
    results = service.retrieve("", top_k=10)  # 尝试取10条，但只会返回最近3条
    print(f"\nRetrieved {len(results)} dialogs (should be 3 due to FIFO limit):")
    for i, result in enumerate(results, 1):
        # result 是字典，包含 'id', 'text', 'metadata', 'score' 等字段
        text = result.get("text", "")
        entry_preview = text[:50] + "..." if len(text) > 50 else text
        print(f"  {i}. {entry_preview}")

    print(f"\n✅ Demo completed: FIFO queue correctly limited to {len(results)} items")


def demo_vdb_memory():
    """演示向量数据库记忆后端 - 暂时跳过，等待 SessionManager 适配"""
    print("\n" + "=" * 50)
    print("Demo 2: Vector Database (VDB) Memory Backend")
    print("=" * 50)
    print("⚠️  Skipped: SessionManager VDB backend needs API update.")
    print("    See neuromem services for direct usage examples.")


def demo_kv_memory():
    """演示键值存储记忆后端 - 暂时跳过，等待 SessionManager 适配"""
    print("\n" + "=" * 50)
    print("Demo 3: Key-Value (KV) Memory Backend")
    print("=" * 50)
    print("⚠️  Skipped: SessionManager KV backend needs API update.")
    print("    See neuromem services for direct usage examples.")


def demo_graph_memory():
    """演示图记忆后端 - 暂时跳过，等待 SessionManager 适配"""
    print("\n" + "=" * 50)
    print("Demo 4: Graph Memory Backend")
    print("=" * 50)
    print("⚠️  Skipped: SessionManager Graph backend needs API update.")
    print("    See neuromem services for direct usage examples.")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 70)
    print(" " * 10 + "SAGE Neuromem Services Demo (Refactored)")
    print("=" * 70)
    print("\n📝 Note: This demo uses the refactored neuromem services directly.")
    print("   SessionManager memory backend API is being updated to support")
    print("   the new neuromem architecture.")

    # Demo 1: Short-Term Memory (FIFO Queue)
    try:
        demo_short_term_memory()
    except Exception as e:
        print(f"\n❌ FIFO demo failed: {e}")
        import traceback

        traceback.print_exc()

    # Demo 2-4: Skipped until SessionManager API is updated
    demo_vdb_memory()
    demo_kv_memory()
    demo_graph_memory()

    print("\n" + "=" * 70)
    print(" " * 20 + "Demo completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
