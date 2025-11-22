"""
SAGE Memory Backend 示例

展示如何使用不同的记忆后端（short_term, vdb, kv, graph）
"""

from sage.gateway.session.manager import SessionManager
from sage.gateway.storage.file_storage import FileStorage


def demo_short_term_memory():
    """演示短期记忆后端"""
    print("\n" + "=" * 50)
    print("Demo 1: Short-Term Memory Backend")
    print("=" * 50)
    
    storage = FileStorage(storage_path=".sage/sessions_short_term.json")
    manager = SessionManager(
        storage=storage,
        memory_backend="short_term",
        max_memory_dialogs=3  # 只保留最近3轮对话
    )
    
    session_id = manager.create_session()
    print(f"Created session: {session_id}")
    
    # 存储5轮对话
    dialogs = [
        ("你好", "您好！有什么可以帮您的吗？"),
        ("今天天气怎么样", "今天天气晴朗，温度适宜。"),
        ("明天呢", "明天预计多云，气温会略有下降。"),
        ("推荐穿什么衣服", "建议穿长袖外套，早晚温差较大。"),
        ("谢谢", "不客气，很高兴能帮到您！"),
    ]
    
    for i, (user_msg, assistant_msg) in enumerate(dialogs, 1):
        manager.store_dialog_to_memory(session_id, user_msg, assistant_msg)
        print(f"Stored dialog {i}: {user_msg}")
    
    # 检索历史（只会返回最近3轮）
    history = manager.retrieve_memory_history(session_id)
    print("\nRetrieved history (last 3 dialogs):")
    print(history)
    
    manager.delete(session_id)
    print(f"\nCleaned up session: {session_id}")


def demo_vdb_memory():
    """演示向量数据库记忆后端"""
    print("\n" + "=" * 50)
    print("Demo 2: Vector Database (VDB) Memory Backend")
    print("=" * 50)
    
    storage = FileStorage(storage_path=".sage/sessions_vdb.json")
    manager = SessionManager(
        storage=storage,
        memory_backend="vdb",
        memory_config={
            "embedding_model": "text-embedding-3-small",
            "embedding_dim": 1536,
            "backend_type": "faiss",
            "max_retrieve": 5
        }
    )
    
    session_id = manager.create_session()
    print(f"Created session: {session_id}")
    
    # 存储不同主题的对话
    dialogs = [
        ("Python如何读取文件", "使用 open() 函数配合 with 语句可以安全地读取文件。"),
        ("什么是机器学习", "机器学习是人工智能的一个分支，通过算法从数据中学习规律。"),
        ("如何写入文件到磁盘", "可以使用 open() 的写模式 'w' 或追加模式 'a' 写入文件。"),
    ]
    
    for user_msg, assistant_msg in dialogs:
        manager.store_dialog_to_memory(session_id, user_msg, assistant_msg)
        print(f"Stored: {user_msg}")
    
    # VDB 支持语义相似度检索
    history = manager.retrieve_memory_history(session_id)
    print("\nRetrieved history (semantic search):")
    print(history)
    
    manager.delete(session_id)
    print(f"\nCleaned up session: {session_id}")


def demo_kv_memory():
    """演示键值存储记忆后端"""
    print("\n" + "=" * 50)
    print("Demo 3: Key-Value (KV) Memory Backend")
    print("=" * 50)
    
    storage = FileStorage(storage_path=".sage/sessions_kv.json")
    manager = SessionManager(
        storage=storage,
        memory_backend="kv",
        memory_config={
            "default_index_type": "bm25s",
            "max_retrieve": 10
        }
    )
    
    session_id = manager.create_session()
    print(f"Created session: {session_id}")
    
    # 存储关键词密集的对话
    dialogs = [
        ("API key 在哪里配置", "API key 需要在 .env 文件中设置 OPENAI_API_KEY。"),
        ("如何测试 API 连接", "可以运行 test_api.py 脚本测试 API 连接状态。"),
        ("API 调用失败怎么办", "检查 API key 是否正确，以及网络连接是否正常。"),
    ]
    
    for user_msg, assistant_msg in dialogs:
        manager.store_dialog_to_memory(session_id, user_msg, assistant_msg)
        print(f"Stored: {user_msg}")
    
    # KV 支持关键词检索
    history = manager.retrieve_memory_history(session_id)
    print("\nRetrieved history (keyword search):")
    print(history)
    
    manager.delete(session_id)
    print(f"\nCleaned up session: {session_id}")


def demo_graph_memory():
    """演示图结构记忆后端"""
    print("\n" + "=" * 50)
    print("Demo 4: Graph Memory Backend")
    print("=" * 50)
    
    storage = FileStorage(storage_path=".sage/sessions_graph.json")
    manager = SessionManager(
        storage=storage,
        memory_backend="graph",
        memory_config={
            "max_depth": 2,
            "max_retrieve": 10
        }
    )
    
    session_id = manager.create_session()
    print(f"Created session: {session_id}")
    
    # 存储有关联关系的对话
    dialogs = [
        ("开始一个新项目", "好的，我们先创建项目结构。"),
        ("添加测试文件", "已添加测试目录和初始测试文件。"),
        ("运行测试", "测试全部通过！项目准备就绪。"),
    ]
    
    for user_msg, assistant_msg in dialogs:
        manager.store_dialog_to_memory(session_id, user_msg, assistant_msg)
        print(f"Stored: {user_msg}")
    
    # Graph 支持关系推理
    history = manager.retrieve_memory_history(session_id)
    print("\nRetrieved history (graph relationship):")
    print(history)
    
    manager.delete(session_id)
    print(f"\nCleaned up session: {session_id}")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 70)
    print(" " * 15 + "SAGE Memory Backend Demo")
    print("=" * 70)
    
    # Demo 1: Short-Term Memory
    demo_short_term_memory()
    
    # Demo 2: VDB Memory (需要 OPENAI_API_KEY)
    try:
        demo_vdb_memory()
    except Exception as e:
        print(f"\nVDB demo skipped: {e}")
        print("(Requires OPENAI_API_KEY environment variable)")
    
    # Demo 3: KV Memory
    try:
        demo_kv_memory()
    except Exception as e:
        print(f"\nKV demo skipped: {e}")
    
    # Demo 4: Graph Memory
    try:
        demo_graph_memory()
    except Exception as e:
        print(f"\nGraph demo skipped: {e}")
    
    print("\n" + "=" * 70)
    print(" " * 20 + "All demos completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
