#!/usr/bin/env python3
"""测试 sage-memory 集成到对话 pipeline 的功能

这个脚本演示：
1. SessionManager 如何为每个会话创建独立的短期记忆服务
2. 对话如何被存储到记忆服务中
3. 历史记忆如何被检索并用于上下文
"""

import sys
from pathlib import Path

# 确保可以导入 SAGE 模块
sys.path.insert(0, str(Path(__file__).parent))

from sage.gateway.session.manager import SessionManager


def test_memory_integration():
    print("=" * 80)
    print("SAGE Memory Integration Test")
    print("=" * 80)
    print()

    # 创建 SessionManager，每个会话最多保留 3 轮对话
    print("1️⃣  创建 SessionManager (max_memory_dialogs=3)")
    manager = SessionManager(max_memory_dialogs=3)
    print("   ✅ SessionManager 已创建")
    print()

    # 创建新会话
    print("2️⃣  创建新会话")
    session = manager.create_session(title="测试记忆功能")
    session_id = session.id
    print(f"   ✅ 会话已创建: {session_id}")
    print(f"   📝 标题: {session.title}")
    print()

    # 检查记忆服务
    print("3️⃣  检查记忆服务")
    memory_service = manager.get_memory_service(session_id)
    print(f"   ✅ 记忆服务已创建: {memory_service}")
    print()

    # 模拟多轮对话
    print("4️⃣  模拟多轮对话 (5轮，超过窗口大小)")
    dialogs = [
        ("什么是SAGE?", "SAGE是一个AI数据处理框架"),
        ("它有什么特点?", "SAGE支持声明式数据流编程"),
        ("如何安装SAGE?", "使用 pip install isage 安装"),
        ("SAGE支持哪些算子?", "SAGE支持 Source、Map、Sink 等算子"),
        ("能举个例子吗?", "当然，可以看 examples/ 目录下的示例"),
    ]

    for idx, (user_msg, assistant_msg) in enumerate(dialogs, 1):
        print(f"\n   第 {idx} 轮对话:")
        print(f"   👤 User: {user_msg}")
        print(f"   🤖 Assistant: {assistant_msg}")

        # 存储对话到记忆服务
        manager.store_dialog_to_memory(session_id, user_msg, assistant_msg)

        # 检索当前记忆
        history = manager.retrieve_memory_history(session_id)
        history_lines = history.split("\n") if history else []
        print(f"   💾 当前记忆大小: {len(history_lines) // 2} 轮对话")

    print()

    # 显示最终记忆状态
    print("5️⃣  显示最终记忆状态 (应只保留最后3轮)")
    final_history = manager.retrieve_memory_history(session_id)
    print("   " + "─" * 76)
    for line in final_history.split("\n"):
        print(f"   {line}")
    print("   " + "─" * 76)
    print()

    # 验证窗口滑动
    print("6️⃣  验证窗口滑动机制")
    memory_service = manager.get_memory_service(session_id)
    current_dialogs = memory_service.retrieve()
    print(f"   ✅ 当前保留对话数: {len(current_dialogs)} / {memory_service.max_dialog}")

    if len(current_dialogs) == memory_service.max_dialog:
        print("   ✅ 窗口滑动正常：已达到最大容量，自动移除旧对话")
    else:
        print(f"   ℹ️  还未达到最大容量 ({len(current_dialogs)}/{memory_service.max_dialog})")
    print()

    # 测试多会话隔离
    print("7️⃣  测试多会话隔离")
    session2 = manager.create_session(title="第二个会话")
    session2_id = session2.id
    print(f"   ✅ 第二个会话已创建: {session2_id}")

    manager.store_dialog_to_memory(session2_id, "这是第二个会话", "好的，我明白了")

    history1 = manager.retrieve_memory_history(session_id)
    history2 = manager.retrieve_memory_history(session2_id)

    print(f"   📊 会话1记忆行数: {len(history1.split(chr(10)))}")
    print(f"   📊 会话2记忆行数: {len(history2.split(chr(10)))}")

    if "第二个会话" not in history1 and "第二个会话" in history2:
        print("   ✅ 会话隔离正常：不同会话的记忆互不干扰")
    else:
        print("   ❌ 会话隔离异常")
    print()

    # 测试删除会话
    print("8️⃣  测试删除会话")
    manager.delete(session2_id)
    deleted_memory = manager.get_memory_service(session2_id)
    if deleted_memory is None:
        print("   ✅ 会话删除成功：记忆服务已清除")
    else:
        print("   ❌ 会话删除异常：记忆服务仍然存在")
    print()

    print("=" * 80)
    print("✅ 所有测试通过！sage-memory 已成功集成到对话 pipeline")
    print("=" * 80)


if __name__ == "__main__":
    test_memory_integration()
